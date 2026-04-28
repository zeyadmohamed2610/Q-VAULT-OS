#!/usr/bin/env python3
"""
tools/long_runtime_simulator.py — Q-Vault OS
Long Runtime Stability Testing — Production Simulation Phase
"""

import sys
import os
import gc
import time
import random
import traceback
import threading
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List

sys.path.append(os.getcwd())

# ── Headless Qt ──────────────────────────────────────────────────
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

# ── Metrics ──────────────────────────────────────────────────────
try:
    import psutil
    PROCESS = psutil.Process(os.getpid())
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ────────────────────────────────────────────────────────────────

@dataclass
class CycleMetrics:
    cycle: int
    elapsed_s: float
    mem_mb: float
    widget_count: int
    timer_events: int
    events_emitted: int
    errors: int
    gc_collected: int

@dataclass
class SimulationReport:
    cycles_run: int = 0
    total_time_s: float = 0.0
    peak_mem_mb: float = 0.0
    start_mem_mb: float = 0.0
    end_mem_mb: float = 0.0
    mem_growth_mb: float = 0.0
    peak_widget_count: int = 0
    total_events: int = 0
    total_errors: int = 0
    total_gc_collected: int = 0
    zombie_widgets_detected: int = 0
    stale_refs_detected: int = 0
    timer_leak_detected: bool = False
    cycle_history: List[CycleMetrics] = field(default_factory=list)
    verdict: str = "UNKNOWN"


