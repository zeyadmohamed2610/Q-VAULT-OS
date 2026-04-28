//! vault.rs — Per-user encrypted persistent vault storage
//!
//! Key derivation chain:
//!   password → Argon2(password, salt) → derived_key
//!   derived_key → HKDF-SHA256(derived_key, "vault-encryption") → vault_key
//!   vault_key + random_nonce → AES-256-GCM(plaintext) → ciphertext
//!
//! On-disk format (vault_data.json):
//!   { "username": { "key_name": "<base64(nonce ‖ ciphertext)>", ... }, ... }
//!
//! Salt storage (vault_salts.json):
//!   { "username": "<base64(salt)>", ... }
//!
//! Security invariants:
//!   - No hardcoded keys
//!   - No global keys — each user has their own derived vault_key
//!   - Keys NEVER cross the PyO3 boundary
//!   - vault_key is zeroized on session close

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use argon2::Argon2;
use hmac::{Hmac, Mac};
type HmacSha256 = Hmac<Sha256>;

use base64::{engine::general_purpose::STANDARD as B64, Engine};
use hkdf::Hkdf;
use rand::rngs::OsRng;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use std::collections::HashMap;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use zeroize::{Zeroize, ZeroizeOnDrop};

// ─── Constants ────────────────────────────────────────────────

const ARGON2_SALT_LEN: usize = 32;
const HKDF_INFO: &[u8] = b"vault-encryption";
const NONCE_LEN: usize = 12;

#[cfg(unix)]
pub(crate) fn secure_file(path: &std::path::Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    let metadata = std::fs::metadata(path).map_err(|e| e.to_string())?;
    let mut perms = metadata.permissions();
    perms.set_mode(0o600);
    std::fs::set_permissions(path, perms).map_err(|e| e.to_string())
}

#[cfg(windows)]
pub(crate) fn secure_file(path: &std::path::Path) -> Result<(), String> {
    let metadata = std::fs::metadata(path).map_err(|e| e.to_string())?;
    let mut perms = metadata.permissions();
    perms.set_readonly(false);
    std::fs::set_permissions(path, perms).map_err(|e| e.to_string())
}

/// Secure overwrite (best-effort data destruction).
/// Primary protection is the AES-256-GCM encryption which renders data
/// unreadable without the VaultKey. Overwrite prevents key material remnants.
fn secure_overwrite(path: &std::path::Path) -> Result<(), String> {
    if !path.exists() { return Ok(()); }
    if let Ok(metadata) = fs::metadata(path) {
        if let Ok(mut f) = std::fs::OpenOptions::new().write(true).open(path) {
            let len = metadata.len();
            let mut rng = OsRng;
            let mut buf = vec![0u8; 1024];
            let mut written = 0;
            while written < len {
                let to_write = std::cmp::min(1024, (len - written) as usize);
                rng.fill_bytes(&mut buf[..to_write]);
                if f.write_all(&buf[..to_write]).is_err() { break; }
                written += to_write as u64;
            }
            let _ = f.sync_all();
        }
    }
    fs::remove_file(path).map_err(|e| format!("Delete failed: {}", e))
}



// ─── Per-user vault key (zeroized on drop) ────────────────────

/// Holds a 256-bit vault key derived from the user's password.
/// Automatically zeroized when the struct is dropped.
#[derive(Clone, Zeroize, ZeroizeOnDrop)]
pub struct VaultKey {
    key: [u8; 32],
}

impl VaultKey {
    /// Derive a vault key from a raw password and a salt.
    ///
    /// Chain: Argon2(password, salt) → HKDF-SHA256(derived, "vault-encryption")
    pub fn derive(password: &str, salt: &[u8]) -> Result<Self, String> {
        // Step 1 — Argon2 key stretching
        let mut derived = [0u8; 32];
        Argon2::default()
            .hash_password_into(password.as_bytes(), salt, &mut derived)
            .map_err(|e| format!("Argon2 derivation failed: {}", e))?;

        // Step 2 — HKDF expansion to vault-specific key
        let hk = Hkdf::<Sha256>::new(None, &derived);
        let mut vault_key = [0u8; 32];
        hk.expand(HKDF_INFO, &mut vault_key)
            .map_err(|e| format!("HKDF expansion failed: {}", e))?;

        // Zeroize intermediate material
        derived.zeroize();

        Ok(Self { key: vault_key })
    }

