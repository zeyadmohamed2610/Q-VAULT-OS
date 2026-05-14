from __future__ import annotations

import logging
import threading
from typing import List, Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from ._adaptive_metrics import MetricsSnapshot, AdaptiveMetricsCollector
from ._adaptive_rules import AdaptiveRulesEngine
from ._adaptive_ai import AdaptiveAIEngine

logger = logging.getLogger(__name__)

METRICS_INTERVAL:     int   = 20
LLM_INTERVAL:         int   = 100
AGING_THRESHOLD:      int   = 30
STARVATION_THRESHOLD: int   = 50

class AdaptiveScheduler:
    """
    AI-augmented adaptive scheduling layer (Refactored v5).
    Decorates the base Scheduler with intelligence and autonomous governance.
    """

    def __init__(
        self,
        metrics_interval:     int   = METRICS_INTERVAL,
        llm_interval:         int   = LLM_INTERVAL,
        aging_threshold:      int   = AGING_THRESHOLD,
        starvation_threshold: int   = STARVATION_THRESHOLD,
    ):
        self._metrics_interval     = metrics_interval
        self._llm_interval         = llm_interval
        self._aging_threshold      = aging_threshold
        self._starvation_threshold = starvation_threshold

        self._lock       = threading.RLock()
        self._subscribed = False
        self._last_tick  = 0
        self._snapshot_history: List[MetricsSnapshot] = []

        self._total_aging_boosts:    int = 0
        self._total_starvation_evts: int = 0
        self._total_algo_changes:    int = 0
        self._total_llm_calls:       int = 0

        logger.info("[ADAPTIVE] Initialized.")

    def start(self) -> None:
        if self._subscribed: return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = True

    def stop(self) -> None:
        if not self._subscribed: return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = False

    def _on_tick(self, payload: EventPayload) -> None:
        tick = payload.data.get("tick", 0)
        self._last_tick = tick

        # 1. Rule-based analysis
        if tick > 0 and tick % self._metrics_interval == 0:
            snapshot = AdaptiveMetricsCollector.collect(tick)
            AdaptiveRulesEngine.apply_aging(self, snapshot)
            AdaptiveRulesEngine.detect_starvation(self, snapshot)
            
            with self._lock:
                self._snapshot_history.append(snapshot)
                if len(self._snapshot_history) > 10: self._snapshot_history.pop(0)

        # 2. AI consultation
        if tick > 0 and tick % self._llm_interval == 0:
            self._total_llm_calls += 1
            last_snap = self.last_snapshot()
            if last_snap:
                recommendation = AdaptiveAIEngine.consult(self, last_snap)
                if recommendation:
                    self._apply_algorithm_change(recommendation, last_snap)

    def _apply_algorithm_change(self, new_algo: str, snapshot: MetricsSnapshot) -> None:
        try:
            from system.kernel.scheduler import SCHEDULER
            if SCHEDULER.algorithm != new_algo:
                old = SCHEDULER.algorithm
                SCHEDULER.set_algorithm(new_algo)
                self._total_algo_changes += 1
                EVENT_BUS.emit(SystemEvent.SCHEDULER_ALGORITHM_CHANGED, {
                    "old_algorithm": old,
                    "new_algorithm": new_algo,
                    "tick": snapshot.tick
                }, source="AdaptiveScheduler")
                logger.info(f"[ADAPTIVE] Algorithm Change: {old} -> {new_algo}")
        except Exception as e:
            logger.error(f"[ADAPTIVE] Failed to change algorithm: {e}")

    @property
    def stats(self) -> dict:
        with self._lock:
            last = self._snapshot_history[-1].as_dict() if self._snapshot_history else {}
        return {
            "last_tick": self._last_tick,
            "total_aging_boosts": self._total_aging_boosts,
            "total_algo_changes": self._total_algo_changes,
            "last_snapshot": last
        }

    def last_snapshot(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._snapshot_history[-1] if self._snapshot_history else None

# ── Central Singleton ─────────────────────────────────────────────
ADAPTIVE_SCHEDULER = AdaptiveScheduler()
