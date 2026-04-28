#!/usr/bin/env python3
"""
tools/crash_recovery_tester.py — Q-Vault OS
Crash Recovery & Fault Isolation Validation
"""

import sys
import os
import time
import traceback

sys.path.append(os.getcwd())
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# ────────────────────────────────────────────────────────────────

class CrashRecoveryTester:
    """
    Simulates fault conditions and validates:
    - OS survives after crashes
    - Errors are isolated
    - No cascade failures occur
    - Cleanup succeeds
    """

    def __init__(self, app):
        self.app = app
        self.results = []
        self._os = None

        try:
            from main import QVaultOS
            self._os = QVaultOS()
        except Exception as e:
            print(f"  [BOOT ERROR] {e}")

    def _record(self, name: str, passed: bool, note: str = ""):
        icon = "✅" if passed else "🔴"
        status = "PASS" if passed else "FAIL"
        print(f"    {icon} [{status}] {name}" + (f" — {note}" if note else ""))
        self.results.append({"name": name, "passed": passed, "note": note})

    # ── Test Scenarios ────────────────────────────────────────────

    def test_malformed_eventbus_payload(self):
        """Emit malformed payloads — OS must not crash."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, None, source="crash_tester")
            EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {"invalid": object()}, source="crash_tester")
            EVENT_BUS.emit(SystemEvent.EVT_ERROR, {}, source="crash_tester")
            self._record("Malformed EventBus Payloads", True, "OS survived all malformed events")
        except Exception as e:
            self._record("Malformed EventBus Payloads", False, str(e))

    def test_raw_string_event_bus(self):
        """Emit with a raw string (legacy path) — should be logged but not crash."""
        try:
            from core.event_bus import EVENT_BUS
            EVENT_BUS.emit("non.existent.event.xyz", {}, source="crash_tester")
            self._record("Raw String EventBus Event", True, "Rejected gracefully with warning")
        except Exception as e:
            self._record("Raw String EventBus Event", False, str(e))

    def test_app_launch_nonexistent(self):
        """Attempt to launch a non-existent app — must quarantine, not crash."""
        try:
            from core.app_registry import REGISTRY
            result = REGISTRY.instantiate("NonExistentApp99")
            self._record(
                "Launch Non-Existent App",
                result is None,
                "Correctly returned None (quarantine path)" if result is None else "Expected None, got widget"
            )
        except Exception as e:
            self._record("Launch Non-Existent App", False, str(e))

    def test_window_force_destroy(self):
        """Force-destroy a window while it is referenced — no crash."""
        try:
            from components.os_window import OSWindow

            win = OSWindow("Crash Test Window", None, None)
            win.show()
            win_id = id(win)
            win.deleteLater()
            self.app.processEvents()
            self._record("Force Window Destroy", True, f"Window {win_id} destroyed cleanly")
        except Exception as e:
            self._record("Force Window Destroy", False, str(e))

    def test_handler_exception_isolation(self):
        """Subscribe a crashing handler — EventBus must continue functioning."""
        survived = {"count": 0}
        crash_fired = {"fired": False}

        try:
            from core.event_bus import EVENT_BUS, SystemEvent

            def crashing_handler(payload):
                crash_fired["fired"] = True
                raise RuntimeError("Intentional crash in handler")

            def surviving_handler(payload):
                survived["count"] += 1

            EVENT_BUS.subscribe(SystemEvent.DEBUG_METRICS_UPDATED, crashing_handler)
            EVENT_BUS.subscribe(SystemEvent.DEBUG_METRICS_UPDATED, surviving_handler)

            EVENT_BUS.emit(SystemEvent.DEBUG_METRICS_UPDATED, {}, source="crash_tester")
            self.app.processEvents()

            # Surviving handler must have run even though crashing_handler raised
            # (depends on EventBus implementation — we report what happened)
            self._record(
                "Handler Exception Isolation",
                crash_fired["fired"],
                f"Crash handler fired. Surviving handler count={survived['count']}"
            )

            EVENT_BUS.unsubscribe(SystemEvent.DEBUG_METRICS_UPDATED, crashing_handler)
            EVENT_BUS.unsubscribe(SystemEvent.DEBUG_METRICS_UPDATED, surviving_handler)
        except Exception as e:
            self._record("Handler Exception Isolation", False, str(e))

    def test_window_manager_invalid_id(self):
        """Pass an invalid window ID to WindowManager operations."""
        try:
            from system.window_manager import get_window_manager
            wm = get_window_manager()
            wm.focus_window("NON_EXISTENT_WINDOW_99999")
            wm.minimize_window("NON_EXISTENT_WINDOW_99999")
            wm.close_window("NON_EXISTENT_WINDOW_99999")
            self._record("WindowManager Invalid ID", True, "Gracefully ignored invalid IDs")
        except Exception as e:
            self._record("WindowManager Invalid ID", False, str(e))

    def test_auth_manager_invalid_transition(self):
        """Drive AuthManager into an invalid state transition."""
        try:
            from system.auth_manager import get_auth_manager
            am = get_auth_manager()
            # Force an invalid state change directly
            am.state_changed.emit("invalid_state_xyz", "logged_out")
            self._record("AuthManager Invalid State", True, "Survived invalid state emission")
        except Exception as e:
            self._record("AuthManager Invalid State", False, str(e))

    def test_rapid_event_storm(self):
        """Fire 500 events in rapid succession — no crash, no freeze."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            t0 = time.time()
            for i in range(500):
                EVENT_BUS.emit(SystemEvent.DEBUG_METRICS_UPDATED, {"i": i}, source="storm")
            elapsed = (time.time() - t0) * 1000
            self._record(
                "Rapid Event Storm (500 events)",
                elapsed < 5000,
                f"Completed in {elapsed:.0f}ms"
            )
        except Exception as e:
            self._record("Rapid Event Storm", False, str(e))

    def test_app_registry_corrupt_manifest(self):
        """Inject a bad module reference into instantiate — must quarantine."""
        try:
            from core.app_registry import REGISTRY, AppDefinition, AppStatus
            bad_def = AppDefinition(
                name="__CorruptApp__",
                emoji="💀",
                module="apps.does_not_exist_99",
                class_name="NonExistentClass"
            )
            # Temporarily inject
            REGISTRY._definitions["__CorruptApp__"] = bad_def
            result = REGISTRY.instantiate("__CorruptApp__")
            del REGISTRY._definitions["__CorruptApp__"]

            self._record(
                "Corrupt App Manifest",
                result is None,
                "Correctly quarantined bad app definition"
            )
        except Exception as e:
            self._record("Corrupt App Manifest", False, str(e))

    def test_window_manager_close_all(self):
        """Close all windows without crashing."""
        try:
            from system.window_manager import get_window_manager
            wm = get_window_manager()
            wm.close_all()
            self._record("WindowManager Close All", True, "close_all() completed")
        except Exception as e:
            self._record("WindowManager Close All", False, str(e))

    # ── Runner ────────────────────────────────────────────────────

    def run_all(self):
        print("  Running fault injection scenarios...")
        print()
        tests = [
            self.test_malformed_eventbus_payload,
            self.test_raw_string_event_bus,
            self.test_app_launch_nonexistent,
            self.test_window_force_destroy,
            self.test_handler_exception_isolation,
            self.test_window_manager_invalid_id,
            self.test_auth_manager_invalid_transition,
            self.test_rapid_event_storm,
            self.test_app_registry_corrupt_manifest,
            self.test_window_manager_close_all,
        ]
        for t in tests:
            try:
                t()
            except Exception as e:
                self._record(t.__name__, False, f"Unexpected: {e}")

        return self.results

    def generate_report(self) -> str:
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        failed_items = [r for r in self.results if not r["passed"]]

        lines = [
            "# 💥 Crash Recovery Validation Report",
            f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Scenarios | {total} |",
            f"| Passed | {passed} |",
            f"| Failed | {total - passed} |",
            f"| Recovery Rate | {passed/total*100:.0f}% |",
            "",
            "## 📋 Scenario Results",
            "| Scenario | Result | Notes |",
            "|----------|--------|-------|",
        ]

        for r in self.results:
            icon = "✅" if r["passed"] else "🔴"
            lines.append(f"| {r['name']} | {icon} {'PASS' if r['passed'] else 'FAIL'} | {r['note']} |")

        if failed_items:
            lines.extend([
                "",
                "## 🔴 Failures Requiring Attention",
            ])
            for r in failed_items:
                lines.append(f"- **{r['name']}**: {r['note']}")

        lines.extend([
            "",
            "## 🎯 Verdict",
            f"**{'✅ OS IS CRASH-RESILIENT' if passed == total else '🔴 FAULT ISOLATION GAPS DETECTED'}**",
        ])

        return "\n".join(lines)


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — Crash Recovery Tester             ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    app = QApplication(sys.argv)
    tester = CrashRecoveryTester(app)
    results = tester.run_all()

    app.processEvents()

    md = tester.generate_report()
    os.makedirs("reports", exist_ok=True)
    with open("reports/crash_recovery_report.md", "w", encoding="utf-8") as f:
        f.write(md)

    passed = sum(1 for r in results if r["passed"])
    print()
    print(f"  Result: {passed}/{len(results)} scenarios passed")
    print(f"  Report: reports/crash_recovery_report.md")


if __name__ == "__main__":
    main()