class LongRuntimeSimulator(QObject):
    """
    Simulates extended OS sessions with realistic user activity.
    Tests for memory leaks, widget accumulation, signal duplication, 
    timer buildup, stale references, and zombie widgets.
    """

    finished = pyqtSignal(object)

    def __init__(self, app, cycles=20, cycle_duration_ms=500):
        super().__init__()
        self.app = app
        self.cycles = cycles
        self.cycle_duration_ms = cycle_duration_ms
        self.current_cycle = 0
        self.report = SimulationReport()
        
        self._event_count = 0
        self._error_count = 0
        self._timer_event_count = 0
        self._weak_refs: List[weakref.ref] = []
        self._spawned_windows = []
        self._sim_start = time.time()

        app.installEventFilter(self)

        # Hook EventBus
        try:
            from core.event_bus import EVENT_BUS
            EVENT_BUS.event_emitted.connect(self._on_event)
            self._bus = EVENT_BUS
        except Exception:
            self._bus = None

        # Boot OS
        try:
            from main import QVaultOS
            self._os = QVaultOS()
            self._os.show()
        except Exception as e:
            print(f"[SIMULATOR] OS boot failed: {e}")
            self._os = None

        if HAS_PSUTIL:
            self.report.start_mem_mb = PROCESS.memory_info().rss / (1024 * 1024)

        # Kick off cycle timer
        self._cycle_timer = QTimer()
        self._cycle_timer.timeout.connect(self._run_cycle)
        self._cycle_timer.start(self.cycle_duration_ms)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.Timer:
            self._timer_event_count += 1
        return False

    def _on_event(self, payload):
        self._event_count += 1

    # ── Simulation Actions ────────────────────────────────────────

    def _sim_open_window(self):
        """Open a simulated app window."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": "Terminal"}, source="simulator")
            
            # Also try direct WindowManager spawn
            from system.window_manager import get_window_manager
            from components.os_window import OSWindow
            
            class FakeApp(QObject):
                pass

            fake = FakeApp()
            win = OSWindow("Sim Window", fake, None)
            self._weak_refs.append(weakref.ref(win))
            self._spawned_windows.append(win)
            win.show()
            return win
        except Exception as e:
            self._error_count += 1
            return None

    def _sim_close_window(self):
        """Close one open window."""
        try:
            if self._spawned_windows:
                win = self._spawned_windows.pop(0)
                win.close()
                win.deleteLater()
        except Exception:
            self._error_count += 1

    def _sim_trigger_eventbus(self):
        """Fire a burst of events to stress the event backbone."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            for _ in range(5):
                EVENT_BUS.emit(SystemEvent.DEBUG_METRICS_UPDATED, {"source": "simulator"}, source="simulator")
        except Exception:
            self._error_count += 1

    def _sim_idle_wake(self):
        """Simulate an idle → wake transition."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(SystemEvent.USER_IDLE, {}, source="simulator")
            self.app.processEvents()
            time.sleep(0.01)
            EVENT_BUS.emit(SystemEvent.LOGIN_SUCCESS, {"username": "sim_user"}, source="simulator")
        except Exception:
            self._error_count += 1

    def _sim_gc_collect(self):
        return gc.collect()

    def _detect_zombie_widgets(self):
        """Count dead weak refs = zombie widgets."""
        dead = sum(1 for ref in self._weak_refs if ref() is None)
        self._weak_refs = [r for r in self._weak_refs if r() is not None]
        return dead

    def _detect_stale_refs(self):
        """Detect windows that are closed but still referenced."""
        stale = 0
        surviving = []
        for win in self._spawned_windows:
            try:
                if not win.isVisible() and not win.isHidden():
                    stale += 1
                else:
                    surviving.append(win)
            except RuntimeError:
                stale += 1
        self._spawned_windows = surviving
        return stale

    # ── Main Cycle ────────────────────────────────────────────────

    def _run_cycle(self):
        self.current_cycle += 1
        cycle_start = time.time()

        actions = [
            self._sim_open_window,
            self._sim_open_window,
            self._sim_trigger_eventbus,
            self._sim_idle_wake,
            self._sim_close_window,
            self._sim_close_window,
        ]
        random.shuffle(actions)
        for action in actions:
            action()

        self.app.processEvents()

        gc_count = self._sim_gc_collect()
        zombie_count = self._detect_zombie_widgets()
        stale_count = self._detect_stale_refs()

        mem_mb = PROCESS.memory_info().rss / (1024 * 1024) if HAS_PSUTIL else 0.0
        widget_count = len(self.app.allWidgets())

        self.report.peak_mem_mb = max(self.report.peak_mem_mb, mem_mb)
        self.report.peak_widget_count = max(self.report.peak_widget_count, widget_count)
        self.report.total_events += self._event_count
        self.report.total_errors += self._error_count
        self.report.total_gc_collected += gc_count
        self.report.zombie_widgets_detected += zombie_count
        self.report.stale_refs_detected += stale_count

        cm = CycleMetrics(
            cycle=self.current_cycle,
            elapsed_s=time.time() - cycle_start,
            mem_mb=mem_mb,
            widget_count=widget_count,
            timer_events=self._timer_event_count,
            events_emitted=self._event_count,
            errors=self._error_count,
            gc_collected=gc_count,
        )
        self.report.cycle_history.append(cm)

        # Reset per-cycle counters
        self._event_count = 0
        self._error_count = 0
        self._timer_event_count = 0

        print(f"  [Cycle {self.current_cycle:02d}/{self.cycles}] "
              f"Mem={mem_mb:.1f}MB | Widgets={widget_count} | "
              f"Zombies={zombie_count} | GC={gc_count}")

        if self.current_cycle >= self.cycles:
            self._finalize()

    def _finalize(self):
        self._cycle_timer.stop()

        total_time = time.time() - self._sim_start
        self.report.cycles_run = self.current_cycle
        self.report.total_time_s = total_time

        if HAS_PSUTIL:
            self.report.end_mem_mb = PROCESS.memory_info().rss / (1024 * 1024)
            self.report.mem_growth_mb = self.report.end_mem_mb - self.report.start_mem_mb

        # Timer leak detection: timers per second > 2000/s is suspicious
        avg_timers_per_cycle = (
            sum(c.timer_events for c in self.report.cycle_history) / max(self.report.cycles_run, 1)
        )
        if avg_timers_per_cycle > 1000:
            self.report.timer_leak_detected = True

        # Verdict
        issues = []
        if self.report.mem_growth_mb > 50:
            issues.append("MEMORY_LEAK")
        if self.report.zombie_widgets_detected > 5:
            issues.append("ZOMBIE_WIDGETS")
        if self.report.timer_leak_detected:
            issues.append("TIMER_LEAK")
        if self.report.total_errors > 10:
            issues.append("HIGH_ERROR_RATE")
        if self.report.stale_refs_detected > 5:
            issues.append("STALE_REFERENCES")

        self.report.verdict = "✅ STABLE" if not issues else f"🔴 UNSTABLE: {', '.join(issues)}"

        self.finished.emit(self.report)


def generate_report(report: SimulationReport) -> str:
    lines = [
        "# 🏃 Long Runtime Simulation Report",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 📊 Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Cycles Run | {report.cycles_run} |",
        f"| Total Duration | {report.total_time_s:.1f}s |",
        f"| Start Memory | {report.start_mem_mb:.1f} MB |",
        f"| End Memory | {report.end_mem_mb:.1f} MB |",
        f"| **Memory Growth** | **{report.mem_growth_mb:+.1f} MB** |",
        f"| Peak Memory | {report.peak_mem_mb:.1f} MB |",
        f"| Peak Widget Count | {report.peak_widget_count} |",
        f"| Total Events Fired | {report.total_events} |",
        f"| Simulation Errors | {report.total_errors} |",
        f"| GC Collections | {report.total_gc_collected} |",
        f"| Zombie Widgets | {report.zombie_widgets_detected} |",
        f"| Stale References | {report.stale_refs_detected} |",
        f"| Timer Leak | {'🔴 YES' if report.timer_leak_detected else '✅ NO'} |",
        "",
        "## 📈 Cycle-by-Cycle Memory Trend",
        "| Cycle | Mem (MB) | Widgets | Events | Errors |",
        "|-------|----------|---------|--------|--------|",
    ]

    for c in report.cycle_history:
        lines.append(f"| {c.cycle:02d} | {c.mem_mb:.1f} | {c.widget_count} | {c.events_emitted} | {c.errors} |")

    lines.extend([
        "",
        "## 🎯 Final Verdict",
        f"**{report.verdict}**",
    ])

    return "\n".join(lines)


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — Long Runtime Simulator             ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  Cycles: 20 | Cycle duration: 500ms")
    print()

    app = QApplication(sys.argv)
    sim = LongRuntimeSimulator(app, cycles=20, cycle_duration_ms=500)

    result_holder = {}

    def on_finished(report):
        result_holder["report"] = report
        app.quit()

    sim.finished.connect(on_finished)
    app.exec_()

    report = result_holder.get("report")
    if report:
        md = generate_report(report)
        os.makedirs("reports", exist_ok=True)
        with open("reports/long_runtime_report.md", "w", encoding="utf-8") as f:
            f.write(md)
        print()
        print(f"  Verdict:  {report.verdict}")
        print(f"  Mem growth: {report.mem_growth_mb:+.1f} MB")
        print(f"  Zombies:    {report.zombie_widgets_detected}")
        print(f"  Stale refs: {report.stale_refs_detected}")
        print(f"  Report: reports/long_runtime_report.md")


if __name__ == "__main__":
    main()
