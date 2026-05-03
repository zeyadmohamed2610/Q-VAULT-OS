from __future__ import annotations

import heapq
import itertools
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent

logger = logging.getLogger(__name__)


# ── Interrupt types ───────────────────────────────────────────────

class InterruptType(Enum):
    TIMER       = "timer"     # periodic clock tick
    IO_COMPLETE = "io"        # I/O operation finished
    PAGE_FAULT  = "page"      # memory page not present
    MEMORY_FULL = "mem_full"  # RAM exhausted
    USB_DEVICE  = "usb"       # Hardware token plugged/unplugged


# ── Default priorities (lower number = higher urgency) ────────────
#   1 = highest (handled before anything else)
#   9 = lowest  (background)

_DEFAULT_PRIORITY: Dict[InterruptType, int] = {
    InterruptType.PAGE_FAULT:  1,   # must resolve immediately
    InterruptType.MEMORY_FULL: 2,   # critical resource exhaustion
    InterruptType.USB_DEVICE:  3,   # hardware attach/detach
    InterruptType.IO_COMPLETE: 4,   # device ready — don't keep it waiting
    InterruptType.TIMER:       5,   # periodic — lowest urgency
}

# How often (in ticks) a TIMER interrupt fires
_TIMER_INTERVAL: int = 5


# ── Interrupt dataclass ───────────────────────────────────────────

@dataclass(order=False)
class Interrupt:
    """
    One interrupt request (IRQ).

    Fields
    ------
    type       : interrupt category
    priority   : 1 = highest urgency, higher numbers = lower urgency
    source_pid : process that triggered the interrupt (None for hardware)
    tick       : simulation tick at which the interrupt was raised
    seq        : monotonic sequence number (tie-break for equal priority)
    """
    type:       InterruptType
    priority:   int
    source_pid: Optional[int]
    tick:       int
    seq:        int = field(default=0, compare=False)

    # ── heap ordering: (priority, seq) — lower wins ──────────────
    def __lt__(self, other: "Interrupt") -> bool:
        return (self.priority, self.seq) < (other.priority, other.seq)

    def as_dict(self) -> dict:
        return {
            "type":       self.type.value,
            "priority":   self.priority,
            "source_pid": self.source_pid,
            "tick":       self.tick,
            "seq":        self.seq,
        }


# ── InterruptManager ──────────────────────────────────────────────

