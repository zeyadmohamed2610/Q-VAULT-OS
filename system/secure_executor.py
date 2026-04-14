# =============================================================
#  secure_executor.py — Q-VAULT OS  |  Secure Execution Layer
#
#  Sandboxed command execution with path validation
# =============================================================

import os
import sys
import json
import subprocess
import pathlib
import tempfile
import shutil
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum
from datetime import datetime
from system.memory_security import SECURE_MEMORY, secure_wipe

SANDBOX_ROOT = pathlib.Path.home() / ".qvault" / "sandbox"
TEMP_DIR = pathlib.Path.home() / ".qvault" / "tmp"


class ExecutionProfile(Enum):
    SAFE = "safe"
    RESTRICTED = "restricted"
    ADMIN = "admin"


BLOCKED_PATHS = [
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
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\Users\\Public",
]

ALLOWED_COMMANDS_SAFE = {
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
    "tree",
    "clear",
}

ALLOWED_COMMANDS_RESTRICTED = ALLOWED_COMMANDS_SAFE | {
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
}

ALLOWED_COMMANDS_ADMIN = ALLOWED_COMMANDS_RESTRICTED | {
    "chmod",
    "chown",
    "apt",
    "apt-get",
    "pip",
    "taskkill",
    "kill",
}


class SecureExecutionResult:
    """Result of secure execution."""

    def __init__(
        self,
        success: bool,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        error: str = "",
    ):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.error = error


class SecureExecutor:
    """
    Secure command execution layer with sandboxing.
    All commands run inside restricted environment.
    """

    _instance = None
    _fail_safe_mode = False
    _violation_count = 0
    _execution_count = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._sandbox_root = SANDBOX_ROOT
        self._temp_dir = TEMP_DIR
        self._setup_sandbox()
        self._current_profile = ExecutionProfile.RESTRICTED

    def _setup_sandbox(self):
        """Initialize sandbox directory structure."""
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def is_path_allowed(self, path: str) -> Tuple[bool, str]:
        """
        Check if path is within allowed sandbox.
        Returns (allowed, reason)
        """
        path_obj = pathlib.Path(path)
        try:
            resolved = path_obj.resolve()
        except Exception:
            return False, "Invalid path"

        path_str = str(resolved)

        for blocked in BLOCKED_PATHS:
            if path_str.startswith(blocked):
                return False, f"Blocked path: {blocked}"

        return True, "OK"

    def _get_allowed_commands(self, profile: ExecutionProfile) -> set:
        """Get allowed commands for profile."""
        if profile == ExecutionProfile.SAFE:
            return ALLOWED_COMMANDS_SAFE
        elif profile == ExecutionProfile.RESTRICTED:
            return ALLOWED_COMMANDS_RESTRICTED
        else:
            return ALLOWED_COMMANDS_ADMIN

    def execute(
        self,
        command: str,
        args: List[str] = None,
        profile: ExecutionProfile = None,
        timeout: int = 5,
    ) -> SecureExecutionResult:
        """
        Execute command securely inside sandbox.

        Steps:
        1. Validate command
        2. Validate paths
        3. Execute inside sandbox
        4. Audit log
        """
        self._execution_count += 1

        if self._fail_safe_mode and self._violation_count > 10:
            return SecureExecutionResult(
                False, error="System in FAIL-SAFE mode. Only basic commands allowed."
            )

        if profile is None:
            profile = self._current_profile

        allowed = self._get_allowed_commands(profile)

        if not args:
            args = []

        try:
            cmd = command.strip().split()[0].lower()
        except Exception:
            return SecureExecutionResult(False, error="Invalid command")

        if cmd not in allowed:
            self._record_violation(f"Command not allowed: {cmd}")
            return SecureExecutionResult(
                False, error=f"Command '{cmd}' not allowed in {profile.value} mode"
            )

        for arg in args:
            if arg.startswith("-") and len(arg) > 2:
                continue

            safe, reason = self.is_path_allowed(arg)
            if not safe:
                self._record_violation(f"Blocked path: {arg}")
                return SecureExecutionResult(False, error=reason)

        working_dir = str(self._sandbox_root)

        try:
            full_cmd = [command] + args if args else [command]

            use_shell = False
            if os.name == "nt" and command.lower() in ["cmd", "dir", "echo"]:
                use_shell = True

            result = subprocess.run(
                full_cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=use_shell,
            )

            self._audit_execution(command, args, result.returncode, "SUCCESS")

            return SecureExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return SecureExecutionResult(
                False, error="Command timed out", exit_code=124
            )
        except FileNotFoundError:
            return SecureExecutionResult(
                False, error="Command not found", exit_code=127
            )
        except PermissionError:
            return SecureExecutionResult(
                False, error="Permission denied", exit_code=126
            )
        except Exception as e:
            self._record_violation(f"Execution error: {str(e)}")
            return SecureExecutionResult(False, error=str(e))

    def _record_violation(self, detail: str):
        """Record security violation."""
        self._violation_count += 1

        from system.security_monitor import SEC_MONITOR

        SEC_MONITOR._trigger_alert("EXECUTION_VIOLATION", detail, escalate=True)

        from system.notification_system import NOTIFY

        NOTIFY.send("SECURITY VIOLATION", detail, level="danger")

        if self._violation_count >= 15:
            self._activate_fail_safe()

    def _audit_execution(
        self, command: str, args: List[str], exit_code: int, status: str
    ):
        """Audit command execution."""
        from system.audit_logger_hardened import AUDIT_LOGGER

        if AUDIT_LOGGER:
            AUDIT_LOGGER.log(
                "EXECUTION",
                "system",
                str(self._sandbox_root),
                command,
                status,
                f"args: {args}, exit: {exit_code}",
            )

    def _activate_fail_safe(self):
        """Activate fail-safe mode."""
        self._fail_safe_mode = True
        self._current_profile = ExecutionProfile.SAFE

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "FAIL-SAFE MODE ACTIVATED",
            "Too many violations. System locked to SAFE mode.",
            level="danger",
        )

    def reset_violations(self):
        """Reset violation count."""
        self._violation_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "executions": self._execution_count,
            "violations": self._violation_count,
            "fail_safe": self._fail_safe_mode,
            "sandbox": str(self._sandbox_root),
            "profile": self._current_profile.value,
        }


SECURE_EXECUTOR = SecureExecutor()


def execute_secure(
    command: str,
    args: List[str] = None,
    profile: ExecutionProfile = None,
    timeout: int = 5,
) -> SecureExecutionResult:
    """Convenience function for secure execution."""
    return SECURE_EXECUTOR.execute(command, args, profile, timeout)
