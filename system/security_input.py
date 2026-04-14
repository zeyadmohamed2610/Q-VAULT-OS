# =============================================================
#  security_input.py — Q-VAULT OS  |  Input Security Layer
#
#  All input sanitization, command validation, and security checks
# =============================================================

import re
import os
import pathlib
from typing import Optional, Tuple
from system.security_system import SEC, EVT_INTRUSION, EVT_PROCESS

# Dangerous command tokens that can enable injection
DANGEROUS_TOKENS = [
    r";",
    r"&&",
    r"\|\|",
    r"`",
    r"\$\(",
    r"\|",
    r">",
    r"<",
    r">>",
    r"<<",
    r"\n",
    r"\r",
    r"\\",
    r"\$",
    r"!",
    r"#",
    r"%",
    r"^",
    r"*",
]

# Commands that require elevated privileges
ROOT_ONLY_COMMANDS = [
    "mkfs",
    "dd",
    "fdisk",
    "parted",
    "mount",
    "umount",
    "deluser",
    "userdel",
    "groupdel",
    "passwd",
    "chmod",
    "chown",
    "shutdown",
    "reboot",
    "halt",
    "init",
    "systemctl",
    "net",
    "netsh",
    "reg",
    "format",
]

# Blocked commands (never allow execution)
BLOCKED_COMMANDS = [
    "rm -rf",
    "rm -rf /",
    "del /f /s /q",
    "format c:",
    "mkfs.ext4",
    "mkfs.ntfs",
    "dd if=",
    "shred",
    "擦除",
    ":(){:|:&};:",
    "fork()",
    "while(true){}",
]

# Whitelist of allowed commands
ALLOWED_COMMANDS = {
    "ls",
    "dir",
    "cd",
    "pwd",
    "cat",
    "type",
    "echo",
    "date",
    "whoami",
    "hostname",
    "uname",
    "systeminfo",
    "ipconfig",
    "ifconfig",
    "netstat",
    "ss",
    "ps",
    "tasklist",
    "top",
    "free",
    "df",
    "du",
    "mkdir",
    "rmdir",
    "touch",
    "copy",
    "copy-item",
    "cp",
    "move",
    "move-item",
    "mv",
    "del",
    "remove-item",
    "rm",
    "rename",
    "ren",
    "cls",
    "clear",
    "tree",
    "find",
    "where",
    "which",
    "help",
    "man",
    "exit",
    "logout",
    "su",
    "sudo",
    "passwd",
    "useradd",
    "usermod",
    "userdel",
    "groupadd",
    "chmod",
    "chown",
    "apt",
    "apt-get",
    "pip",
    "npm",
    "brew",
    "choco",
    "git",
    "curl",
    "wget",
    "ping",
    "tracert",
    "traceroute",
    "nslookup",
    "dig",
    "taskkill",
    "kill",
}