class InterruptManager:
    """
    Kernel interrupt subsystem — priority-queue based IRQ handler.

    Architecture
    ------------
    _queue  : min-heap of Interrupt objects, ordered by (priority, seq)
    _seq    : monotonic counter for tie-breaking equal-priority IRQs
              (FIFO within the same priority level)
    _handlers : optional per-type Python callbacks for custom logic

    The manager subscribes to:
      • CLOCK_TICK  → auto-fires TIMER every TIMER_INTERVAL ticks
                   → calls handle() to drain pending interrupts
      • MEMORY_FULL → auto-raises a MEMORY_FULL interrupt
    """

    def __init__(self, timer_interval: int = _TIMER_INTERVAL):
        self._queue:          List[Interrupt] = []   # heapq min-heap
        self._seq             = itertools.count()
        self._lock            = threading.RLock()
        self._subscribed      = False
        self._timer_interval  = timer_interval
        self._last_tick:  int = 0
        self._total_raised:  int = 0
        self._total_handled: int = 0

        # Optional per-type handler callbacks:
        #   register via set_handler(InterruptType.PAGE_FAULT, my_fn)
        self._handlers: Dict[InterruptType, Callable[[Interrupt], None]] = {}

        logger.info(
            f"[IRQ] Initialized — timer_interval={timer_interval} ticks"
        )

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to CLOCK_TICK and MEMORY_FULL. Safe to call multiple times."""
        if self._subscribed:
            logger.debug("[IRQ] start() already subscribed — no-op.")
            return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK,   self._on_clock_tick)
        EVENT_BUS.subscribe(SystemEvent.MEMORY_FULL,  self._on_memory_full)
        self._subscribed = True
        logger.info("[IRQ] Started — subscribed to CLOCK_TICK + MEMORY_FULL.")

    def stop(self) -> None:
        """Unsubscribe from all EventBus events."""
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK,  self._on_clock_tick)
        EVENT_BUS.unsubscribe(SystemEvent.MEMORY_FULL, self._on_memory_full)
        self._subscribed = False
        logger.info("[IRQ] Stopped.")

    # ── Public API ────────────────────────────────────────────────

    def raise_interrupt(
        self,
        itype:      InterruptType,
        source_pid: Optional[int] = None,
        priority:   Optional[int] = None,
        tick:       int = 0,
    ) -> Interrupt:
        """
        Push a new interrupt onto the priority queue.

        Parameters
        ----------
        itype      : type of interrupt (InterruptType enum)
        source_pid : PID of the triggering process (None = hardware/kernel)
        priority   : override default priority (1=highest; default per type)
        tick       : simulation tick at raise time

        Returns
        -------
        Interrupt — the queued interrupt object
        """
        prio = priority if priority is not None else _DEFAULT_PRIORITY.get(itype, 5)
        irq  = Interrupt(
            type       = itype,
            priority   = prio,
            source_pid = source_pid,
            tick       = tick or self._last_tick,
            seq        = next(self._seq),
        )
        with self._lock:
            heapq.heappush(self._queue, irq)
            self._total_raised += 1
            qlen = len(self._queue)

        EVENT_BUS.emit(
            SystemEvent.INTERRUPT_RAISED,
            data={
                "interrupt":   irq.as_dict(),
                "queue_depth": qlen,
            },
            source="InterruptManager",
        )
        logger.debug(
            f"[IRQ] RAISED  — {itype.value:12s} | prio={prio} "
            f"pid={source_pid} tick={irq.tick} seq={irq.seq} "
            f"queue_depth={qlen}"
        )
        return irq

    def handle(self, tick: int = 0) -> Optional[Interrupt]:
        """
        Dequeue and process the highest-priority pending interrupt.

        If a per-type handler is registered (via set_handler), it is
        called synchronously before the INTERRUPT_HANDLED event fires.

        Returns
        -------
        Interrupt — the interrupt that was handled
        None      — if the queue was empty (no-op)
        """
        with self._lock:
            if not self._queue:
                return None
            irq = heapq.heappop(self._queue)
            self._total_handled += 1
            remaining = len(self._queue)

        # Invoke optional custom handler (outside lock)
        callback = self._handlers.get(irq.type)
        if callback:
            try:
                callback(irq)
            except Exception as exc:
                logger.error(
                    f"[IRQ] Handler for {irq.type.value} raised: {exc}"
                )

        EVENT_BUS.emit(
            SystemEvent.INTERRUPT_HANDLED,
            data={
                "interrupt":       irq.as_dict(),
                "handled_at_tick": tick or self._last_tick,
                "queue_remaining": remaining,
                "total_handled":   self._total_handled,
            },
            source="InterruptManager",
        )
        logger.info(
            f"[IRQ] HANDLED — {irq.type.value:12s} | prio={irq.priority} "
            f"pid={irq.source_pid} raised@{irq.tick} "
            f"handled@{tick or self._last_tick} "
            f"remaining={remaining}"
        )
        return irq

    def handle_all(self, tick: int = 0) -> List[Interrupt]:
        """
        Drain the entire interrupt queue in priority order.
        Returns the list of handled interrupts (highest priority first).
        """
        handled = []
        while True:
            irq = self.handle(tick=tick)
            if irq is None:
                break
            handled.append(irq)
        return handled

    def set_handler(
        self,
        itype:    InterruptType,
        callback: Callable[[Interrupt], None],
    ) -> None:
        """
        Register a custom Python callable for a specific interrupt type.
        The callback receives the Interrupt object and is called
        synchronously inside handle() before the event is emitted.
        """
        self._handlers[itype] = callback
        logger.debug(f"[IRQ] Custom handler registered for {itype.value}")

    def clear_handler(self, itype: InterruptType) -> None:
        """Remove the custom handler for an interrupt type."""
        self._handlers.pop(itype, None)

    def pending_count(self) -> int:
        """Number of interrupts currently in the queue."""
        with self._lock:
            return len(self._queue)

    @property
    def timer_interval(self) -> int:
        return self._timer_interval

    @timer_interval.setter
    def timer_interval(self, value: int) -> None:
        if value <= 0:
            raise ValueError(f"timer_interval must be > 0, got {value}")
        self._timer_interval = value
        logger.info(f"[IRQ] Timer interval updated → {value} ticks")

    @property
    def stats(self) -> dict:
        with self._lock:
            snapshot = [irq.as_dict() for irq in sorted(self._queue)]
        return {
            "total_raised":   self._total_raised,
            "total_handled":  self._total_handled,
            "pending":        len(snapshot),
            "timer_interval": self._timer_interval,
            "last_tick":      self._last_tick,
            "subscribed":     self._subscribed,
            "queue":          snapshot,
        }

    # ── EventBus handlers ─────────────────────────────────────────

    def _on_clock_tick(self, payload: EventPayload) -> None:
        """
        Called on every CLOCK_TICK.

        1. Fires a TIMER interrupt every `timer_interval` ticks.
        2. Calls handle() once to service the top pending interrupt.
           (One interrupt per tick — mirrors real hardware ISR pacing.)
        """
        tick = payload.data.get("tick", 0)
        self._last_tick = tick

        # Fire TIMER interrupt at the configured interval
        if tick > 0 and tick % self._timer_interval == 0:
            self.raise_interrupt(
                InterruptType.TIMER,
                source_pid=None,
                tick=tick,
            )

        # Service one pending interrupt per tick
        self.handle(tick=tick)

    def _on_memory_full(self, payload: EventPayload) -> None:
        """
        Called when MEMORY_FULL is emitted by the MemoryManager.
        Raises a MEMORY_FULL interrupt with the requesting PID.
        """
        tick = payload.data.get("tick", self._last_tick)
        pid  = payload.data.get("pid")
        self.raise_interrupt(
            InterruptType.MEMORY_FULL,
            source_pid=pid,
            tick=tick,
        )


# ── Central Singleton ─────────────────────────────────────────────
INTERRUPT_MANAGER = InterruptManager(timer_interval=_TIMER_INTERVAL)
