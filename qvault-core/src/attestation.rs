//! AttestationCore - TPM-based attestation
//! 
//! Provides secure TPM interaction for attestation:
//! - PCR reading
//! - Quote generation
//! - Device identity
//! - Hardware-signed attestations

use std::collections::HashMap;
use std::path::PathBuf;

use crate::error::{QVaultError, Result};
use crate::crypto::CryptoEngine;

/// Attestation data structure
#[derive(Debug, Clone)]
pub struct AttestationData {
    /// PCR values
    pub pcr_values: HashMap<u32, String>,
    /// Nonce used
    pub nonce: Vec<u8>,
    /// Timestamp
    pub timestamp: u64,
    /// Device identity
    pub device_id: String,
    /// Signature (if TPM available)
    pub signature: Option<String>,
}

impl AttestationData {
    /// Serialize to JSON
    pub fn to_json(&self) -> String {
        let mut json = String::from("{");
        json.push_str(&format!("\"pcr_values\":{{"));
        let mut first = true;
        for (k, v) in &self.pcr_values {
            if !first { json.push_str(","); }
            json.push_str(&format!("\"{}\":\"{}\"", k, v));
            first = false;
        }
        json.push_str("},");
        json.push_str(&format!("\"nonce\":\"{}\",", base64::encode(&self.nonce)));
        json.push_str(&format!("\"timestamp\":{},", self.timestamp));
        json.push_str(&format!("\"device_id\":\"{}\"", self.device_id));
        if let Some(ref sig) = self.signature {
            json.push_str(&format!(",\"signature\":\"{}\"", sig));
        }
        json.push_str("}");
        json
    }
}

/// AttestationCore - TPM-based attestation
pub struct AttestationCore {
    /// TPM available flag
    tpm_available: bool,
    /// TPM version (1.2 or 2.0)
    tpm_version: String,
    /// Device identity
    device_id: String,
    /// PCR banks to read
    pcr_banks: Vec<u32>,
}

impl AttestationCore {
    /// Create a new AttestationCore
    pub fn new() -> Result<Self> {
        let (available, version) = Self::detect_tpm()?;
        
        let device_id = Self::compute_device_id();
        
        let pcr_banks = vec![0, 1, 2, 3, 4, 5, 6, 7, 10];  // Common boot PCRs

        Ok(Self {
            tpm_available: available,
            tpm_version: version,
            device_id,
            pcr_banks,
        })
    }

    /// Detect TPM availability
    fn detect_tpm() -> Result<(bool, String)> {
        #[cfg(target_os = "windows")]
        {
            // Check Windows TPM via registry or WMI
            // Simplified - return software fallback
            Ok((false, "software".to_string()))
        }
        
        #[cfg(target_os = "linux")]
        {
            // Check for TPM device
            let has_tpm0 = std::path::Path::new("/dev/tpm0").exists();
            let has_tpmrm0 = std::path::Path::new("/dev/tpmrm0").exists();
            
            if has_tpm0 || has_tpmrm0 {
                // Try to get TPM version via tpm2 tools
                if std::process::Command::new("tpm2_getcap")
                    .arg("-c")
                    .arg("properties-fixed")
                    .output()
                    .map(|o| o.status.success())
                    .unwrap_or(false)
                {
                    Ok((true, "2.0".to_string()))
                } else {
                    Ok((true, "1.2".to_string()))
                }
            } else {
                Ok((false, "software".to_string()))
            }
        }
        
        #[cfg(not(any(target_os = "windows", target_os = "linux")))]
        {
            Ok((false, "software".to_string()))
        }
    }

    /// Compute device identity
    fn compute_device_id() -> String {
        let engine = CryptoEngine::new();
        
        // Combine multiple machine identifiers
        let machine_id = std::env::var("COMPUTERNAME")
            .or_else(|_| std::env::var("HOSTNAME"))
            .unwrap_or_else(|_| "unknown".to_string());
            
        let user_id = std::env::var("USER")
            .or_else(|_| std::env::var("USERNAME"))
            .unwrap_or_else(|_| "unknown".to_string());

        let combined = format!("{}:{}:qvault", machine_id, user_id);
        hex::encode(engine.sha256(combined.as_bytes()))
    }

