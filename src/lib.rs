//! Q-Vault Core — Strict PyO3 API boundary
//!
//! This module is the ONLY interface between Python and the security core.
//! Python sends plaintext credentials and opaque tokens.
//! Rust handles all crypto, session state, RBAC, and vault I/O.
//!
//! ## Master key & audit log wiring
//!
//! `SecurityEngine::new()` performs the following once, at startup:
//!
//! 1. Load (or generate) the per-installation master key from
//!    `<root_dir>/master.key` via `master_key::MasterKey::load_or_create`.
//!
//! 2. Derive a system-level audit signing key:
//!    `HKDF-SHA256(master_key, "audit-log") → audit_key`
//!    and store an `AuditLogger` in the engine.  **All** events — including
//!    boot, shutdown, sweeper and migration — are logged and HMAC-signed with
//!    this key.  No event can be silently dropped.
//!
//! 3. Pass the master key copy to `UserDB::new` (for user-DB HMAC integrity)
//!    and `VaultStore::new` (for salt/version file HMAC integrity and vault
//!    envelope MACs).  This closes the static-seed vulnerability: every
//!    installation generates its own 256-bit secret on first run.
//!
//! Exported methods (strict contract):
//!   login, logout, create_user, store_secret, get_secret, list_secrets, hash_data

use pyo3::prelude::*;
use std::path::PathBuf;
use std::sync::{Arc, atomic::{AtomicBool, Ordering}};

pub mod audit;
pub mod auth;
pub mod master_key;
pub mod rbac;
pub mod session;
pub mod vault;

use audit::AuditLogger;
use auth::UserDB;
use rbac::Role;
use session::SessionManager;
use vault::VaultStore;

#[pyclass]
pub struct SecurityEngine {
    users: UserDB,
    sessions: Arc<SessionManager>,
    vault: Arc<VaultStore>,
    root_dir: PathBuf,
    /// Signed audit logger — every event goes through this.
    /// Holds a 32-byte subkey derived from master_key via HKDF("audit-log").
    audit: Arc<AuditLogger>,
    /// H-6: Shutdown signal for the background key sweeper thread.
    sweeper_shutdown: Arc<AtomicBool>,
}

