from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent

logger = logging.getLogger(__name__)


# ── Tunable constants ─────────────────────────────────────────────

METRICS_INTERVAL:     int   = 20    # ticks between rule-based passes
LLM_INTERVAL:         int   = 100   # ticks between LLM consultations
AGING_THRESHOLD:      int   = 30    # ticks waiting → priority +1
STARVATION_THRESHOLD: int   = 50    # ticks waiting → starvation alert
MAX_PRIORITY:         int   = 10    # cap for priority after aging
FRAG_WARN_THRESHOLD:  float = 0.70  # memory fragmentation warning level
UTIL_SPREAD_THRESHOLD:float = 0.40  # core utilisation imbalance threshold

VALID_ALGORITHMS = {"FCFS", "SJF", "RR", "PRIO"}

# Deterministic fallback rules (when LLM unavailable):
#   high avg_waiting_time → favour short-burst scheduling
#   starvation present    → switch to FCFS (age-ordered fairness)
#   otherwise             → keep RR as safe default
_FALLBACK_HIGH_WAIT_ALGO  = "SJF"
_FALLBACK_STARVATION_ALGO  = "FCFS"
_FALLBACK_DEFAULT_ALGO     = "RR"


# ── Metrics snapshot ──────────────────────────────────────────────

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
            "core_utilization":     {str(k): round(v, 3)
                                     for k, v in self.core_utilization.items()},
            "memory_fragmentation": round(self.memory_fragmentation, 4),
            "memory_used":          self.memory_used,
            "memory_total":         self.memory_total,
            "llm_available":        self.llm_available,
        }


# ── AdaptiveScheduler ─────────────────────────────────────────────

