# =============================================================
#  self_protect.py — Q-VAULT OS  |  Self-Protection System
#
#  Automatic lockdown when threat level is CRITICAL
# =============================================================

import os
import sys
import time
import threading
from typing import Dict, List, Optional, Any
from enum import Enum

THREAT_LEVEL_NORMAL = "NORMAL"
THREAT_LEVEL_ELEVATED = "ELEVATED"
THREAT_LEVEL_HIGH = "HIGH"
THREAT_LEVEL_CRITICAL = "CRITICAL"


class LockdownMode(Enum):
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"
    MAXIMUM = "maximum"


class SelfProtect:
    """
    Self-protection system.
    Activates lockdown when threat level reaches CRITICAL.
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

        self._lockdown_mode = LockdownMode.NONE
        self._threat_level = THREAT_LEVEL_NORMAL
        self._lockdown_reason = ""
        self._lockdown_time = 0
        self._lock = threading.Lock()
        self._sessions_cleared = False

    def set_threat_level(self, level: str):
        """Set system threat level."""
        with self._lock:
            old_level = self._threat_level
            self._threat_level = level

            if level == THREAT_LEVEL_CRITICAL and old_level != THREAT_LEVEL_CRITICAL:
                self._activate_lockdown("Threat level CRITICAL")
            elif level == THREAT_LEVEL_HIGH and old_level == THREAT_LEVEL_NORMAL:
                self._activate_soft_lockdown("Threat level elevated")

    def _activate_lockdown(self, reason: str):
        """Activate full lockdown."""
        self._lockdown_mode = LockdownMode.MAXIMUM
        self._lockdown_reason = reason
        self._lockdown_time = time.time()

        self._clear_sensitive_memory()
        self._kill_processes()
        self._disable_terminal()
        self._show_lockdown_dialog()

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "SYSTEM LOCKDOWN ACTIVATED",
            reason,
            level="danger",
        )

    def _activate_soft_lockdown(self, reason: str):
        """Activate soft lockdown."""
        self._lockdown_mode = LockdownMode.SOFT
        self._lockdown_reason = reason
        self._lockdown_time = time.time()

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "ELEVATED THREAT DETECTED",
            reason,
            level="warning",
        )

    def _clear_sensitive_memory(self):
        """Clear all sensitive memory with multi-pass overwrite."""
        from system.memory_security import SECURE_MEMORY

        SECURE_MEMORY.wipe_all()

        from system.anti_memory_dump import ANTI_MEMORY_DUMP

        ANTI_MEMORY_DUMP.wipe_all()

    def _kill_processes(self):
        """Kill all user processes."""
        try:
            from core.process_manager import PM

            processes = PM.list_processes()
            for proc in processes:
                if proc.get("pid", 0) > 1:
                    try:
                        PM.kill(proc["pid"])
                    except Exception:
                        pass
        except Exception:
            pass

    def _disable_terminal(self):
        """Disable terminal input."""
        from system.secure_executor import SECURE_EXECUTOR

        SECURE_EXECUTOR._fail_safe_mode = True

    def _show_lockdown_dialog(self):
        """Show blocking lockdown dialog."""
        from system.security_system import SEC, EVT_INTRUSION

        SEC.report(
            EVT_INTRUSION,
            source="self_protect",
            detail=self._lockdown_reason,
            escalate=True,
        )

    def is_locked(self) -> bool:
        """Check if system is in lockdown."""
        return self._lockdown_mode != LockdownMode.NONE

    def get_lockdown_mode(self) -> str:
        """Get lockdown mode string."""
        return self._lockdown_mode.value

    def get_threat_level(self) -> str:
        """Get current threat level."""
        return self._threat_level

    def unlock(self):
        """Unlock system (manual reset)."""
        with self._lock:
            self._lockdown_mode = LockdownMode.NONE
            self._threat_level = THREAT_LEVEL_NORMAL
            self._lockdown_reason = ""
            self._lockdown_time = 0

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "SYSTEM UNLOCKED",
            "Lockdown has been manually lifted",
            level="success",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get self-protection statistics."""
        return {
            "lockdown_mode": self._lockdown_mode.value,
            "threat_level": self._threat_level,
            "lockdown_reason": self._lockdown_reason,
            "lockdown_time": self._lockdown_time,
            "is_locked": self.is_locked(),
        }


SELF_PROTECT = SelfProtect()
