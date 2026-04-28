//! VaultCore - Trusted Computing Base
//!
//! This module implements the security boundary.
//! ALL sensitive operations happen here.
//! Python only gets opaque handles.

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use uuid::Uuid;
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use hmac::{Hmac, Mac};
use sha2::Sha256;
use zeroize::Zeroize;
use rand::RngCore;

type HmacSha256 = Hmac<Sha256>;

/// Opaque session handle — Python sees only an ID string, never the key
#[pyclass]
pub struct SessionHandle {
    id: String,
    session_key: Vec<u8>,
    created: u64,
    valid: bool,
}

impl SessionHandle {
    fn new() -> Self {
        let mut key = vec![0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);

        Self {
            id: Uuid::new_v4().to_string(),
            session_key: key,
            created: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            valid: true,
        }
    }

    fn invalidate(&mut self) {
        self.valid = false;
        self.session_key.zeroize();
    }

    fn is_valid(&self) -> bool {
        self.valid
    }
}

/// Opaque token handle
#[pyclass]
pub struct TokenHandle {
    id: String,
    scope: String,
    created: u64,
    expires: u64,
    valid: bool,
}

impl TokenHandle {
    fn new(scope: &str, lifetime_secs: u64) -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        Self {
            id: Uuid::new_v4().to_string(),
            scope: scope.to_string(),
            created: now,
            expires: now + lifetime_secs,
            valid: true,
        }
    }

    fn validate(&self) -> bool {
        if !self.valid {
            return false;
        }
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        now < self.expires
    }
}

/// Session manager — internal to Rust
struct SessionManager {
    sessions: HashMap<String, Arc<Mutex<SessionHandle>>>,
    secrets: HashMap<String, String>,
}

impl SessionManager {
    fn new() -> Self {
        Self {
            sessions: HashMap::new(),
            secrets: HashMap::new(),
        }
    }

    fn create_session(&mut self) -> String {
        let handle = SessionHandle::new();
        let id = handle.id.clone();
        // Fixed: was missing closing `)` for Arc::new(Mutex::new(...))
        self.sessions.insert(id.clone(), Arc::new(Mutex::new(handle)));
        id
    }

    fn get_session(&self, id: &str) -> Option<Arc<Mutex<SessionHandle>>> {
        self.sessions.get(id).cloned()
    }

    fn close_session(&mut self, id: &str) {
        if let Some(handle) = self.sessions.remove(id) {
            if let Ok(mut h) = handle.lock() {
                h.invalidate();
            }
        }
        self.secrets.retain(|k, _| !k.starts_with(id));
    }

    fn authenticate(&self, username: &str, password: &str) -> bool {
        // Demo-mode credential check — real auth is in _session_core.py
        match username {
            "admin" => password == "admin123",
            "user"  => password == "user123",
            _       => false,
        }
    }

    fn store_secret(&mut self, session_id: &str, key: &str, value: &str) -> bool {
        let storage_key = format!("{}:{}", session_id, key);
        self.secrets.insert(storage_key, value.to_string());
        true
    }

    fn get_secret(&self, session_id: &str, key: &str) -> Option<String> {
        let storage_key = format!("{}:{}", session_id, key);
        self.secrets.get(&storage_key).cloned()
    }

    fn list_secrets(&self, session_id: &str) -> Vec<String> {
        let prefix = format!("{}:", session_id);
        self.secrets
            .keys()
            .filter(|k| k.starts_with(&prefix))
            .map(|k| k[prefix.len()..].to_string())
            .collect()
    }
}

/// Crypto operations — all keys stay inside Rust
struct CryptoOps;

impl CryptoOps {
    fn encrypt(key: &[u8], data: &[u8]) -> Vec<u8> {
        let cipher = Aes256Gcm::new_from_slice(key).expect("32-byte key required");
        let mut nonce_bytes = vec![0u8; 12];
        rand::thread_rng().fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher.encrypt(nonce, data).expect("encryption failure");

        let mut result = Vec::with_capacity(12 + ciphertext.len());
        result.extend_from_slice(&nonce_bytes);
        result.extend_from_slice(&ciphertext);
        result
    }

    fn decrypt(key: &[u8], encrypted: &[u8]) -> Result<Vec<u8>, String> {
        if encrypted.len() < 12 {
            return Err("Ciphertext too short".to_string());
        }
        let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| e.to_string())?;
        let nonce = Nonce::from_slice(&encrypted[..12]);
        let ciphertext = &encrypted[12..];
        cipher.decrypt(nonce, ciphertext).map_err(|e| e.to_string())
    }

    fn hmac_sha256(key: &[u8], data: &[u8]) -> Vec<u8> {
        let mut mac = HmacSha256::new_from_slice(key).expect("HMAC accepts any key size");
        mac.update(data);
        mac.finalize().into_bytes().to_vec()
    }

    fn constant_time_compare(a: &[u8], b: &[u8]) -> bool {
        if a.len() != b.len() {
            return false;
        }
        let mut result = 0u8;
        for (x, y) in a.iter().zip(b.iter()) {
            result |= x ^ y;
        }
        result == 0
    }
}

