use crate::rbac::Role;
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use hmac::{Hmac, Mac};
use sha2::Sha256;
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use hkdf::Hkdf;

type HmacSha256 = Hmac<Sha256>;

// Hardcoded HMAC seed removed. We now use a per-installation master key.

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UserRecord {
    pub username: String,
    pub password_hash: String,
    pub role: Role,
    #[serde(default)]
    pub failed_attempts: u32,
    #[serde(default)]
    pub locked_until: Option<i64>,
}

pub struct UserDB {
    file_path: PathBuf,
    users: Arc<Mutex<HashMap<String, UserRecord>>>,
    master_key: [u8; 32],
}

impl UserDB {
    pub fn new(root_dir: PathBuf, master_key: [u8; 32]) -> Result<Self, String> {
        let file_path = root_dir.join("vault_users.json");
        let users = Arc::new(Mutex::new(HashMap::new()));
        
        let db = Self { file_path, users, master_key };
        db.load()?;
        
        // Seed default users if empty
        let mut do_seed = false;
        if let Ok(guard) = db.users.lock() {
            if guard.is_empty() { do_seed = true; }
        } else {
            return Err(crate::error::SecurityError::StateCorruption.to_string());
        }
        if do_seed {
            let _ = db.seed_defaults();
        }
        
        Ok(db)
    }

    fn mac_path(&self) -> PathBuf {
        let mut name = self.file_path.as_os_str().to_owned();
        name.push(".mac");
        PathBuf::from(name)
    }

    fn derive_db_mac_key(&self) -> Result<[u8; 32], String> {
        let hk = Hkdf::<Sha256>::new(None, &self.master_key);
        let mut key = [0u8; 32];
        hk.expand(b"user-db-integrity", &mut key)
            .map_err(|e| format!("HKDF expansion failed: {}", e))?;
        Ok(key)
    }

    fn load(&self) -> Result<(), String> {
        let mac_path = self.mac_path();
        let data_exists = self.file_path.exists();
        let mac_exists = mac_path.exists();

        // Neither file exists = fresh install, will seed defaults
        if !data_exists && !mac_exists {
            return Ok(());
        }

        // Data exists without MAC = first run after upgrade, one-time migration
        if data_exists && !mac_exists {
            let raw = fs::read_to_string(&self.file_path)
                .map_err(|e| format!("Failed to read users file: {}", e))?;
            let mut records: Vec<UserRecord> = serde_json::from_str(&raw)
                .map_err(|e| format!("Users database JSON is corrupt: {}", e))?;

            // H-1: Fix empty password hashes during migration
            for record in records.iter_mut() {
                if record.password_hash.is_empty() {
                    if let Ok(hash) = Self::hash_password(&record.username) {
                        record.password_hash = hash;
                    }
                }
            }

            let mut map = self.users.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
            for record in records {
                map.insert(record.username.clone(), record);
            }
            drop(map);

            // Generate MAC for migrated data (one-time)
            self.save()?;
            return Ok(());
        }

        // MAC exists without data = tampering
        if !data_exists && mac_exists {
            return Err("Integrity violation: MAC file exists without users database. Possible tampering.".to_string());
        }

        // Both exist — verify MAC before trusting content
        let content = fs::read(&self.file_path)
            .map_err(|e| format!("Failed to read users file: {}", e))?;
        if content.is_empty() {
            return Err("Integrity violation: users database is empty. Possible tampering.".to_string());
        }

        let stored_mac_b64 = fs::read_to_string(&mac_path)
            .map_err(|_| "Failed to read users MAC file".to_string())?;
        let stored_mac = B64.decode(stored_mac_b64.trim())
            .map_err(|_| "Invalid MAC encoding in users MAC file".to_string())?;

        let mac_key = self.derive_db_mac_key()?;
        let mut mac = HmacSha256::new_from_slice(&mac_key)
            .map_err(|_| "HMAC initialization failed".to_string())?;
        mac.update(&content);

        if mac.verify_slice(&stored_mac).is_err() {
            return Err("Integrity violation: users database MAC verification failed. File has been tampered with.".to_string());
        }

        // MAC valid — safe to parse
        let data = String::from_utf8(content)
            .map_err(|_| "Users database is not valid UTF-8".to_string())?;
        let records: Vec<UserRecord> = serde_json::from_str(&data)
            .map_err(|e| format!("Users database JSON is corrupt: {}", e))?;

        let mut map = self.users.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        for record in records {
            map.insert(record.username.clone(), record);
        }

        Ok(())
    }

    fn save(&self) -> Result<(), String> {
        let map = self.users.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        let mut records: Vec<&UserRecord> = map.values().collect();
        // Sort for deterministic serialization (required for stable MAC)
        records.sort_by(|a, b| a.username.cmp(&b.username));

        let json = serde_json::to_string_pretty(&records)
            .map_err(|e| format!("Failed to serialize users: {}", e))?;

        if let Some(parent) = self.file_path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }

