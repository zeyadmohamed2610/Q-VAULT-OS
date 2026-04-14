# =============================================================
#  telemetry.py — Q-VAULT OS  |  Anonymous Telemetry System
#
#  Collects anonymous usage data with opt-in consent
# =============================================================

import os
import json
import time
import threading
import hashlib
from typing import Dict, List, Any
from pathlib import Path
from collections import deque
from datetime import datetime

try:
    from system.sync_manager import SYNC_MANAGER

    HAS_SYNC = True
except Exception:
    HAS_SYNC = False

TELEMETRY_ENABLED = False


class TelemetryEvent:
    def __init__(self, event_type: str, data: Dict):
        self.event_type = event_type
        self.data = data
        self.timestamp = time.time()


class Telemetry:
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

        self._enabled = TELEMETRY_ENABLED
        self._events: deque = deque(maxlen=1000)
        self._command_usage: Dict[str, int] = {}
        self._app_usage: Dict[str, int] = {}
        self._crash_logs: List[Dict] = []
        self._lock = threading.Lock()
        self._session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def record_command(self, command: str):
        if not self._enabled:
            return

        with self._lock:
            self._command_usage[command] = self._command_usage.get(command, 0) + 1
            self._events.append(
                TelemetryEvent("command", {"cmd": command, "ts": time.time()})
            )

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_telemetry("command", {"cmd": command})
            except Exception:
                pass

    def record_app_usage(self, app_name: str):
        if not self._enabled:
            return

        with self._lock:
            self._app_usage[app_name] = self._app_usage.get(app_name, 0) + 1
            self._events.append(
                TelemetryEvent("app", {"app": app_name, "ts": time.time()})
            )

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_telemetry("app_usage", {"app": app_name})
            except Exception:
                pass

    def record_crash(self, error_type: str, message: str, traceback: str):
        if not self._enabled:
            return

        with self._lock:
            self._crash_logs.append(
                {
                    "error_type": error_type,
                    "message": message,
                    "timestamp": time.time(),
                    "session_id": self._session_id,
                }
            )

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_telemetry(
                    "crash", {"error_type": error_type, "message": message}
                )
            except Exception:
                pass

    def _anonymize_data(self, data: Dict) -> Dict:
        anonymized = dict(data)
        sensitive_keys = ["password", "token", "secret", "key", "path"]
        for key in sensitive_keys:
            if key in anonymized:
                anonymized[key] = "***REDACTED***"
        return anonymized

    def get_batch(self) -> List[Dict]:
        if not self._enabled:
            return []

        with self._lock:
            batch = []
            for event in list(self._events):
                batch.append(
                    {
                        "session_id": self._session_id,
                        "event_type": event.event_type,
                        "data": self._anonymize_data(event.data),
                        "timestamp": event.timestamp,
                    }
                )
            self._events.clear()
            return batch

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "session_id": self._session_id,
                "total_events": len(self._events),
                "unique_commands": len(self._command_usage),
                "unique_apps": len(self._app_usage),
                "crash_count": len(self._crash_logs),
                "command_usage": dict(self._command_usage),
                "app_usage": dict(self._app_usage),
            }

    def clear_data(self):
        with self._lock:
            self._events.clear()
            self._command_usage.clear()
            self._app_usage.clear()
            self._crash_logs.clear()


TELEMETRY = Telemetry()
