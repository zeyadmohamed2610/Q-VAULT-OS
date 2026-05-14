import time
import logging
from typing import Dict, Any
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Singleton orchestrator for system metrics.
    Reacts to events to update its internal snapshot.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
        
        # ── State ──
        self.start_time = time.time()
        self.event_count = 0
        self.error_count = 0
        self.active_windows = 0
        self.active_processes = 0
        
        self.events_per_sec = 0.0
        self._last_sec_timestamp = time.time()
        self._sec_event_count = 0
        
        self.latencies = [] # Store last 100 handler latencies
        self._history = []  # Historical snapshots
        
        from system.config import get_qvault_home
        import os
        self.save_path = os.path.join(get_qvault_home(), "system_metrics.json")
        self._save_counter = 0
        
        # ── Subscribe ──
        EVENT_BUS.subscribe(SystemEvent.DEBUG_EVENT_EMITTED, self._on_debug_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_OPENED, lambda _: self._update_windows(1))
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED, lambda _: self._update_windows(-1))
        EVENT_BUS.subscribe(SystemEvent.PROC_SPAWNED, lambda _: self._update_procs(1))
        EVENT_BUS.subscribe(SystemEvent.PROC_COMPLETED, lambda _: self._update_procs(-1))
        
        # Periodic report
        from PyQt5.QtCore import QTimer
        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _update_windows(self, delta):
        self.active_windows += delta

    def _update_procs(self, delta):
        self.active_processes += delta

    def _on_debug_event(self, payload):
        self.event_count += 1
        self._sec_event_count += 1
        
        # Update handler latency if provided in a hypothetical future debug fact
        # For now, we'll just track throughput

    def _on_tick(self):
        now = time.time()
        dt = now - self._last_sec_timestamp
        if dt >= 1.0:
            self.events_per_sec = self._sec_event_count / dt
            self._sec_event_count = 0
            self._last_sec_timestamp = now
            
            # Emit Metrics Fact
            snapshot = self.get_metrics_snapshot()
            self._history.append(snapshot)
            if len(self._history) > 100: self._history.pop(0)

            EVENT_BUS.emit(SystemEvent.DEBUG_METRICS_UPDATED, snapshot, source="MetricsCollector")
            
            # Persist every 10 ticks
            self._save_counter += 1
            if self._save_counter >= 10:
                self._save_counter = 0
                self._persist_history()

    def _persist_history(self):
        try:
            import json
            with open(self.save_path, "w") as f:
                json.dump(self._history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")

    def get_history(self):
        return self._history

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.start_time)
        return {
            "uptime_sec": uptime,
            "total_events": self.event_count,
            "events_per_sec": round(self.events_per_sec, 2),
            "active_windows": self.active_windows,
            "active_processes": self.active_processes,
            "errors": self.error_count
        }

# Global Instance Accessor
_collector = None
def get_metrics_collector():
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
