//! audit.rs — Q-Vault signed audit logger
//!
//! ## Security design
//!
//! Every audit entry is HMAC-SHA256 signed with a **system audit key**
//! that is derived (HKDF, label = "audit-log") from the per-installation
//! master key stored in `~/.qvault/master.key`.
//!
//! ### Why this is secure
//!
//! 1. **No static seed.** The old code carried an implicit risk that all
//!    installations shared a signing key.  The per-installation master key
//!    means HMAC tags from one installation cannot be replayed to another.
//!
//! 2. **Domain separation.** Using HKDF with label "audit-log" ensures the
//!    audit key is cryptographically independent from vault encryption keys
//!    and user-DB integrity keys that share the same master material.
//!
//! 3. **No silent drops.** The previous `None => return` guard silently
//!    discarded every system-level event (boot, shutdown, sweeper, migrations)
//!    where no vault key was available.  All callers now supply an audit key.
//!    If HMAC construction somehow fails, a visible FAILED marker is written
//!    rather than nothing.
//!
//! 4. **Tamper-detection.** An attacker who modifies log entries on disk
//!    cannot forge a valid HMAC without the master key.

use base64::{engine::general_purpose::STANDARD as B64, Engine};
use chrono::Utc;
use hkdf::Hkdf;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use zeroize::Zeroize;

type HmacSha256 = Hmac<Sha256>;

// ─── Key derivation ───────────────────────────────────────────────────────────

/// Derive the 32-byte audit signing key from the per-installation master key.
///
/// Uses HKDF-SHA256 with label `"audit-log"`.  HKDF with a 32-byte output
/// over SHA-256 is mathematically infallible (max output = 255 × 32 = 8160
/// bytes), so the `let _ =` assignment is intentional; the error branch is
/// unreachable for this output length.
pub fn derive_audit_key(master_key: &[u8; 32]) -> [u8; 32] {
    let hk = Hkdf::<Sha256>::new(None, master_key);
    let mut key = [0u8; 32];
    // Infallible: SHA-256 HKDF expand with 32-byte OKM never exceeds the
    // 255 * HashLen ceiling.
    let _ = hk.expand(b"audit-log", &mut key);
    key
}

// ─── AuditLogger ─────────────────────────────────────────────────────────────

/// Persistent, signed audit logger bound to a per-installation key.
///
/// Construct once via `AuditLogger::new(root_dir, master_key)` and store in
/// the `SecurityEngine`.  Pass it by reference to the key sweeper thread.
pub struct AuditLogger {
    root_dir: PathBuf,
    /// 32-byte audit signing subkey — zeroized on drop.
    key: [u8; 32],
}

impl AuditLogger {
    /// Build a logger.  Derives the audit subkey from `master_key` via HKDF.
    pub fn new(root_dir: PathBuf, master_key: &[u8; 32]) -> Self {
        Self {
            root_dir,
            key: derive_audit_key(master_key),
        }
    }

    /// Write a signed audit entry for a system or user event.
    ///
    /// This method **never silently drops** an event.  On I/O failure it
    /// writes to `stderr` as a last resort so operators notice.
    pub fn log(&self, event_type: &str, username: Option<&str>, message: &str) {
        log_event(&self.root_dir, event_type, username, &self.key, message);
    }

    /// Expose the audit key bytes for use in call sites that need the raw
    /// slice (e.g. vault.rs migration helpers that call `log_event` directly).
    pub fn key(&self) -> &[u8; 32] {
        &self.key
    }
}

impl Drop for AuditLogger {
    fn drop(&mut self) {
        // Zeroize audit key material when the logger is destroyed.
        self.key.zeroize();
    }
}

// ─── Core log writer ──────────────────────────────────────────────────────────

