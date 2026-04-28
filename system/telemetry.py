"""
system/telemetry.py — Q-Vault OS
Production Observability & Telemetry Layer

Tracks:
- crashes and warnings
- runtime anomalies
- event storms
- startup timings
- memory pressure
- subsystem health

Thread-safe singleton. Does NOT import UI components.
"""

from __future__ import annotations

import json
import logging
import os
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Telemetry Severity ────────────────────────────────────────────

class TelemetrySeverity(Enum):
    DEBUG   = "debug"
    INFO    = "info"
    WARN    = "warn"
    ERROR   = "error"
    CRASH   = "crash"


# ── Telemetry Entry ───────────────────────────────────────────────

@dataclass
class TelemetryEntry:
    timestamp: float
    severity: str
    category: str
    source: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


# ── Subsystem Health State ────────────────────────────────────────

@dataclass
class SubsystemHealth:
    name: str
    status: str = "UNKNOWN"          # HEALTHY | DEGRADED | DOWN
    last_heartbeat: float = 0.0
    error_count: int = 0
    warn_count: int = 0
    last_error: str = ""


# ── Telemetry System ──────────────────────────────────────────────

class TelemetrySystem:
    """
    Process-wide telemetry collector. Thread-safe.
    
    Usage:
        from system.telemetry import TELEMETRY
        TELEMETRY.record_crash("MyModule", "NullRef on foo")
        TELEMETRY.heartbeat("EventBus")
        TELEMETRY.record_event_storm("EventBus", count=1200)
    """

    _MAX_BUFFER = 2000  # Rolling in-memory buffer

    def __init__(self):
        self._lock = threading.Lock()
        self._buffer: Deque[TelemetryEntry] = deque(maxlen=self._MAX_BUFFER)
        self._subsystems: Dict[str, SubsystemHealth] = {}
        self._event_storm_threshold = 500  # events/sec
        self._event_storm_window: Deque[float] = deque(maxlen=1000)
        self._startup_time: Optional[float] = None
        self._boot_complete_time: Optional[float] = None
        self._counters: Dict[str, int] = defaultdict(int)

    # ── Lifecycle ─────────────────────────────────────────────────

    def record_startup(self, source: str = "main"):
        """Call this at the very first line of main()."""
        self._startup_time = time.time()
        self._log(TelemetrySeverity.INFO, "lifecycle", source, "OS startup initiated")
        logger.info("[TELEMETRY] Startup recorded")

    def record_boot_complete(self, source: str = "main"):
        """Call when the boot screen finishes."""
        self._boot_complete_time = time.time()
        elapsed = (
            (self._boot_complete_time - self._startup_time) * 1000
            if self._startup_time else 0
        )
        self._log(TelemetrySeverity.INFO, "lifecycle", source,
                  f"Boot complete in {elapsed:.0f}ms", {"boot_ms": elapsed})
        logger.info(f"[TELEMETRY] Boot complete in {elapsed:.0f}ms")

    # ── Crash & Warning Tracking ──────────────────────────────────

    def record_crash(self, source: str, message: str, data: Dict = None):
        self._counters["crashes"] += 1
        self._log(TelemetrySeverity.CRASH, "crash", source, message, data or {})
        self._update_subsystem(source, status="DOWN", error=message)
        logger.error(f"[TELEMETRY][CRASH] {source}: {message}")

    def record_error(self, source: str, message: str, data: Dict = None):
        self._counters["errors"] += 1
        self._log(TelemetrySeverity.ERROR, "error", source, message, data or {})
        self._update_subsystem(source, error=message)

    def record_warning(self, source: str, message: str, data: Dict = None):
        self._counters["warnings"] += 1
        self._log(TelemetrySeverity.WARN, "warning", source, message, data or {})
        self._update_subsystem(source, warn=message)

    def record_info(self, source: str, message: str, data: Dict = None):
        self._log(TelemetrySeverity.INFO, "info", source, message, data or {})

    # ── Event Storm Detection ─────────────────────────────────────

    def record_event_tick(self, source: str = "event_bus"):
        """Call once per event emission to detect storms."""
        now = time.time()
        with self._lock:
            self._event_storm_window.append(now)
            # Check last 1 second
            cutoff = now - 1.0
            recent = sum(1 for t in self._event_storm_window if t > cutoff)
            if recent > self._event_storm_threshold:
                self._counters["event_storms"] += 1
                self._log(TelemetrySeverity.WARN, "event_storm", source,
                          f"Event storm detected: {recent} events/sec",
                          {"rate": recent})

    def record_event_storm(self, source: str, count: int):
        """Explicitly record a detected event storm."""
        self._counters["event_storms"] += 1
        self._log(TelemetrySeverity.WARN, "event_storm", source,
                  f"Event storm: {count} events/sec", {"rate": count})

    # ── Memory Pressure ───────────────────────────────────────────

    def record_memory_pressure(self, mem_mb: float, source: str = "watchdog"):
        """Record a memory snapshot; auto-warn above thresholds."""
        severity = TelemetrySeverity.INFO
        if mem_mb > 500:
            severity = TelemetrySeverity.WARN
            self._counters["memory_warnings"] += 1
        if mem_mb > 1000:
            severity = TelemetrySeverity.ERROR
            self._counters["memory_critical"] += 1
        self._log(severity, "memory", source, f"Memory: {mem_mb:.1f} MB", {"mem_mb": mem_mb})

    # ── Subsystem Health ──────────────────────────────────────────

    def heartbeat(self, subsystem: str):
        """Mark a subsystem as healthy (alive)."""
        with self._lock:
            sh = self._subsystems.setdefault(subsystem, SubsystemHealth(name=subsystem))
            sh.last_heartbeat = time.time()
            sh.status = "HEALTHY"

    def mark_degraded(self, subsystem: str, reason: str):
        with self._lock:
            sh = self._subsystems.setdefault(subsystem, SubsystemHealth(name=subsystem))
            sh.status = "DEGRADED"
            sh.last_error = reason
            sh.error_count += 1

    def mark_down(self, subsystem: str, reason: str):
        with self._lock:
            sh = self._subsystems.setdefault(subsystem, SubsystemHealth(name=subsystem))
            sh.status = "DOWN"
            sh.last_error = reason
            sh.error_count += 1

    def check_stale_heartbeats(self, timeout_s: float = 30.0) -> List[str]:
        """Return subsystem names with stale heartbeats (potential hangs)."""
        now = time.time()
        stale = []
        with self._lock:
            for name, sh in self._subsystems.items():
                if sh.last_heartbeat > 0 and (now - sh.last_heartbeat) > timeout_s:
                    stale.append(name)
        return stale

    # ── Report Generation ─────────────────────────────────────────

    def generate_summary(self) -> str:
        """Generate the telemetry_summary.md report."""
        now = time.time()
        startup_ms = (
            (self._boot_complete_time - self._startup_time) * 1000
            if self._startup_time and self._boot_complete_time else "N/A"
        )

        lines = [
            "# 📡 Production Telemetry Summary",
            f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## ⚡ Startup Performance",
            f"- Boot time: `{startup_ms if isinstance(startup_ms, str) else f'{startup_ms:.0f} ms'}`",
            "",
            "## 📊 Event Counters",
            f"| Category | Count |",
            f"|----------|-------|",
        ]

        for k, v in sorted(self._counters.items()):
            lines.append(f"| {k} | {v} |")

        lines.extend([
            "",
            "## 🏥 Subsystem Health",
            "| Subsystem | Status | Errors | Last Error |",
            "|-----------|--------|--------|------------|",
        ])

        with self._lock:
            for name, sh in sorted(self._subsystems.items()):
                status_icon = {"HEALTHY": "✅", "DEGRADED": "🟡", "DOWN": "🔴", "UNKNOWN": "⚪"}.get(sh.status, "")
                lines.append(
                    f"| {name} | {status_icon} {sh.status} | {sh.error_count} | {sh.last_error[:60] or 'none'} |"
                )

        # Recent entries
        lines.extend([
            "",
            "## 📜 Recent Events (last 20)",
            "| Time | Sev | Source | Message |",
            "|------|-----|--------|---------|",
        ])

        recent = list(self._buffer)[-20:]
        for e in reversed(recent):
            ts = time.strftime("%H:%M:%S", time.localtime(e.timestamp))
            lines.append(f"| {ts} | {e.severity.upper()} | {e.source} | {e.message[:80]} |")

        stale = self.check_stale_heartbeats()
        if stale:
            lines.extend([
                "",
                "## ⚠️ Stale Subsystems (no heartbeat >30s)",
            ])
            for s in stale:
                lines.append(f"- `{s}`")

        crash_count = self._counters.get("crashes", 0)
        error_count = self._counters.get("errors", 0)
        storm_count = self._counters.get("event_storms", 0)

        if crash_count == 0 and error_count < 5 and storm_count == 0:
            verdict = "✅ NOMINAL — No critical anomalies detected."
        elif crash_count > 0:
            verdict = f"🔴 CRITICAL — {crash_count} crash(es) recorded."
        else:
            verdict = f"🟡 DEGRADED — {error_count} errors, {storm_count} storms."

        lines.extend([
            "",
            "## 🎯 Verdict",
            f"**{verdict}**",
        ])

        return "\n".join(lines)

    # ── Internal ──────────────────────────────────────────────────

    def _log(self, severity: TelemetrySeverity, category: str, source: str,
             message: str, data: Dict = None):
        entry = TelemetryEntry(
            timestamp=time.time(),
            severity=severity.value,
            category=category,
            source=source,
            message=message,
            data=data or {},
        )
        with self._lock:
            self._buffer.append(entry)

    def _update_subsystem(self, source: str, status: str = None,
                          error: str = None, warn: str = None):
        with self._lock:
            sh = self._subsystems.setdefault(source, SubsystemHealth(name=source))
            if status:
                sh.status = status
            if error:
                sh.error_count += 1
                sh.last_error = error
            if warn:
                sh.warn_count += 1

    def write_summary(self, path: str = "reports/telemetry_summary.md"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_summary())
        logger.info(f"[TELEMETRY] Summary written to {path}")


# ── Process-wide Singleton ────────────────────────────────────────

TELEMETRY = TelemetrySystem()


def get_telemetry() -> TelemetrySystem:
    return TELEMETRY


if __name__ == "__main__":
    # Self-test
    t = TelemetrySystem()
    t.record_startup("main")
    t.heartbeat("EventBus")
    t.heartbeat("AppController")
    t.mark_degraded("AppRegistry", "Quarantine triggered for TestApp")
    t.record_warning("EventBus", "High event rate observed")
    t.record_error("WindowManager", "Invalid window ID passed")
    t.record_boot_complete("main")
    t.record_memory_pressure(128.5)

    os.makedirs("reports", exist_ok=True)
    with open("reports/telemetry_summary.md", "w") as f:
        f.write(t.generate_summary())

    print("[TELEMETRY] Self-test complete. Report: reports/telemetry_summary.md")