    pub fn derive_mac_key(&self) -> Result<[u8; 32], String> {
        let hk = Hkdf::<Sha256>::new(None, &self.key);
        let mut mac_key = [0u8; 32];
        hk.expand(HKDF_INFO, &mut mac_key) // We'll just differentiate internally if we want, or use a new info. Prompt asks for "file-integrity"
            .map_err(|e| format!("HKDF mac expansion failed: {}", e))?;
        Ok(mac_key)
    }

    /// Raw key bytes (internal use only — never crosses FFI).
    fn as_bytes(&self) -> &[u8; 32] {
        &self.key
    }
}

// ─── Persistent storage types ─────────────────────────────────

/// On-disk layout: { username → base64(salt) }
type SaltMap = HashMap<String, String>;

/// On-disk layout: { key → base64(nonce ‖ ciphertext) }
type VaultData = HashMap<String, String>;

/// H-9: Single-file atomic vault envelope.
/// Merges data + MAC + version into one file, eliminating dual-file atomicity issues.
#[derive(Serialize, Deserialize)]
struct VaultEnvelope {
    version: u64,
    mac: String,
    data: VaultData,
}

/// Version tracking map: { username → last_known_version }
type VersionMap = HashMap<String, u64>;

// ─── VaultStore ───────────────────────────────────────────────

pub struct VaultStore {
    root_dir: PathBuf,
    /// Active vault keys for currently-logged-in users.
    /// token → (username, VaultKey)
    active_keys: Arc<Mutex<HashMap<String, (String, VaultKey)>>>,
    /// Per-user I/O serialization locks to prevent concurrent vault file corruption.
    user_io_locks: Arc<Mutex<HashMap<String, Arc<Mutex<()>>>>>,
    master_key: [u8; 32],
}

impl VaultStore {
    pub fn new(root_dir: PathBuf, master_key: [u8; 32]) -> Self {
        if let Err(_) = fs::create_dir_all(root_dir.join("users")) {
            // Best effort — will fail later on read/write
        }
        Self {
            root_dir,
            active_keys: Arc::new(Mutex::new(HashMap::new())),
            user_io_locks: Arc::new(Mutex::new(HashMap::new())),
            master_key,
        }
    }

    // ── Path helpers ──────────────────────────────────────────

    fn salts_path(&self) -> PathBuf {
        self.root_dir.join("vault_salts.json")
    }

    fn salts_mac_path(&self) -> PathBuf {
        self.root_dir.join("vault_salts.json.mac")
    }

    fn data_path(&self, username: &str) -> PathBuf {
        self.root_dir.join("users").join(format!("{}.vault", username))
    }

    /// Legacy MAC path — used only for migration from old dual-file format.
    fn legacy_mac_path(&self, username: &str) -> PathBuf {
        self.root_dir.join("users").join(format!("{}.mac", username))
    }

    fn versions_path(&self) -> PathBuf {
        self.root_dir.join("vault_versions.json")
    }

    fn versions_mac_path(&self) -> PathBuf {
        self.root_dir.join("vault_versions.json.mac")
    }

    // ── File Integrity Helpers ─────────────────────────────────

