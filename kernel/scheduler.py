from __future__ import annotations

import logging
import threading
from typing import List, Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from kernel.process_manager import (
    Process,
    STATUS_RUNNING,
    STATUS_READY,
    STATUS_TERMINATED,
    STATUS_WAITING,
)

logger = logging.getLogger(__name__)


# ── Algorithm identifiers ─────────────────────────────────────────

ALGO_FCFS = "FCFS"
ALGO_SJF  = "SJF"
ALGO_RR   = "RR"
ALGO_PRIO = "PRIO"

_VALID_ALGORITHMS = {ALGO_FCFS, ALGO_SJF, ALGO_RR, ALGO_PRIO}

_DEFAULT_QUANTUM = 3   # ticks


# ── Scheduler ────────────────────────────────────────────────────

class Scheduler:
    """
    Kernel CPU scheduler — tick-driven, algorithm-pluggable.

    The scheduler subscribes to SystemEvent.CLOCK_TICK and calls
    schedule() on every tick.  All state mutations are protected by
    an RLock so external callers (UI, tests) can safely call
    add_process / remove_process from any thread.

    Scheduling state per tick:
      • current_process  — the Process currently holding the CPU
      • ready_queue      — ordered list of READY processes
      • _tick_count      — global tick counter (mirrors clock)
      • _quantum_ticks   — how many ticks current_process has run
                           in the current quantum (RR only)
    """

    def __init__(
        self,
        algorithm: str = ALGO_FCFS,
        quantum: int = _DEFAULT_QUANTUM,
    ):
        self._algorithm: str = algorithm
        self._quantum: int = quantum

        self.ready_queue: List[Process] = []
        self.current_process: Optional[Process] = None

        self._tick_count: int = 0       # monotonic, from CLOCK_TICK payloads
        self._quantum_ticks: int = 0    # ticks spent by current_process this quantum

        self._lock = threading.RLock()
        self._subscribed = False

        logger.info(
            f"[SCHEDULER] Initialized — algorithm={algorithm}, quantum={quantum}"
        )

    # ── Public API ───────────────────────────────────────────────

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def quantum(self) -> int:
        return self._quantum

    @quantum.setter
    def quantum(self, value: int):
        if value <= 0:
            raise ValueError(f"quantum must be > 0, got {value}")
        with self._lock:
            self._quantum = value
        logger.info(f"[SCHEDULER] Quantum updated → {value} ticks")

    def set_algorithm(self, algorithm: str) -> None:
        """
        Hot-swap the scheduling algorithm.
        Accepts: "FCFS", "SJF", "RR", "PRIO"
        Takes effect from the very next tick.
        """
        algo = algorithm.upper()
        if algo not in _VALID_ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Valid choices: {sorted(_VALID_ALGORITHMS)}"
            )
        with self._lock:
            old = self._algorithm
            self._algorithm = algo
            self._quantum_ticks = 0   # reset quantum counter on switch
        logger.info(f"[SCHEDULER] Algorithm switched: {old} → {algo}")

    def start(self) -> None:
        """Subscribe to CLOCK_TICK. Safe to call more than once."""
        if self._subscribed:
            logger.debug("[SCHEDULER] start() called but already subscribed.")
            return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = True
        logger.info("[SCHEDULER] Started — listening for CLOCK_TICK.")

    def stop(self) -> None:
        """Unsubscribe from CLOCK_TICK."""
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK, self._on_tick)
        self._subscribed = False
        logger.info("[SCHEDULER] Stopped.")

    def add_process(self, proc: Process, current_tick: int = 0) -> None:
        """
        Enqueue a Process into the ready queue.
        Sets arrival_tick if not already set.
        """
        with self._lock:
            if proc.arrival_tick == 0 and current_tick:
                proc.arrival_tick = current_tick
            proc.status = STATUS_READY
            self.ready_queue.append(proc)
        logger.debug(
            f"[SCHEDULER] Enqueued PID {proc.pid} ({proc.name}) "
            f"burst={proc.burst_time} prio={proc.priority}"
        )

    def remove_process(self, pid: int) -> bool:
        """
        Remove a process from the ready queue (e.g. killed externally).
        If it is the current_process, preempt it first.
        Returns True if found anywhere.
        """
        with self._lock:
            # Check current process
            if self.current_process and self.current_process.pid == pid:
                self._preempt(reason="removed")
                return True
            # Check ready queue
            before = len(self.ready_queue)
            self.ready_queue = [p for p in self.ready_queue if p.pid != pid]
            return len(self.ready_queue) < before

    @property
    def stats(self) -> dict:
        """Snapshot for UI / debug tools."""
        with self._lock:
            return {
                "algorithm":       self._algorithm,
                "quantum":         self._quantum,
                "tick":            self._tick_count,
                "quantum_ticks":   self._quantum_ticks,
                "current_pid":     self.current_process.pid if self.current_process else None,
                "ready_queue_len": len(self.ready_queue),
                "ready_pids":      [p.pid for p in self.ready_queue],
            }

    # ── Tick handler ─────────────────────────────────────────────

    def _on_tick(self, payload: EventPayload) -> None:
        """Called by EventBus on every CLOCK_TICK — drives the scheduler."""
        tick = payload.data.get("tick", self._tick_count + 1)
        with self._lock:
            self._tick_count = tick
            self._tick_waiting_processes()
            self.schedule()

    # ── Core scheduling logic ────────────────────────────────────

    def schedule(self) -> None:
        """
        One scheduling decision per tick.

        Steps:
          1. Advance current process (decrement remaining_time).
          2. Check for completion / quantum expiry / preemption.
          3. If CPU is free, select next process using the active algorithm.
          4. Emit PROC_SCHEDULED when a new process takes the CPU.
        """
        # ── Step 1: Advance current process ─────────────────────
        if self.current_process is not None:
            cp = self.current_process

            # Decrement remaining ticks (only when burst_time was specified)
            if cp.burst_time > 0:
                cp.remaining_time = max(0, cp.remaining_time - 1)

            self._quantum_ticks += 1

            # ── Step 2a: Process has finished ───────────────────
            if cp.burst_time > 0 and cp.remaining_time == 0:
                cp.turnaround_time = self._tick_count - cp.arrival_tick
                cp.status = STATUS_TERMINATED
                logger.info(
                    f"[SCHEDULER] PID {cp.pid} ({cp.name}) terminated — "
                    f"TAT={cp.turnaround_time} wait={cp.waiting_time}"
                )
                self.current_process = None
                self._quantum_ticks = 0

            # ── Step 2b: Round-Robin quantum expired ────────────
            elif self._algorithm == ALGO_RR and self._quantum_ticks >= self._quantum:
                EVENT_BUS.emit(
                    SystemEvent.PROC_QUANTUM_EXPIRED,
                    data={
                        "pid":           cp.pid,
                        "name":          cp.name,
                        "remaining":     cp.remaining_time,
                        "quantum_ticks": self._quantum_ticks,
                        "tick":          self._tick_count,
                    },
                    source="Scheduler",
                )
                self._preempt(reason="quantum_expired", re_queue=True)

            # ── Step 2c: Priority preemption ─────────────────────
            elif self._algorithm == ALGO_PRIO and self.ready_queue:
                best = max(self.ready_queue, key=lambda p: p.priority)
                if best.priority > cp.priority:
                    self._preempt(reason="priority", re_queue=True)

        # ── Step 3: Select next process if CPU is free ───────────
        if self.current_process is None and self.ready_queue:
            next_proc = self._select_next()
            if next_proc is not None:
                self.ready_queue.remove(next_proc)
                next_proc.status = STATUS_RUNNING
                self.current_process = next_proc
                self._quantum_ticks = 0

                # ── Multicore: ask engine for core assignment ─────
                core_id = 0
                mce = _get_multicore_engine()
                if mce is not None:
                    core_id = mce.assign(next_proc)

                EVENT_BUS.emit(
                    SystemEvent.PROC_SCHEDULED,
                    data={
                        "pid":           next_proc.pid,
                        "name":          next_proc.name,
                        "algorithm":     self._algorithm,
                        "burst_time":    next_proc.burst_time,
                        "remaining":     next_proc.remaining_time,
                        "priority":      next_proc.priority,
                        "waiting_time":  next_proc.waiting_time,
                        "arrival_tick":  next_proc.arrival_tick,
                        "tick":          self._tick_count,
                        "core_id":       core_id,
                    },
                    source="Scheduler",
                )
                logger.debug(
                    f"[SCHEDULER] Scheduled PID {next_proc.pid} ({next_proc.name}) "
                    f"via {self._algorithm} on core {core_id}"
                )

    # ── Selection strategies ─────────────────────────────────────

    def _select_next(self) -> Optional[Process]:
        """Return the next process to run without removing it from the queue."""
        if not self.ready_queue:
            return None

        if self._algorithm == ALGO_FCFS:
            # Earliest arrival_tick wins; tie-break by pid (insertion order)
            return min(self.ready_queue, key=lambda p: (p.arrival_tick, p.pid))

        elif self._algorithm == ALGO_SJF:
            # Shortest remaining burst_time wins; tie-break by arrival_tick
            return min(
                self.ready_queue,
                key=lambda p: (p.burst_time if p.burst_time > 0 else float("inf"),
                               p.arrival_tick),
            )

        elif self._algorithm == ALGO_RR:
            # Round-Robin: just take the head of the queue (FIFO order)
            return self.ready_queue[0]

        elif self._algorithm == ALGO_PRIO:
            # Highest priority wins; tie-break by arrival_tick
            return max(
                self.ready_queue,
                key=lambda p: (p.priority, -p.arrival_tick),
            )

        # Fallback — should never be reached
        logger.warning(f"[SCHEDULER] Unknown algorithm '{self._algorithm}', falling back to FCFS")
        return self.ready_queue[0]

    # ── Helpers ──────────────────────────────────────────────────

    def _preempt(self, reason: str = "preempted", re_queue: bool = False) -> None:
        """
        Remove current_process from CPU.
        If re_queue=True, push it back to the tail of the ready queue.
        Emits PROC_PREEMPTED.
        """
        cp = self.current_process
        if cp is None:
            return

        cp.status = STATUS_READY
        EVENT_BUS.emit(
            SystemEvent.PROC_PREEMPTED,
            data={
                "pid":           cp.pid,
                "name":          cp.name,
                "reason":        reason,
                "remaining":     cp.remaining_time,
                "quantum_ticks": self._quantum_ticks,
                "tick":          self._tick_count,
            },
            source="Scheduler",
        )
        logger.debug(
            f"[SCHEDULER] PID {cp.pid} preempted (reason={reason}, re_queue={re_queue})"
        )

        if re_queue:
            self.ready_queue.append(cp)

        # Release core back to MulticoreEngine
        mce = _get_multicore_engine()
        if mce is not None:
            mce.release(cp.pid)

        self.current_process = None
        self._quantum_ticks = 0

    def _tick_waiting_processes(self) -> None:
        """
        Increment waiting_time for every process sitting in the ready queue.
        Called once per tick before schedule() runs.
        """
        for proc in self.ready_queue:
            proc.waiting_time += 1


def _get_multicore_engine():
    """Lazy import to avoid circular dependency with multicore_engine."""
    from kernel.multicore_engine import MULTICORE_ENGINE
    return MULTICORE_ENGINE


# ── Central Singleton ─────────────────────────────────────────────
SCHEDULER = Scheduler(algorithm=ALGO_FCFS, quantum=_DEFAULT_QUANTUM)
