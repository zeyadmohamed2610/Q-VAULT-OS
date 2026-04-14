# =============================================================
#  audit_logger.py — Q-Vault OS  |  Audit Logging System
#
#  Comprehensive audit logging for security events
# =============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time
import json
import os

try:
    from system.sync_manager import SYNC_MANAGER

    HAS_SYNC = True
except Exception:
    HAS_SYNC = False


class AuditEventType(Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    FILE_ACCESS = "FILE_ACCESS"
    FILE_CREATE = "FILE_CREATE"
    FILE_DELETE = "FILE_DELETE"
    FILE_MODIFY = "FILE_MODIFY"
    COMMAND_EXEC = "COMMAND_EXEC"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    USER_CREATE = "USER_CREATE"
    USER_DELETE = "USER_DELETE"
    USER_MODIFY = "USER_MODIFY"
    PACKAGE_INSTALL = "PACKAGE_INSTALL"
    PACKAGE_REMOVE = "PACKAGE_REMOVE"
    SYSTEM_CONFIG_CHANGE = "SYSTEM_CONFIG_CHANGE"
    SECURITY_ALERT = "SECURITY_ALERT"
    PROCESS_START = "PROCESS_START"
    PROCESS_STOP = "PROCESS_STOP"
    NETWORK_CONNECT = "NETWORK_CONNECT"
    NETWORK_DISCONNECT = "NETWORK_DISCONNECT"


class AuditSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AuditEntry:
    """Single audit log entry."""

    entry_id: int
    timestamp: float
    event_type: AuditEventType
    severity: AuditSeverity
    user: str
    resource: str
    action: str
    result: str
    detail: str
    source_ip: str = ""


class AuditLogger:
    """Audit logging system with persistence."""

    def __init__(self):
        self._next_id = 1
        self._entries: list[AuditEntry] = []
        self._max_entries = 10000
        self._log_file = ""

    def set_log_file(self, path: str):
        """Set log file path for persistence."""
        self._log_file = path

    def log(
        self,
        event_type: AuditEventType,
        user: str,
        resource: str,
        action: str,
        result: str,
        detail: str = "",
        severity: AuditSeverity = AuditSeverity.INFO,
        source_ip: str = "",
    ) -> int:
        """Log an audit event."""
        entry = AuditEntry(
            entry_id=self._next_id,
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            user=user,
            resource=resource,
            action=action,
            result=result,
            detail=detail,
            source_ip=source_ip,
        )

        self._next_id += 1
        self._entries.append(entry)

        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        self._persist_entry(entry)

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_audit_log(
                    entry.event_type.value,
                    entry.severity.value,
                    user_id=entry.user,
                    metadata={
                        "resource": entry.resource,
                        "action": entry.action,
                        "result": entry.result,
                        "detail": entry.detail,
                    },
                )
            except Exception:
                pass

        return entry.entry_id

    def _persist_entry(self, entry: AuditEntry):
        """Write entry to log file."""
        if not self._log_file:
            return

        try:
            line = json.dumps(
                {
                    "id": entry.entry_id,
                    "ts": entry.timestamp,
                    "type": entry.event_type.value,
                    "severity": entry.severity.value,
                    "user": entry.user,
                    "resource": entry.resource,
                    "action": entry.action,
                    "result": entry.result,
                    "detail": entry.detail,
                    "ip": entry.source_ip,
                }
            )
            with open(self._log_file, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def query(
        self,
        user: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        from_time: Optional[float] = None,
        to_time: Optional[float] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit log entries."""
        results = self._entries

        if user:
            results = [e for e in results if e.user == user]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if severity:
            results = [e for e in results if e.severity == severity]
        if from_time:
            results = [e for e in results if e.timestamp >= from_time]
        if to_time:
            results = [e for e in results if e.timestamp <= to_time]

        return results[-limit:]

    def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        """Get recent audit entries."""
        return self._entries[-limit:]

    def get_critical(self) -> list[AuditEntry]:
        """Get all critical severity entries."""
        return [e for e in self._entries if e.severity == AuditSeverity.CRITICAL]

    def clear_old_entries(self, before_timestamp: float) -> int:
        """Clear entries older than timestamp. Returns count cleared."""
        old_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp >= before_timestamp]
        return old_count - len(self._entries)

    def get_stats(self) -> dict:
        """Get audit log statistics."""
        by_type = {}
        by_severity = {}
        by_user = {}

        for entry in self._entries:
            t = entry.event_type.value
            by_type[t] = by_type.get(t, 0) + 1

            s = entry.severity.value
            by_severity[s] = by_severity.get(s, 0) + 1

            u = entry.user
            by_user[u] = by_user.get(u, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_user": by_user,
        }

    def export_json(self, filepath: str) -> bool:
        """Export audit log to JSON file."""
        try:
            data = []
            for entry in self._entries:
                data.append(
                    {
                        "id": entry.entry_id,
                        "timestamp": entry.timestamp,
                        "event_type": entry.event_type.value,
                        "severity": entry.severity.value,
                        "user": entry.user,
                        "resource": entry.resource,
                        "action": entry.action,
                        "result": entry.result,
                        "detail": entry.detail,
                        "source_ip": entry.source_ip,
                    }
                )
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False


AUDIT = AuditLogger()