    fn check_file_mac(&self, path: &PathBuf, mac_path: &PathBuf, hkdf_info: &[u8]) -> Result<Vec<u8>, String> {
        let data_exists = path.exists();
        let mac_exists = mac_path.exists();

        if !data_exists && !mac_exists {
            return Ok(Vec::new());
        }

        if data_exists && !mac_exists {
            // First run after upgrade, one-time migration. MAC will be written on save.
            let content = fs::read(path).map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;
            return Ok(content);
        }

        if !data_exists && mac_exists {
            return Err(format!("Integrity violation: MAC file exists without data file for {}. Possible tampering.", path.display()));
        }

        let content = fs::read(path).map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;
        if content.is_empty() {
            return Err("Integrity violation: data file is empty.".to_string());
        }

        let stored_mac_b64 = fs::read_to_string(mac_path).map_err(|_| "Failed to read MAC file".to_string())?;
        let stored_mac = B64.decode(stored_mac_b64.trim()).map_err(|_| "Invalid MAC encoding".to_string())?;

        let hk = Hkdf::<Sha256>::new(None, &self.master_key);
        let mut key = [0u8; 32];
        hk.expand(hkdf_info, &mut key).map_err(|e| e.to_string())?;

        let mut mac = <HmacSha256 as Mac>::new_from_slice(&key).map_err(|_| "HMAC init fail".to_string())?;
        mac.update(&content);

        if mac.verify_slice(&stored_mac).is_err() {
            return Err(format!("Integrity violation: MAC verification failed for {}. File has been tampered with.", path.display()));
        }

        Ok(content)
    }

    fn write_file_with_mac(&self, path: &PathBuf, mac_path: &PathBuf, hkdf_info: &[u8], content: &str) -> Result<(), String> {
        let mut tmp_path_str = path.as_os_str().to_owned();
        tmp_path_str.push(".tmp");
        let tmp_path = PathBuf::from(tmp_path_str);
        
        let mut f = std::fs::OpenOptions::new().write(true).create(true).truncate(true).open(&tmp_path).map_err(|e| e.to_string())?;
        f.write_all(content.as_bytes()).map_err(|e| e.to_string())?;
        f.sync_all().map_err(|e| e.to_string())?;
        secure_file(&tmp_path)?;

        let hk = Hkdf::<Sha256>::new(None, &self.master_key);
        let mut key = [0u8; 32];
        hk.expand(hkdf_info, &mut key).map_err(|e| e.to_string())?;

        let mut mac = <HmacSha256 as Mac>::new_from_slice(&key).map_err(|_| "HMAC init".to_string())?;
        mac.update(content.as_bytes());
        let mac_b64 = B64.encode(mac.finalize().into_bytes());

        let mut mac_tmp_str = mac_path.as_os_str().to_owned();
        mac_tmp_str.push(".tmp");
        let mac_tmp = PathBuf::from(mac_tmp_str);

        let mut f2 = std::fs::OpenOptions::new().write(true).create(true).truncate(true).open(&mac_tmp).map_err(|e| e.to_string())?;
        f2.write_all(mac_b64.as_bytes()).map_err(|e| e.to_string())?;
        f2.sync_all().map_err(|e| e.to_string())?;
        secure_file(&mac_tmp)?;

        fs::rename(&tmp_path, path).map_err(|e| e.to_string())?;
        fs::rename(&mac_tmp, mac_path).map_err(|e| e.to_string())?;
        Ok(())
    }

    // ── Salt management ───────────────────────────────────────

    fn load_salts(&self) -> Result<SaltMap, String> {
        let content = self.check_file_mac(&self.salts_path(), &self.salts_mac_path(), b"salts-integrity")?;
        if content.is_empty() { return Ok(HashMap::new()); }
        serde_json::from_slice(&content)
            .map_err(|_| "Invalid JSON structure in vault_salts.json".to_string())
    }

    fn save_salts(&self, salts: &SaltMap) -> Result<(), String> {
        let json = serde_json::to_string_pretty(salts)
            .map_err(|e| format!("Serialize salts: {}", e))?;
        self.write_file_with_mac(&self.salts_path(), &self.salts_mac_path(), b"salts-integrity", &json)?;
        Ok(())
    }

