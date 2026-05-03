from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from kernel.process_manager import (
    Process,
    STATUS_READY,
    STATUS_RUNNING,
)

logger = logging.getLogger(__name__)


# ── Simulated register-file keys ──────────────────────────────────

_REG_PC    = "PC"     # Program Counter
_REG_SP    = "SP"     # Stack Pointer
_REG_ACC   = "ACC"    # Accumulator
_REG_FLAGS = "FLAGS"  # Status / flags word
_REG_TICK  = "TICK"   # Snapshot tick (when were these saved?)


# ── Dispatcher ────────────────────────────────────────────────────

class Dispatcher:
    """
    CPU context-switch engine — driven by PROC_SCHEDULED events.

    The Dispatcher does NOT choose which process to run — that is the
    Scheduler's job.  The Dispatcher only performs the mechanical
    register save/restore and status transitions.

    Thread safety:
        All mutable state is guarded by an RLock.  _on_scheduled() is
        called from the EventBus (which may be on the clock thread), so
        every public method is safe to call from any thread.
    """

    def __init__(self):
        self._lock = threading.RLock()

        # ── Accounting ───────────────────────────────────────────
        self.context_switch_count: int = 0
        self._total_switch_ns: int = 0      # cumulative switch overhead (ns)
        self._last_tick: int = 0            # tick of the most recent switch

        # ── CPU state ────────────────────────────────────────────
        # current_process mirrors the Scheduler's view but is owned
        # here for register-save purposes.
        self._current_process: Optional[Process] = None

        self._subscribed: bool = False

        logger.info("[DISPATCHER] Initialized.")

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to PROC_SCHEDULED. Safe to call more than once."""
        if self._subscribed:
            logger.debug("[DISPATCHER] start() already subscribed — no-op.")
            return
        EVENT_BUS.subscribe(SystemEvent.PROC_SCHEDULED, self._on_scheduled)
        self._subscribed = True
        logger.info("[DISPATCHER] Started — listening for PROC_SCHEDULED.")

    def stop(self) -> None:
        """Unsubscribe from PROC_SCHEDULED."""
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.PROC_SCHEDULED, self._on_scheduled)
        self._subscribed = False
        logger.info("[DISPATCHER] Stopped.")

    # ── Public API ────────────────────────────────────────────────

    def context_switch(
        self,
        from_process: Optional[Process],
        to_process: Process,
        tick: int = 0,
        cpu_id: int = 0,
    ) -> dict:
        """
        Perform a full context switch.

        Steps
        -----
        1. Save from_process registers into its PCB (saved_registers).
        2. Transition from_process status → READY (if it was RUNNING).
        3. Load to_process registers from its PCB (or create initial set).
        4. Transition to_process status → RUNNING, assign cpu_id.
        5. Increment context_switch_count.
        6. Emit PROC_CONTEXT_SWITCHED.
        7. Log the switch with tick number and wall-clock timing.

        Returns
        -------
        dict  — the payload that was emitted with PROC_CONTEXT_SWITCHED.
        """
        t_start = time.perf_counter_ns()

        with self._lock:
            tick = tick or self._last_tick

            # ── Step 1 & 2: Save outgoing process ───────────────
            saved_from: Optional[dict] = None
            if from_process is not None and from_process is not to_process:
                saved_from = self._save_registers(from_process, tick)
                if from_process.status == STATUS_RUNNING:
                    from_process.status = STATUS_READY
                logger.debug(
                    f"[DISPATCHER] tick={tick} | SAVE   PID {from_process.pid}"
                    f" ({from_process.name}) regs={saved_from}"
                )

            # ── Step 3 & 4: Load incoming process ────────────────
            loaded_regs = self._load_registers(to_process, tick, cpu_id)
            to_process.status = STATUS_RUNNING
            to_process.cpu_id = cpu_id

            # ── Step 5: Update accounting ─────────────────────────
            self.context_switch_count += 1
            self._last_tick = tick
            self._current_process = to_process

            t_end = time.perf_counter_ns()
            overhead_ns = t_end - t_start
            self._total_switch_ns += overhead_ns

            # ── Step 6: Build event payload ───────────────────────
            payload_data = {
                "tick":                 tick,
                "switch_number":        self.context_switch_count,
                "cpu_id":               cpu_id,
                "overhead_us":          round(overhead_ns / 1_000, 3),
                # outgoing
                "from_pid":             from_process.pid  if from_process else None,
                "from_name":            from_process.name if from_process else None,
                "from_saved_registers": saved_from,
                # incoming
                "to_pid":               to_process.pid,
                "to_name":              to_process.name,
                "to_loaded_registers":  loaded_regs,
                "to_remaining":         to_process.remaining_time,
                "to_priority":          to_process.priority,
            }

        # ── Step 6 (cont.): Emit outside lock to avoid deadlock ──
        EVENT_BUS.emit(
            SystemEvent.PROC_CONTEXT_SWITCHED,
            data=payload_data,
            source="Dispatcher",
        )

        # ── Step 7: Log ───────────────────────────────────────────
        from_label = (
            f"PID {from_process.pid} ({from_process.name})"
            if from_process else "idle"
        )
        logger.info(
            f"[DISPATCHER] tick={tick:>6} | CTX #{self.context_switch_count:>5} | "
            f"{from_label} → PID {to_process.pid} ({to_process.name}) | "
            f"cpu={cpu_id} | overhead={overhead_ns/1_000:.1f}µs"
        )

        return payload_data

    @property
    def current_process(self) -> Optional[Process]:
        """The process currently holding the CPU (Dispatcher's view)."""
        return self._current_process

    @property
    def stats(self) -> dict:
        """Observability snapshot for UI / debug tools."""
        with self._lock:
            avg_us = (
                round(self._total_switch_ns / max(self.context_switch_count, 1) / 1_000, 3)
                if self.context_switch_count else 0.0
            )
            return {
                "context_switch_count": self.context_switch_count,
                "avg_switch_overhead_us": avg_us,
                "total_overhead_ms":   round(self._total_switch_ns / 1_000_000, 3),
                "last_tick":           self._last_tick,
                "current_pid":         self._current_process.pid
                                       if self._current_process else None,
                "subscribed":          self._subscribed,
            }

    # ── EventBus handler ─────────────────────────────────────────

    def _on_scheduled(self, payload: EventPayload) -> None:
        """
        Triggered by PROC_SCHEDULED (emitted by Scheduler).

        The Scheduler has already selected the next process and updated
        ready_queue / current_process.  The Dispatcher's job here is
        purely mechanical: save the old registers, load the new ones.

        Because we don't hold a direct reference to the Scheduler, we
        extract what we need from the event payload and from the
        Process objects the Scheduler has already mutated.
        """
        data = payload.data
        tick   = data.get("tick", 0)
        to_pid = data.get("pid")

        if to_pid is None:
            logger.warning("[DISPATCHER] PROC_SCHEDULED payload missing 'pid' — skipping.")
            return

        # Retrieve the incoming Process object.
        # The Scheduler already set its status to RUNNING, so we trust
        # the reference stored in our _current_process as the outgoing one.
        with self._lock:
            outgoing = self._current_process

        # Import lazily to avoid circular imports at module load time.
        from kernel.process_manager import PM
        incoming = PM.get(to_pid)

        if incoming is None:
            logger.warning(
                f"[DISPATCHER] PROC_SCHEDULED for unknown PID {to_pid} — "
                f"process not found in PM table."
            )
            return

        # Avoid switching to the same process (no-op)
        if outgoing is not None and outgoing.pid == incoming.pid:
            logger.debug(
                f"[DISPATCHER] PID {to_pid} already on CPU — no switch needed."
            )
            return

        cpu_id = data.get("cpu_id", 0)
        self.context_switch(
            from_process=outgoing,
            to_process=incoming,
            tick=tick,
            cpu_id=cpu_id,
        )

    # ── Register helpers ─────────────────────────────────────────

    def _save_registers(self, proc: Process, tick: int) -> dict:
        """
        Snapshot the simulated CPU state into proc.saved_registers.

        The register values are derived from the process's scheduling
        metadata so the snapshot is deterministic and meaningful for
        OS simulation purposes (no real CPU registers exist).

        Returns the saved register dict.
        """
        regs = {
            _REG_PC:    tick,                   # "where we left off"
            _REG_SP:    proc.remaining_time,    # work left on the stack
            _REG_ACC:   proc.waiting_time,      # accumulated wait
            _REG_FLAGS: (proc.priority << 4) | (proc.cpu_id & 0xF),
            _REG_TICK:  tick,
        }
        proc.saved_registers = regs
        return regs

    def _load_registers(
        self, proc: Process, tick: int, cpu_id: int
    ) -> dict:
        """
        Restore the process's saved registers (or initialise fresh ones).

        If proc.saved_registers is empty (first time on CPU), we build
        an initial register set from the process's current state.

        Returns the loaded register dict.
        """
        if proc.saved_registers:
            # Restore previously saved state
            regs = dict(proc.saved_registers)
        else:
            # First dispatch — synthesise initial registers
            regs = {
                _REG_PC:    proc.arrival_tick,
                _REG_SP:    proc.burst_time,
                _REG_ACC:   0,
                _REG_FLAGS: (proc.priority << 4) | (cpu_id & 0xF),
                _REG_TICK:  tick,
            }

        # Always update TICK to the current context-switch tick so
        # observers can tell when these registers were last loaded.
        regs[_REG_TICK] = tick
        proc.saved_registers = regs
        return regs


# ── Central Singleton ─────────────────────────────────────────────
DISPATCHER = Dispatcher()
