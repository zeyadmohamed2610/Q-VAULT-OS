import logging
import subprocess
import shlex
import time
from collections import deque
from typing import Union, List, Any
from .permissions import PM_GUARD, ENFORCEMENT_LEVEL
from system.runtime_manager import RUNTIME_MANAGER

logger = logging.getLogger("sandbox.process_guard")


# Hard allowlist of executable names (stem only, lowercase).
# This is the ONLY set of programs any app may invoke.
_PROCESS_ALLOWLIST = frozenset({
    "ping", "nslookup", "tracert", "traceroute", "ipconfig", "ifconfig",
})

# Chars that indicate shell injection in a string command.
_INJECTION_CHARS = frozenset("&|;$`\n<>")


class ProcessGuard:
    """
    Execution Gate — Controlled Enforcement.

    Safe Alternatives:
      run() / Popen() -> blocked + logged when allowlist violated.
      In controlled mode: command is sanitised or dropped.
      No shell=True ever permitted.
    """

    def __init__(self, app_id: str, api=None):
        self.app_id = app_id
        self.api = api # Reference to SecureAPI for lock checks
        self._call_window = deque() # Sliding window for rate limiting

    # ── Internal validation ───────────────────────────────────────────────────

    def _enforce_rate_limit(self):
        """Graduated Penalty Rate Limiting based on Hybrid Model."""
        now = time.time()
        while self._call_window and now - self._call_window[0] > 1.0:
            self._call_window.popleft()
        
        count = len(self._call_window)
        self._call_window.append(now)

        if count < 10: return

        overflow = count - 10
        target_id = (self.api.instance_id if self.api else None) or self.app_id

        if 1 <= overflow <= 2:
            logger.debug("[ProcessGuard] Rate Limit Soft Warning for '%s' (Calls: %d)", self.app_id, count)
        if 3 <= overflow <= 5:
            if RUNTIME_MANAGER:
                RUNTIME_MANAGER.apply_penalty(target_id, -5, f"Suspicious process activity speed ({count} calls/sec)")
            raise PermissionError(f"[Sandbox] Process Rate Limit Exceeded (Suspicious).")
        elif overflow > 5:
            if RUNTIME_MANAGER:
                RUNTIME_MANAGER.report_violation(target_id, f"Process Flooding Attempt detected ({count} calls/sec)")
            raise PermissionError(f"[Sandbox] CRITICAL: Process Flooding Blocked.")

    def _validate(self, cmd: Union[str, List[str]], kwargs: dict) -> str:
        """
        Returns the executable name if safe, raises ValueError if not.
        Caller decides what to do with the exception.
        """
        if kwargs.get("shell", False):
            raise ValueError(
                f"[ProcessGuard] shell=True is NEVER permitted (app='{self.app_id}')."
            )

        if isinstance(cmd, str):
            for ch in cmd:
                if ch in _INJECTION_CHARS:
                    raise ValueError(
                        f"[ProcessGuard] Injection char '{ch}' in command (app='{self.app_id}')."
                    )
            parts = shlex.split(cmd)
        else:
            parts = list(cmd)

        if not parts:
            raise ValueError("[ProcessGuard] Empty command.")

        exe = parts[0].lower()
        # Strip path — only care about the basename
        exe = exe.split("\\")[-1].split("/")[-1]
        if exe.endswith(".exe"):
            exe = exe[:-4]

        if exe not in _PROCESS_ALLOWLIST:
            raise ValueError(
                f"[PROCESS VIOLATION] App='{self.app_id}' tried to run forbidden exe '{exe}'."
            )

        return parts

    def _handle_blocked(self, reason: str) -> None:
        logger.critical(reason)
        PM_GUARD.check(self.app_id, "system_calls", reason)

        if ENFORCEMENT_LEVEL == "strict":
            raise ProcessLookupError(f"[Sandbox] Blocked: {reason}")
        # observation / controlled: logged, will return a dummy result

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, cmd: Union[str, List[str]], **kwargs) -> Any:
        """Controlled drop-in for subprocess.run()."""
        self._enforce_rate_limit()
        if self.api:
            self.api.check_api_lock("process")
        try:
            self._validate(cmd, kwargs)
        except ValueError as exc:
            self._handle_blocked(str(exc))
            # Controlled fallback: return a fake completed-process
            class _Fake:
                returncode = 1
                stdout = ""
                stderr = str(exc)
            return _Fake()

        logger.debug("[ProcessGuard] run(%s) for '%s'", cmd, self.app_id)
        
        
        # Governed Synchronous Spawn
        if RUNTIME_MANAGER:
            return RUNTIME_MANAGER.spawn_process(
                self.api.instance_id, 
                argv=self._validate(cmd, kwargs),
                background=False
            )
        else:
            # Subprocess Proxy Case (Handled by RemoteProcessProxy)
            raise RuntimeError("[Sandbox] Local spawning is disabled. Use api.process.")

    def Popen(self, cmd: Union[str, List[str]], **kwargs) -> Any:
        """Controlled drop-in for subprocess.Popen()."""
        self._enforce_rate_limit()
        if self.api:
            self.api.check_api_lock("process")
        try:
            self._validate(cmd, kwargs)
        except ValueError as exc:
            self._handle_blocked(str(exc))
            raise ProcessLookupError(str(exc))    # Popen callers expect a real object; can't fake it trivially

        logger.debug("[ProcessGuard] Popen(%s) for '%s'", cmd, self.app_id)
        
        
        # Governed Asynchronous Spawn
        if RUNTIME_MANAGER:
            return RUNTIME_MANAGER.spawn_process(
                self.api.instance_id, 
                argv=self._validate(cmd, kwargs),
                background=True
            )
        else:
            raise RuntimeError("[Sandbox] Local spawning is disabled. Use api.process.")

    def kill(self, pid: int) -> bool:
        """Controlled drop-in for process termination. Only allowed for self-owned pids."""
        if not self.api: return False
        return RUNTIME_MANAGER.kill_process(self.api.instance_id, pid)

    def terminate(self, pid: int) -> bool:
        """Alias for kill()."""
        return self.kill(pid)
