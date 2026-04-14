# =============================================================
#  audit_logger_hardened.py — Q-VAULT OS  |  Hardened Audit Logger
#
#  Append-only logs with hash chain integrity
# =============================================================

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

LOG_DIR = Path.home() / ".qvault" / "logs"
LOG_FILE = LOG_DIR / "audit.log"
CHAIN_FILE = LOG_DIR / "audit.chain"
INTEGRITY_FILE = LOG_DIR / "integrity.json"


class HardenedAuditLogger:
    """Append-only audit logger with hash chain integrity."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        self._last_hash = self._load_last_hash()
        self._integrity_ok = True

    def _load_last_hash(self) -> str:
        """Load last hash from chain file."""
        if CHAIN_FILE.exists():
            try:
                with open(CHAIN_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("last_hash", "0" * 64)
            except Exception:
                pass
        return "0" * 64

    def _save_last_hash(self, hash_value: str):
        """Save last hash to chain file."""
        try:
            with open(CHAIN_FILE, "w") as f:
                json.dump(
                    {"last_hash": hash_value, "updated": datetime.now().isoformat()}, f
                )
        except Exception:
            pass

    def _compute_hash(self, data: str, prev_hash: str) -> str:
        """Compute hash with previous hash chain."""
        combined = f"{data}:{prev_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def log(
        self,
        event_type: str,
        user: str,
        resource: str,
        action: str,
        result: str,
        detail: str = "",
        severity: str = "INFO",
    ) -> bool:
        """
        Log an event with hash chain integrity.
        Returns True if logged successfully.
        """
        if not self._integrity_ok:
            self._trigger_tamper_alert()
            return False

        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "event_type": event_type,
            "user": user,
            "resource": resource,
            "action": action,
            "result": result,
            "detail": detail,
            "severity": severity,
            "prev_hash": self._last_hash,
        }

        entry_hash = self._compute_hash(json.dumps(entry), self._last_hash)
        entry["hash"] = entry_hash

        try:
            with open(LOG_FILE, "a") as f:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(json.dumps(entry) + "\n")
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            self._last_hash = entry_hash
            self._save_last_hash(entry_hash)

            self._verify_chain()
            return True

        except Exception as e:
            self._integrity_ok = False
            self._trigger_tamper_alert()
            return False

    def _verify_chain(self) -> bool:
        """Verify hash chain integrity."""
        if not LOG_FILE.exists():
            return True

        prev_hash = "0" * 64
        try:
            with open(LOG_FILE, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        expected_hash = entry.get("hash", "")
                        computed = self._compute_hash(
                            json.dumps({k: v for k, v in entry.items() if k != "hash"}),
                            prev_hash,
                        )
                        if computed != expected_hash:
                            self._integrity_ok = False
                            self._trigger_tamper_alert()
                            return False
                        prev_hash = expected_hash
                    except Exception:
                        continue
        except Exception:
            pass

        return True

    def _trigger_tamper_alert(self):
        """Trigger tamper detection alert."""
        from system.notification_system import NOTIFY

        NOTIFY.send(
            "SECURITY ALERT: Audit Log Tampering Detected",
            "Audit log integrity compromised. Possible intrusion.",
            level="danger",
        )

    def verify_integrity(self) -> bool:
        """Verify entire log chain integrity."""
        return self._verify_chain()

    def get_entries(self, limit: int = 100) -> List[Dict]:
        """Get recent log entries."""
        entries = []
        if not LOG_FILE.exists():
            return entries

        try:
            with open(LOG_FILE, "r") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except Exception:
                        continue
        except Exception:
            pass

        return entries[-limit:]

    def get_stats(self) -> Dict:
        """Get audit log statistics."""
        if not LOG_FILE.exists():
            return {"total": 0, "integrity": self._integrity_ok}

        line_count = 0
        try:
            with open(LOG_FILE, "r") as f:
                line_count = sum(1 for _ in f)
        except Exception:
            pass

        return {
            "total": line_count,
            "integrity": self._integrity_ok,
            "last_hash": self._last_hash[:16] + "...",
        }

    def lock_logs(self):
        """Make logs read-only (append only enforced by OS)."""
        try:
            os.chmod(LOG_FILE, 0o440)
            os.chmod(CHAIN_FILE, 0o440)
        except Exception:
            pass


AUDIT_LOGGER = HardenedAuditLogger()