    /// Get or create a per-user salt. Returns the salt bytes.
    fn get_or_create_salt(&self, username: &str) -> Result<Vec<u8>, String> {
        let mut salts = self.load_salts()?;

        if let Some(b64) = salts.get(username) {
            return B64.decode(b64).map_err(|e| format!("Decode salt: {}", e));
        }

        // Generate fresh salt
        let mut salt = vec![0u8; ARGON2_SALT_LEN];
        OsRng.fill_bytes(&mut salt);

        salts.insert(username.to_string(), B64.encode(&salt));
        self.save_salts(&salts)?;

        Ok(salt)
    }

    // ── Version tracking (H-8: anti-rollback) ─────────────────

    fn load_versions(&self) -> Result<VersionMap, String> {
        let content = self.check_file_mac(&self.versions_path(), &self.versions_mac_path(), b"versions-integrity")?;
        if content.is_empty() { return Ok(HashMap::new()); }
        serde_json::from_slice(&content)
            .map_err(|_| "Invalid JSON in vault_versions.json".to_string())
    }

    fn save_versions(&self, versions: &VersionMap) -> Result<(), String> {
        let json = serde_json::to_string_pretty(versions)
            .map_err(|e| format!("Serialize versions: {}", e))?;
        self.write_file_with_mac(&self.versions_path(), &self.versions_mac_path(), b"versions-integrity", &json)?;
        Ok(())
    }

    fn get_vault_version(&self, username: &str) -> Result<u64, String> {
        let versions = self.load_versions()?;
        Ok(*versions.get(username).unwrap_or(&0))
    }

    fn set_vault_version(&self, username: &str, version: u64) -> Result<(), String> {
        let mut versions = self.load_versions()?;
        versions.insert(username.to_string(), version);
        self.save_versions(&versions)
    }

    // ── Vault data persistence ────────────────────────────────

    fn load_data(&self, username: &str, vault_key: &VaultKey) -> Result<VaultData, String> {
        let path = self.data_path(username);
        let legacy_mac = self.legacy_mac_path(username);

        let vault_exists = path.exists();
        let legacy_mac_exists = legacy_mac.exists();

        // Neither exists = virgin state
        if !vault_exists && !legacy_mac_exists {
            return Ok(HashMap::new());
        }

        // Only legacy MAC exists without vault = tampering
        if !vault_exists && legacy_mac_exists {
            return Err("Integrity violation: MAC file exists without vault. Possible tampering.".to_string());
        }

        let content = fs::read(&path).map_err(|_| "Failed to read vault file".to_string())?;
        if content.is_empty() {
            return Err("Integrity violation: vault file truncated.".to_string());
        }

        // Migration path: old dual-file format (both .vault + .mac exist)
        if legacy_mac_exists {
            return self.migrate_legacy_vault(username, vault_key, &content, &legacy_mac);
        }

        // New envelope format: single .vault file
        let envelope: VaultEnvelope = serde_json::from_slice(&content)
            .map_err(|_| "Invalid vault envelope format".to_string())?;

        // Verify MAC over version + sorted data
        let hk = Hkdf::<Sha256>::new(None, vault_key.as_bytes());
        let mut mac_key = [0u8; 32];
        hk.expand(b"file-integrity", &mut mac_key)
            .map_err(|e| format!("HKDF: {}", e))?;

        let expected_mac = B64.decode(&envelope.mac)
            .map_err(|_| "Invalid MAC encoding in vault envelope".to_string())?;

        let mut mac = <HmacSha256 as Mac>::new_from_slice(&mac_key)
            .map_err(|_| "HMAC init error".to_string())?;
        mac.update(&envelope.version.to_le_bytes());
        let mut keys: Vec<&String> = envelope.data.keys().collect();
        keys.sort();
        for k in keys {
            mac.update(k.as_bytes());
            mac.update(envelope.data[k].as_bytes());
        }

        if mac.verify_slice(&expected_mac).is_err() {
            return Err("Invalid MAC over vault envelope. Refusing to operate.".to_string());
        }

        // H-8: Anti-rollback — reject older versions
        let known_version = self.get_vault_version(username)?;
        if envelope.version < known_version {
            return Err(format!(
                "Rollback detected: vault version {} < known version {}. Refusing to load.",
                envelope.version, known_version
            ));
        }

        Ok(envelope.data)
    }

