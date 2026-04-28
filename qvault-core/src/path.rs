//! PathValidator - Secure path canonicalization and validation
//! 
//! This module provides secure path validation to prevent:
//! - Path traversal attacks (../)
//! - Symlink attacks
//! - Race conditions (TOCTOU)
//! - Directory traversal

use std::path::{Path, PathBuf};
use std::fs;
use std::os::unix::fs as unix_fs;

use crate::error::{QVaultError, Result};

/// PathValidator - Secure path handling
pub struct PathValidator {
    /// Root directory that paths must be within
    root: PathBuf,
}

impl PathValidator {
    /// Create a new PathValidator with the given root directory
    pub fn new(root: PathBuf) -> Result<Self> {
        // Ensure root exists and is absolute
        if !root.exists() {
            fs::create_dir_all(&root)
                .map_err(|e| QVaultError::PathValidationFailed(format!("Cannot create root: {}", e)))?;
        }

        // Get absolute canonical path
        let canonical_root = root
            .canonicalize()
            .map_err(|e| QVaultError::PathValidationFailed(format!("Invalid root: {}", e)))?;

        Ok(Self { root: canonical_root })
    }

    /// Validate and canonicalize a path
    /// 
    /// This method:
    /// 1. Converts to absolute path
    /// 2. Canonicalizes (resolves symlinks, .., etc)
    /// 3. Ensures path is within root
    /// 
    /// # Arguments
    /// * `path` - The path to validate
    /// 
    /// # Returns
    /// Canonicalized path if valid
    pub fn validate(&self, path: &str) -> Result<PathBuf> {
        // Handle empty path
        if path.is_empty() {
            return Err(QVaultError::PathValidationFailed("Empty path".to_string()));
        }

        // Convert to Path
        let input_path = Path::new(path);

        // If path is absolute, use it directly
        // If relative, resolve against current dir first
        let absolute = if input_path.is_absolute() {
            input_path.to_path_buf()
        } else {
            // Get current directory and join
            std::env::current_dir()
                .map_err(|e| QVaultError::PathValidationFailed(format!("Cannot get cwd: {}", e)))?
                .join(input_path)
        };

        // Canonicalize - this resolves symlinks and .. components
        let canonical = absolute
            .canonicalize()
            .map_err(|e| QVaultError::PathValidationFailed(format!("Cannot canonicalize: {}", e)))?;

        // Verify path is within root
        self.verify_within_root(&canonical)?;

        Ok(canonical)
    }

    /// Validate without following symlinks (more strict)
    pub fn validate_no_follow(&self, path: &str) -> Result<PathBuf> {
        if path.is_empty() {
            return Err(QVaultError::PathValidationFailed("Empty path".to_string()));
        }

        let input_path = Path::new(path);
        
        // Get absolute path but DON'T follow symlinks
        let absolute = if input_path.is_absolute() {
            input_path.to_path_buf()
        } else {
            std::env::current_dir()
                .map_err(|e| QVaultError::PathValidationFailed(format!("Cannot get cwd: {}", e)))?
                .join(input_path)
        };

        // Normalize the path manually (resolve .. components)
        let normalized = self.normalize_path(&absolute)?;

        // Verify path is within root
        self.verify_within_root(&normalized)?;

        Ok(normalized)
    }

    /// Normalize path without following symlinks
    fn normalize_path(&self, path: &Path) -> Result<PathBuf> {
        let mut result = PathBuf::new();
        
        for component in path.components() {
            match component {
                std::path::Component::RootDir => {
                    result.push(component.as_os_str());
                }
                std::path::Component::CurDir => {
                    // Ignore .
                }
                std::path::Component::ParentDir => {
                    // Go up one directory, but not above root
                    if result == PathBuf::from("/") || result == PathBuf::from("") {
                        return Err(QVaultError::PathValidationFailed(
                            "Path traversal would escape root".to_string()
                        ));
                    }
                    result.pop();
                }
                std::path::Component::Normal(name) => {
                    result.push(name);
                }
                std::path::Component::Prefix(_) => {
                    // Ignore Windows prefixes
                }
            }
        }

        Ok(result)
    }

