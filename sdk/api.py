# =============================================================
#  sdk/api.py — Q-Vault OS  |  Unified Public API
#
#  The authoritative entry point for all Q-Vault developers.
#  Supports both local plugins and isolated processes.
# =============================================================

import logging
from typing import Any, Callable, Dict, Optional
from core.event_bus import EVENT_BUS, SystemEvent
from .events import REQ_NOTIFICATION, REQ_APP_LAUNCH

logger = logging.getLogger(__name__)

class QVaultAPI:
    """
    Main SDK interface. 
    Decouples developers from internal managers using EventBus.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QVaultAPI, cls).__new__(cls)
            cls._instance._init_api()
        return cls._instance

    def _init_api(self):
        self._bridge = None # Set this for isolated IPC mode
        self.version = "2.0.0"

    def set_bridge(self, bridge):
        """Configure the API to use an IPC bridge (Isolated Mode)."""
        self._bridge = bridge

    def emit(self, event_name: str, payload: Dict[str, Any] = None):
        """Generic event emitter."""
        if self._bridge:
            self._bridge.send_event(event_name, payload)
        else:
            EVENT_BUS.emit(event_name, payload)

    def subscribe(self, event_name: str, callback: Callable):
        """Generic event listener."""
        if self._bridge:
            self._bridge.listen(event_name, callback)
        else:
            EVENT_BUS.subscribe(event_name, callback)

    def notify(self, title: str, message: str, level: str = "info"):
        """Request a system notification."""
        payload = {
            "title": title,
            "message": message,
            "level": level
        }
        self.emit(REQ_NOTIFICATION, payload)

    def launch_app(self, app_id: str):
        """Request to launch another application."""
        self.emit(REQ_APP_LAUNCH, {"name": app_id})

    def toggle_debug(self):
        """Toggle the System Observability Layer."""
        from .events import REQ_DEBUG_TOGGLE
        self.emit(REQ_DEBUG_TOGGLE)

    def ask_ai(self, prompt: str):
        """Send a natural language request to the AI Controller."""
        from .events import REQ_USER_INPUT
        self.emit(REQ_USER_INPUT, {"text": prompt})

    def get_system_state(self) -> Dict[str, Any]:
        """
        Returns a safe snapshot of non-sensitive system data.
        In local mode, reads from core.system_state.
        In IPC mode, performs a sync call via bridge.
        """
        if self._bridge:
            return self._bridge.call("sys.get_state")
        
        try:
            from core.system_state import STATE
            return {
                "user": STATE.current_user if STATE.current_user else "guest",
                "uptime": STATE.get_uptime_seconds(),
                "status": "online"
            }
        except Exception:
            return {"status": "unknown"}

# Singleton instance for public use
api = QVaultAPI()