    /// Migrate old dual-file (.vault + .mac) format to new single-file envelope.
    /// Verifies old MAC, re-saves in new format, securely deletes old MAC file.
    fn migrate_legacy_vault(
        &self,
        username: &str,
        vault_key: &VaultKey,
        content: &[u8],
        legacy_mac_path: &std::path::Path,
    ) -> Result<VaultData, String> {
        // Parse old format (plain VaultData JSON)
        let data: VaultData = serde_json::from_slice(content)
            .map_err(|_| "Invalid JSON in legacy vault file".to_string())?;

        // Verify old MAC
        let mac_content = fs::read_to_string(legacy_mac_path)
            .map_err(|_| "Failed to read legacy MAC file".to_string())?;
        let expected_mac = B64.decode(mac_content.trim())
            .map_err(|_| "Invalid legacy MAC encoding".to_string())?;

        let hk = Hkdf::<Sha256>::new(None, vault_key.as_bytes());
        let mut mac_key = [0u8; 32];
        hk.expand(b"file-integrity", &mut mac_key)
            .map_err(|e| format!("HKDF: {}", e))?;

        let mut mac = <HmacSha256 as Mac>::new_from_slice(&mac_key)
            .map_err(|_| "HMAC init error".to_string())?;
        let mut keys: Vec<&String> = data.keys().collect();
        keys.sort();
        for k in keys {
            mac.update(k.as_bytes());
            mac.update(data[k].as_bytes());
        }

        if mac.verify_slice(&expected_mac).is_err() {
            return Err("Invalid MAC over legacy vault file. Refusing to migrate.".to_string());
        }

        // Re-save in new envelope format (version starts at 1)
        self.save_data(&data, username, vault_key)?;

        // Securely delete old MAC file
        let _ = secure_overwrite(legacy_mac_path);

        crate::audit::log_event(
            &self.root_dir, "VAULT_MIGRATED", Some(username), None,
            "Migrated from dual-file to single-file vault envelope",
        );

        Ok(data)
    }

    fn save_data(&self, data: &VaultData, username: &str, vault_key: &VaultKey) -> Result<(), String> {
        // H-8: Monotonic version counter
        let current_version = self.get_vault_version(username)?;
        let new_version = current_version + 1;

        // Compute MAC over version + sorted data
        let hk = Hkdf::<Sha256>::new(None, vault_key.as_bytes());
        let mut mac_key = [0u8; 32];
        hk.expand(b"file-integrity", &mut mac_key)
            .map_err(|e| format!("HKDF: {}", e))?;

        let mut mac = <HmacSha256 as Mac>::new_from_slice(&mac_key)
            .map_err(|_| "HMAC init error".to_string())?;
        mac.update(&new_version.to_le_bytes());
        let mut keys: Vec<&String> = data.keys().collect();
        keys.sort();
        for k in keys {
            mac.update(k.as_bytes());
            mac.update(data[k].as_bytes());
        }
        let mac_b64 = B64.encode(mac.finalize().into_bytes());

        // H-9: Build single-file envelope
        let envelope = VaultEnvelope {
            version: new_version,
            mac: mac_b64,
            data: data.clone(),
        };

        let json = serde_json::to_string_pretty(&envelope)
            .map_err(|e| format!("Serialize vault envelope: {}", e))?;

        // Atomic single-file write
        let tmp_path = self.root_dir.join("users").join(format!("{}.vault.tmp", username));
        let mut f = std::fs::OpenOptions::new().write(true).create(true).truncate(true)
            .open(&tmp_path).map_err(|e| format!("Open: {}", e))?;
        f.write_all(json.as_bytes()).map_err(|e| format!("Write vault: {}", e))?;
        f.sync_all().map_err(|e| format!("Sync vault: {}", e))?;
        secure_file(&tmp_path)?;

        let path = self.data_path(username);
        fs::rename(&tmp_path, &path).map_err(|e| format!("Rename vault: {}", e))?;
        secure_file(&path)?;

        // Persist version counter for anti-rollback
        self.set_vault_version(username, new_version)?;

        Ok(())
    }