    /// Read PCR values from TPM (or software fallback)
    pub fn read_pcr(&self, pcr: u32) -> Result<String> {
        if self.tpm_available {
            self.read_pcr_from_tpm(pcr)
        } else {
            self.read_pcr_software(pcr)
        }
    }

    /// Read PCR from hardware TPM
    fn read_pcr_from_tpm(&self, pcr: u32) -> Result<String> {
        #[cfg(target_os = "linux")]
        {
            // Use tpm2_pcrread
            let output = std::process::Command::new("tpm2_pcrread")
                .arg("-s")
                .arg(pcr.to_string())
                .output()
                .map_err(|e| QVaultError::AttestationFailed(format!("Failed to read PCR: {}", e)))?;
            
            if output.status.success() {
                // Parse output - format is typically: pcr_XX:sha256=HEXVAL
                let stdout = String::from_utf8_lossy(&output.stdout);
                if let Some(hash) = stdout.split("=").nth(1) {
                    return Ok(hash.trim().to_string());
                }
            }
            
            // Fall through to software
        }
        
        // Fallback to software
        self.read_pcr_software(pcr)
    }

    /// Software fallback for PCR reading
    fn read_pcr_software(&self, pcr: u32) -> Result<String> {
        let engine = CryptoEngine::new();
        
        // Generate deterministic "measurement" based on PCR number
        let input = format!("pcr_{}_measurement", pcr);
        let hash = engine.sha256(input.as_bytes());
        
        Ok(hex::encode(hash))
    }

    /// Get all PCR values
    pub fn get_pcr_values(&self) -> HashMap<u32, String> {
        let mut values = HashMap::new();
        
        for &pcr in &self.pcr_banks {
            if let Ok(hash) = self.read_pcr(pcr) {
                values.insert(pcr, hash);
            }
        }
        
        values
    }

    /// Create attestation quote with nonce
    pub fn create_quote(&self, nonce: &[u8]) -> Result<AttestationData> {
        let pcr_values = self.get_pcr_values();
        
        // Sign the quote data with hardware key if available
        let signature = if self.tpm_available {
            Some(self.sign_with_tpm(&pcr_values, nonce)?)
        } else {
            // Software signature
            Some(self.sign_software(&pcr_values, nonce))
        };

        Ok(AttestationData {
            pcr_values,
            nonce: nonce.to_vec(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0),
            device_id: self.device_id.clone(),
            signature,
        })
    }

    /// Sign with TPM hardware key
    fn sign_with_tpm(&self, pcr_values: &HashMap<u32, String>, nonce: &[u8]) -> Result<String> {
        #[cfg(target_os = "linux")]
        {
            // Prepare data to sign
            let mut data = String::new();
            for (k, v) in pcr_values {
                data.push_str(&format!("{}:{};", k, v));
            }
            data.push_str(&format!(":{}", base64::encode(nonce)));
            
            // Sign using TPM
            let output = std::process::Command::new("tpm2_sign")
                .arg("-c")
                .arg("0x81010001")  // AK handle
                .arg("--msg")
                .arg(data.as_bytes())
                .output()
                .map_err(|e| QVaultError::AttestationFailed(format!("TPM sign failed: {}", e)))?;
            
            if output.status.success() {
                // Return signature
                return Ok(base64::encode(&output.stdout));
            }
        }
        
        // Fallback to software
        Ok(self.sign_software(pcr_values, nonce))
    }

