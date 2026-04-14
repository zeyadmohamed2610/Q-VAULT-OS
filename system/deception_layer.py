# =============================================================
#  deception_layer.py — Q-VAULT OS  |  Deception Layer
#
#  Return fake data when attacker detected
# =============================================================

import os
import time
import random
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

FAKE_FILE_SYSTEM = {
    "/etc/shadow": "root:$6$fake$salt:18000:0:99999:7:::\n",
    "/etc/passwd": "root:x:0:0:root:/root:/bin/bash\n",
    "/home/user/.bash_history": "",
    "/var/log/messages": "",
    "C:\\Windows\\System32\\config": "REGISTRY DUMP",
    "C:\\Users\\Admin\\.ssh\\id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMOCKKEY\n-----END RSA PRIVATE KEY-----",
}

FAKE_PATHS = [
    "/fake/bin",
    "/honeypot/home",
    "/decoy/data",
    "C:\\QVault\\secret",
    "C:\\temp\\hidden",
]

TRAP_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/root/.ssh",
    "C:\\Windows\\System32",
    "C:\\Windows\\System32\\config",
]


class DeceptionLayer:
    """
    Deception layer for attacker detection.
    Returns fake data instead of real data when under attack.
    """

    _instance = None
    _active = False
    _attacker_detected = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._attacker_commands: List[str] = []
        self._decoy_accesses: Dict[str, int] = {}
        self._trap_triggers: Dict[str, int] = {}
        self._fake_data_cache: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._generate_fake_data()

    def _generate_fake_data(self):
        """Generate fake sensitive-looking data."""
        self._fake_data_cache = dict(FAKE_FILE_SYSTEM)

    def activate(self):
        """Activate deception layer."""
        self._active = True
        self._attacker_detected = True

    def deactivate(self):
        """Deactivate deception layer."""
        self._active = False
        self._attacker_detected = False

    def is_active(self) -> bool:
        """Check if deception layer is active."""
        return self._active

    def record_attacker_command(self, command: str):
        """Record command from suspected attacker."""
        with self._lock:
            self._attacker_commands.append(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {command}"
            )

            if len(self._attacker_commands) > 100:
                self._attacker_commands = self._attacker_commands[-100:]

    def record_decoy_access(self, path: str):
        """Record access to decoy/honeypot path."""
        with self._lock:
            if path not in self._decoy_accesses:
                self._decoy_accesses[path] = 0
            self._decoy_accesses[path] += 1

            if self._decoy_accesses[path] >= 3:
                self.activate()

    def record_trap_trigger(self, path: str):
        """Record trigger of a trap path."""
        with self._lock:
            if path not in self._trap_triggers:
                self._trap_triggers[path] = 0
            self._trap_triggers[path] += 1

            if self._trap_triggers[path] >= 1:
                self.activate()
                self._trigger_defensive_response()

    def get_fake_path(self, requested_path: str) -> str:
        """Return fake path instead of real one."""
        if not self._active:
            return requested_path

        fake = random.choice(FAKE_PATHS)
        return fake

    def get_fake_file_content(self, path: str) -> Optional[str]:
        """Return fake file content."""
        if not self._active:
            return None

        if path in self._fake_data_cache:
            return self._fake_data_cache[path]

        path_lower = path.lower()
        for key in self._fake_data_cache:
            if key.lower() in path_lower:
                return self._fake_data_cache[key]

        return self._generate_random_fake_content(path)

    def _generate_random_fake_content(self, path: str) -> str:
        """Generate random fake content for unknown paths."""
        content_type = random.choice(["log", "config", "data", "backup"])
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        if content_type == "log":
            return f"[{timestamp}] INFO: System operation completed\n" * 10
        elif content_type == "config":
            return f"# Config generated at {timestamp}\nkey=value\n"
        elif content_type == "data":
            return f"DUMMY_DATA_{random.randint(1000, 9999)}\n"
        else:
            return f"Backup created: {timestamp}\n"

    def is_trap_path(self, path: str) -> bool:
        """Check if path is a trap/honeypot."""
        path_lower = path.lower()
        for trap in TRAP_PATHS:
            if trap.lower() in path_lower:
                return True
        return False

    def should_intercept(self, path: str) -> bool:
        """Check if path access should be intercepted."""
        if not self._active:
            return False

        return self.is_trap_path(path) or path in FAKE_PATHS

    def _trigger_defensive_response(self):
        """Trigger defensive response when trap triggered."""
        from system.security_system import SEC, EVT_INTRUSION
        from system.notification_system import NOTIFY
        from system.behavior_monitor import BEHAVIOR_MONITOR

        detail = f"Trap path accessed. Deception layer activated."

        SEC.report(
            EVT_INTRUSION,
            source="deception_layer",
            detail=detail,
            escalate=True,
        )

        BEHAVIOR_MONITOR.record_event(
            "TRAP_TRIGGERED",
            "unknown",
            detail,
            risk_weight=30,
        )

        NOTIFY.send(
            "INTRUSION DETECTED",
            detail,
            level="danger",
        )

    def get_decoy_access_count(self, path: str) -> int:
        """Get number of decoy accesses for path."""
        return self._decoy_accesses.get(path, 0)

    def get_attacker_commands(self) -> List[str]:
        """Get recorded attacker commands."""
        return list(self._attacker_commands)

    def get_stats(self) -> Dict[str, Any]:
        """Get deception layer statistics."""
        return {
            "active": self._active,
            "attacker_detected": self._attacker_detected,
            "decoy_accesses": dict(self._decoy_accesses),
            "trap_triggers": dict(self._trap_triggers),
            "recorded_commands": len(self._attacker_commands),
        }


DECEPTION_LAYER = DeceptionLayer()