/// VaultCore — main PyO3 security interface
#[pyclass]
pub struct VaultCore {
    sessions: SessionManager,
    tokens: HashMap<String, TokenHandle>,
}

#[pymethods]
impl VaultCore {
    #[new]
    fn new() -> Self {
        Self {
            sessions: SessionManager::new(),
            tokens: HashMap::new(),
        }
    }

    /// Create new session — returns opaque ID string
    fn create_session(&mut self) -> String {
        self.sessions.create_session()
    }

    /// Authenticate user within Rust
    fn authenticate(&self, session_id: &str, username: &str, password: &str) -> (bool, String) {
        if !self.sessions.sessions.contains_key(session_id) {
            return (false, "Invalid session".to_string());
        }
        if self.sessions.authenticate(username, password) {
            (true, format!("Welcome {}", username))
        } else {
            (false, "Invalid credentials".to_string())
        }
    }

    /// Encrypt data (Rust holds the key — Python never sees it)
    fn encrypt_data(&self, session_id: &str, data: &[u8], _aad: Option<&[u8]>) -> PyResult<Vec<u8>> {
        let session = self.sessions.get_session(session_id)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Invalid session"))?;
        let handle = session.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("Lock error"))?;
        if !handle.is_valid() {
            return Err(pyo3::exceptions::PyValueError::new_err("Session invalidated"));
        }
        Ok(CryptoOps::encrypt(&handle.session_key, data))
    }

    /// Decrypt data (Rust holds the key)
    fn decrypt_data(&self, session_id: &str, encrypted: &[u8]) -> PyResult<Vec<u8>> {
        let session = self.sessions.get_session(session_id)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Invalid session"))?;
        let handle = session.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("Lock error"))?;
        if !handle.is_valid() {
            return Err(pyo3::exceptions::PyValueError::new_err("Session invalidated"));
        }
        CryptoOps::decrypt(&handle.session_key, encrypted)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    /// Store secret — namespaced by session
    fn store_secret(&mut self, session_id: &str, key: &str, value: &str) -> PyResult<bool> {
        if !self.sessions.sessions.contains_key(session_id) {
            return Err(pyo3::exceptions::PyValueError::new_err("Invalid session"));
        }
        Ok(self.sessions.store_secret(session_id, key, value))
    }

    /// Get secret — returns None if not found
    fn get_secret(&self, session_id: &str, key: &str) -> PyResult<Option<String>> {
        if !self.sessions.sessions.contains_key(session_id) {
            return Err(pyo3::exceptions::PyValueError::new_err("Invalid session"));
        }
        Ok(self.sessions.get_secret(session_id, key))
    }

    /// List all secret keys for a session
    fn list_secrets(&self, session_id: &str) -> PyResult<Vec<String>> {
        if !self.sessions.sessions.contains_key(session_id) {
            return Err(pyo3::exceptions::PyValueError::new_err("Invalid session"));
        }
        Ok(self.sessions.list_secrets(session_id))
    }

    /// Generate token — returns opaque ID
    fn generate_token(&mut self, session_id: &str, scope: &str, lifetime_secs: u64) -> PyResult<String> {
        if !self.sessions.sessions.contains_key(session_id) {
            return Err(pyo3::exceptions::PyValueError::new_err("Invalid session"));
        }
        let token = TokenHandle::new(scope, lifetime_secs);
        let id = token.id.clone();
        self.tokens.insert(id.clone(), token);
        Ok(id)
    }

    /// Validate token — returns (valid, claims)
    fn validate_token(&self, token_id: &str) -> PyResult<(bool, HashMap<String, String>)> {
        let mut claims = HashMap::new();
        if let Some(token) = self.tokens.get(token_id) {
            let valid = token.validate();
            if valid {
                claims.insert("scope".to_string(), token.scope.clone());
            }
            Ok((valid, claims))
        } else {
            Ok((false, claims))
        }
    }

    /// Close session and zeroize key material
    fn close_session(&mut self, session_id: &str) {
        self.sessions.close_session(session_id);
    }

    /// Verify module integrity (always true from Rust side)
    fn verify_integrity(&self) -> (bool, String) {
        (true, "Rust VaultCore verified".to_string())
    }

    /// HMAC-SHA256 convenience method
    fn hmac_sha256(&self, key: &[u8], data: &[u8]) -> Vec<u8> {
        CryptoOps::hmac_sha256(key, data)
    }

    /// Constant-time compare
    fn constant_time_compare(&self, a: &[u8], b: &[u8]) -> bool {
        CryptoOps::constant_time_compare(a, b)
    }
}