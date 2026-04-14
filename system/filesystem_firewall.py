# =============================================================
#  filesystem_firewall.py — Q-VAULT OS  |  Filesystem Firewall
#
#  Block access to protected system paths
# =============================================================

import os
import pathlib
from typing import Tuple, Set, List
from enum import Enum


class PathAction(Enum):
    ALLOW = "allow"
    DENY = "deny"
    SANDBOX = "sandbox"


BLOCKED_PATH_PREFIXES = [
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/usr/local/bin",
    "/etc",
    "/boot",
    "/dev",
    "/sys",
    "/proc",
    "/root",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\Users\\Public",
    "C:\\$Recycle.Bin",
    "/private/etc",
    "/private/var",
    "/System",
]

ALLOWED_PATH_PREFIXES = [".qvault", ".qvault/users", ".qvault/tmp", ".qvault/sandbox"]

PROTECTED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".sys",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".vbs",
    ".js",
    ".jse",
    ".msi",
    ".cab",
}


class FilesystemFirewall:
    """
    Filesystem firewall - blocks access to protected paths.
    Implements defense-in-depth for file operations.
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

        self._blocked_count = 0
        self._allowed_count = 0
        self._custom_rules: List[Tuple[str, PathAction]] = []

    def check_path(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """
        Check if path is accessible.
        Returns: (allowed, reason)
        """
        if not path:
            return False, "Empty path"

        path_obj = pathlib.Path(path)

        try:
            resolved = path_obj.resolve()
        except Exception:
            return False, "Invalid path"

        path_str = str(resolved).replace("\\", "/")

        for blocked in BLOCKED_PATH_PREFIXES:
            blocked_normalized = blocked.replace("\\", "/")
            if path_str.startswith(blocked_normalized) or path_str.startswith(blocked):
                self._blocked_count += 1
                self._record_violation("BLOCKED_PATH", path_str, operation)
                return False, f"Access denied: {blocked}"

        self._allowed_count += 1
        return True, "OK"

    def check_extension(self, path: str) -> Tuple[bool, str]:
        """
        Check if file extension is dangerous.
        Returns: (allowed, reason)
        """
        ext = pathlib.Path(path).suffix.lower()

        if ext in PROTECTED_EXTENSIONS:
            self._record_violation("DANGEROUS_EXTENSION", path, ext)
            return False, f"Dangerous extension blocked: {ext}"

        return True, "OK"

    def check_write_operation(self, path: str) -> Tuple[bool, str]:
        """
        Check if write operation is allowed.
        """
        allowed, reason = self.check_path(path, "write")
        if not allowed:
            return allowed, reason

        allowed, reason = self.check_extension(path)
        if not allowed:
            return allowed, reason

        return True, "OK"

    def check_read_operation(self, path: str) -> Tuple[bool, str]:
        """
        Check if read operation is allowed.
        """
        return self.check_path(path, "read")

    def sanitize_path(self, path: str) -> str:
        """
        Sanitize path - remove dangerous components.
        """
        path_obj = pathlib.Path(path)

        parts = []
        for part in path_obj.parts:
            if part in ["..", "."]:
                continue
            if part.startswith("."):
                continue
            parts.append(part)

        base = pathlib.Path.home() / ".qvault" / "sandbox"
        for part in parts:
            base = base / part

        return str(base.resolve())

    def add_custom_rule(self, path_prefix: str, action: PathAction):
        """Add custom firewall rule."""
        self._custom_rules.append((path_prefix, action))

    def _record_violation(self, violation_type: str, path: str, detail: str = ""):
        """Record firewall violation."""
        self._blocked_count += 1

        from system.security_monitor import SEC_MONITOR

        SEC_MONITOR._trigger_alert(
            f"FILESYSTEM_{violation_type}", f"{path} - {detail}", escalate=True
        )

    def get_stats(self) -> dict:
        """Get firewall statistics."""
        return {
            "blocked": self._blocked_count,
            "allowed": self._allowed_count,
            "blocked_prefixes": BLOCKED_PATH_PREFIXES,
            "protected_extensions": list(PROTECTED_EXTENSIONS),
        }

    def reset_stats(self):
        """Reset statistics."""
        self._blocked_count = 0
        self._allowed_count = 0


FILESYSTEM_FIREWALL = FilesystemFirewall()


def check_path_access(path: str, operation: str = "read") -> Tuple[bool, str]:
    """Convenience function for path checking."""
    if operation == "write":
        return FILESYSTEM_FIREWALL.check_write_operation(path)
    return FILESYSTEM_FIREWALL.check_read_operation(path)
