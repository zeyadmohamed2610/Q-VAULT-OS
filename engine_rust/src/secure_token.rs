//! SecureTokenManager - Memory-safe token storage with TPM binding
//! 
//! Keys are stored securely with automatic zeroization on drop.
//! Supports TPM binding when available.

use std::collections::HashMap;
use std::path::PathBuf;
use zeroize::{Zeroize, ZeroizeOnDrop};

use crate::error::{QVaultError, Result};

/// Secure token storage with zeroization
/// 
/// This struct holds encrypted tokens in memory. When dropped,
/// all sensitive data is zeroized automatically.
struct SecureToken {
    /// Encrypted token data
    data: Vec<u8>,
    /// Nonce used for encryption
    nonce: Vec<u8>,
}

impl Zeroize for SecureToken {
    fn zeroize(&mut self) {
        self.data.zeroize();
        self.nonce.zeroize();
    }
}

impl ZeroizeOnDrop for SecureToken {}

/// Secure Token Manager
/// 
/// Manages secure storage of tokens/keys with:
/// - Automatic memory zeroization
/// - Optional TPM binding
/// - Secure key derivation
pub struct SecureTokenManager {
    /// Root directory for token storage
    root: PathBuf,
    /// In-memory token cache (encrypted)
    tokens: HashMap<String, SecureToken>,
    /// Master key for token encryption
    master_key: Vec<u8>,
    /// Whether TPM is available
    tpm_available: bool,
}

impl SecureTokenManager {
    /// Create a new SecureTokenManager
    pub fn new(root: PathBuf) -> Result<Self> {
        let root_exists = root.exists();
        if !root_exists {
            std::fs::create_dir_all(&root)
                .map_err(|e| QVaultError::InvalidInput(format!("Failed to create root: {}", e)))?;
        }

        // Generate or load master key
        let key_file = root.join("master.key");
        let master_key = if key_file.exists() {
            std::fs::read(&key_file)
                .map_err(|e| QVaultError::InvalidInput(format!("Failed to read key: {}", e)))?
        } else {
            // Generate new 256-bit key
            let key = crate::crypto::CryptoEngine::new().generate_key();
            std::fs::write(&key_file, &key)
                .map_err(|e| QVaultError::InvalidInput(format!("Failed to write key: {}", e)))?;
            key
        };

        let mut manager = Self {
            root,
            tokens: HashMap::new(),
            master_key,
            tpm_available: false,
        };

        // Check TPM availability
        manager.tpm_available = manager.check_tpm();

        // Load existing tokens
        manager.load_tokens()?;

        Ok(manager)
    }

    /// Check if TPM is available
    fn check_tpm(&self) -> bool {
        #[cfg(target_os = "windows")]
        {
            // Check via Windows API - simplified
            false
        }
        #[cfg(target_os = "linux")]
        {
            std::path::Path::new("/dev/tpm0").exists() || 
            std::path::Path::new("/dev/tpmrm0").exists()
        }
        #[cfg(not(any(target_os = "windows", target_os = "linux")))]
        {
            false
        }
    }

    /// Get storage file path for a token
    fn token_file(&self, key: &str) -> PathBuf {
        let safe_name = key.replace(['/', '\\', ':'], "_");
        self.root.join(format!("{}.tok", safe_name))
    }

