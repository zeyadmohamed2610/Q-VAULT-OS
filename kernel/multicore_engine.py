from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from kernel.process_manager import Process

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────

_DEFAULT_CORE_COUNT:     int   = 4
_MIGRATION_THRESHOLD:    float = 0.30   # trigger migration if spread ≥ this
_UTILIZATION_DECAY:      float = 0.95   # per-tick EWMA decay factor


# ── Core ─────────────────────────────────────────────────────────

@dataclass
class Core:
    """
    One virtual CPU core.

    core_id         : 0-based index
    current_process : Process currently executing on this core (or None)
    utilization     : EWMA utilization  0.0 (idle) … 1.0 (fully busy)
    total_ticks     : ticks this core has been active (started)
    busy_ticks      : ticks this core had a process assigned
    """
    core_id:         int
    current_process: Optional[Process] = field(default=None, repr=False)
    utilization:     float             = 0.0
    total_ticks:     int               = 0
    busy_ticks:      int               = 0

    # ── Derived helpers ──────────────────────────────────────────

    @property
    def is_idle(self) -> bool:
        return self.current_process is None

    @property
    def raw_utilization(self) -> float:
        """Non-smoothed ratio: busy_ticks / total_ticks."""
        return self.busy_ticks / max(self.total_ticks, 1)

    def as_dict(self) -> dict:
        proc = self.current_process
        return {
            "core_id":         self.core_id,
            "is_idle":         self.is_idle,
            "utilization":     round(self.utilization, 4),
            "raw_utilization": round(self.raw_utilization, 4),
            "total_ticks":     self.total_ticks,
            "busy_ticks":      self.busy_ticks,
            "current_pid":     proc.pid  if proc else None,
            "current_name":    proc.name if proc else None,
        }


# ── MulticoreEngine ───────────────────────────────────────────────

