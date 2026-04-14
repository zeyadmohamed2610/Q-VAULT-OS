# =============================================================
#  anti_reverse.py — Q-VAULT OS  |  Anti-Reverse Engineering
#
#  Runtime string obfuscation and project integrity checking
# =============================================================

import os
import sys
import hashlib
import threading
import time
from typing import Dict, List, Optional, Set
from pathlib import Path

CORE_DIRS = [
    "core",
    "components",
    "apps",
    "system",
    "assets",
]

OBFUSCATED_STRINGS: Dict[str, str] = {}


class StringObfuscator:
    """Runtime string obfuscation for sensitive data."""

    @staticmethod
    def hash_string(s: str) -> str:
        """Hash a string using SHA256."""
        return hashlib.sha256(s.encode()).hexdigest()

    @staticmethod
    def obfuscate(s: str) -> str:
        """Obfuscate a string at runtime."""
        return f"_obf_{hashlib.md5(s.encode()).hexdigest()[:12]}"

    @staticmethod
    def store_obfuscated(key: str, value: str):
        """Store an obfuscated string mapping."""
        hashed = StringObfuscator.obfuscate(key)
        OBFSUCATED_STRINGS[hashed] = value

    @staticmethod
    def retrieve(key: str) -> Optional[str]:
        """Retrieve an obfuscated string."""
        hashed = StringObfuscator.obfuscate(key)
        return OBFSUCATED_STRINGS.get(hashed)


class FileIntegrityChecker:
    """Check integrity of core files."""

    def __init__(self):
        self._file_hashes: Dict[str, str] = {}
        self._snapshot_created = False
        self._lock = threading.Lock()
        self._tamper_detected = False

    def _get_all_files(self) -> List[str]:
        """Get list of all Python files in core directories."""
        files = []
        base = Path(__file__).parent.parent

        for directory in CORE_DIRS:
            dir_path = base / directory
            if dir_path.exists():
                for root, _, filenames in os.walk(dir_path):
                    for fname in filenames:
                        if fname.endswith(".py"):
                            fpath = os.path.join(root, fname)
                            files.append(fpath)
        return files

    def create_snapshot(self):
        """Create integrity snapshot of all core files."""
        print("[ANTI-REVERSE] Creating integrity snapshot...")

        with self._lock:
            self._file_hashes.clear()
            files = self._get_all_files()

            for fpath in files:
                try:
                    with open(fpath, "rb") as f:
                        content = f.read()
                        h = hashlib.sha256(content).hexdigest()
                        rel_path = os.path.relpath(fpath, Path(__file__).parent.parent)
                        self._file_hashes[rel_path] = h
                except Exception:
                    pass

            self._snapshot_created = True
        print(f"[ANTI-REVERSE] Snapshot created: {len(self._file_hashes)} files")

    def verify_integrity(self) -> bool:
        """Verify file integrity against snapshot."""
        if not self._snapshot_created:
            return True

        print("[ANTI-REVERSE] Verifying integrity...")

        with self._lock:
            files = self._get_all_files()

            for fpath in files:
                try:
                    rel_path = os.path.relpath(fpath, Path(__file__).parent.parent)

                    with open(fpath, "rb") as f:
                        content = f.read()
                        current_hash = hashlib.sha256(content).hexdigest()

                    stored_hash = self._file_hashes.get(rel_path)
                    if stored_hash and current_hash != stored_hash:
                        print(f"[ANTI-REVERSE] TAMPER DETECTED: {rel_path}")
                        self._tamper_detected = True
                        return False
                except Exception:
                    pass

        return True

    def get_tamper_status(self) -> bool:
        """Get tamper detection status."""
        return self._tamper_detected

    def get_file_count(self) -> int:
        """Get number of tracked files."""
        return len(self._file_hashes)


class AntiReverse:
    """
    Anti-reverse engineering system.
    Handles string obfuscation, integrity checking, and tamper detection.
    """

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

        self._obfuscator = StringObfuscator()
        self._integrity = FileIntegrityChecker()
        self._debugger_blocked = False
        self._tracing_detected = False
        self._lock = threading.Lock()

    def initialize(self):
        """Initialize anti-reverse systems."""
        self._integrity.create_snapshot()
        self._obfuscate_sensitive_strings()
        self._start_monitoring()

    def _obfuscate_sensitive_strings(self):
        """Obfuscate sensitive strings at startup."""
        sensitive = [
            "admin123",
            "root",
            "password",
            "secret",
            "token",
            "api_key",
            "private_key",
        ]

        for s in sensitive:
            self._obfuscator.store_obfuscated(s, s)

    def _start_monitoring(self):
        """Start background integrity monitoring."""
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            if not self._integrity.verify_integrity():
                self._trigger_tamper_response()
            time.sleep(60)

    def _trigger_tamper_response(self):
        """Trigger response to tamper detection."""
        from system.security_system import SEC, EVT_INTRUSION
        from system.notification_system import NOTIFY

        detail = "Core file modification detected - possible tampering"

        SEC.report(
            EVT_INTRUSION,
            source="anti_reverse",
            detail=detail,
            escalate=True,
        )

        NOTIFY.send(
            "TAMPER DETECTED",
            detail,
            level="danger",
        )

    def check_tracing(self) -> bool:
        """Check if code is being traced."""
        if sys.gettrace() is not None:
            self._tracing_detected = True
            return True
        return False

    def check_debugger(self) -> bool:
        """Check for debuggers."""
        import subprocess

        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["tasklist"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                debuggers = ["x64dbg", "x32dbg", "ollydbg", "ida", "windbg"]
                for dbg in debuggers:
                    if dbg.lower() in result.stdout.lower():
                        self._debugger_blocked = True
                        return True
            except Exception:
                pass
        return False

    def is_secure(self) -> bool:
        """Check if system is secure."""
        if self._tamper_detected or self._debugger_blocked or self._tracing_detected:
            return False
        return True

    def get_status(self) -> Dict:
        """Get anti-reverse status."""
        return {
            "integrity_verified": self._integrity.verify_integrity(),
            "tamper_detected": self._integrity.get_tamper_status(),
            "tracing_detected": self._tracing_detected,
            "debugger_blocked": self._debugger_blocked,
            "tracked_files": self._integrity.get_file_count(),
            "secure": self.is_secure(),
        }


ANTI_REVERSE = AntiReverse()