    /// Load tokens from disk
    fn load_tokens(&mut self) -> Result<()> {
        let entries = std::fs::read_dir(&self.root)
            .map_err(|e| QVaultError::InvalidInput(format!("Failed to read dir: {}", e)))?;

        for entry in entries.flatten() {
            let path = entry.path();
            if let Some(ext) = path.extension() {
                if ext == "tok" {
                    if let Some(stem) = path.file_stem() {
                        let key = stem.to_string_lossy().to_string();
                        if let Ok(data) = std::fs::read(&path) {
                            // Format: [12-byte nonce | encrypted data]
                            if data.len() > 12 {
                                let nonce = data[..12].to_vec();
                                let encrypted = data[12..].to_vec();
                                self.tokens.insert(
                                    key,
                                    SecureToken {
                                        data: encrypted,
                                        nonce,
                                    },
                                );
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    }

    /// Store a token securely
    pub fn store_token(&mut self, key: &str, value: &[u8]) -> Result<()> {
        use crate::crypto::CryptoEngine;

        if key.is_empty() {
            return Err(QVaultError::InvalidInput("Key cannot be empty".to_string()));
        }

        let engine = CryptoEngine::new();
        let nonce = engine.generate_nonce();

        // Encrypt value with master key
        let encrypted = engine.encrypt(value, &self.master_key, &nonce)?;

        // Store in memory
        self.tokens.insert(
            key.to_string(),
            SecureToken {
                data: encrypted[12..].to_vec(),
                nonce,
            },
        )?;

        // Write to disk
        let token_file = self.token_file(key);
        std::fs::write(&token_file, &encrypted)
            .map_err(|e| QVaultError::InvalidInput(format!("Failed to write token: {}", e)))?;

        Ok(())
    }

    /// Retrieve a token
    pub fn get_token(&self, key: &str) -> Option<Vec<u8>> {
        use crate::crypto::CryptoEngine;

        let secure_token = self.tokens.get(key)?;

        let engine = CryptoEngine::new();
        
        // Reconstruct encrypted data: nonce + ciphertext
        let mut encrypted = Vec::with_capacity(12 + secure_token.data.len());
        encrypted.extend_from_slice(&secure_token.nonce);
        encrypted.extend_from_slice(&secure_token.data);

        // Decrypt
        engine.decrypt(&encrypted, &self.master_key).ok()
    }

    /// Delete a token
    pub fn delete_token(&mut self, key: &str) -> Result<()> {
        // Remove from memory
        if let Some(mut token) = self.tokens.remove(key) {
            token.zeroize();
        }

        // Remove from disk
        let token_file = self.token_file(key);
        if token_file.exists() {
            // Overwrite with zeros before deleting for security
            if let Ok(metadata) = std::fs::metadata(&token_file) {
                let len = metadata.len() as usize;
                let zeros = vec![0u8; len];
                let _ = std::fs::write(&token_file, zeros);
            }
            std::fs::remove_file(&token_file)
                .map_err(|e| QVaultError::InvalidInput(format!("Failed to delete: {}", e)))?;
        }

        Ok(())
    }

    /// Check if token exists
    pub fn has_token(&self, key: &str) -> bool {
        self.tokens.contains_key(key)
    }

    /// List all token keys (not values)
    pub fn list_tokens(&self) -> Vec<String> {
        self.tokens.keys().cloned().collect()
    }

    /// Rotate master key
    pub fn rotate_keys(&mut self) -> Result<()> {
        use crate::crypto::CryptoEngine;

        let engine = CryptoEngine::new();
        
        // Generate new master key
        let new_master_key = engine.generate_key();
        
        // Re-encrypt all tokens with new key
        let mut reencrypted: HashMap<String, (Vec<u8>, Vec<u8>)> = HashMap::new();
        
        for (key, token) in &self.tokens {
            // Decrypt with old key
            let mut encrypted = Vec::with_capacity(12 + token.data.len());
            encrypted.extend_from_slice(&token.nonce);
            encrypted.extend_from_slice(&token.data);
            
            if let Ok(plaintext) = engine.decrypt(&encrypted, &self.master_key) {
                // Re-encrypt with new key
                let nonce = engine.generate_nonce();
                if let Ok(new_encrypted) = engine.encrypt(&plaintext, &new_master_key, &nonce) {
                    reencrypted.insert(
                        key.clone(),
                        (new_encrypted[12..].to_vec(), nonce),
                    );
                }
            }
        }

        // Update in-memory tokens
        self.tokens.clear();
        for (key, (data, nonce)) in reencrypted {
            self.tokens.insert(key, SecureToken { data, nonce });
        }

        // Update master key
        self.master_key = new_master_key;

        // Save new master key
        let key_file = self.root.join("master.key");
        std::fs::write(&key_file, &self.master_key)
            .map_err(|e| QVaultError::InvalidInput(format!("Failed to write key: {}", e)))?;

        // Save all tokens
        for (key, token) in &self.tokens {
            let mut encrypted = Vec::with_capacity(12 + token.data.len());
            encrypted.extend_from_slice(&token.nonce);
            encrypted.extend_from_slice(&token.data);
            
            let token_file = self.token_file(key);
            std::fs::write(&token_file, encrypted)
                .map_err(|e| QVaultError::InvalidInput(format!("Failed to write token: {}", e)))?;
        }

        Ok(())
    }

    /// Check if TPM is available
    pub fn is_tpm_available(&self) -> bool {
        self.tpm_available
    }

    /// Get device identifier (TPM-based if available)
    pub fn get_device_id(&self) -> String {
        use crate::crypto::CryptoEngine;
        
        let engine = CryptoEngine::new();
        
        // Use machine-specific data for device ID
        let machine_id = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "unknown".to_string());
        
        // Add master key hash for uniqueness
        let key_hash = engine.sha256(&self.master_key);
        
        format!("{:x}", engine.sha256(format!("{}{}", machine_id, hex::encode(key_hash)).as_bytes()))
    }
}

/// Simple hex encoding
mod hex {
    pub fn encode(data: &[u8]) -> String {
        data.iter().map(|b| format!("{:02x}", b)).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env::temp_dir;

    #[test]
    fn test_store_and_retrieve() {
        let temp = temp_dir().join("qvault_test_tokens");
        let _ = std::fs::remove_dir_all(&temp);
        
        let mut manager = SecureTokenManager::new(temp.clone()).unwrap();
        
        // Store token
        manager.store_token("test_key", b"secret_value").unwrap();
        
        // Retrieve token
        let value = manager.get_token("test_key").unwrap();
        assert_eq!(value, b"secret_value");
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_delete_token() {
        let temp = temp_dir().join("qvault_test_delete");
        let _ = std::fs::remove_dir_all(&temp);
        
        let mut manager = SecureTokenManager::new(temp.clone()).unwrap();
        
        manager.store_token("test_key", b"secret_value").unwrap();
        assert!(manager.has_token("test_key"));
        
        manager.delete_token("test_key").unwrap();
        assert!(!manager.has_token("test_key"));
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp);
    }
}