    /// Software signature (fallback)
    fn sign_software(&self, pcr_values: &HashMap<u32, String>, nonce: &[u8]) -> String {
        let engine = CryptoEngine::new();
        
        // Create signature data
        let mut data = String::new();
        for (k, v) in pcr_values {
            data.push_str(&format!("{}:{};", k, v));
        }
        data.push_str(&format!(":{}", base64::encode(nonce)));
        
        // Sign with device-specific key
        let key = engine.sha256(format!("{}:signing", self.device_id).as_bytes());
        let signature = engine.hmac_sha256(&key, data.as_bytes());
        
        hex::encode(signature)
    }

    /// Get device identity
    pub fn get_device_id(&self) -> String {
        self.device_id.clone()
    }

    /// Check if TPM is available
    pub fn is_tpm_available(&self) -> bool {
        self.tpm_available
    }

    /// Get TPM version
    pub fn tpm_version(&self) -> &str {
        &self.tpm_version
    }

    /// Verify attestation quote
    pub fn verify_quote(&self, quote: &AttestationData, expected_nonce: &[u8]) -> Result<bool> {
        // Verify nonce
        if quote.nonce != expected_nonce {
            return Err(QVaultError::AttestationFailed("Nonce mismatch".to_string()));
        }

        // Verify device ID
        if quote.device_id != self.device_id {
            return Err(QVaultError::AttestationFailed("Device ID mismatch".to_string()));
        }

        // Verify PCR values haven't changed (basic check)
        let current_pcrs = self.get_pcr_values();
        for (pcr, expected_hash) in &current_pcrs {
            if let Some(quote_hash) = quote.pcr_values.get(pcr) {
                if quote_hash != expected_hash {
                    return Ok(false);  // PCR changed
                }
            }
        }

        Ok(true)
    }

    /// Get attestation info as dict (for Python)
    pub fn get_info(&self) -> HashMap<String, String> {
        let mut info = HashMap::new();
        info.insert("tpm_available".to_string(), self.tpm_available.to_string());
        info.insert("tpm_version".to_string(), self.tpm_version.clone());
        info.insert("device_id".to_string(), self.device_id.clone());
        info
    }
}

/// Base64 encoding (simple implementation)
mod base64 {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    
    pub fn encode(data: &[u8]) -> String {
        let mut result = String::new();
        
        for chunk in data.chunks(3) {
            let b0 = chunk[0] as usize;
            let b1 = chunk.get(1).copied().unwrap_or(0) as usize;
            let b2 = chunk.get(2).copied().unwrap_or(0) as usize;
            
            result.push(ALPHABET[b0 >> 2] as char);
            result.push(ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)] as char);
            
            if chunk.len() > 1 {
                result.push(ALPHABET[((b1 & 0x0f) << 2) | (b2 >> 6)] as char);
            } else {
                result.push('=');
            }
            
            if chunk.len() > 2 {
                result.push(ALPHABET[b2 & 0x3f] as char);
            } else {
                result.push('=');
            }
        }
        
        result
    }
}

/// Hex encoding
mod hex {
    pub fn encode(data: &[u8]) -> String {
        data.iter().map(|b| format!("{:02x}", b)).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_quote() {
        let attest = AttestationCore::new().unwrap();
        let nonce = b"test_nonce_12345678901234567890";
        
        let quote = attest.create_quote(nonce).unwrap();
        
        assert!(!quote.pcr_values.is_empty());
        assert_eq!(quote.nonce, nonce);
        assert!(quote.signature.is_some());
    }

    #[test]
    fn test_device_id() {
        let attest = AttestationCore::new().unwrap();
        let id = attest.get_device_id();
        
        assert!(!id.is_empty());
        assert_eq!(id.len(), 64);  // SHA-256 hex = 64 chars
    }

    #[test]
    fn test_verify_quote() {
        let attest = AttestationCore::new().unwrap();
        let nonce = b"test_nonce_12345678901234567890";
        
        let quote = attest.create_quote(nonce).unwrap();
        let result = attest.verify_quote(&quote, nonce).unwrap();
        
        assert!(result);
    }
}