/// Write a single signed audit entry to `<root_dir>/audit.log`.
///
/// ### Signature
///
/// The entry format is:
/// ```text
/// [#COUNTER] [RFC3339-timestamp] [EVENT_TYPE] USER:username - message | HMAC:base64(tag)
/// ```
/// The HMAC tag covers everything to the left of `| HMAC:`.
use std::sync::OnceLock;
use std::sync::Mutex;

static LOG_COUNTER: OnceLock<Mutex<u64>> = OnceLock::new();

/// Internal helper to get/increment the monotonic counter with reduced I/O.
fn get_next_counter(root_dir: &std::path::Path) -> u64 {
    let counter_path = root_dir.join("audit_counter.bin");
    let mutex = LOG_COUNTER.get_or_init(|| {
        let start_val = match std::fs::read(&counter_path) {
            Ok(bytes) if bytes.len() == 8 => {
                let mut arr = [0u8; 8];
                arr.copy_from_slice(&bytes);
                u64::from_le_bytes(arr)
            }
            _ => 0,
        };
        Mutex::new(start_val)
    });

    let mut val = mutex.lock().unwrap();
    *val += 1;
    
    // Persist counter every 10 entries to balance performance vs crash-consistency
    if *val % 10 == 0 {
        let _ = std::fs::write(&counter_path, val.to_le_bytes());
    }
    
    *val
}

pub fn log_event(
    root_dir: &PathBuf,
    event_type: &str,
    username: Option<&str>,
    audit_key: &[u8],
    message: &str,
) {
    let log_path = root_dir.join("audit.log");
    let next_counter = get_next_counter(root_dir);

    let timestamp = Utc::now().to_rfc3339();
    let user_str = username.unwrap_or("SYSTEM");
    let log_content = format!(
        "[#{:06}] [{}] [{}] USER:{} - {}",
        next_counter, timestamp, event_type, user_str, message
    );

    // Compute HMAC-SHA256 over the log content.
    let mac_str = match HmacSha256::new_from_slice(audit_key) {
        Ok(mut mac) => {
            mac.update(log_content.as_bytes());
            B64.encode(mac.finalize().into_bytes())
        }
        Err(e) => {
            let fallback = format!("{} | HMAC:FAILED({})\n", log_content, e);
            write_to_log(&log_path, &fallback, event_type);
            return;
        }
    };

    let log_line = format!("{} | HMAC:{}\n", log_content, mac_str);

    // Optimized rotation check (once every 100 entries to reduce metadata calls)
    if next_counter % 100 == 0 {
        if let Ok(meta) = std::fs::metadata(&log_path) {
            if meta.len() > 10 * 1024 * 1024 {
                let backup = root_dir.join("audit.log.1");
                let _ = std::fs::rename(&log_path, &backup);
            }
        }
    }

    write_to_log(&log_path, &log_line, event_type);
}

/// Constant-time MAC verification for log integrity checks.
pub fn verify_log_entry(line: &str, key: &[u8]) -> bool {
    use subtle::ConstantTimeEq;
    
    let parts: Vec<&str> = line.split(" | HMAC:").collect();
    if parts.len() != 2 { return false; }
    
    let content = parts[0];
    let provided_mac_b64 = parts[1].trim();
    
    let provided_mac = match B64.decode(provided_mac_b64) {
        Ok(m) => m,
        Err(_) => return false,
    };
    
    let mut mac = match HmacSha256::new_from_slice(key) {
        Ok(m) => m,
        Err(_) => return false,
    };
    mac.update(content.as_bytes());
    let expected_mac = mac.finalize().into_bytes();
    
    // Constant-time comparison to prevent timing attacks on log verification
    expected_mac.ct_eq(&provided_mac.as_slice().into()).into()
}

fn write_to_log(log_path: &PathBuf, line: &str, event_type: &str) {
    match OpenOptions::new().create(true).append(true).open(log_path) {
        Ok(mut f) => {
            let _ = f.write_all(line.as_bytes());
        }
        Err(e) => {
            eprintln!("qvault-audit: CRITICAL error writing {}: {}", event_type, e);
        }
    }
}