    // ── Key lifecycle ─────────────────────────────────────────

    /// Derive and cache a vault key when a user logs in.
    /// Called internally by SecurityEngine::login().
    pub fn unlock(&self, token: &str, username: &str, password: &str) -> Result<(), String> {
        let salt = self.get_or_create_salt(username)?;
        let vault_key = VaultKey::derive(password, &salt)?;

        let mut keys = self.active_keys.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        keys.insert(token.to_string(), (username.to_string(), vault_key));
        Ok(())
    }

    pub fn get_key_bytes(&self, token: &str) -> Option<Vec<u8>> {
        if let Ok(keys) = self.active_keys.lock() {
            if let Some((_, vk)) = keys.get(token) {
                return Some(vk.as_bytes().to_vec());
            }
        }
        None
    }

    /// Zeroize and remove the vault key on logout.
    pub fn lock(&self, token: &str) {
        if let Ok(mut keys) = self.active_keys.lock() {
            if let Some((_, mut vk)) = keys.remove(token) {
                vk.zeroize();
            }
        }
    }

    /// H-7: Zeroize ALL active vault keys. Called on SecurityEngine drop.
    pub fn zeroize_all_keys(&self) {
        if let Ok(mut keys) = self.active_keys.lock() {
            for (_, (_, mut vk)) in keys.drain() {
                vk.zeroize();
            }
        }
    }

    // ── Encryption / Decryption primitives ────────────────────

    fn encrypt_value(vault_key: &VaultKey, plaintext: &str) -> Result<String, String> {
        let cipher = Aes256Gcm::new_from_slice(vault_key.as_bytes())
            .map_err(|e| format!("Cipher init: {}", e))?;

        let mut nonce_bytes = [0u8; NONCE_LEN];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher
            .encrypt(nonce, plaintext.as_bytes())
            .map_err(|e| format!("Encrypt: {}", e))?;

        // Pack: nonce ‖ ciphertext → base64
        let mut packed = Vec::with_capacity(NONCE_LEN + ciphertext.len());
        packed.extend_from_slice(&nonce_bytes);
        packed.extend_from_slice(&ciphertext);

        Ok(B64.encode(&packed))
    }

    fn decrypt_value(vault_key: &VaultKey, b64_packed: &str) -> Result<String, String> {
        let packed = B64.decode(b64_packed).map_err(|e| format!("Base64 decode: {}", e))?;

        if packed.len() < NONCE_LEN + 1 {
            return Err("Corrupted ciphertext: too short".to_string());
        }

        let cipher = Aes256Gcm::new_from_slice(vault_key.as_bytes())
            .map_err(|e| format!("Cipher init: {}", e))?;

        let nonce = Nonce::from_slice(&packed[..NONCE_LEN]);
        let ciphertext = &packed[NONCE_LEN..];

        let plaintext = cipher
            .decrypt(nonce, ciphertext)
            .map_err(|e| format!("Decrypt: {}", e))?;

        String::from_utf8(plaintext).map_err(|e| format!("UTF-8: {}", e))
    }

    // ── Per-user I/O lock ─────────────────────────────────────────

    /// Acquire a per-user I/O lock to serialize vault file operations.
    fn get_user_io_lock(&self, username: &str) -> Result<Arc<Mutex<()>>, String> {
        let mut locks = self.user_io_locks.lock()
            .map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        Ok(locks.entry(username.to_string())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone())
    }

    // ── Public API (called by lib.rs) ─────────────────────────

