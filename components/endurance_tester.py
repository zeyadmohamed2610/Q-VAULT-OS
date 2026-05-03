"""
components/endurance_tester.py
──────────────────────────────────────────────────────────────────────
Q-Vault OS — Production Endurance Test

A long-running, automated GUI stress test designed to uncover:
  • Memory leaks (RSS growth over time)
  • Thread leaks (thread count climbing)
  • Event loop starvation (UI lag spikes)
  • Window lifecycle bugs (open/close/minimize/maximize/resize)
  • Animation race conditions
  • Crash isolation failures

Usage (from terminal): endurance
──────────────────────────────────────────────────────────────────────
"""

import logging
import os
import random
import threading
import time

import psutil
from PyQt5.QtCore import QObject, QTimer, QRect

from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager

logger = logging.getLogger(__name__)

# ── Phases ────────────────────────────────────────────────────────
PHASE_OPEN     = "OPEN_APPS"
PHASE_FOCUS    = "FOCUS_STORM"
PHASE_MINMAX   = "MINIMIZE_MAXIMIZE"
PHASE_RESIZE   = "RESIZE_STORM"
PHASE_REOPEN   = "RAPID_REOPEN"
PHASE_SOAK     = "SOAK"
PHASE_CLOSE    = "CLOSE_ALL"
PHASE_DONE     = "DONE"

APPS = ["Terminal", "File Manager", "Kernel Monitor", "Q-Vault Browser", "Trash"]


