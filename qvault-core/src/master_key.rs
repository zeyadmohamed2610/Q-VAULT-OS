use rand::rngs::OsRng;
use rand::RngCore;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::PathBuf;
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Zeroize, ZeroizeOnDrop)]
pub struct MasterKey {
    key: [u8; 32],
}

impl MasterKey {
    pub fn load_or_create(root_dir: &PathBuf) -> Result<Self, String> {
        let key_path = root_dir.join("master.key");

        if key_path.exists() {
            let mut file = OpenOptions::new()
                .read(true)
                .open(&key_path)
                .map_err(|e| format!("Failed to open master key: {}", e))?;

            let mut key = [0u8; 32];
            file.read_exact(&mut key)
                .map_err(|e| format!("Failed to read master key: {}", e))?;

            Ok(Self { key })
        } else {
            let mut key = [0u8; 32];
            OsRng.fill_bytes(&mut key);

            // Ensure directory exists
            if let Some(parent) = key_path.parent() {
                fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }

            let mut file = OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .open(&key_path)
                .map_err(|e| format!("Failed to create master key: {}", e))?;

            file.write_all(&key)
                .map_err(|e| format!("Failed to write master key: {}", e))?;
            file.sync_all()
                .map_err(|e| format!("Failed to sync master key: {}", e))?;

            crate::vault::secure_file(&key_path)?;

            Ok(Self { key })
        }
    }

    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.key
    }
}
