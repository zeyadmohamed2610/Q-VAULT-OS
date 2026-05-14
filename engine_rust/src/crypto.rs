//! CryptoEngine - Constant-time cryptographic operations
//! 
//! This module provides constant-time cryptographic operations
//! to prevent timing attacks. All sensitive comparisons use
//! constant-time algorithms.

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use hmac::{Hmac, Mac};
use rand::RngCore;
use sha2::Sha256;
use zeroize::Zeroize;
use subtle::ConstantTimeEq;

use crate::error::{QVaultError, Result};

/// HMAC-SHA256 type
type HmacSha256 = Hmac<Sha256>;

/// CryptoEngine with constant-time operations
pub struct CryptoEngine {
    _private: (),
}

impl CryptoEngine {
    /// Create a new CryptoEngine
    pub fn new() -> Self {
        Self { _private: () }
    }

    /// Generate a random 256-bit key
    pub fn generate_key(&self) -> Vec<u8> {
        let mut key = vec![0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);
        key
    }

    /// Generate a random 96-bit nonce
    pub fn generate_nonce(&self) -> Vec<u8> {
        let mut nonce = vec![0u8; 12];
        rand::thread_rng().fill_bytes(&mut nonce);
        nonce
    }

    /// Encrypt data using AES-256-GCM
    /// 
    /// # Arguments
    /// * `data` - Plaintext to encrypt
    /// * `key` - 256-bit key (must be exactly 32 bytes)
    /// * `nonce` - 96-bit nonce (must be exactly 12 bytes)
    /// 
    /// # Returns
    /// Encrypted data with nonce prepended: [nonce (12 bytes) | ciphertext]
    pub fn encrypt(&self, data: &[u8], key: &[u8], nonce: &[u8]) -> Result<Vec<u8>> {
        if key.len() != 32 {
            return Err(QVaultError::InvalidKeyLength(key.len()));
        }
        if nonce.len() != 12 {
            return Err(QVaultError::InvalidInput("Nonce must be 12 bytes".to_string()));
        }

        let cipher = Aes256Gcm::new_from_slice(key)
            .map_err(|e| QVaultError::EncryptionFailed(e.to_string()))?;

        let nonce = Nonce::from_slice(nonce);
        
        let ciphertext = cipher
            .encrypt(nonce, data)
            .map_err(|e| QVaultError::EncryptionFailed(e.to_string()))?;

        // Prepend nonce to ciphertext
        let mut result = Vec::with_capacity(12 + ciphertext.len());
        result.extend_from_slice(nonce);
        result.extend_from_slice(&ciphertext);
        
        Ok(result)
    }

    /// Decrypt data using AES-256-GCM
    /// 
    /// # Arguments
    /// * `encrypted_data` - Data with nonce prepended
    /// * `key` - 256-bit key
    /// 
    /// # Returns
    /// Decrypted plaintext
    pub fn decrypt(&self, encrypted_data: &[u8], key: &[u8]) -> Result<Vec<u8>> {
        if key.len() != 32 {
            return Err(QVaultError::InvalidKeyLength(key.len()));
        }
        if encrypted_data.len() < 12 {
            return Err(QVaultError::InvalidInput("Invalid encrypted data".to_string()));
        }

        let cipher = Aes256Gcm::new_from_slice(key)
            .map_err(|e| QVaultError::DecryptionFailed(e.to_string()))?;

        let nonce = Nonce::from_slice(&encrypted_data[..12]);
        let ciphertext = &encrypted_data[12..];

        cipher
            .decrypt(nonce, ciphertext)
            .map_err(|e| QVaultError::DecryptionFailed(e.to_string()))
    }

    /// Compute HMAC-SHA256
    /// 
    /// # Arguments
    /// * `key` - HMAC key
    /// * `data` - Data to authenticate
    /// 
    /// # Returns
    /// 32-byte HMAC
    pub fn hmac_sha256(&self, key: &[u8], data: &[u8]) -> Result<Vec<u8>> {
        let mut mac = HmacSha256::new_from_slice(key)
            .map_err(|e| QVaultError::InvalidInput(e.to_string()))?;
        mac.update(data);
        Ok(mac.finalize().into_bytes().to_vec())
    }

    /// Constant-time comparison - prevents timing attacks
    /// 
    /// This function takes constant time regardless of where
    /// the comparison matches, preventing attackers from
    /// using timing information to guess secrets.
    pub fn constant_time_compare(&self, a: &[u8], b: &[u8]) -> bool {
        if a.len() != b.len() {
            return false;
        }
        
        a.ct_eq(b).unwrap_u8() == 1
    }

    /// Verify HMAC in constant time
    pub fn verify_hmac(&self, key: &[u8], data: &[u8], expected: &[u8]) -> bool {
        if let Ok(computed) = self.hmac_sha256(key, data) {
            self.constant_time_compare(&computed, expected)
        } else {
            false
        }
    }

    /// Derive a key from input using HKDF-like derivation
    /// 
    /// # Arguments
    /// * `input` - Input material
    /// * `salt` - Salt value
    /// * `info` - Optional context info
    /// 
    /// # Returns
    /// 32-byte derived key
    pub fn derive_key(&self, input: &[u8], salt: &[u8], info: &[u8]) -> Result<Vec<u8>> {
        // Use HMAC as a simple KDF
        let mut result = Vec::new();
        let mut current = Vec::new();
        
        let mut counter = 1u8;
        while result.len() < 32 {
            current.clear();
            current.extend_from_slice(info);
            current.push(counter);
            
            let mut mac = HmacSha256::new_from_slice(salt)
                .map_err(|e| QVaultError::InvalidInput(e.to_string()))?;
            mac.update(input);
            mac.update(&current);
            
            let hmac_result: Vec<u8> = mac.finalize().into_bytes().to_vec();
            result.extend_from_slice(&hmac_result);
            counter += 1;
        }
        
        result.truncate(32);
        Ok(result)
    }

    /// Compute SHA-256 hash
    pub fn sha256(&self, data: &[u8]) -> Vec<u8> {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(data);
        hasher.finalize().to_vec()
    }
}

impl Default for CryptoEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt() {
        let engine = CryptoEngine::new();
        let key = engine.generate_key();
        let nonce = engine.generate_nonce();
        
        let plaintext = b"Hello, Q-Vault!";
        let encrypted = engine.encrypt(plaintext, &key, &nonce).unwrap();
        let decrypted = engine.decrypt(&encrypted, &key).unwrap();
        
        assert_eq!(plaintext.to_vec(), decrypted);
    }

    #[test]
    fn test_constant_time_compare() {
        let engine = CryptoEngine::new();
        
        // Equal arrays
        assert!(engine.constant_time_compare(b"test", b"test"));
        
        // Different length
        assert!(!engine.constant_time_compare(b"test", b"tes"));
        
        // Different content - should be constant time
        assert!(!engine.constant_time_compare(b"test", b"Test"));
    }

    #[test]
    fn test_hmac() {
        let engine = CryptoEngine::new();
        let key = b"my_secret_key";
        let data = b"data to authenticate";
        
        let hmac = engine.hmac_sha256(key, data);
        
        // Verify HMAC is 32 bytes
        assert_eq!(hmac.len(), 32);
    }
}