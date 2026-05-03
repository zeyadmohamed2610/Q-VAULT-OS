import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs" / "qvault"


class QVaultAdapter(QObject):
    """
    Non-destructive adapter for the qvault-pc-mediator subsystem.

    This class is the SOLE interface between the OS and QVault.
    All status queries, lifecycle commands, and event emissions
    flow through this adapter.
    """

    # Qt signals for direct UI binding
    state_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._process = None            # subprocess.Popen handle
        self._running = False
        self._pid: Optional[int] = None
        self._start_time: Optional[float] = None
        self._token_connected = False
        self._vault_locked = True
        self._session_active = False
        self._last_error: Optional[str] = None
        self._event_log: list = []

        # Ensure log directory exists
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Poll timer — checks process status every 2s
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)

        self._log_event("ADAPTER_INIT", "QVault adapter initialized")
        logger.info("[QVault] Adapter initialized")

    # ── Public API ────────────────────────────────────────────

    def connect(self) -> bool:
        """Start monitoring the mediator. Launches if not running."""
        if not self._running:
            return self.launch()
        self._log_event("CONNECT", "Adapter connected to running mediator")
        return True

    def disconnect(self):
        """Stop monitoring (does NOT terminate the mediator)."""
        self._poll_timer.stop()
        self._log_event("DISCONNECT", "Adapter disconnected")

    def is_running(self) -> bool:
        """Check if the mediator process is alive."""
        with self._lock:
            if self._process is not None:
                alive = self._process.poll() is None
                if not alive and self._running:
                    self._handle_process_exit()
                return alive
            return False

    def launch(self) -> bool:
        """Launch the mediator subprocess."""
        if self.is_running():
            self._log_event("LAUNCH_SKIP", "Mediator already running")
            return True

        try:
            from desktop.applications.qvault_launcher import launch_mediator
            process = launch_mediator()
            if process is None:
                self._last_error = "Failed to launch mediator executable"
                self._emit_event("EVENT_QVAULT_ERROR", {
                    "error": self._last_error
                })
                return False

            with self._lock:
                self._process = process
                self._running = True
                self._pid = process.pid
                self._start_time = time.time()
                self._last_error = None

            self._poll_timer.start(2000)
            self._log_event("STARTED", f"Mediator started (PID={process.pid})")
            self._emit_event("EVENT_QVAULT_STARTED", {
                "pid": process.pid,
                "timestamp": time.time(),
            })
            self._emit_state()
            return True

        except Exception as exc:
            self._last_error = str(exc)
            self._log_event("LAUNCH_ERROR", str(exc))
            self._emit_event("EVENT_QVAULT_ERROR", {"error": str(exc)})
            return False

    def shutdown(self):
        """Gracefully stop the mediator subprocess."""
        if not self._running or self._process is None:
            return

        try:
            from desktop.applications.qvault_launcher import terminate_mediator
            terminate_mediator(self._process)
        except Exception as exc:
            logger.error("[QVault] Shutdown error: %s", exc)

        self._handle_process_exit()

    def get_token_status(self) -> Dict[str, Any]:
        """Get current token connection status."""
        return {
            "connected": self._token_connected,
            "mediator_running": self._running,
        }

    def get_vault_status(self) -> Dict[str, Any]:
        """Get current vault status."""
        return {
            "locked": self._vault_locked,
            "session_active": self._session_active,
            "mediator_running": self._running,
        }

    def get_full_state(self) -> Dict[str, Any]:
        """Get complete state snapshot."""
        with self._lock:
            uptime = None
            if self._start_time and self._running:
                uptime = time.time() - self._start_time

            return {
                "mediator_running": self._running,
                "pid": self._pid,
                "uptime": uptime,
                "token_connected": self._token_connected,
                "vault_locked": self._vault_locked,
                "session_active": self._session_active,
                "last_error": self._last_error,
                "event_count": len(self._event_log),
            }

    def get_event_log(self, limit: int = 50) -> list:
        """Get recent integration events."""
        return list(self._event_log[-limit:])

    # ── Simulated State Transitions ───────────────────────────
    # These allow the OS to update state based on external signals
    # or future IPC mechanisms without modifying qvault internals.

    def set_token_connected(self, connected: bool):
        """Update token connection state (called by bridge/IPC)."""
        if self._token_connected != connected:
            self._token_connected = connected
            event = "EVENT_QVAULT_CONNECTED" if connected else "EVENT_QVAULT_DISCONNECTED"
            state = "connected" if connected else "disconnected"
            self._log_event("TOKEN_" + state.upper(), f"Token {state}")
            self._emit_event(event, {"token_state": state})
            self._emit_state()

    def set_vault_locked(self, locked: bool):
        """Update vault lock state (called by bridge/IPC)."""
        if self._vault_locked != locked:
            self._vault_locked = locked
            event = "EVENT_QVAULT_LOCKED" if locked else "EVENT_QVAULT_UNLOCKED"
            state = "locked" if locked else "unlocked"
            self._log_event("VAULT_" + state.upper(), f"Vault {state}")
            self._emit_event(event, {"vault_state": state})
            self._emit_state()

    # ── Internal ──────────────────────────────────────────────

    def _poll_status(self):
        """Periodic process health check."""
        if self._process is None:
            return

        poll = self._process.poll()
        if poll is not None and self._running:
            self._handle_process_exit()

    def _handle_process_exit(self):
        """Handle mediator process termination."""
        with self._lock:
            exit_code = None
            if self._process is not None:
                exit_code = self._process.poll()
            self._running = False
            self._token_connected = False
            self._vault_locked = True
            self._session_active = False

        self._poll_timer.stop()
        self._log_event("STOPPED", f"Mediator stopped (exit={exit_code})")
        self._emit_event("EVENT_QVAULT_STOPPED", {
            "exit_code": exit_code,
            "pid": self._pid,
        })
        self._emit_state()

    def _emit_event(self, event_name: str, data: dict = None):
        """Emit an event through the OS EventBus."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            event_map = {
                "EVENT_QVAULT_STARTED": SystemEvent.EVENT_QVAULT_STARTED,
                "EVENT_QVAULT_STOPPED": SystemEvent.EVENT_QVAULT_STOPPED,
                "EVENT_QVAULT_CONNECTED": SystemEvent.EVENT_QVAULT_CONNECTED,
                "EVENT_QVAULT_DISCONNECTED": SystemEvent.EVENT_QVAULT_DISCONNECTED,
                "EVENT_QVAULT_UNLOCKED": SystemEvent.EVENT_QVAULT_UNLOCKED,
                "EVENT_QVAULT_LOCKED": SystemEvent.EVENT_QVAULT_LOCKED,
                "EVENT_QVAULT_ERROR": SystemEvent.EVENT_QVAULT_ERROR,
            }
            ev = event_map.get(event_name)
            if ev:
                EVENT_BUS.emit(ev, data or {}, source="QVaultAdapter")
        except Exception as exc:
            logger.debug("[QVault] EventBus emit failed: %s", exc)

    def _emit_state(self):
        """Emit full state snapshot via Qt signal."""
        try:
            self.state_changed.emit(self.get_full_state())
        except Exception:
            pass

    def _log_event(self, event_type: str, message: str):
        """Write to integration log file and in-memory log."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] [{event_type}] {message}"
        self._event_log.append(entry)
        if len(self._event_log) > 200:
            self._event_log = self._event_log[-100:]

        try:
            log_file = _LOG_DIR / "integration.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass

    def cleanup(self):
        """Release resources. Called on OS shutdown."""
        self._poll_timer.stop()
        self._log_event("CLEANUP", "Adapter shutting down")
        # Note: we do NOT kill the mediator on adapter cleanup
        # to preserve the user's spec of independent runnability.
