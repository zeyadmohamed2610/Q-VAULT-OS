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
/// [RFC3339-timestamp] [EVENT_TYPE] USER:username - message | HMAC:base64(tag)
/// ```
/// The HMAC tag covers everything to the left of `| HMAC:`.
///
/// ### Failure handling
///
/// * If HMAC construction fails (should never happen for 32-byte keys) the
///   line is written with `HMAC:FAILED(reason)` so the gap is visible.
/// * If the log file cannot be opened, a message is printed to `stderr`.
///   Neither case silently drops the event.
///
/// ### Rotation
///
/// The log is rotated to `audit.log.1` when it exceeds 10 MiB.
pub fn log_event(
    root_dir: &PathBuf,
    event_type: &str,
    username: Option<&str>,
    audit_key: &[u8],       // ← required; was `Option<&[u8]>` with `None => return`
    message: &str,
) {
    let log_path = root_dir.join("audit.log");
    let timestamp = Utc::now().to_rfc3339();
    let user_str = username.unwrap_or("SYSTEM");
    let log_content = format!(
        "[{}] [{}] USER:{} - {}",
        timestamp, event_type, user_str, message
    );

    // Compute HMAC-SHA256 over the log content.
    // Fail-visible: write a FAILED marker rather than dropping the entry.
    let mac_str = match HmacSha256::new_from_slice(audit_key) {
        Ok(mut mac) => {
            mac.update(log_content.as_bytes());
            B64.encode(mac.finalize().into_bytes())
        }
        Err(e) => {
            // This branch is reached only if `audit_key` is somehow zero-length,
            // which cannot happen for a correctly-derived 32-byte key.
            // Write a visible failure marker rather than dropping the entry.
            let fallback = format!("{} | HMAC:FAILED({})\n", log_content, e);
            write_to_log(&log_path, &fallback, event_type);
            return;
        }
    };

    let log_line = format!("{} | HMAC:{}\n", log_content, mac_str);

    // Rotate at 10 MiB.
    if let Ok(meta) = std::fs::metadata(&log_path) {
        if meta.len() > 10 * 1024 * 1024 {
            let backup = root_dir.join("audit.log.1");
            let _ = std::fs::rename(&log_path, &backup);
        }
    }

    write_to_log(&log_path, &log_line, event_type);
}

/// Append `line` to `log_path`.  Prints to `stderr` on failure — does not
/// panic, does not silently discard.
fn write_to_log(log_path: &PathBuf, line: &str, event_type: &str) {
    match OpenOptions::new().create(true).append(true).open(log_path) {
        Ok(mut f) => {
            if f.write_all(line.as_bytes()).is_err() {
                eprintln!(
                    "qvault-audit: WARNING: failed to write entry (event={})",
                    event_type
                );
            }
        }
        Err(e) => {
            eprintln!(
                "qvault-audit: CRITICAL: cannot open audit log {}: {}",
                log_path.display(),
                e
            );
        }
    }
}