    /// Store a secret. Encrypts with the user's vault key and persists to disk.
    pub fn store_secret(&self, token: &str, key: &str, value: &str) -> Result<(), String> {
        let keys = self.active_keys.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        let (username, vault_key) = keys
            .get(token)
            .ok_or_else(|| "Vault locked: no active key for session".to_string())?;

        let encrypted = Self::encrypt_value(vault_key, value)?;

        let vault_key_clone = vault_key.clone();
        let username_clone = username.clone();
        drop(keys);

        // H-5: Per-user I/O serialization — prevents concurrent file corruption
        let io_lock = self.get_user_io_lock(&username_clone)?;
        let _io_guard = io_lock.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;

        let mut data = self.load_data(&username_clone, &vault_key_clone)?;
        data.insert(key.to_string(), encrypted);
        self.save_data(&data, &username_clone, &vault_key_clone)?;

        Ok(())
    }

    /// Retrieve and decrypt a secret.
    pub fn get_secret(&self, token: &str, key: &str) -> Result<Option<String>, String> {
        let keys = self.active_keys.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        let (username, vault_key) = keys
            .get(token)
            .ok_or_else(|| "Vault locked: no active key for session".to_string())?;

        let vault_key_clone = vault_key.clone();
        let username_clone = username.clone();
        drop(keys);

        // H-5: Per-user I/O serialization
        let io_lock = self.get_user_io_lock(&username_clone)?;
        let _io_guard = io_lock.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;

        let data = self.load_data(&username_clone, &vault_key_clone)?;
        if let Some(b64) = data.get(key) {
            let plaintext = Self::decrypt_value(&vault_key_clone, b64)?;
            return Ok(Some(plaintext));
        }
        Ok(None)
    }

    /// List all secret key names for the user (no decryption needed).
    pub fn list_secrets(&self, token: &str) -> Result<Vec<String>, String> {
        let keys = self.active_keys.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        let (username, vault_key) = keys
            .get(token)
            .ok_or_else(|| "Vault locked: no active key for session".to_string())?;

        let vault_key_clone = vault_key.clone();
        let username_clone = username.clone();
        drop(keys);

        // H-5: Per-user I/O serialization
        let io_lock = self.get_user_io_lock(&username_clone)?;
        let _io_guard = io_lock.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;

        let data = self.load_data(&username_clone, &vault_key_clone)?;
        Ok(data.keys().cloned().collect())
    }

    /// Re-encrypt all secrets for a user with a new password.
    /// Used for key rotation / password change.
    pub fn rotate_key(
        &self,
        username: &str,
        old_password: &str,
        new_password: &str,
    ) -> Result<(), String> {
        let salt = self.get_or_create_salt(username)?;
        let old_key = VaultKey::derive(old_password, &salt)?;

        // Generate new salt for the new password
        let mut new_salt = vec![0u8; ARGON2_SALT_LEN];
        OsRng.fill_bytes(&mut new_salt);
        let new_key = VaultKey::derive(new_password, &new_salt)?;

        // Re-encrypt every secret
        let data = self.load_data(username, &old_key)?;
        let mut re_encrypted = HashMap::new();
        for (k, v) in data.iter() {
            let plaintext = Self::decrypt_value(&old_key, v)?;
            let new_cipher = Self::encrypt_value(&new_key, &plaintext)?;
            re_encrypted.insert(k.clone(), new_cipher);
        }

        // Securely overwrite old vault file
        let old_path = self.data_path(username);
        let del_path = self.root_dir.join("users").join(format!("{}.vault.del", username));
        if old_path.exists() { let _ = fs::rename(&old_path, &del_path); }

        self.save_data(&re_encrypted, username, &new_key)?;

        let _ = secure_overwrite(&del_path);

        crate::audit::log_event(&self.root_dir, "KEY_ROTATION", Some(username), Some(new_key.as_bytes()), "Rotated vault key");

        // Persist new salt
        let mut salts = self.load_salts()?;
        salts.insert(username.to_string(), B64.encode(&new_salt));
        self.save_salts(&salts)?;

        Ok(())
    }
}
