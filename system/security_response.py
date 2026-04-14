# =============================================================
#  security_response.py — Q-VAULT OS  |  Security Response System
#
#  Unified security response coordination
# =============================================================

import time
import threading
from typing import Dict, List, Optional, Any
from enum import Enum

THREAT_LEVEL_LOW = "LOW"
THREAT_LEVEL_MEDIUM = "MEDIUM"
THREAT_LEVEL_HIGH = "HIGH"
THREAT_LEVEL_CRITICAL = "CRITICAL"


class ResponseAction(Enum):
    NONE = "none"
    WARN = "warn"
    LOCK = "lock"
    ISOLATE = "isolate"
    SHUTDOWN = "shutdown"


class SecurityResponseSystem:
    """
    Unified security response system.
    Coordinates all security subsystems.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._threat_level = THREAT_LEVEL_LOW
        self._response_action = ResponseAction.NONE
        self._locked_features: List[str] = []
        self._response_count = 0
        self._lockdown_active = False
        self._lock = threading.Lock()

    def assess_threat(
        self,
        source: str,
        threat_type: str,
        severity: int = 50,
    ) -> str:
        """
        Assess threat and determine response.
        Returns the action taken.
        """
        with self._lock:
            if severity >= 80:
                new_level = THREAT_LEVEL_CRITICAL
                action = ResponseAction.ISOLATE
            elif severity >= 60:
                new_level = THREAT_LEVEL_HIGH
                action = ResponseAction.LOCK
            elif severity >= 40:
                new_level = THREAT_LEVEL_MEDIUM
                action = ResponseAction.WARN
            else:
                new_level = THREAT_LEVEL_LOW
                action = ResponseAction.NONE

            self._escalate_if_needed(new_level)

            if new_level > self._threat_level:
                self._threat_level = new_level

            if action != ResponseAction.NONE:
                self._response_action = action
                self._execute_response(action, source, threat_type)
                self._response_count += 1

            return action.value

    def _escalate_if_needed(self, new_level: str):
        """Escalate threat level if needed."""
        levels = [
            THREAT_LEVEL_LOW,
            THREAT_LEVEL_MEDIUM,
            THREAT_LEVEL_HIGH,
            THREAT_LEVEL_CRITICAL,
        ]

        current_idx = levels.index(self._threat_level)
        new_idx = levels.index(new_level)

        if new_idx > current_idx:
            self._threat_level = new_level

    def _execute_response(self, action: ResponseAction, source: str, threat_type: str):
        """Execute security response action."""
        if action == ResponseAction.WARN:
            self._send_warning(source, threat_type)
        elif action == ResponseAction.LOCK:
            self._lock_system(source, threat_type)
        elif action == ResponseAction.ISOLATE:
            self._isolate_system(source, threat_type)
        elif action == ResponseAction.SHUTDOWN:
            self._shutdown_system(source, threat_type)

    def _send_warning(self, source: str, threat_type: str):
        """Send warning notification."""
        from system.notification_system import NOTIFY

        NOTIFY.send(
            f"THREAT DETECTED: {threat_type}",
            f"Source: {source}. Monitoring increased.",
            level="warning",
        )

    def _lock_system(self, source: str, threat_type: str):
        """Lock critical system features."""
        from system.secure_executor import SECURE_EXECUTOR
        from system.notification_system import NOTIFY

        SECURE_EXECUTOR._current_profile = SECURE_EXECUTOR.ExecutionProfile.SAFE
        self._locked_features = ["file_write", "terminal_exec", "network_raw"]
        self._lockdown_active = True

        NOTIFY.send(
            "SYSTEM LOCKED",
            f"Threat level HIGH. Features restricted. Source: {source}",
            level="danger",
        )

    def _isolate_system(self, source: str, threat_type: str):
        """Isolate system - maximum containment."""
        from system.secure_executor import SECURE_EXECUTOR
        from system.notification_system import NOTIFY

        SECURE_EXECUTOR._activate_fail_safe()

        from system.deception_layer import DECEPTION_LAYER

        DECEPTION_LAYER.activate()

        self._locked_features = [
            "file_write",
            "file_read",
            "terminal_exec",
            "network_raw",
            "process_create",
        ]
        self._lockdown_active = True

        NOTIFY.send(
            "SYSTEM ISOLATED",
            f"Critical threat detected. System in containment. Source: {source}",
            level="danger",
        )

    def _shutdown_system(self, source: str, threat_type: str):
        """Shutdown system - ultimate response."""
        from system.notification_system import NOTIFY
        from system.audit_logger_hardened import AUDIT_LOGGER

        NOTIFY.send(
            "CRITICAL: SYSTEM SHUTDOWN",
            f"Severe threat detected. Initiating shutdown. Source: {source}",
            level="danger",
        )

        if AUDIT_LOGGER:
            AUDIT_LOGGER.log(
                "SHUTDOWN",
                source,
                "security_response",
                threat_type,
                "CRITICAL",
                f"Shutdown triggered by {source}",
            )

        self._threat_level = THREAT_LEVEL_CRITICAL
        self._response_action = ResponseAction.SHUTDOWN

    def get_threat_level(self) -> str:
        """Get current threat level."""
        return self._threat_level

    def get_response_action(self) -> str:
        """Get current response action."""
        return self._response_action.value

    def is_lockdown_active(self) -> bool:
        """Check if lockdown is active."""
        return self._lockdown_active

    def get_locked_features(self) -> List[str]:
        """Get list of locked features."""
        return list(self._locked_features)

    def reset_threat(self):
        """Reset threat level to normal."""
        with self._lock:
            self._threat_level = THREAT_LEVEL_LOW
            self._response_action = ResponseAction.NONE
            self._locked_features.clear()
            self._lockdown_active = False

    def get_stats(self) -> Dict[str, Any]:
        """Get security response statistics."""
        return {
            "threat_level": self._threat_level,
            "response_action": self._response_action.value,
            "response_count": self._response_count,
            "lockdown_active": self._lockdown_active,
            "locked_features": self._locked_features,
        }


SECURITY_RESPONSE = SecurityResponseSystem()


def assess_threat(source: str, threat_type: str, severity: int = 50) -> str:
    """Convenience function to assess threat."""
    return SECURITY_RESPONSE.assess_threat(source, threat_type, severity)


def get_threat_level() -> str:
    """Get current threat level."""
    return SECURITY_RESPONSE.get_threat_level()


def is_lockdown_active() -> bool:
    """Check if lockdown is active."""
    return SECURITY_RESPONSE.is_lockdown_active()
