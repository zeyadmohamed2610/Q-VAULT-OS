//! session.rs — TTL-enforced session management with vault key binding
//!
//! Each session stores:
//!   - username
//!   - role (RBAC)
//!   - expiration timestamp (1-hour TTL)
//!   - reference token for vault key lookup
//!
//! Security invariants:
//!   - TTL enforced on EVERY access via get_session()
//!   - Expired sessions are immediately deleted
//!   - Tokens are UUID v4 (cryptographically random)
//!   - logout() invalidates session AND signals vault key zeroization

use crate::rbac::Role;
use chrono::{DateTime, Duration, Utc};
use std::sync::{Arc, Mutex};
use subtle::ConstantTimeEq;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct Session {
    pub username: String,
    pub role: Role,
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub token: String,
}

impl Session {
    pub fn is_valid(&self) -> bool {
        Utc::now() < self.expires_at
    }
}

pub struct SessionManager {
    sessions: Arc<Mutex<HashMap<String, Session>>>,
}

impl SessionManager {
    pub fn new() -> Self {
        Self {
            sessions: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Create a session. Returns the UUID v4 token.
    pub fn create_session(&self, username: String, role: Role) -> Result<String, String> {
        self.cleanup();

        // Enforce max 3 sessions per user
        let mut map = self.sessions.lock().map_err(|_| crate::error::SecurityError::StateCorruption.to_string())?;

        let mut user_sessions: Vec<(String, DateTime<Utc>)> = map
            .iter()
            .filter(|(_, s)| s.username == username)
            .map(|(t, s)| (t.clone(), s.created_at))
            .collect();
        
        if user_sessions.len() >= 3 {
            user_sessions.sort_by(|a, b| a.1.cmp(&b.1));
            for i in 0..=(user_sessions.len() - 3) {
                map.remove(&user_sessions[i].0);
            }
        }

        let token = Uuid::new_v4().to_string();
        let now = Utc::now();
        let expires_at = now + Duration::hours(1);

        let session = Session {
            username,
            role,
            created_at: now,
            expires_at,
            token: token.clone(),
        };

        map.insert(token.clone(), session);
        Ok(token)
    }

    /// Retrieve a session. Enforces TTL on every call. Uses constant-time string comparison.
    pub fn get_session(&self, token: &str) -> Option<Session> {
        let mut map = self.sessions.lock().ok()?;

        let mut matched_key: Option<String> = None;
        let token_bytes = token.as_bytes();
        
        for (k, _) in map.iter() {
            let k_bytes = k.as_bytes();
            if k_bytes.len() == token_bytes.len() {
                if k_bytes.ct_eq(token_bytes).unwrap_u8() == 1 {
                    matched_key = Some(k.clone());
                }
            }
        }

        if let Some(key) = matched_key {
            if let Some(session) = map.get(&key) {
                if session.is_valid() {
                    return Some(session.clone());
                }
            }
            map.remove(&key);
        }
        None
    }

    /// Hard-invalidate a session using constant-time check.
    pub fn invalidate_session(&self, token: &str) {
        let mut map = if let Ok(guard) = self.sessions.lock() { guard } else { return; };
        let mut matched_key: Option<String> = None;
        let token_bytes = token.as_bytes();
        
        for (k, _) in map.iter() {
            let k_bytes = k.as_bytes();
            if k_bytes.len() == token_bytes.len() {
                if k_bytes.ct_eq(token_bytes).unwrap_u8() == 1 {
                    matched_key = Some(k.clone());
                }
            }
        }
        
        if let Some(key) = matched_key {
            map.remove(&key);
        }
    }

    /// Collect all expired tokens (for vault key cleanup).
    pub fn collect_expired(&self) -> Vec<String> {
        let mut map = if let Ok(guard) = self.sessions.lock() { guard } else { return Vec::new(); };
        let now = Utc::now();
        let expired: Vec<String> = map
            .iter()
            .filter(|(_, s)| s.expires_at <= now)
            .map(|(t, _)| t.clone())
            .collect();

        for t in &expired {
            map.remove(t);
        }
        expired
    }

    /// Evict expired sessions.
    fn cleanup(&self) {
        let mut map = if let Ok(guard) = self.sessions.lock() { guard } else { return; };
        let now = Utc::now();
        map.retain(|_, s| s.expires_at > now);
    }
}