class MulticoreEngine:
    """
    SMP core manager — assignment, load balancing, and migration.

    The engine subscribes to CLOCK_TICK to:
      • Tick each core's utilization counters.
      • Run rebalance() to check for migration candidates.

    The Scheduler queries assign(proc) to get a core_id before
    scheduling a process; it calls release(pid) when a process
    terminates or is preempted off the CPU.
    """

    def __init__(
        self,
        core_count:          int   = _DEFAULT_CORE_COUNT,
        migration_threshold: float = _MIGRATION_THRESHOLD,
    ):
        self._lock                = threading.RLock()
        self._migration_threshold = migration_threshold
        self._subscribed          = False
        self._last_tick: int      = 0

        # Build initial core list
        self.cores: List[Core] = [Core(core_id=i) for i in range(core_count)]

        # pid → core_id index for O(1) release lookups
        self._proc_core: Dict[int, int] = {}

        logger.info(
            f"[MCE] Initialized — {core_count} cores, "
            f"migration_threshold={migration_threshold}"
        )

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to CLOCK_TICK for utilization tracking + rebalancing."""
        if self._subscribed:
            return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK, self._on_clock_tick)
        self._subscribed = True
        logger.info("[MCE] Started — subscribed to CLOCK_TICK.")

    def stop(self) -> None:
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK, self._on_clock_tick)
        self._subscribed = False
        logger.info("[MCE] Stopped.")

    # ── Core count ───────────────────────────────────────────────

    def set_core_count(self, n: int) -> None:
        """
        Resize the core pool to `n` cores.
        Reducing count: processes on removed cores are migrated first.
        """
        if n <= 0:
            raise ValueError(f"core_count must be ≥ 1, got {n}")
        with self._lock:
            current = len(self.cores)
            if n == current:
                return

            if n > current:
                # Add new idle cores
                for i in range(current, n):
                    self.cores.append(Core(core_id=i))
                logger.info(f"[MCE] Cores expanded: {current} → {n}")

            else:
                # Shrink: migrate processes off cores that will be removed
                for core in self.cores[n:]:
                    if core.current_process is not None:
                        # Find a target among surviving cores
                        target = self._least_loaded_core(exclude=None,
                                                          among=self.cores[:n])
                        if target is not None:
                            self._migrate(core, target, tick=self._last_tick)
                        else:
                            # No surviving core free — just unassign
                            proc = core.current_process
                            proc.cpu_id = -1
                            core.current_process = None
                            self._proc_core.pop(proc.pid, None)
                self.cores = self.cores[:n]
                logger.info(f"[MCE] Cores shrunk: {current} → {n}")

    # ── Assignment API ────────────────────────────────────────────

    def assign(self, proc: Process) -> int:
        """
        Assign `proc` to the most appropriate core.

        Priority:
          1. Affinity: if proc.preferred_core ≥ 0 and that core is idle.
          2. Least utilization among all cores.

        Sets proc.cpu_id and proc.preferred_core (if affinity was used).
        Emits CORE_ASSIGNED.

        Returns
        -------
        int — the core_id assigned.
        """
        with self._lock:
            chosen: Optional[Core] = None

            # 1. Core affinity
            pref = getattr(proc, 'preferred_core', -1)
            if 0 <= pref < len(self.cores):
                candidate = self.cores[pref]
                if candidate.is_idle:
                    chosen = candidate
                    logger.debug(
                        f"[MCE] Affinity hit: PID {proc.pid} → core {pref}"
                    )

            # 2. Least loaded core
            if chosen is None:
                chosen = self._least_loaded_core()

            if chosen is None:
                # All cores busy — pick the one with lowest utilization anyway
                chosen = min(self.cores, key=lambda c: c.utilization)

            # ── Assign ──────────────────────────────────────────
            if not chosen.is_idle:
                # Core is busy — current holder is now preempted
                # (Scheduler already handles status; we just track cores)
                old_proc = chosen.current_process
                self._proc_core.pop(old_proc.pid, None)

            chosen.current_process = proc
            self._proc_core[proc.pid] = chosen.core_id
            proc.cpu_id = chosen.core_id

            core_id = chosen.core_id

        EVENT_BUS.emit(
            SystemEvent.CORE_ASSIGNED,
            data={
                "pid":         proc.pid,
                "name":        proc.name,
                "core_id":     core_id,
                "utilization": round(self.cores[core_id].utilization, 4),
                "tick":        self._last_tick,
                "affinity":    (pref == core_id),
            },
            source="MulticoreEngine",
        )
        logger.debug(
            f"[MCE] ASSIGNED  PID {proc.pid} ({proc.name}) → core {core_id} "
            f"util={self.cores[core_id].utilization:.2f}"
        )
        return core_id

    def release(self, pid: int) -> bool:
        """
        Free the core currently held by `pid`.
        Called when a process terminates or is preempted.
        Returns True if the process was found.
        """
        with self._lock:
            core_id = self._proc_core.pop(pid, None)
            if core_id is None:
                return False
            core = self.cores[core_id]
            if core.current_process and core.current_process.pid == pid:
                core.current_process = None
        logger.debug(f"[MCE] RELEASED  PID {pid} from core {core_id}")
        return True

    def get_core_for(self, pid: int) -> Optional[int]:
        """Return the core_id currently assigned to `pid`, or None."""
        return self._proc_core.get(pid)

    # ── Load balance / migration ──────────────────────────────────

    def get_load_balance(self) -> Dict[int, float]:
        """Return {core_id: utilization} for all cores."""
        with self._lock:
            return {c.core_id: round(c.utilization, 4) for c in self.cores}

    def rebalance(self, tick: int = 0) -> List[int]:
        """
        Check utilization spread between busiest and idlest cores.
        If the spread exceeds migration_threshold, migrate the process
        from the busiest core to the idlest one.

        Returns list of migrated PIDs (usually 0 or 1 per call).
        """
        migrated_pids: List[int] = []

        with self._lock:
            if len(self.cores) < 2:
                return migrated_pids

            busiest = max(self.cores, key=lambda c: c.utilization)
            idlest  = min(self.cores, key=lambda c: c.utilization)

            spread = busiest.utilization - idlest.utilization
            if spread < self._migration_threshold:
                return migrated_pids

            # Only migrate if the busiest core actually has a process
            if busiest.current_process is None:
                return migrated_pids

            migrated_pid = self._migrate(busiest, idlest, tick=tick)
            if migrated_pid is not None:
                migrated_pids.append(migrated_pid)

        return migrated_pids

    # ── Query & stats ─────────────────────────────────────────────

    @property
    def core_count(self) -> int:
        return len(self.cores)

    @property
    def migration_threshold(self) -> float:
        return self._migration_threshold

    @migration_threshold.setter
    def migration_threshold(self, value: float) -> None:
        if not 0.0 < value <= 1.0:
            raise ValueError(f"threshold must be in (0, 1], got {value}")
        self._migration_threshold = value

    @property
    def stats(self) -> dict:
        with self._lock:
            cores_snap = [c.as_dict() for c in self.cores]
            busy  = sum(1 for c in self.cores if not c.is_idle)
            idle  = len(self.cores) - busy
            avg_u = sum(c.utilization for c in self.cores) / max(len(self.cores), 1)
        return {
            "core_count":          len(cores_snap),
            "busy_cores":          busy,
            "idle_cores":          idle,
            "avg_utilization":     round(avg_u, 4),
            "migration_threshold": self._migration_threshold,
            "last_tick":           self._last_tick,
            "cores":               cores_snap,
        }

    # ── Internal helpers ──────────────────────────────────────────

    def _least_loaded_core(
        self,
        exclude:  Optional[Core] = None,
        among:    Optional[List[Core]] = None,
    ) -> Optional[Core]:
        """
        Return the idle core with the lowest utilization.
        If no idle core exists, return None (caller falls back).
        """
        pool = among if among is not None else self.cores
        idle_cores = [
            c for c in pool
            if c.is_idle and (exclude is None or c.core_id != exclude.core_id)
        ]
        if not idle_cores:
            return None
        return min(idle_cores, key=lambda c: c.utilization)

    def _migrate(self, src: Core, dst: Core, tick: int = 0) -> Optional[int]:
        """
        Move src.current_process to dst.
        MUST be called with self._lock held.
        Emits PROCESS_MIGRATED.

        Returns the migrated PID or None if src had no process.
        """
        proc = src.current_process
        if proc is None:
            return None

        old_core = src.core_id
        new_core = dst.core_id

        src.current_process = None
        dst.current_process = proc
        self._proc_core[proc.pid] = new_core
        proc.cpu_id = new_core

        logger.info(
            f"[MCE] MIGRATE   PID {proc.pid} ({proc.name}) "
            f"core {old_core} → core {new_core} "
            f"(spread={src.utilization - dst.utilization:.2f})"
        )

        # Emit outside lock is preferred but we hold the lock here;
        # EventBus.emit is safe to call under lock in this project.
        EVENT_BUS.emit(
            SystemEvent.PROCESS_MIGRATED,
            data={
                "pid":          proc.pid,
                "name":         proc.name,
                "from_core":    old_core,
                "to_core":      new_core,
                "tick":         tick,
                "src_util":     round(src.utilization, 4),
                "dst_util":     round(dst.utilization, 4),
            },
            source="MulticoreEngine",
        )
        return proc.pid

    def _tick_cores(self, tick: int) -> None:
        """
        Update per-core utilization counters once per CLOCK_TICK.
        Uses EWMA smoothing so utilization changes gradually.
        """
        with self._lock:
            for core in self.cores:
                core.total_ticks += 1
                is_busy = not core.is_idle
                if is_busy:
                    core.busy_ticks += 1
                # EWMA: utilization = α * current_state + (1-α) * old_util
                instant = 1.0 if is_busy else 0.0
                core.utilization = (
                    _UTILIZATION_DECAY * core.utilization
                    + (1.0 - _UTILIZATION_DECAY) * instant
                )

    # ── EventBus handler ─────────────────────────────────────────

    def _on_clock_tick(self, payload: EventPayload) -> None:
        tick = payload.data.get("tick", 0)
        self._last_tick = tick
        self._tick_cores(tick)
        self.rebalance(tick=tick)


# ── Central Singleton ─────────────────────────────────────────────
MULTICORE_ENGINE = MulticoreEngine(
    core_count=_DEFAULT_CORE_COUNT,
    migration_threshold=_MIGRATION_THRESHOLD,
)
