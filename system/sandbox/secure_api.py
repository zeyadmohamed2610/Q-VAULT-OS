"""
system/sandbox/secure_api.py
─────────────────────────────────────────────────────────────────────────────
The Single Context Gateway for all sandboxed Q-Vault applications.

Every app launched by AppRegistry receives a SecureAPI instance injected
as `widget.secure_api`.  Apps MUST use this instead of raw system imports:

  ❌  import subprocess; subprocess.run(...)
  ✅  self.secure_api.process.run(...)

  ❌  import socket; socket.socket(...)
  ✅  self.secure_api.network.ping(...) / .port_scan(...)

  ❌  open("C:\\Windows\\...")
  ✅  self.secure_api.fs.open(path, "r")

  ❌  import os; os.scandir(path)
  ✅  self.secure_api.fs.scandir(path)

The API is app-ID-scoped so every sub-guard knows which app is acting.
"""

import uuid
import threading
import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject

from system.runtime_manager import RUNTIME_MANAGER

from .fs_guard import FileSystemGuard
from .process_guard import ProcessGuard
from .network_guard import NetworkGuard
from .system_guard import SystemGuard
from .intel_guard import IntelligenceGuard
from .permissions import PM_GUARD, ENFORCEMENT_LEVEL

logger = logging.getLogger("sandbox.secure_api")

# ── Phase 13.9: Hard Runtime Interdiction ──
# We interdict raw subprocess.Popen via stack-trace analysis to ensure
# NO app (Terminal, etc.) can bypass the SecureAPI governance logic.
import subprocess
_SYS_POPEN = subprocess.Popen

def _governed_popen_guard(*args, **kwargs):
    import traceback
    # Analyze the call stack to see if an app is trying a direct bypass
    stack = traceback.extract_stack()
    for frame in stack:
        # If any frame is inside the 'apps/' directory, it's an unauthorized bypass
        fn = frame.filename.replace("\\", "/")
        if "/apps/" in fn:
            logger.critical("[BYPASS INTERDICTED] App attempted direct subprocess execution: %s", fn)
            raise PermissionError("[Sandbox] CRITICAL: Direct subprocess access is FORBIDDEN. Use self.secure_api.process instead.")
    return _SYS_POPEN(*args, **kwargs)

# Secure the OS boundary
subprocess.Popen = _governed_popen_guard


class SecureAPI:
    """
    Controlled, transparent security gateway for Q-Vault OS apps.

    Attributes exposed to apps
    --------------------------
    fs       -> FileSystemGuard   (safe file operations)
    process  -> ProcessGuard      (safe subprocess execution)
    network  -> NetworkGuard      (safe ping / port-scan / local-info)
    app_id   -> str               (this app's identifier for audit trails)
    """

    def __init__(self, app_id: str, instance_id: str = None):
        self.app_id = app_id
        self.instance_id = instance_id or app_id  # Fallback to app_id
        self.is_locked = False
        
        # ── Centralized App Logging (with Rotation) ──
        import logging.handlers
        from pathlib import Path
        log_dir = Path(".logs/apps")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{app_id}.log"

        self.logger = logging.getLogger(f"app.{app_id}")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            # maxBytes=1MB, backupCount=3
            fh = logging.handlers.RotatingFileHandler(
                str(log_file), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
            fh.setFormatter(logging.Formatter("%(asctime)s | [%(levelname)s] %(message)s"))
            self.logger.addHandler(fh)
            self.logger.propagate = False

        # ── Initialize Guards with API reference for internal locking ──
        self._fs      = FileSystemGuard(app_id, api=self)
        self._process = ProcessGuard(app_id, api=self)
        self._network = NetworkGuard(app_id, api=self)
        self._system  = SystemGuard(app_id, api=self)
        self._intel   = IntelligenceGuard(app_id, api=self)

        logger.debug("[SecureAPI] Initialised for '%s' (ID: %s)", app_id, self.instance_id)

    @property
    def worker_token(self):
        """Context manager hook for Stage B/C Spawn Control with UUID tracking."""
        from contextlib import contextmanager
        import uuid

        @contextmanager
        def _token(worker_type: str = "total"):
            token_id = str(uuid.uuid4())
            # 1. Acquire with Token
            RUNTIME_MANAGER.acquire_worker(self.instance_id, worker_type, token=token_id)
            try:
                yield
            finally:
                # 2. Release with Token
                RUNTIME_MANAGER.release_worker(self.instance_id, worker_type, token=token_id)
        
        return _token

    def check_api_lock(self, component: str):
        """Internal check for guards to call directly."""
        if self.is_locked:
            self._report_quarantine_violation(component)

    @property
    def fs(self):
        self.check_api_lock("fs")
        return self._fs

    @property
    def process(self):
        self.check_api_lock("process")
        return self._process

    @property
    def network(self):
        self.check_api_lock("network")
        return self._network

    @property
    def system(self):
        # We don't check lock for system telemetry (read-only health)
        return self._system

    @property
    def intel(self):
        self.check_api_lock("intel")
        return self._intel

    def _report_quarantine_violation(self, component: str):
        err = f"App attempted to use {component} while QUARANTINED."
        logger.critical(f"[API LOCKED] {self.app_id} | {err}")
        raise PermissionError(f"[Sandbox] Access Denied: App is Quarantined and API is locked.")

    # ── Event reporting (legacy wrapper around dedicated logger) ──────────────

    def report_event(self, message: str, level: str = "INFO") -> None:
        """Apps may write to the system log at INFO/WARNING only."""
        if level.upper() == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    # ── Permission check (read-only) ──────────────────────────────────────────

    def can(self, action: str) -> bool:
        """
        Quick permission probe.
        Does not raise — just returns True/False so UI can adapt.
        """
        from .permissions import PermissionManager
        pm = PermissionManager()
        manifest = pm._load_manifest(self.app_id)
        return pm._evaluate(action, manifest.get("permissions", {}))

    # ── Catch-all: block undeclared API surface ───────────────────────────────

    def __getattr__(self, name: str):
        """Block any attribute not explicitly declared above."""
        logger.critical(
            "[API VIOLATION] App '%s' tried to access undeclared API '%s'.",
            self.app_id, name,
        )
        raise AttributeError(
            f"[Sandbox] SecureAPI has no attribute '{name}' — "
            f"access by '{self.app_id}' denied."
        )