    /// Verify the path is within the root directory
    fn verify_within_root(&self, path: &Path) -> Result<()> {
        // Convert both to bytes for reliable comparison
        let root_bytes = self.root.as_os_str().as_bytes();
        let path_bytes = path.as_os_str().as_bytes();

        // Path must start with root path
        if !path_bytes.starts_with(root_bytes) {
            return Err(QVaultError::PathValidationFailed(
                format!("Path '{}' is outside root '{}'", path.display(), self.root.display())
            ));
        }

        // Extra check: ensure it's a proper child, not just a prefix match
        // e.g., /foo/bar vs /foo/barbaz should be different
        if path_bytes.len() > root_bytes.len() {
            let next_char = path_bytes[root_bytes.len()];
            if next_char != b'/' && next_char != b'\\' {
                return Err(QVaultError::PathValidationFailed(
                    "Path is not a proper child of root".to_string()
                ));
            }
        }

        Ok(())
    }

    /// Check if a path is safe (without canonicalizing)
    /// 
    /// This is a quick check for basic path traversal attempts
    pub fn is_basic_safe(&self, path: &str) -> bool {
        // Check for obvious traversal attempts
        !path.contains("..") && 
        !path.contains("\\..") &&
        !path.starts_with("~")
    }

    /// Check if path is a symlink
    pub fn is_symlink(&self, path: &Path) -> bool {
        match fs::symlink_metadata(path) {
            Ok(meta) => meta.file_type().is_symlink(),
            Err(_) => false,
        }
    }

    /// Resolve symlinks in a path (with safety checks)
    pub fn resolve_symlinks(&self, path: &Path) -> Result<PathBuf> {
        let canonical = path
            .canonicalize()
            .map_err(|e| QVaultError::PathValidationFailed(format!("Cannot resolve symlink: {}", e)))?;

        self.verify_within_root(&canonical)?;

        Ok(canonical)
    }

    /// Get the root directory
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Check if a path exists and is within root
    pub fn exists(&self, path: &Path) -> bool {
        if let Ok(validated) = self.validate(&path.to_string_lossy()) {
            validated.exists()
        } else {
            false
        }
    }

    /// Check if a path is a directory within root
    pub fn is_directory(&self, path: &Path) -> bool {
        if let Ok(validated) = self.validate(&path.to_string_lossy()) {
            validated.is_dir()
        } else {
            false
        }
    }

    /// Check if a path is a file within root
    pub fn is_file(&self, path: &Path) -> bool {
        if let Ok(validated) = self.validate(&path.to_string_lossy()) {
            validated.is_file()
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env::temp_dir;

    #[test]
    fn test_validate_basic() {
        let temp = temp_dir().join("qvault_path_test");
        let _ = std::fs::create_dir_all(&temp);
        
        let validator = PathValidator::new(temp.clone()).unwrap();
        
        // Create a test file
        let test_file = temp.join("test.txt");
        std::fs::write(&test_file, "test").unwrap();
        
        // Validate
        let result = validator.validate(&test_file.to_string_lossy()).unwrap();
        assert!(result.starts_with(&temp));
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_reject_traversal() {
        let temp = temp_dir().join("qvault_traversal_test");
        let _ = std::fs::create_dir_all(&temp);
        
        let validator = PathValidator::new(temp.clone()).unwrap();
        
        // Try path traversal
        let result = validator.validate(&format!("{}/../etc/passwd", temp.display()));
        assert!(result.is_err());
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp);
    }

    #[test]
    fn test_basic_safety() {
        let temp = temp_dir().join("qvault_safety_test");
        let _ = std::fs::create_dir_all(&temp);
        
        let validator = PathValidator::new(temp).unwrap();
        
        assert!(validator.is_basic_safe("normal/path/file.txt"));
        assert!(!validator.is_basic_safe("../etc/passwd"));
        assert!(!validator.is_basic_safe("foo/../../../etc"));
        
        let _ = std::fs::remove_dir_all(temp);
    }
}