        use std::io::Write;

        // Write data file atomically
        let tmp_path = self.file_path.with_extension("tmp");
        let mut f = std::fs::OpenOptions::new().write(true).create(true).truncate(true).open(&tmp_path).map_err(|e| format!("Open: {}", e))?;
        f.write_all(json.as_bytes()).map_err(|e| format!("Write: {}", e))?;
        f.sync_all().map_err(|e| format!("Sync: {}", e))?;

        // Compute HMAC-SHA256 over exact serialized bytes
        let mac_key = self.derive_db_mac_key()?;
        let mut mac = HmacSha256::new_from_slice(&mac_key)
            .map_err(|_| "HMAC initialization failed".to_string())?;
        mac.update(json.as_bytes());
        let mac_b64 = B64.encode(mac.finalize().into_bytes());

        // Write MAC file atomically
        let mac_path = self.mac_path();
        let mac_tmp = {
            let mut p = mac_path.as_os_str().to_owned();
            p.push(".tmp");
            PathBuf::from(p)
        };
        let mut f2 = std::fs::OpenOptions::new().write(true).create(true).truncate(true).open(&mac_tmp).map_err(|e| format!("Open MAC: {}", e))?;
        f2.write_all(mac_b64.as_bytes()).map_err(|e| format!("Write MAC: {}", e))?;
        f2.sync_all().map_err(|e| format!("Sync MAC: {}", e))?;

        // Atomic renames
        std::fs::rename(&tmp_path, &self.file_path).map_err(|e| format!("Rename data: {}", e))?;
        std::fs::rename(&mac_tmp, &mac_path).map_err(|e| format!("Rename MAC: {}", e))?;

        Ok(())
    }

    pub fn hash_password(password: &str) -> Result<String, String> {
        if password.is_empty() {
            return Err("Empty passwords are not allowed".to_string());
        }
        let salt = SaltString::generate(&mut OsRng);
        let argon2 = Argon2::default();
        argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|_| "Password hashing failed".to_string())
            .map(|h| h.to_string())
    }

    pub fn verify_password(hash: &str, password: &str) -> bool {
        // H-1: Reject empty credentials for ALL roles — no bypass
        if hash.is_empty() || password.is_empty() {
            return false;
        }
        let parsed_hash = match PasswordHash::new(hash) {
            Ok(h) => h,
            Err(_) => return false,
        };
        Argon2::default()
            .verify_password(password.as_bytes(), &parsed_hash)
            .is_ok()
    }

    fn seed_defaults(&self) -> Result<(), String> {
        self.create_user("admin", "admin123", Role::Admin)?;
        self.create_user("user", "user123", Role::User)?;
        self.create_user("guest", "guest", Role::Guest)?;
        Ok(())
    }

    pub fn create_user(&self, username: &str, password: &str, role: Role) -> Result<(), String> {
        let username_lower = username.to_lowercase();
        
        let mut map = self.users.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        if map.contains_key(&username_lower) {
            return Err("User already exists".to_string());
        }
        
        let record = UserRecord {
            username: username_lower.clone(),
            password_hash: Self::hash_password(password)?,
            role,
            failed_attempts: 0,
            locked_until: None,
        };
        
        map.insert(username_lower, record);
        drop(map);
        
        self.save()
    }

    pub fn authenticate(&self, username: &str, password: &str) -> Result<UserRecord, String> {
        let mut map = self.users.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;
        let current_time = chrono::Utc::now().timestamp();
        
        let record = map.get_mut(&username.to_lowercase()).ok_or_else(|| format!("{{\"code\": \"AUTH_FAILED\", \"message\": \"Invalid credentials\", \"retry_after\": 0}}"))?;

        // Check if locked
        if let Some(lock_time) = record.locked_until {
            if current_time < lock_time {
                let retry = lock_time - current_time;
                return Err(format!("{{\"code\": \"AUTH_LOCKED\", \"message\": \"Account is locked due to too many failed attempts\", \"retry_after\": {}}}", retry));
            } else {
                // Cooldown passed, reset
                record.locked_until = None;
                record.failed_attempts = 0;
            }
        }

        if Self::verify_password(&record.password_hash, password) {
            record.failed_attempts = 0;
            let cloned_record = record.clone();
            drop(map);
            let _ = self.save();
            Ok(cloned_record)
        } else {
            record.failed_attempts += 1;
            if record.failed_attempts >= 5 {
                record.locked_until = Some(current_time + 5 * 60); // 5 minutes cooldown
            }
            drop(map);
            let _ = self.save();
            Err(format!("{{\"code\": \"AUTH_FAILED\", \"message\": \"Invalid credentials\", \"retry_after\": 0}}"))
        }
    }
}
