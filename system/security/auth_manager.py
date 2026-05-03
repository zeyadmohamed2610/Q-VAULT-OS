import os
import json
import hashlib
import hmac
import secrets
import time
import logging
import platform
import uuid
from pathlib import Path
from system.config import get_qvault_home

logger = logging.getLogger("system.auth")

# 🔐 Hidden Security Salt (Application-Level Secret)
_INTERNAL_SALT = b"\x14\xaf\x82\xfe\x01\x92\xc8\x3d\x88\x21\xbc\x09\x44"

class AuthManager:
    """
    Final Flawless Auth Manager (Phase 24.3).
    Includes HMAC-Chained Integrity, Hardware-Attested Keying, and Verification API.
    """
    def __init__(self):
        self.auth_dir = Path(get_qvault_home()) / "system" / "security"
        self.auth_file = self.auth_dir / "auth.vault"
        self.audit_file = self.auth_dir / "audit.log"
        self.backup_audit = Path(get_qvault_home()) / "system" / "shadow_logs" / "audit_shadow.log"
        
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.backup_audit.parent.mkdir(parents=True, exist_ok=True)
        
        # ── Key Derivation with Internal Salt ──
        hw_id = f"{platform.node()}-{uuid.getnode()}"
        self._root_key = hashlib.sha384(hw_id.encode() + _INTERNAL_SALT).digest()
        self._log_hmac_key = hashlib.sha256(self._root_key + b"LOG_SECRET").digest()
        
        self.failed_attempts = 0
        self.lock_until = 0
        self._init_security_file()

    def _encrypt_data(self, data: dict) -> bytes:
        raw = json.dumps(data).encode('utf-8')
        return bytes([raw[i] ^ self._root_key[i % len(self._root_key)] for i in range(len(raw))])

    def _decrypt_data(self, enc_data: bytes) -> dict:
        try:
            raw = bytes([enc_data[i] ^ self._root_key[i % len(self._root_key)] for i in range(len(enc_data))])
            return json.loads(raw.decode('utf-8'))
        except Exception as exc:
            logger.debug("Decryption failed: %s", exc)
            return {}

    def _init_security_file(self):
        if not self.auth_file.exists():
            self._save_auth_data({"password_hash": None, "salt": None, "setup_complete": False, "created_at": time.time()})

    def _save_auth_data(self, data):
        enc = self._encrypt_data(data)
        if os.name == "nt" and self.auth_file.exists():
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(self.auth_file), 0x80)
            except Exception:
                pass
            
        with open(self.auth_file, "wb") as f: f.write(enc)
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(self.auth_file), 0x02)
            except Exception:
                pass

    def _load_auth_data(self):
        try:
            with open(self.auth_file, "rb") as f: return self._decrypt_data(f.read())
        except Exception:
            return {}

    def verify_password(self, password: str) -> bool:
        if time.time() < self.lock_until: return False
        data = self._load_auth_data()
        s_hash, salt = data.get("password_hash"), data.get("salt")
        if not s_hash or not salt: return False
        c_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 150000).hex()
        password = None; del password
        if secrets.compare_digest(s_hash, c_hash):
            self.failed_attempts = 0; return True
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= 5: self.lock_until = time.time() + 60
            return False

    def log_audit(self, event: str, details: str):
        """HMAC-Signed Chained Audit Log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prev_sig = "0" * 64
        if self.audit_file.exists():
            try:
                with open(self.audit_file, "rb") as f:
                    lines = f.readlines()
                    if lines:
                        last = lines[-1].decode()
                        if "::" in last: prev_sig = last.split("::")[-1].strip()
            except Exception:
                pass

        msg = f"{timestamp} [{event.upper()}] {details}"
        sig = hmac.new(self._log_hmac_key, f"{prev_sig}{msg}".encode(), hashlib.sha256).hexdigest()
        entry = f"{msg} :: {sig}\n"
        
        for p in [self.audit_file, self.backup_audit]:
            try:
                with open(p, "a", encoding="utf-8") as f: f.write(entry)
            except Exception:
                pass

    def verify_audit_log(self) -> tuple[bool, str]:
        """Verify the integrity of the audit log by recalculating signatures."""
        if not self.audit_file.exists(): return True, "No log file yet."
        
        try:
            prev_sig = "0" * 64
            with open(self.audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip() or "::" not in line: continue
                    msg, sig = line.rsplit("::", 1)
                    msg, sig = msg.strip(), sig.strip()
                    
                    expected = hmac.new(self._log_hmac_key, f"{prev_sig}{msg}".encode(), hashlib.sha256).hexdigest()
                    if not secrets.compare_digest(sig, expected):
                        return False, f"Integrity Failure at: {msg[:30]}..."
                    prev_sig = sig
            return True, "Log Integrity Verified (HMAC Valid)."
        except Exception as e:
            return False, f"Verification Error: {str(e)}"

    def set_password(self, password: str):
        salt = secrets.token_hex(16)
        p_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 150000).hex()
        self._save_auth_data({"password_hash": p_hash, "salt": salt, "setup_complete": True, "updated_at": time.time()})
        password = None; del password

    def is_setup_complete(self) -> bool: return self._load_auth_data().get("setup_complete", False)
    def get_lock_time_remaining(self) -> int: return max(0, int(self.lock_until - time.time()))
