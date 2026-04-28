use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use chrono::Utc;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use base64::{engine::general_purpose::STANDARD as B64, Engine};
type HmacSha256 = Hmac<Sha256>;

use hkdf::Hkdf;

pub fn log_event(root_dir: &PathBuf, event_type: &str, username: Option<&str>, vault_key: Option<&[u8]>, message: &str) {
    let mut log_path = root_dir.clone();
    log_path.push("audit.log");

    let timestamp = Utc::now().to_rfc3339();
    let user_str = username.unwrap_or("SYSTEM");
    let log_content = format!("[{}] [{}] USER:{} - {}", timestamp, event_type, user_str, message);
    
    let key_bytes = match vault_key {
        Some(k) => k,
        None => return, // No unsigned entries allowed
    };

    let mac_str = {
        let hk = Hkdf::<Sha256>::new(None, key_bytes);
        let mut audit_key = [0u8; 32];
        if hk.expand(b"audit-log", &mut audit_key).is_ok() {
            if let Ok(mut mac) = HmacSha256::new_from_slice(&audit_key) {
                mac.update(log_content.as_bytes());
                B64.encode(mac.finalize().into_bytes())
            } else {
                return; // Fail safe
            }
        } else {
            return; // Fail safe
        }
    };
    
    let log_line = format!("{} | HMAC:{}\n", log_content, mac_str);

    // Phase 4: Audit Log Rotation. Max size: 10MB
    if let Ok(metadata) = std::fs::metadata(&log_path) {
        if metadata.len() > 10 * 1024 * 1024 {
            let mut backup_path = root_dir.clone();
            backup_path.push("audit.log.1");
            let _ = std::fs::rename(&log_path, &backup_path);
        }
    }

    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&log_path) {
        let _ = file.write_all(log_line.as_bytes());
        let _ = file.flush();
        let _ = file.sync_data();
    }
}
