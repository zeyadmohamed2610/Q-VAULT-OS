import logging
import time
from collections import deque
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger("system.runtime.pressure_manager")

class PressureManager:
    """
    Autonomous Pressure Core (Phase 13.5).
    Monitors system load and manages backpressure signals to prevent kernel congestion.
    """
    def __init__(self):
        self.current_pressure_ratio = 0.0
        self.max_pressure_seen = 0.0
        self.pressure_history = deque(maxlen=120) # 2 mins @ 1Hz
        self._last_calc = time.time()
        
    def calculate_system_pressure(self, cpu_usage: float, ram_usage: float, queue_backlog: int):
        """
        Weighted Pressure Engine (Phase 15.5).
        Combines CPU, RAM, and Message Queue backlog into a single 'Pressure Ratio'.
        """
        now = time.time()
        # Weights: CPU (40%), RAM (30%), Queue (30%)
        q_factor = min(1.0, queue_backlog / 500.0) # Normalized
        
        self.current_pressure_ratio = (cpu_usage * 0.004) + (ram_usage * 0.003) + (q_factor * 0.3)
        self.max_pressure_seen = max(self.max_pressure_seen, self.current_pressure_ratio)
        
        # Log history every second
        if now - self._last_calc >= 1.0:
            self.pressure_history.append({"time": now, "ratio": round(self.current_pressure_ratio, 2)})
            self._last_calc = now
            
        self._evaluate_state()

    def _evaluate_state(self):
        """Transition system state based on pressure levels."""
        if self.current_pressure_ratio > 1.3:
            EVENT_BUS.emit(SystemEvent.EVENT_QVAULT_ERROR, {"detail": "CRITICAL_CONGESTION", "ratio": self.current_pressure_ratio})
        elif self.current_pressure_ratio > 1.0:
            # Trigger aggressive throttling
            pass

    def get_backpressure_factor(self) -> float:
        """Returns a multiplier for rate-limiting (1.0 = Normal, >1.0 = Throttled)."""
        if self.current_pressure_ratio > 1.0:
            return 1.0 + (self.current_pressure_ratio - 1.0) * 2
        return 1.0

# Global Singleton
PRESSURE_MANAGER = PressureManager()
