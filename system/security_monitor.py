# =============================================================
#  security_monitor.py — Q-VAULT OS  |  Security Monitor
#
#  Intrusion detection and suspicious activity monitoring
# =============================================================

import time
import threading
from typing import Callable, Optional
from collections import deque
from system.security_system import SEC, EVT_INTRUSION, EVT_PROCESS

SUSPICIOUS_COMMANDS = [
    "rm -rf",
    "rm -rf /",
    "del /f /s /q",
    "format",
    "mkfs",
    "dd if=",
    "shred",
    "fdisk",
    "parted",
    ":(){:|:&};:",
    "fork()",
    "eval",
    "base64 -d",
    "wget",
    "curl",
    "nc ",
    "netcat",
    "socat",
    "msfconsole",
    "msfvenom",
    "sqlmap",
    "nmap",
]

FAILED_AUTH_LIMIT = 5
COMMAND_RATE_LIMIT = 10
COMMAND_RATE_WINDOW = 60


class SecurityMonitor:
    """
    Security monitoring for intrusion detection.
    Tracks failed logins, suspicious commands, and rate limits.
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

        self._failed_auths = {}
        self._command_times = deque(maxlen=100)
        self._suspicious_alerts = deque(maxlen=50)
        self._lock = threading.Lock()

        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring."""
        self._monitoring = True

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False

    def record_failed_auth(self, username: str) -> int:
        """Record failed authentication. Returns count of consecutive failures."""
        with self._lock:
            if username not in self._failed_auths:
                self._failed_auths[username] = []
            self._failed_auths[username].append(time.time())

            failures = self._failed_auths[username]

            cutoff = time.time() - 300
            self._failed_auths[username] = [t for t in failures if t > cutoff]

            count = len(self._failed_auths[username])

            if count >= FAILED_AUTH_LIMIT:
                self._trigger_alert(
                    "BRUTE_FORCE",
                    f"Multiple failed login attempts for user '{username}': {count} failures",
                    escalate=True,
                )
                self._failed_auths[username] = []

            return count

    def clear_failed_auths(self, username: str):
        """Clear failed auth count after successful login."""
        with self._lock:
            if username in self._failed_auths:
                self._failed_auths[username] = []

    def check_command_rate(self, user: str) -> bool:
        """Check if user is hitting rate limit. Returns True if OK."""
        now = time.time()
        cutoff = now - COMMAND_RATE_WINDOW

        with self._lock:
            recent = [t for t in self._command_times if t > cutoff and user in str(t)]
            if len(recent) >= COMMAND_RATE_LIMIT:
                self._trigger_alert(
                    "RATE_LIMIT",
                    f"User '{user}' exceeded command rate limit ({COMMAND_RATE_LIMIT}/{COMMAND_RATE_WINDOW}s)",
                    escalate=False,
                )
                return False

            self._command_times.append((now, user))
            return True

    def check_suspicious_command(self, command: str, user: str) -> bool:
        """Check for suspicious commands. Returns True if suspicious."""
        cmd_lower = command.lower()

        for sus_cmd in SUSPICIOUS_COMMANDS:
            if sus_cmd in cmd_lower:
                self._trigger_alert(
                    "SUSPICIOUS_COMMAND",
                    f"User '{user}' executed suspicious command: {command[:50]}",
                    escalate=True,
                )
                return True

        return False

    def check_path_traversal(self, path: str, user: str) -> bool:
        """Check for path traversal attempts."""
        if ".." in path or path.startswith("/etc") or path.startswith("/bin"):
            self._trigger_alert(
                "PATH_TRAVERSAL",
                f"User '{user}' attempted path traversal: {path}",
                escalate=True,
            )
            return True
        return False

    def _trigger_alert(self, alert_type: str, detail: str, escalate: bool = False):
        """Trigger security alert."""
        self._suspicious_alerts.append(
            {"type": alert_type, "detail": detail, "timestamp": time.time()}
        )

        SEC.report(
            EVT_INTRUSION, source="security_monitor", detail=detail, escalate=escalate
        )

        from system.notification_system import NOTIFY

        NOTIFY.send(
            f"SECURITY ALERT: {alert_type}",
            detail,
            level="danger" if escalate else "warning",
        )

    def get_failed_auth_count(self, username: str) -> int:
        """Get failed auth count for user."""
        with self._lock:
            if username not in self._failed_auths:
                return 0
            cutoff = time.time() - 300
            recent = [t for t in self._failed_auths[username] if t > cutoff]
            return len(recent)

    def get_alerts(self, limit: int = 10) -> list:
        """Get recent security alerts."""
        return list(self._suspicious_alerts)[-limit:]

    def get_stats(self) -> dict:
        """Get security monitoring statistics."""
        with self._lock:
            return {
                "failed_auths_tracked": len(self._failed_auths),
                "total_alerts": len(self._suspicious_alerts),
                "suspicious_commands": SUSPICIOUS_COMMANDS,
                "auth_fail_limit": FAILED_AUTH_LIMIT,
                "rate_limit": COMMAND_RATE_LIMIT,
            }

    def reset(self):
        """Reset all monitoring data."""
        with self._lock:
            self._failed_auths.clear()
            self._command_times.clear()
            self._suspicious_alerts.clear()


SEC_MONITOR = SecurityMonitor()