class InputSanitizer:
    """Centralized input sanitization and security validation."""

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
        self._last_blocked = []

    def sanitize_command_input(self, user_input: str) -> Tuple[bool, str, str]:
        """
        Sanitize command input from terminal.
        Returns: (is_safe, sanitized_input, reason)
        """
        if not user_input or not user_input.strip():
            return False, "", "Empty input"

        # Check for dangerous tokens
        for token in DANGEROUS_TOKENS:
            if re.search(token, user_input):
                self._blocked_count += 1
                self._last_blocked.append(user_input[:50])
                self._report_intrusion(f"Command injection attempt: {user_input[:50]}")
                return False, "", f"Dangerous token blocked: {token}"

        # Check for blocked commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in user_input.lower():
                self._blocked_count += 1
                self._last_blocked.append(user_input[:50])
                self._report_intrusion(f"Blocked command: {user_input[:50]}")
                return False, "", f"Command blocked: {blocked}"

        # Extract base command
        base_cmd = user_input.split()[0] if user_input.split() else ""

        # Check whitelist
        if base_cmd.lower() not in ALLOWED_COMMANDS:
            # Allow but warn for unknown commands
            SEC.report(
                EVT_PROCESS,
                source="terminal",
                detail=f"Unknown command: {base_cmd}",
                escalate=False,
            )

        return True, user_input.strip(), "OK"

    def validate_path(
        self, path: str, sandbox_root: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate path to prevent traversal attacks.
        Returns: (is_safe, resolved_path)
        """
        if not user_input or not user_input.strip():
            return False, "", "Empty input"

        # Check for dangerous tokens
        for token in DANGEROUS_TOKENS:
            if re.search(token, user_input):
                self._blocked_count += 1
                self._last_blocked.append(user_input[:50])
                self._report_intrusion(f"Command injection attempt: {user_input[:50]}")
                return False, "", f"Dangerous token blocked: {token}"

        # Check for blocked commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in user_input.lower():
                self._blocked_count += 1
                self._last_blocked.append(user_input[:50])
                self._report_intrusion(f"Blocked command: {user_input[:50]}")
                return False, "", f"Command blocked: {blocked}"

        # Extract base command
        base_cmd = user_input.split()[0] if user_input.split() else ""

        # Check whitelist
        if base_cmd.lower() not in ALLOWED_COMMANDS:
            # Allow but warn for unknown commands
            SEC.report(
                EVT_PROCESS,
                source="terminal",
                detail=f"Unknown command: {base_cmd}",
                escalate=False,
            )

        return True, user_input.strip(), "OK"

    def validate_path(
        self, path: str, sandbox_root: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Validate path to prevent traversal attacks.
        Returns: (is_safe, resolved_path)
        """
        if not path:
            return False, ""

        try:
            # Normalize path
            resolved = os.path.realpath(os.path.expanduser(path))

            # If sandbox root specified, ensure path is within
            if sandbox_root:
                sandbox_resolved = os.path.realpath(sandbox_root)
                if not resolved.startswith(sandbox_resolved):
                    self._report_intrusion(f"Path traversal attempt: {path}")
                    return False, ""

            # Check for traversal patterns
            path_parts = pathlib.Path(path).parts
            if ".." in path_parts:
                self._report_intrusion(f"Path traversal attempt: {path}")
                return False, ""

            return True, resolved

        except Exception as e:
            return False, ""

    def check_root_command(
        self, cmd: str, user: str, is_root: bool
    ) -> tuple[bool, str]:
        """
        Check if command requires root privileges.
        Returns: (allowed, reason)
        """
        cmd_lower = cmd.lower()

        # Check if it's a root-only command
        for root_cmd in ROOT_ONLY_COMMANDS:
            if cmd_lower.startswith(root_cmd):
                if not is_root:
                    self._report_intrusion(
                        f"Root-only command attempt by {user}: {cmd}"
                    )
                    return False, f"Command '{root_cmd}' requires root privileges"
                return True, "OK"

        return True, "OK"

    def validate_filename(self, filename: str) -> tuple[bool, str]:
        """
        Validate filename for safety.
        Returns: (is_safe, sanitized_name)
        """
        if not filename:
            return False, ""

        # Block null bytes
        if "\x00" in filename:
            return False, ""

        # Remove path separators
        safe_name = filename.replace("/", "_").replace("\\", "_")

        # Block dangerous characters
        dangerous = ["<", ">", ":", '"', "|", "?", "*"]
        for char in dangerous:
            if char in safe_name:
                return False, ""

        return True, safe_name

    def _report_intrusion(self, detail: str):
        """Report intrusion attempt to security system."""
        SEC.report(
            EVT_INTRUSION,
            source="input_sanitizer",
            detail=detail,
            escalate=True,
        )

    def get_stats(self) -> dict:
        """Get sanitization statistics."""
        return {
            "blocked_count": self._blocked_count,
            "last_blocked": self._last_blocked[-10:],
        }


SANITIZER = InputSanitizer()


def sanitize_input(user_input: str) -> tuple[bool, str, str]:
    """Convenience function for input sanitization."""
    return SANITIZER.sanitize_command_input(user_input)


def validate_path(path: str, sandbox_root: Optional[str] = None) -> tuple[bool, str]:
    """Convenience function for path validation."""
    return SANITIZER.validate_path(path, sandbox_root)


def check_root_command(cmd: str, user: str, is_root: bool) -> tuple[bool, str]:
    """Convenience function for root command check."""
    return SANITIZER.check_root_command(cmd, user, is_root)
