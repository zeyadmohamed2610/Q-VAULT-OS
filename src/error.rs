//! Q-Vault Core Error Types

use pyo3::PyErr;
use thiserror::Error;

/// Q-Vault Core error type
#[derive(Error, Debug)]
pub enum QVaultError {
    #[error("TPM not available")]
    TpmNotAvailable,
    
    #[error("Invalid key length: {0}")]
    InvalidKeyLength(usize),
    
    #[error("Encryption failed: {0}")]
    EncryptionFailed(String),
    
    #[error("Decryption failed: {0}")]
    DecryptionFailed(String),
    
    #[error("Path validation failed: {0}")]
    PathValidationFailed(String),
    
    #[error("Attestation failed: {0}")]
    AttestationFailed(String),
    
    #[error("Key not found: {0}")]
    KeyNotFound(String),
    
    #[error("Invalid input: {0}")]
    InvalidInput(String),
}

impl From<QVaultError> for PyErr {
    fn from(err: QVaultError) -> PyErr {
        use pyo3::exceptions::PyValueError;
        PyValueError::new_err(err.to_string())
    }
}

/// Result type alias
pub type Result<T> = std::result::Result<T, QVaultError>;

#[derive(Error, Debug)]
pub enum SecurityError {
    #[error("State corruption: Mutex poisoned")]
    StateCorruption,
    #[error("MAC error: {0}")]
    MacError(String),
    #[error("File error: {0}")]
    FileError(String),
}

impl From<SecurityError> for PyErr {
    fn from(err: SecurityError) -> PyErr {
        use pyo3::exceptions::PyRuntimeError;
        PyRuntimeError::new_err(err.to_string())
    }
}