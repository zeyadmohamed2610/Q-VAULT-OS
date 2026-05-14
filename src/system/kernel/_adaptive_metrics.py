from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .adaptive_scheduler import AdaptiveScheduler

logger = logging.getLogger(__name__)

@dataclass
class MetricsSnapshot:
    """Point-in-time system metrics captured by AdaptiveScheduler."""
    tick:                  int
    algorithm:             str
    process_count:         int
    avg_waiting_time:      float
    max_waiting_time:      int
    starved_pids:          List[int]          = field(default_factory=list)
    aged_pids:             List[int]          = field(default_factory=list)
    core_utilization:      Dict[int, float]   = field(default_factory=dict)
    memory_fragmentation:  float              = 0.0
    memory_used:           int                = 0
    memory_total:          int                = 1024
    llm_available:         bool               = False

    def as_dict(self) -> dict:
        return {
            "tick":                 self.tick,
            "algorithm":            self.algorithm,
            "process_count":        self.process_count,
            "avg_waiting_time":     round(self.avg_waiting_time, 2),
            "max_waiting_time":     self.max_waiting_time,
            "starved_pids":         self.starved_pids,
            "aged_pids":            self.aged_pids,
            "core_utilization":     {str(k): round(v, 3) for k, v in self.core_utilization.items()},
            "memory_fragmentation": round(self.memory_fragmentation, 4),
            "memory_used":          self.memory_used,
            "memory_total":         self.memory_total,
            "llm_available":        self.llm_available,
        }

class AdaptiveMetricsCollector:
    """
    Handles system-wide metrics collection for the Adaptive Scheduler.
    """

    @staticmethod
    def collect(tick: int) -> MetricsSnapshot:
        algorithm = "UNKNOWN"
        process_count = 0
        wait_times: List[int] = []
        core_util: Dict[int, float] = {}
        frag = 0.0
        mem_used = 0
        mem_total = 1024
        llm_avail = False

        # Scheduler
        try:
            from system.kernel.scheduler import SCHEDULER
            algorithm = SCHEDULER.algorithm
            procs = list(SCHEDULER.ready_queue)
            if SCHEDULER.current_process: procs.append(SCHEDULER.current_process)
            process_count = len(procs)
            wait_times = [p.waiting_time for p in procs]
        except Exception as e:
            logger.debug(f"[ADAPTIVE] Metrics: Scheduler read failed: {e}")

        # Multicore
        try:
            from system.kernel.multicore_engine import MULTICORE_ENGINE
            core_util = MULTICORE_ENGINE.get_load_balance()
        except Exception as e:
            logger.debug(f"[ADAPTIVE] Metrics: Multicore read failed: {e}")

        # Memory
        try:
            from system.kernel.memory_manager import MEMORY_MANAGER
            frag = MEMORY_MANAGER.get_fragmentation_ratio()
            mem_used = MEMORY_MANAGER.total_used()
            mem_total = MEMORY_MANAGER.total_size
        except Exception as e:
            logger.debug(f"[ADAPTIVE] Metrics: Memory read failed: {e}")

        # AI
        try:
            from system.ai.llm_adapter import LLMAdapter
            llm_avail = LLMAdapter().is_connected
        except Exception:
            llm_avail = False

        avg_wait = (sum(wait_times) / len(wait_times)) if wait_times else 0.0
        
        return MetricsSnapshot(
            tick=tick,
            algorithm=algorithm,
            process_count=process_count,
            avg_waiting_time=avg_wait,
            max_waiting_time=max_wait(wait_times, default=0),
            core_utilization=core_util,
            memory_fragmentation=frag,
            memory_used=mem_used,
            memory_total=mem_total,
            llm_available=llm_avail
        )