class AdaptiveScheduler:
    """
    AI-augmented adaptive scheduling layer.

    Observes the system every tick and makes autonomous adjustments
    via deterministic rules (aging, starvation detection) and optional
    LLM-driven algorithm switching.

    This class does NOT replace the base Scheduler — it decorates it.
    It calls SCHEDULER.set_algorithm() to apply changes.
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

        # Running history of snapshots (last 10 kept for LLM context)
        self._snapshot_history: List[MetricsSnapshot] = []

        # Total counts for observability
        self._total_aging_boosts:    int = 0
        self._total_starvation_evts: int = 0
        self._total_algo_changes:    int = 0
        self._total_llm_calls:       int = 0

        logger.info(
            f"[ADAPTIVE] Initialized — metrics every {metrics_interval} ticks, "
            f"LLM every {llm_interval} ticks"
        )

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to CLOCK_TICK. Safe to call multiple times."""
        if self._subscribed:
            return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = True
        logger.info("[ADAPTIVE] Started.")

    def stop(self) -> None:
        """Unsubscribe from CLOCK_TICK."""
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = False
        logger.info("[ADAPTIVE] Stopped.")

    def _should_throttle(self) -> bool:
        """Return True if CPU usage is high enough to warrant throttling."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            return cpu > 85
        except Exception:
            return False

    def _on_tick(self, payload: EventPayload) -> None:
        tick = payload.data.get("tick", 0)
        self._last_tick = tick

        # CPU throttle check — skip non-critical work under heavy load
        if self._should_throttle():
            if tick % 60 == 0:  # Log once per ~second (60 ticks)
                logger.warning("[ADAPTIVE] CPU throttle active — skipping non-critical tasks")
            return  # Skip analytics/metrics when overloaded

        # Rule-based pass every METRICS_INTERVAL ticks
        if tick > 0 and tick % self._metrics_interval == 0:
            snapshot = self._collect_metrics(tick)
            self._apply_aging(snapshot)
            self._detect_starvation(snapshot)
            self._check_imbalance(snapshot)
            with self._lock:
                self._snapshot_history.append(snapshot)
                if len(self._snapshot_history) > 10:
                    self._snapshot_history.pop(0)

        # LLM consultation every LLM_INTERVAL ticks
        if tick > 0 and tick % self._llm_interval == 0:
            self._consult_llm(tick)

    # ── Metrics collection ────────────────────────────────────────

    def _collect_metrics(self, tick: int) -> MetricsSnapshot:
        """
        Pull a system-wide metrics snapshot from all kernel singletons.
        All imports are lazy to avoid circular dependencies.
        """
        algorithm      = "UNKNOWN"
        process_count  = 0
        wait_times:  List[int] = []
        core_util:   Dict[int, float] = {}
        frag         = 0.0
        mem_used     = 0
        mem_total    = 1024
        llm_avail    = False

        # ── Scheduler ────────────────────────────────────────
        try:
            from kernel.scheduler import SCHEDULER
            algorithm     = SCHEDULER.algorithm
            queue_procs   = list(SCHEDULER.ready_queue)
            process_count = len(queue_procs)
            # Include current process if any
            cur = SCHEDULER.current_process
            if cur:
                queue_procs.append(cur)
                process_count += 1
            wait_times = [p.waiting_time for p in queue_procs]
        except Exception as exc:
            logger.debug(f"[ADAPTIVE] Scheduler read failed: {exc}")

        # ── Multicore Engine ──────────────────────────────────
        try:
            from kernel.multicore_engine import MULTICORE_ENGINE
            core_util = MULTICORE_ENGINE.get_load_balance()
        except Exception as exc:
            logger.debug(f"[ADAPTIVE] Multicore read failed: {exc}")

        # ── Memory Manager ────────────────────────────────────
        try:
            from kernel.memory_manager import MEMORY_MANAGER
            frag      = MEMORY_MANAGER.get_fragmentation_ratio()
            mem_used  = MEMORY_MANAGER.total_used()
            mem_total = MEMORY_MANAGER.total_size
        except Exception as exc:
            logger.debug(f"[ADAPTIVE] Memory read failed: {exc}")

        # ── LLM Adapter availability ──────────────────────────
        try:
            from system.ai.llm_adapter import LLMAdapter
            # Check if any connected adapter is available;
            # LLMAdapter.is_connected is False by default in the stub.
            _probe = LLMAdapter()
            llm_avail = _probe.is_connected
        except Exception:
            llm_avail = False

        avg_wait = (sum(wait_times) / len(wait_times)) if wait_times else 0.0
        max_wait = max(wait_times, default=0)

        return MetricsSnapshot(
            tick                 = tick,
            algorithm            = algorithm,
            process_count        = process_count,
            avg_waiting_time     = avg_wait,
            max_waiting_time     = max_wait,
            core_utilization     = core_util,
            memory_fragmentation = frag,
            memory_used          = mem_used,
            memory_total         = mem_total,
            llm_available        = llm_avail,
        )

    # ── Rule-based: Aging ─────────────────────────────────────────

    def _apply_aging(self, snapshot: MetricsSnapshot) -> None:
        """
        Aging: processes waiting longer than AGING_THRESHOLD ticks
        receive a +1 priority boost (capped at MAX_PRIORITY).
        This prevents low-priority processes from starving forever.
        """
        aged: List[int] = []

        try:
            from kernel.scheduler import SCHEDULER
            for proc in list(SCHEDULER.ready_queue):
                if proc.waiting_time >= self._aging_threshold:
                    old_prio = proc.priority
                    proc.priority = min(MAX_PRIORITY, proc.priority + 1)
                    if proc.priority != old_prio:
                        aged.append(proc.pid)
                        self._total_aging_boosts += 1
                        logger.debug(
                            f"[ADAPTIVE] AGING  PID {proc.pid} "
                            f"prio {old_prio} → {proc.priority} "
                            f"(waited {proc.waiting_time} ticks)"
                        )
        except Exception as exc:
            logger.debug(f"[ADAPTIVE] Aging pass failed: {exc}")

        snapshot.aged_pids = aged

        if aged:
            EVENT_BUS.emit(
                SystemEvent.AGING_APPLIED,
                data={
                    "tick":          snapshot.tick,
                    "aged_pids":     aged,
                    "count":         len(aged),
                    "threshold":     self._aging_threshold,
                    "total_boosts":  self._total_aging_boosts,
                },
                source="AdaptiveScheduler",
            )
            logger.info(
                f"[ADAPTIVE] Aging applied to {len(aged)} process(es): {aged}"
            )

    # ── Rule-based: Starvation detection ─────────────────────────

    def _detect_starvation(self, snapshot: MetricsSnapshot) -> None:
        """
        Flag any process whose waiting_time exceeds STARVATION_THRESHOLD.
        Emits STARVATION_DETECTED with full details for each offender.
        """
        starved: List[int] = []

        try:
            from kernel.scheduler import SCHEDULER
            for proc in list(SCHEDULER.ready_queue):
                if proc.waiting_time > self._starvation_threshold:
                    starved.append(proc.pid)
                    self._total_starvation_evts += 1
                    logger.warning(
                        f"[ADAPTIVE] STARVATION  PID {proc.pid} "
                        f"({proc.name})  waited {proc.waiting_time} ticks  "
                        f"prio={proc.priority}"
                    )
        except Exception as exc:
            logger.debug(f"[ADAPTIVE] Starvation scan failed: {exc}")

        snapshot.starved_pids = starved

        if starved:
            EVENT_BUS.emit(
                SystemEvent.STARVATION_DETECTED,
                data={
                    "tick":            snapshot.tick,
                    "starved_pids":    starved,
                    "count":           len(starved),
                    "threshold_ticks": self._starvation_threshold,
                    "current_algo":    snapshot.algorithm,
                },
                source="AdaptiveScheduler",
            )

    # ── Rule-based: Imbalance warnings ───────────────────────────

    def _check_imbalance(self, snapshot: MetricsSnapshot) -> None:
        utils = list(snapshot.core_utilization.values())
        if len(utils) < 2:
            return
        spread = max(utils) - min(utils)
        if spread >= UTIL_SPREAD_THRESHOLD:
            logger.warning(
                f"[ADAPTIVE] Core utilization imbalance: "
                f"spread={spread:.2f}  {snapshot.core_utilization}"
            )
        if snapshot.memory_fragmentation >= FRAG_WARN_THRESHOLD:
            logger.warning(
                f"[ADAPTIVE] High memory fragmentation: "
                f"{snapshot.memory_fragmentation:.1%}"
            )

    # ── AI-driven: LLM consultation ───────────────────────────────

    def _consult_llm(self, tick: int) -> None:
        """
        Build a metrics snapshot, ask the LLMAdapter for a scheduling
        recommendation, validate it, and apply if appropriate.
        Falls back to deterministic rules when LLM is unavailable.
        """
        with self._lock:
            history_snap = list(self._snapshot_history)

        snapshot = self._collect_metrics(tick)
        self._total_llm_calls += 1

        if snapshot.llm_available:
            recommendation = self._ask_llm(snapshot, history_snap)
        else:
            recommendation = self._deterministic_recommendation(snapshot)

        if recommendation:
            self._apply_algorithm_change(
                new_algo=recommendation,
                snapshot=snapshot,
                source="LLM" if snapshot.llm_available else "deterministic",
            )

    def _ask_llm(
        self,
        snapshot: MetricsSnapshot,
        history: List[MetricsSnapshot],
    ) -> Optional[str]:
        """
        Send a structured prompt to LLMAdapter and parse the response.

        Expected JSON response format:
          {
            "algorithm": "RR" | "FCFS" | "SJF" | "PRIO",
            "reasoning": "...",
            "confidence": 0.0 - 1.0
          }

        Returns the recommended algorithm string, or None if:
          - LLM is unavailable / returns None
          - Response JSON is malformed
          - Recommended algorithm is not in VALID_ALGORITHMS
          - Recommended algorithm is the same as the current one
        """
        try:
            from system.ai.llm_adapter import LLMAdapter
            adapter = LLMAdapter()
        except ImportError:
            return None

        prompt = self._build_llm_prompt(snapshot)
        context = {
            "domain":        "os_kernel_scheduling",
            "current_algo":  snapshot.algorithm,
            "metrics":       snapshot.as_dict(),
            "history_ticks": [s.tick for s in history],
        }

        try:
            response = adapter.process(prompt, context)
        except Exception as exc:
            logger.error(f"[ADAPTIVE] LLM call failed: {exc}")
            return None

        if response is None:
            logger.debug("[ADAPTIVE] LLM returned None — using fallback")
            return None

        return self._parse_llm_response(response, snapshot.algorithm)

    def _build_llm_prompt(self, snapshot: MetricsSnapshot) -> str:
        """Construct the scheduling advisory prompt for the LLM."""
        starved_str = (
            f"{len(snapshot.starved_pids)} process(es) starving "
            f"(PIDs: {snapshot.starved_pids})"
            if snapshot.starved_pids else "none"
        )
        util_str = ", ".join(
            f"core{k}={v:.0%}"
            for k, v in snapshot.core_utilization.items()
        ) or "unknown"

        return (
            f"You are a kernel scheduling advisor for Q-Vault OS.\n\n"
            f"Current system state at tick {snapshot.tick}:\n"
            f"  Algorithm:          {snapshot.algorithm}\n"
            f"  Processes in queue: {snapshot.process_count}\n"
            f"  Avg waiting time:   {snapshot.avg_waiting_time:.1f} ticks\n"
            f"  Max waiting time:   {snapshot.max_waiting_time} ticks\n"
            f"  Starvation:         {starved_str}\n"
            f"  Core utilization:   {util_str}\n"
            f"  Memory frag:        {snapshot.memory_fragmentation:.1%}\n\n"
            f"Available algorithms: FCFS, SJF, RR, PRIO\n\n"
            f"Respond ONLY with valid JSON, no markdown, no explanation:\n"
            f'{{"algorithm":"<ALGO>","reasoning":"<why>","confidence":<0.0-1.0>}}'
        )

    def _parse_llm_response(
        self,
        response: Any,
        current_algo: str,
    ) -> Optional[str]:
        """
        Parse the LLM response dict into a validated algorithm string.
        Accepts both a raw dict and a JSON string.
        """
        try:
            if isinstance(response, str):
                # Strip markdown fences if present
                cleaned = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(cleaned)
            elif isinstance(response, dict):
                data = response
            else:
                logger.warning(f"[ADAPTIVE] Unexpected LLM response type: {type(response)}")
                return None

            algo = str(data.get("algorithm", "")).upper().strip()
            confidence = float(data.get("confidence", 0.0))
            reasoning  = data.get("reasoning", "")

            if algo not in VALID_ALGORITHMS:
                logger.warning(f"[ADAPTIVE] LLM suggested unknown algo '{algo}' — rejected")
                return None

            if algo == current_algo:
                logger.info(
                    f"[ADAPTIVE] LLM agrees: keep {algo} "
                    f"(conf={confidence:.2f})  reason='{reasoning}'"
                )
                return None

            if confidence < 0.5:
                logger.info(
                    f"[ADAPTIVE] LLM suggestion '{algo}' rejected — "
                    f"low confidence {confidence:.2f}"
                )
                return None

            logger.info(
                f"[ADAPTIVE] LLM recommends '{algo}' "
                f"(conf={confidence:.2f})  reason='{reasoning}'"
            )
            return algo

        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(f"[ADAPTIVE] LLM response parse error: {exc}")
            return None

    def _deterministic_recommendation(self, snapshot: MetricsSnapshot) -> Optional[str]:
        """
        Rule-based algorithm recommendation when the LLM is offline.

        Rules (in priority order):
          1. Active starvation present        → FCFS (arrival-order fairness)
          2. High avg wait (> 40 ticks)       → SJF  (reduce completion time)
          3. Balanced, normal load            → RR   (default fairness)
          4. Same as current                  → None (no change needed)
        """
        if snapshot.starved_pids:
            target = _FALLBACK_STARVATION_ALGO
            reason = f"starvation detected ({len(snapshot.starved_pids)} PIDs)"
        elif snapshot.avg_waiting_time > 40:
            target = _FALLBACK_HIGH_WAIT_ALGO
            reason = f"high avg wait {snapshot.avg_waiting_time:.1f} ticks"
        else:
            target = _FALLBACK_DEFAULT_ALGO
            reason = "stable load — default fairness"

        if target == snapshot.algorithm:
            logger.debug(f"[ADAPTIVE] Deterministic: keep {target} ({reason})")
            return None

        logger.info(f"[ADAPTIVE] Deterministic: switch to {target} — {reason}")
        return target

    # ── Algorithm application ─────────────────────────────────────

    def _apply_algorithm_change(
        self,
        new_algo: str,
        snapshot: MetricsSnapshot,
        source:   str = "adaptive",
    ) -> None:
        """
        Apply the new scheduling algorithm via SCHEDULER.set_algorithm()
        and emit SCHEDULER_ALGORITHM_CHANGED.
        """
        old_algo = snapshot.algorithm

        try:
            from kernel.scheduler import SCHEDULER
            SCHEDULER.set_algorithm(new_algo)
        except Exception as exc:
            logger.error(f"[ADAPTIVE] Failed to apply algorithm '{new_algo}': {exc}")
            return

        self._total_algo_changes += 1

        EVENT_BUS.emit(
            SystemEvent.SCHEDULER_ALGORITHM_CHANGED,
            data={
                "old_algorithm":   old_algo,
                "new_algorithm":   new_algo,
                "source":          source,
                "tick":            snapshot.tick,
                "avg_wait":        round(snapshot.avg_waiting_time, 2),
                "starved_count":   len(snapshot.starved_pids),
                "total_changes":   self._total_algo_changes,
            },
            source="AdaptiveScheduler",
        )
        logger.info(
            f"[ADAPTIVE] Algorithm changed: {old_algo} → {new_algo} "
            f"(source={source}, tick={snapshot.tick})"
        )

    # ── Observability ─────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        with self._lock:
            last = self._snapshot_history[-1].as_dict() if self._snapshot_history else {}
        return {
            "subscribed":             self._subscribed,
            "last_tick":              self._last_tick,
            "metrics_interval":       self._metrics_interval,
            "llm_interval":           self._llm_interval,
            "aging_threshold":        self._aging_threshold,
            "starvation_threshold":   self._starvation_threshold,
            "total_aging_boosts":     self._total_aging_boosts,
            "total_starvation_evts":  self._total_starvation_evts,
            "total_algo_changes":     self._total_algo_changes,
            "total_llm_calls":        self._total_llm_calls,
            "snapshot_history_len":   len(self._snapshot_history),
            "last_snapshot":          last,
        }

    def last_snapshot(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._snapshot_history[-1] if self._snapshot_history else None


# ── Central Singleton ─────────────────────────────────────────────
ADAPTIVE_SCHEDULER = AdaptiveScheduler()
