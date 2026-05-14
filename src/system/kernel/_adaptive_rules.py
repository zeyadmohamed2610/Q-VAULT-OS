from __future__ import annotations
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .adaptive_scheduler import AdaptiveScheduler
    from ._adaptive_metrics import MetricsSnapshot

logger = logging.getLogger(__name__)

class AdaptiveRulesEngine:
    """
    Deterministic rule-based logic for aging, starvation, and imbalance detection.
    """

    @staticmethod
    def apply_aging(scheduler: 'AdaptiveScheduler', snapshot: 'MetricsSnapshot') -> List[int]:
        from system.kernel.scheduler import SCHEDULER
        from core.event_bus import EVENT_BUS, SystemEvent
        
        aged: List[int] = []
        try:
            for proc in list(SCHEDULER.ready_queue):
                if proc.waiting_time >= scheduler._aging_threshold:
                    old_prio = proc.priority
                    proc.priority = min(10, proc.priority + 1) # MAX_PRIORITY=10
                    if proc.priority != old_prio:
                        aged.append(proc.pid)
                        scheduler._total_aging_boosts += 1
        except Exception as e:
            logger.debug(f"[ADAPTIVE] Aging failed: {e}")

        if aged:
            EVENT_BUS.emit(SystemEvent.AGING_APPLIED, {"tick": snapshot.tick, "aged_pids": aged}, source="AdaptiveScheduler")
        return aged

    @staticmethod
    def detect_starvation(scheduler: 'AdaptiveScheduler', snapshot: 'MetricsSnapshot') -> List[int]:
        from system.kernel.scheduler import SCHEDULER
        from core.event_bus import EVENT_BUS, SystemEvent
        
        starved: List[int] = []
        try:
            for proc in list(SCHEDULER.ready_queue):
                if proc.waiting_time > scheduler._starvation_threshold:
                    starved.append(proc.pid)
                    scheduler._total_starvation_evts += 1
        except Exception as e:
            logger.debug(f"[ADAPTIVE] Starvation scan failed: {e}")

        if starved:
            EVENT_BUS.emit(SystemEvent.STARVATION_DETECTED, {"tick": snapshot.tick, "starved_pids": starved}, source="AdaptiveScheduler")
        return starved
