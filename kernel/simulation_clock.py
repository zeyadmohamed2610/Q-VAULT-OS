import logging
import threading
import time
from typing import Optional

from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)


# ── Default Configuration ─────────────────────────────────────────

_DEFAULT_TICK_MS: int = 100   # 100 ms per tick → 10 Hz


# ── SimulationClock ───────────────────────────────────────────────

class SimulationClock:
    """
    Kernel-level simulation clock that drives the OS tick cycle.

    Usage:
        from kernel.simulation_clock import SIMULATION_CLOCK

        SIMULATION_CLOCK.start()            # Begin ticking
        SIMULATION_CLOCK.pause()            # Suspend ticks
        SIMULATION_CLOCK.resume()           # Continue ticking
        SIMULATION_CLOCK.reset()            # Stop + zero tick counter
        SIMULATION_CLOCK.tick_interval_ms = 50  # Change speed live

    Each tick emits SystemEvent.CLOCK_TICK with:
        {
            "tick":     int    — total ticks since last reset,
            "elapsed":  float  — wall-clock seconds since start/resume,
            "interval": int    — current tick interval in ms,
        }
    """

    def __init__(self, tick_interval_ms: int = _DEFAULT_TICK_MS):
        self._interval_ms: int = tick_interval_ms
        self._tick_count: int = 0

        self._running: bool = False
        self._paused: bool = False

        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._pause_event: threading.Event = threading.Event()   # Set = NOT paused
        self._pause_event.set()

        self._lock: threading.Lock = threading.Lock()
        self._start_time: Optional[float] = None

        logger.info(f"[SIMULATION_CLOCK] Initialized — interval: {self._interval_ms}ms")

    # ── Public Properties ─────────────────────────────────────────

    @property
    def tick_interval_ms(self) -> int:
        """Current tick interval in milliseconds."""
        return self._interval_ms

    @tick_interval_ms.setter
    def tick_interval_ms(self, value: int):
        """Hot-adjust the tick interval without restarting the clock."""
        if value <= 0:
            raise ValueError(f"tick_interval_ms must be > 0, got {value}")
        with self._lock:
            self._interval_ms = value
        logger.info(f"[SIMULATION_CLOCK] Tick interval updated → {value}ms")

    @property
    def tick_count(self) -> int:
        """Total ticks dispatched since the last reset."""
        return self._tick_count

    @property
    def is_running(self) -> bool:
        """True if the clock thread is active (not stopped)."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """True if the clock is paused (thread alive but suspended)."""
        return self._paused

    @property
    def elapsed_seconds(self) -> float:
        """Wall-clock seconds elapsed since start (pauses do NOT count)."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    # ── Lifecycle API ─────────────────────────────────────────────

    def start(self):
        """
        Start the simulation clock.
        No-op if already running.
        """
        with self._lock:
            if self._running:
                logger.warning("[SIMULATION_CLOCK] start() called but clock is already running.")
                return

            self._running = True
            self._paused = False
            self._stop_event.clear()
            self._pause_event.set()   # Ensure not paused
            self._start_time = time.monotonic()

            self._thread = threading.Thread(
                target=self._tick_loop,
                name="SimulationClock",
                daemon=True,
            )
            self._thread.start()

        logger.info("[SIMULATION_CLOCK] Started.")

    def pause(self):
        """
        Pause tick emission.
        The clock thread stays alive but sleeps until resume().
        Emits SystemEvent.CLOCK_PAUSED.
        """
        with self._lock:
            if not self._running:
                logger.warning("[SIMULATION_CLOCK] pause() called but clock is not running.")
                return
            if self._paused:
                logger.debug("[SIMULATION_CLOCK] pause() called but already paused.")
                return

            self._paused = True
            self._pause_event.clear()   # Signal the loop to suspend

        EVENT_BUS.emit(
            SystemEvent.CLOCK_PAUSED,
            data={"tick": self._tick_count, "interval": self._interval_ms},
            source="SimulationClock",
        )
        logger.info(f"[SIMULATION_CLOCK] Paused at tick {self._tick_count}.")

    def resume(self):
        """
        Resume a paused clock.
        Emits SystemEvent.CLOCK_RESUMED.
        """
        with self._lock:
            if not self._running:
                logger.warning("[SIMULATION_CLOCK] resume() called but clock is not running.")
                return
            if not self._paused:
                logger.debug("[SIMULATION_CLOCK] resume() called but not paused.")
                return

            self._paused = False
            # Resync start_time so elapsed_seconds stays meaningful
            self._start_time = time.monotonic()
            self._pause_event.set()   # Unblock the loop

        EVENT_BUS.emit(
            SystemEvent.CLOCK_RESUMED,
            data={"tick": self._tick_count, "interval": self._interval_ms},
            source="SimulationClock",
        )
        logger.info(f"[SIMULATION_CLOCK] Resumed at tick {self._tick_count}.")

    def stop(self):
        """
        Stop the clock and join the thread.
        The tick count is preserved (use reset() to zero it).
        """
        with self._lock:
            if not self._running:
                logger.debug("[SIMULATION_CLOCK] stop() called but clock is not running.")
                return

            self._running = False
            self._stop_event.set()
            self._pause_event.set()   # Unblock if suspended, so thread can exit

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info(f"[SIMULATION_CLOCK] Stopped at tick {self._tick_count}.")

    def reset(self):
        """
        Stop the clock and zero the tick counter.
        Call start() afterward to run again.
        """
        self.stop()
        with self._lock:
            self._tick_count = 0
            self._start_time = None
        logger.info("[SIMULATION_CLOCK] Reset.")

    # ── Internal Tick Loop ────────────────────────────────────────

    def _tick_loop(self):
        """
        Worker thread: emit CLOCK_TICK every tick_interval_ms milliseconds.
        Respects pause/stop signals without busy-waiting.
        """
        logger.debug("[SIMULATION_CLOCK] Tick loop started.")

        while not self._stop_event.is_set():
            # Block here while paused (releases GIL; ~zero CPU)
            self._pause_event.wait()

            if self._stop_event.is_set():
                break

            # Read interval inside loop so hot-changes take effect immediately
            with self._lock:
                interval_s = self._interval_ms / 1000.0

            # Sleep for the tick interval (interruptible)
            interrupted = self._stop_event.wait(timeout=interval_s)
            if interrupted:
                break   # stop() was called mid-sleep

            # Check pause again — may have been paused during sleep
            if not self._pause_event.is_set():
                continue

            # Increment and emit
            with self._lock:
                self._tick_count += 1
                tick = self._tick_count
                interval = self._interval_ms

            elapsed = self.elapsed_seconds

            EVENT_BUS.emit(
                SystemEvent.CLOCK_TICK,
                data={
                    "tick":     tick,
                    "elapsed":  round(elapsed, 4),
                    "interval": interval,
                },
                source="SimulationClock",
            )

        logger.debug("[SIMULATION_CLOCK] Tick loop exited.")


# ── Central Singleton ─────────────────────────────────────────────
SIMULATION_CLOCK = SimulationClock(tick_interval_ms=_DEFAULT_TICK_MS)