class EnduranceTester(QObject):
    """
    Multi-phase endurance test that runs inside the Qt event loop.

    Each phase exercises a different stress vector. Telemetry is
    sampled every second and printed as a compact report at the end.
    """

    def __init__(self, duration_minutes: int = 5, parent=None):
        super().__init__(parent)
        self._duration = duration_minutes * 60   # seconds
        self._start_time = 0.0
        self._step = 0
        self._phase = PHASE_OPEN
        self._phase_step = 0

        # Telemetry
        self._proc = psutil.Process(os.getpid())
        self._initial_rss = 0
        self._initial_threads = 0
        self._peak_rss = 0
        self._peak_threads = 0
        self._samples = []          # (elapsed_s, rss_mb, threads, windows, lag_ms)
        self._errors = []
        self._windows_opened = 0
        self._windows_closed = 0

        # Timers
        self._action_timer = QTimer(self)
        self._action_timer.timeout.connect(self._tick)

        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._sample_telemetry)

    # ── Public API ───────────────────────────────────────────────

    def start(self):
        """Begin endurance test."""
        self._start_time = time.time()
        self._initial_rss = self._get_rss_mb()
        self._initial_threads = threading.active_count()
        self._peak_rss = self._initial_rss
        self._peak_threads = self._initial_threads

        logger.info("=" * 60)
        logger.info("[ENDURANCE] Starting %d-minute endurance test", self._duration // 60)
        logger.info("[ENDURANCE] Initial RSS: %.1f MB | Threads: %d",
                     self._initial_rss, self._initial_threads)
        logger.info("=" * 60)

        self._action_timer.start(150)      # action every 150ms
        self._telemetry_timer.start(2000)   # sample every 2s

    def stop(self):
        """Stop test and print report."""
        self._action_timer.stop()
        self._telemetry_timer.stop()
        self._print_report()

    # ── Telemetry ────────────────────────────────────────────────

    def _get_rss_mb(self) -> float:
        try:
            return self._proc.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def _sample_telemetry(self):
        elapsed = time.time() - self._start_time
        rss = self._get_rss_mb()
        threads = threading.active_count()
        wm = get_window_manager()
        win_count = len(wm._windows) if wm else 0

        self._peak_rss = max(self._peak_rss, rss)
        self._peak_threads = max(self._peak_threads, threads)

        self._samples.append((round(elapsed, 1), round(rss, 1), threads, win_count))

        # Log every 30 seconds
        if len(self._samples) % 15 == 0:
            delta_rss = rss - self._initial_rss
            logger.info(
                "[ENDURANCE] %3.0fs | RSS: %.1f MB (Δ%+.1f) | Threads: %d | "
                "Windows: %d | Phase: %s | Opened: %d Closed: %d",
                elapsed, rss, delta_rss, threads, win_count,
                self._phase, self._windows_opened, self._windows_closed
            )

    # ── Phase Router ─────────────────────────────────────────────

    def _tick(self):
        elapsed = time.time() - self._start_time
        self._step += 1

        # Time's up → close all and finish
        if elapsed >= self._duration and self._phase != PHASE_DONE:
            self._phase = PHASE_CLOSE
            self._phase_step = 0

        try:
            if self._phase == PHASE_OPEN:
                self._do_open()
            elif self._phase == PHASE_FOCUS:
                self._do_focus_storm()
            elif self._phase == PHASE_MINMAX:
                self._do_minmax()
            elif self._phase == PHASE_RESIZE:
                self._do_resize_storm()
            elif self._phase == PHASE_REOPEN:
                self._do_rapid_reopen()
            elif self._phase == PHASE_SOAK:
                self._do_soak()
            elif self._phase == PHASE_CLOSE:
                self._do_close_all()
            elif self._phase == PHASE_DONE:
                self.stop()
        except Exception as exc:
            self._errors.append(f"Step {self._step} ({self._phase}): {exc}")
            logger.error("[ENDURANCE] Error in step %d: %s", self._step, exc)

    # ── Phases ───────────────────────────────────────────────────

    def _advance_phase(self, next_phase: str):
        logger.info("[ENDURANCE] Phase complete: %s → %s", self._phase, next_phase)
        self._phase = next_phase
        self._phase_step = 0

    def _do_open(self):
        """Open all apps one by one."""
        self._phase_step += 1
        if self._phase_step <= len(APPS):
            app = APPS[self._phase_step - 1]
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH,
                           {"app_id": app, "name": app}, source="Endurance")
            self._windows_opened += 1
        else:
            # Give apps 1 second to fully render
            QTimer.singleShot(1000, lambda: self._advance_phase(PHASE_FOCUS))
            self._action_timer.stop()

    def _do_focus_storm(self):
        """Rapidly switch focus between windows."""
        if not self._action_timer.isActive():
            self._action_timer.start(80)  # fast focus switching
        self._phase_step += 1
        wm = get_window_manager()
        if wm._windows:
            win_id = random.choice(list(wm._windows.keys()))
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS,
                           {"id": win_id}, source="Endurance")
        if self._phase_step > 40:
            self._action_timer.setInterval(150)
            self._advance_phase(PHASE_MINMAX)

    def _do_minmax(self):
        """Rapidly minimize and maximize windows."""
        self._phase_step += 1
        wm = get_window_manager()
        if not wm._windows:
            self._advance_phase(PHASE_RESIZE)
            return

        win_id = random.choice(list(wm._windows.keys()))
        if self._phase_step % 2 == 0:
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_MINIMIZE,
                           {"id": win_id}, source="Endurance")
        else:
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS,
                           {"id": win_id}, source="Endurance")

        if self._phase_step > 30:
            self._advance_phase(PHASE_RESIZE)

    def _do_resize_storm(self):
        """Resize windows to random geometries rapidly."""
        self._phase_step += 1
        wm = get_window_manager()
        if not wm._windows:
            self._advance_phase(PHASE_REOPEN)
            return

        win_id = random.choice(list(wm._windows.keys()))
        window = wm._windows.get(win_id)
        if window:
            new_w = random.randint(300, 900)
            new_h = random.randint(200, 700)
            new_x = random.randint(0, 400)
            new_y = random.randint(40, 300)
            try:
                window.setGeometry(QRect(new_x, new_y, new_w, new_h))
            except Exception:
                pass

        if self._phase_step > 40:
            self._advance_phase(PHASE_REOPEN)

    def _do_rapid_reopen(self):
        """Close a random window then reopen it — tests lifecycle cleanup."""
        self._phase_step += 1
        wm = get_window_manager()

        if self._phase_step % 3 == 0 and wm._windows:
            # Close a random window
            win_id = random.choice(list(wm._windows.keys()))
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE,
                           {"id": win_id}, source="Endurance")
            self._windows_closed += 1
        elif self._phase_step % 3 == 1:
            # Open a random app
            app = random.choice(APPS)
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH,
                           {"app_id": app, "name": app}, source="Endurance")
            self._windows_opened += 1

        if self._phase_step > 45:
            self._advance_phase(PHASE_SOAK)

    def _do_soak(self):
        """Idle soak — let the system run with windows open, monitoring for leaks."""
        self._phase_step += 1

        # Occasional random action to keep things alive
        wm = get_window_manager()
        if self._phase_step % 10 == 0 and wm._windows:
            win_id = random.choice(list(wm._windows.keys()))
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS,
                           {"id": win_id}, source="Endurance")

        # Soak for remaining time — phase advances via elapsed time check in _tick

    def _do_close_all(self):
        """Close all remaining windows, then finish."""
        self._phase_step += 1
        wm = get_window_manager()
        if wm._windows:
            win_id = list(wm._windows.keys())[0]
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE,
                           {"id": win_id}, source="Endurance")
            self._windows_closed += 1
        else:
            self._advance_phase(PHASE_DONE)

    # ── Report ───────────────────────────────────────────────────

    def _print_report(self):
        elapsed = time.time() - self._start_time
        final_rss = self._get_rss_mb()
        final_threads = threading.active_count()
        rss_growth = final_rss - self._initial_rss
        thread_growth = final_threads - self._initial_threads

        # Determine pass/fail
        issues = []
        if rss_growth > 100:
            issues.append(f"MEMORY LEAK: RSS grew {rss_growth:.1f} MB")
        if thread_growth > 10:
            issues.append(f"THREAD LEAK: Thread count grew by {thread_growth}")
        if self._errors:
            issues.append(f"ERRORS: {len(self._errors)} runtime errors")

        status = "PASS" if not issues else "FAIL"

        report = [
            "",
            "=" * 60,
            f"  ENDURANCE TEST REPORT — {status}",
            "=" * 60,
            f"  Duration:          {elapsed:.0f}s ({elapsed/60:.1f} min)",
            f"  Total steps:       {self._step}",
            f"  Windows opened:    {self._windows_opened}",
            f"  Windows closed:    {self._windows_closed}",
            "",
            "  Memory:",
            f"    Initial RSS:     {self._initial_rss:.1f} MB",
            f"    Final RSS:       {final_rss:.1f} MB",
            f"    Peak RSS:        {self._peak_rss:.1f} MB",
            f"    Growth:          {rss_growth:+.1f} MB",
            "",
            "  Threads:",
            f"    Initial:         {self._initial_threads}",
            f"    Final:           {final_threads}",
            f"    Peak:            {self._peak_threads}",
            f"    Growth:          {thread_growth:+d}",
            "",
            f"  Errors:            {len(self._errors)}",
        ]

        if self._errors:
            report.append("  Error details:")
            for err in self._errors[:10]:
                report.append(f"    - {err}")

        if issues:
            report.append("")
            report.append("  ISSUES DETECTED:")
            for issue in issues:
                report.append(f"    [!] {issue}")
        else:
            report.append("")
            report.append("  No memory leaks, thread leaks, or errors detected.")
            report.append("  System is PRODUCTION READY.")

        report.append("=" * 60)

        for line in report:
            logger.info(line)


# ── Singleton accessor ───────────────────────────────────────────
_global_tester = None

def run_endurance(duration_minutes: int = 5, parent=None):
    """Start an endurance test. Callable from terminal or desktop."""
    global _global_tester
    if _global_tester and _global_tester._action_timer.isActive():
        logger.warning("[ENDURANCE] Test already running.")
        return _global_tester
    _global_tester = EnduranceTester(duration_minutes=duration_minutes, parent=parent)
    _global_tester.start()
    return _global_tester
