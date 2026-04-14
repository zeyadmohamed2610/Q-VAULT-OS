# =============================================================
#  file_integrity_monitor.py — Q-VAULT OS  |  File Integrity Monitor
#
#  Monitor critical file integrity and detect tampering
# =============================================================

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

INTEGRITY_DB = Path.home() / ".qvault" / "integrity_db.json"
SCAN_INTERVAL = 300


class FileIntegrityMonitor:
    """Monitor file integrity and detect tampering."""

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

        self._critical_files: Set[str] = set()
        self._file_hashes: Dict[str, Dict] = {}
        self._tamper_alerts: List[Dict] = []
        self._load_db()

    def _load_db(self):
        """Load integrity database."""
        if INTEGRITY_DB.exists():
            try:
                with open(INTEGRITY_DB, "r") as f:
                    data = json.load(f)
                    self._file_hashes = data.get("hashes", {})
                    self._critical_files = set(data.get("critical", []))
            except Exception:
                pass

    def _save_db(self):
        """Save integrity database."""
        try:
            INTEGRITY_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(INTEGRITY_DB, "w") as f:
                json.dump(
                    {
                        "hashes": self._file_hashes,
                        "critical": list(self._critical_files),
                        "updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def _compute_hash(self, filepath: str) -> Optional[str]:
        """Compute SHA-256 hash of file."""
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def add_critical_file(self, filepath: str):
        """Add file to critical monitoring list."""
        filepath = str(Path(filepath).resolve())
        self._critical_files.add(filepath)

        hash_val = self._compute_hash(filepath)
        if hash_val:
            self._file_hashes[filepath] = {
                "hash": hash_val,
                "size": os.path.getsize(filepath),
                "mtime": os.path.getmtime(filepath),
                "first_seen": datetime.now().isoformat(),
            }

        self._save_db()

    def remove_critical_file(self, filepath: str):
        """Remove file from monitoring."""
        filepath = str(Path(filepath).resolve())
        self._critical_files.discard(filepath)
        self._file_hashes.pop(filepath, None)
        self._save_db()

    def scan_integrity(self) -> List[Dict]:
        """
        Scan all critical files for changes.
        Returns list of tamper alerts.
        """
        alerts = []

        for filepath in list(self._critical_files):
            if not os.path.exists(filepath):
                alert = {
                    "type": "MISSING",
                    "file": filepath,
                    "time": datetime.now().isoformat(),
                }
                alerts.append(alert)
                self._tamper_alerts.append(alert)
                continue

            current_hash = self._compute_hash(filepath)
            stored = self._file_hashes.get(filepath, {})

            if current_hash != stored.get("hash"):
                alert = {
                    "type": "MODIFIED",
                    "file": filepath,
                    "old_hash": stored.get("hash", "unknown"),
                    "new_hash": current_hash,
                    "time": datetime.now().isoformat(),
                }
                alerts.append(alert)
                self._tamper_alerts.append(alert)

                self._file_hashes[filepath] = {
                    "hash": current_hash,
                    "size": os.path.getsize(filepath),
                    "mtime": os.path.getmtime(filepath),
                    "last_check": datetime.now().isoformat(),
                }

        if alerts:
            self._save_db()
            self._trigger_integrity_alert(alerts)

        return alerts

    def _trigger_integrity_alert(self, alerts: List[Dict]):
        """Trigger integrity alert."""
        from system.notification_system import NOTIFY

        alert_count = len(alerts)
        NOTIFY.send(
            f"CRITICAL SECURITY ALERT: File Integrity Violation",
            f"{alert_count} file(s) modified or missing",
            level="danger",
        )

        from system.security_monitor import SEC_MONITOR

        for alert in alerts:
            SEC_MONITOR._trigger_alert(
                "FILE_TAMPERING",
                f"{alert['type']}: {alert.get('file', 'unknown')}",
                escalate=True,
            )

    def verify_file(self, filepath: str) -> bool:
        """Verify single file integrity."""
        filepath = str(Path(filepath).resolve())

        if not os.path.exists(filepath):
            return False

        current_hash = self._compute_hash(filepath)
        stored = self._file_hashes.get(filepath, {})

        return current_hash == stored.get("hash")

    def get_critical_files(self) -> List[str]:
        """Get list of monitored files."""
        return list(self._critical_files)

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent tamper alerts."""
        return self._tamper_alerts[-limit:]

    def get_stats(self) -> Dict:
        """Get integrity monitor statistics."""
        return {
            "critical_files": len(self._critical_files),
            "total_alerts": len(self._tamper_alerts),
            "integrity_db_exists": INTEGRITY_DB.exists(),
        }

    def initialize_baseline(self):
        """Initialize baseline for all critical files."""
        for filepath in list(self._critical_files):
            if os.path.exists(filepath):
                hash_val = self._compute_hash(filepath)
                if hash_val:
                    self._file_hashes[filepath] = {
                        "hash": hash_val,
                        "size": os.path.getsize(filepath),
                        "mtime": os.path.getmtime(filepath),
                        "baseline": datetime.now().isoformat(),
                    }
        self._save_db()


INTEGRITY_MONITOR = FileIntegrityMonitor()
