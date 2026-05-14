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
import inspect
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject

from system.runtime_manager import RUNTIME_MANAGER
from system.runtime.inspector import INSPECTOR

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
    stack = traceback.extract_stack()
    
    # Trusted internal components that are allowed to launch processes
    TRUSTED_COMPONENTS = ["qvault_launcher.py", "qvault_adapter.py", "qvault_runtime_bridge.py"]
    
    # If any part of the call stack is a trusted component, allow the launch
    for frame in stack:
        fn = frame.filename.replace("\\", "/")
        if any(trusted in fn for trusted in TRUSTED_COMPONENTS):
            return _SYS_POPEN(*args, **kwargs)
            
    # Otherwise, check if any app is trying to bypass
    for frame in stack:
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

        # ── Sovereign Governor: Resource Quotas ──
        self._call_count = 0
        self._last_reset = 0.0
        self._throttle_delay = 0.0
        self._governance_lock = threading.Lock()

        logger.debug("[SecureAPI] Initialised for '%s' (ID: %s)", app_id, self.instance_id)

    def _apply_governance(self):
        """
        Sovereign Resource Governor.
        Detects high-frequency API flooding and introduces artificial latency.
        """
        import time
        from core.event_bus import EVENT_BUS, SystemEvent

        now = time.time()
        with self._governance_lock:
            # Reset counter every second
            if now - self._last_reset > 1.0:
                self._call_count = 0
                self._last_reset = now
                self._throttle_delay = 0.0

            self._call_count += 1
            
            # Threshold: 50 calls per second
            if self._call_count > 50:
                # Progressive throttling: add 10ms for every 10 calls over limit
                self._throttle_delay = min(0.5, (self._call_count - 50) * 0.001)
                
                # Emit pressure event to UI
                EVENT_BUS.emit(
                    "ui.resource_pressure",
                    data={
                        "app_id": self.app_id,
                        "instance_id": self.instance_id,
                        "calls_per_sec": self._call_count,
                        "delay_ms": int(self._throttle_delay * 1000)
                    },
                    source="SovereignGovernor"
                )

        if self._throttle_delay > 0:
            time.sleep(self._throttle_delay)

    def _verify_caller_integrity(self):
        """
        Forensic Stack Verification.
        Ensures that the caller of a sensitive API method is actually 
        within the expected module path for this instance.
        """
        stack = inspect.stack()
        if len(stack) < 3: return

        # stack[1] is the property getter, stack[2] is the actual caller
        caller_frame = stack[2]
        filename = caller_frame.filename.replace("\\", "/")
        
        # Internal system components are trusted
        if "/system/" in filename or "/core/" in filename or "/apps/terminal/" in filename:
            return

        # Check if the caller is inside the apps directory
        if "/apps/" not in filename:
            INSPECTOR._log_governance(self.instance_id, "INTEGRITY_VIOLATION", 
                                     f"API call from unexpected file: {filename}")
            raise PermissionError(f"[Sandbox] Cross-context API invocation blocked: {filename}")

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
        if RUNTIME_MANAGER.is_system_locked:
            raise PermissionError("[Sandbox] System is LOCKED. Please authenticate to continue.")
            
        if self.is_locked:
            self._report_quarantine_violation(component)

    @property
    def fs(self):
        self._verify_caller_integrity()
        self._apply_governance()
        self.check_api_lock("fs")
        return self._fs

    @property
    def process(self):
        self._verify_caller_integrity()
        self._apply_governance()
        self.check_api_lock("process")
        return self._process

    @property
    def network(self):
        self._verify_caller_integrity()
        self._apply_governance()
        self.check_api_lock("network")
        return self._network

    @property
    def system(self):
        # We don't check lock for system telemetry (read-only health)
        return self._system

    @property
    def intel(self):
        self._apply_governance()
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

    def request_permission(self, permission_id: str, justification: str) -> bool:
        """
        Dynamic Privilege Escalation: Request a permission from the user at runtime.
        
        This triggers a Kernel-level Modal Dialog that the app cannot influence.
        Returns True if the user grants the permission, False otherwise.
        """
        import time
        from core.event_bus import EVENT_BUS, SystemEvent
        
        logger.info("[CONSENT] App '%s' is requesting permission: %s", self.app_id, permission_id)
        
        # We use a threading.Event to wait for the user's response from the UI thread
        response_event = threading.Event()
        result = {"granted": False}

        def _on_response(payload):
            if payload.data.get("request_id") == request_id:
                result["granted"] = payload.data.get("granted", False)
                response_event.set()

        request_id = str(uuid.uuid4())
        EVENT_BUS.subscribe("ui.permission_response", _on_response)
        
        EVENT_BUS.emit(
            SystemEvent.REQ_USER_INPUT, # We can use a specific event or a generic one
            data={
                "type": "permission_consent",
                "request_id": request_id,
                "app_id": self.app_id,
                "permission": permission_id,
                "justification": justification
            },
            source="SecureAPI"
        )
        
        # Wait up to 60 seconds for user response
        timed_out = not response_event.wait(timeout=60.0)
        EVENT_BUS.unsubscribe("ui.permission_response", _on_response)
        
        if timed_out:
            logger.warning("[CONSENT] Request timed out for app '%s'", self.app_id)
            return False
            
        if result["granted"]:
            # Grant temporary permission in the PM_GUARD
            PM_GUARD.grant_temporary(self.app_id, permission_id)
            logger.info("[CONSENT] User GRANTED '%s' to app '%s'", permission_id, self.app_id)
            return True
        else:
            logger.warning("[CONSENT] User DENIED '%s' to app '%s'", permission_id, self.app_id)
            return False

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