#[pymethods]
impl SecurityEngine {
    #[new]
    fn new(root_dir: &str) -> PyResult<Self> {
        let root = PathBuf::from(root_dir);

        // ── Step 1: Load (or generate) the per-installation master key ────────
        //
        // On first run this creates a cryptographically-random 256-bit key in
        // `<root_dir>/master.key` with 0o600 permissions.  On subsequent runs
        // the existing key is loaded.  All downstream HMAC operations (user DB,
        // salt file, version file, audit log) are keyed from this material via
        // HKDF domain separation, so there is no static seed anywhere.
        let master = master_key::MasterKey::load_or_create(&root)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
                format!("{{\"code\": \"MASTER_KEY_FAILURE\", \"message\": \"{}\", \"retry_after\": 0}}", e)
            ))?;
        let mk = *master.as_bytes(); // copy before master is dropped

        // ── Step 2: Derive the system audit key and create the logger ─────────
        //
        // The AuditLogger derives its signing key via HKDF(master_key, "audit-log").
        // It is shared (Arc) so the sweeper thread can log without borrowing the
        // engine.  All events are signed; the `None => return` guard is gone.
        let audit = Arc::new(AuditLogger::new(root.clone(), &mk));

        // ── Step 3: Construct subsystems with master key copies ───────────────
        //
        // UserDB uses HKDF(master_key, "user-db-integrity") for its MAC key.
        // VaultStore uses HKDF(master_key, "salts-integrity") and
        // HKDF(master_key, "versions-integrity") for metadata file MACs.
        let users = UserDB::new(root.clone(), mk)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;

        // Phase 6: Windows Security Note
        if cfg!(windows) {
            audit.log(
                "SYSTEM_WARNING",
                None,
                "File permissions not strictly enforced. OS detected as Windows.",
            );
            println!("WARNING: File permissions not strictly enforced on Windows.");
        }

        let sessions = Arc::new(SessionManager::new());
        let vault = Arc::new(VaultStore::new(root.clone(), mk));
        let sweeper_shutdown = Arc::new(AtomicBool::new(false));

        // ── Step 4: Log ENGINE_BOOT ───────────────────────────────────────────
        //
        // Previously absent — boot was never recorded.  With a mandatory audit
        // key this event is guaranteed to be signed and persisted.
        audit.log("ENGINE_BOOT", None, "SecurityEngine initialized — master key loaded");

        // H-6: Spawn background key sweeper — runs every 30s
        {
            let sess = sessions.clone();
            let vlt = vault.clone();
            let shutdown = sweeper_shutdown.clone();
            let sweep_audit = audit.clone();   // sweeper uses its own Arc reference

            std::thread::Builder::new()
                .name("qvault-key-sweeper".to_string())
                .spawn(move || {
                    while !shutdown.load(Ordering::Relaxed) {
                        std::thread::sleep(std::time::Duration::from_secs(30));
                        if shutdown.load(Ordering::Relaxed) { break; }

                        let expired = sess.collect_expired();
                        for t in &expired {
                            vlt.lock(t);
                        }
                        if !expired.is_empty() {
                            // Previously: `log_event(... None ...)` → silently dropped.
                            // Now: always signed with the system audit key.
                            sweep_audit.log(
                                "KEY_SWEEP",
                                None,
                                &format!("Swept {} expired session key(s)", expired.len()),
                            );
                        }
                    }
                    // Log when the sweeper thread exits cleanly.
                    sweep_audit.log("KEY_SWEEPER_STOPPED", None, "Key sweeper thread exiting");
                })
                .ok(); // Best-effort — system continues if thread spawn fails
        }

        Ok(Self {
            users,
            sessions,
            vault,
            root_dir: root,
            audit,
            sweeper_shutdown,
        })
    }

    /// Authenticate a user and return a session token UUID.
    ///
    /// Internally:
    ///   1. Verify credentials via Argon2 (auth.rs)
    ///   2. Create TTL session (session.rs)
    ///   3. Derive per-user vault key from password → Argon2 → HKDF (vault.rs)
    ///   4. Cache vault key in memory, bound to the session token
    ///
    /// Python receives only the opaque UUID token.
    fn login(&self, username: &str, password: &str) -> PyResult<String> {
        // H-3: FFI input size limits
        if username.len() > 64 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Username exceeds 64 byte limit\", \"retry_after\": 0}"));
        }
        if password.len() > 1024 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Password exceeds 1024 byte limit\", \"retry_after\": 0}"));
        }

        // Cleanup expired sessions and their vault keys
        let expired = self.sessions.collect_expired();
        for t in &expired {
            self.vault.lock(t);
        }

        // Step 1 — Authenticate
        let user = match self.users.authenticate(username, password) {
            Ok(u) => {
                // Previously: `log_event(... None ...)` — dropped in old code.
                self.audit.log("AUTH_SUCCESS", Some(username), "User logged in successfully");
                u
            }
            Err(e) => {
                self.audit.log("AUTH_FAIL", Some(username), &format!("Failed login attempt: {}", e));
                return Err(pyo3::exceptions::PyValueError::new_err(e));
            }
        };

        // Step 2 — Create session
        let token = self.sessions
            .create_session(user.username.clone(), user.role)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
                format!("{{\"code\": \"INTERNAL_ERROR\", \"message\": \"Session lock failed: {}\", \"retry_after\": 0}}", e)
            ))?;

        // Step 3 — Derive and cache vault key
        self.vault.unlock(&token, &user.username, password)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
                format!("{{\"code\": \"INTERNAL_ERROR\", \"message\": \"Vault key derivation failed: {}\", \"retry_after\": 0}}", e)
            ))?;

        Ok(token)
    }

    /// Invalidate a session token AND zeroize the vault key.
    fn logout(&self, token: &str) -> PyResult<()> {
        if let Some(session) = self.sessions.get_session(token) {
            // Previously: `log_event(... key_bytes.as_deref() ...)` — would drop
            // if no vault key was cached (e.g. already expired).
            // Now: system audit key always available.
            self.audit.log("LOGOUT", Some(&session.username), "User logged out");
        }
        self.vault.lock(token);
        self.sessions.invalidate_session(token);
        Ok(())
    }

    /// Create a new user (requires Admin token).
    fn create_user(
        &self,
        token: &str,
        new_username: &str,
        password: &str,
        role_str: &str,
    ) -> PyResult<()> {
        // H-3: FFI input size limits
        if new_username.len() > 64 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Username exceeds 64 byte limit\", \"retry_after\": 0}"));
        }
        if password.len() > 1024 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Password exceeds 1024 byte limit\", \"retry_after\": 0}"));
        }

        let session = self.sessions.get_session(token)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "{\"code\": \"SESSION_EXPIRED\", \"message\": \"Session expired\", \"retry_after\": 0}"
            ))?;

        if !session.role.can_create_user() {
            return Err(pyo3::exceptions::PyPermissionError::new_err(
                "{\"code\": \"PERMISSION_DENIED\", \"message\": \"Permission denied\", \"retry_after\": 0}"
            ));
        }

        let role = match role_str.to_lowercase().as_str() {
            "admin" => Role::Admin,
            "user"  => Role::User,
            "guest" => Role::Guest,
            _ => return Err(pyo3::exceptions::PyValueError::new_err("Invalid role")),
        };

        self.users.create_user(new_username, password, role)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))?;

        self.audit.log(
            "USER_CREATED",
            Some(&session.username),
            &format!("Created user: {} with role: {}", new_username, role_str),
        );

        Ok(())
    }

    /// Store a secret in the user's isolated, encrypted vault.
    /// Persisted to disk as base64(nonce ‖ AES-256-GCM ciphertext).
    fn store_secret(&self, token: &str, key: &str, value: &str) -> PyResult<()> {
        // H-3: FFI input size limits
        if key.len() > 256 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Secret key name exceeds 256 byte limit\", \"retry_after\": 0}"));
        }
        if value.len() > 512 * 1024 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Secret value exceeds 512KB limit\", \"retry_after\": 0}"));
        }

        let session = self.sessions.get_session(token)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "{\"code\": \"SESSION_EXPIRED\", \"message\": \"Session expired\", \"retry_after\": 0}"
            ))?;

        if !session.role.can_store_secret() {
            return Err(pyo3::exceptions::PyPermissionError::new_err(
                "{\"code\": \"PERMISSION_DENIED\", \"message\": \"Permission denied\", \"retry_after\": 0}"
            ));
        }

        let res = self.vault.store_secret(token, key, value)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e));

        if res.is_ok() {
            self.audit.log(
                "SECRET_STORED",
                Some(&session.username),
                &format!("Stored secret: {}", key),
            );
        }
        res
    }

    /// Get a secret from the user's vault.  Decrypted with their vault key.
    fn get_secret(&self, token: &str, key: &str) -> PyResult<Option<String>> {
        // H-3: FFI input size limits
        if key.len() > 256 {
            return Err(pyo3::exceptions::PyValueError::new_err("{\"code\": \"INPUT_TOO_LARGE\", \"message\": \"Secret key name exceeds 256 byte limit\", \"retry_after\": 0}"));
        }

        let session = self.sessions.get_session(token)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "{\"code\": \"SESSION_EXPIRED\", \"message\": \"Session expired\", \"retry_after\": 0}"
            ))?;

        if !session.role.can_get_secret() {
            return Err(pyo3::exceptions::PyPermissionError::new_err(
                "{\"code\": \"PERMISSION_DENIED\", \"message\": \"Permission denied\", \"retry_after\": 0}"
            ));
        }

        let res = self.vault.get_secret(token, key)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e));

        // Log access regardless of hit/miss — every access must be recorded.
        self.audit.log(
            "SECRET_ACCESSED",
            Some(&session.username),
            &format!("Accessed secret: {}", key),
        );

        res
    }

    /// List all secret key names (no decryption — just key names).
    fn list_secrets(&self, token: &str) -> PyResult<Vec<String>> {
        let _session = self.sessions.get_session(token)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(
                "{\"code\": \"SESSION_EXPIRED\", \"message\": \"Session expired\", \"retry_after\": 0}"
            ))?;

        self.vault.list_secrets(token)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    /// SHA-256 hash (for file integrity, etc. — not for passwords).
    fn hash_data(&self, data: &[u8]) -> PyResult<Vec<u8>> {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(data);
        Ok(hasher.finalize().to_vec())
    }
}

/// H-7: Drop safety — zeroize ALL active vault keys on engine destruction.
impl Drop for SecurityEngine {
    fn drop(&mut self) {
        // Signal sweeper thread to stop first.
        self.sweeper_shutdown.store(true, Ordering::Relaxed);

        // Force-zeroize every remaining active key.
        self.vault.zeroize_all_keys();

        // Log clean shutdown.  Previously `log_event(... None ...)` which was
        // silently dropped.  Now: AuditLogger always fires with its subkey.
        // Note: `self.audit` may be the last Arc reference — log before drop.
        self.audit.log(
            "ENGINE_SHUTDOWN",
            None,
            "SecurityEngine dropped — all vault keys zeroized",
        );
        // AuditLogger::drop() will zeroize the audit key bytes.
    }
}

#[pymodule]
fn qvault_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SecurityEngine>()?;
    Ok(())
}
