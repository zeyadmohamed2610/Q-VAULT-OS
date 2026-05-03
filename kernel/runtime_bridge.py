from __future__ import annotations

import logging
import threading
from typing import Optional

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent

logger = logging.getLogger(__name__)


class RuntimeBridge:
    """
    Coherence bridge between ProcessManager, Scheduler, and MulticoreEngine.

    Ensures that process lifecycle events propagate correctly across
    all kernel subsystems without direct coupling between them.
    """

    def __init__(self):
        self._lock       = threading.RLock()
        self._subscribed = False
        self._spawned_count    = 0
        self._terminated_count = 0
        self._cleaned_count    = 0

    def start(self) -> None:
        """Subscribe to process lifecycle events."""
        if self._subscribed:
            return
        EVENT_BUS.subscribe(SystemEvent.PROC_SPAWNED,   self._on_spawned)
        EVENT_BUS.subscribe(SystemEvent.PROC_STOPPED,   self._on_process_ended)
        EVENT_BUS.subscribe(SystemEvent.PROC_COMPLETED, self._on_process_ended)
        self._subscribed = True
        logger.info("[BRIDGE] Runtime bridge started.")

    def stop(self) -> None:
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.PROC_SPAWNED,   self._on_spawned)
        EVENT_BUS.unsubscribe(SystemEvent.PROC_STOPPED,   self._on_process_ended)
        EVENT_BUS.unsubscribe(SystemEvent.PROC_COMPLETED, self._on_process_ended)
        self._subscribed = False
        logger.info("[BRIDGE] Runtime bridge stopped.")

    # ── Event handlers ────────────────────────────────────────────

    def _on_spawned(self, payload: EventPayload) -> None:
        """
        Track process spawns for observability.

        NOTE: Enqueuing into the Scheduler is handled exclusively by
        Scheduler._on_process_spawned (which is also subscribed to
        PROC_SPAWNED). The bridge does NOT duplicate that logic here
        to avoid race conditions between subscribers.

        The bridge only acts as a cleanup layer (PROC_STOPPED/COMPLETED).
        """
        with self._lock:
            self._spawned_count += 1

        pid   = payload.data.get("pid")
        burst = payload.data.get("process", {}).get("burst_time", 0)
        logger.debug(f"[BRIDGE] PROC_SPAWNED pid={pid} burst={burst} (tracking only)")

    def _on_process_ended(self, payload: EventPayload) -> None:
        """
        Clean up Scheduler and MulticoreEngine when a process is stopped
        or completed (e.g. killed externally, shell command finished).

        The Scheduler handles its own terminations (remaining_time→0).
        This covers external kills: PM.kill(), app crashes, user kills.
        """
        pid = payload.data.get("pid")
        if not pid:
            return

        with self._lock:
            self._cleaned_count += 1

        # Remove from scheduler if still present
        try:
            from kernel.scheduler import SCHEDULER
            removed = SCHEDULER.remove_process(pid)
            if removed:
                logger.debug(f"[BRIDGE] Removed PID {pid} from scheduler (external kill)")
        except Exception as exc:
            logger.debug(f"[BRIDGE] Scheduler remove failed for pid={pid}: {exc}")

        # Release core from multicore engine
        try:
            from kernel.multicore_engine import MULTICORE_ENGINE
            MULTICORE_ENGINE.release(pid)
        except Exception as exc:
            logger.debug(f"[BRIDGE] MCE release failed for pid={pid}: {exc}")

    # ── Fallback helpers ──────────────────────────────────────────

    def _late_enqueue(self, pid: int) -> None:
        """Last-resort enqueue for processes that missed the PROC_SPAWNED window."""
        try:
            from kernel.process_manager import PM
        except ImportError:
            try:
                from kernel.process_manager import PM
            except ImportError:
                return

        proc = PM.get(pid)
        if proc is None or proc.burst_time <= 0:
            return

        try:
            from kernel.scheduler import SCHEDULER
            SCHEDULER.add_process(proc)
            logger.info(f"[BRIDGE] Late-enqueued PID {pid} ({proc.name})")
        except Exception as exc:
            logger.error(f"[BRIDGE] Late enqueue failed for pid={pid}: {exc}")

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "subscribed":       self._subscribed,
                "spawned_seen":     self._spawned_count,
                "terminated_seen":  self._terminated_count,
                "cleaned":          self._cleaned_count,
            }


# ── Central Singleton ─────────────────────────────────────────────
RUNTIME_BRIDGE = RuntimeBridge()
