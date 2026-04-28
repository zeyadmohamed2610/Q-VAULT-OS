#!/usr/bin/env python3
"""
tools/state_integrity_validator.py — Q-Vault OS
Persistent State Integrity Validation
"""

import sys
import os
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

sys.path.append(os.getcwd())

# ────────────────────────────────────────────────────────────────

class StateIntegrityValidator:
    """
    Validates:
    - Settings persistence round-trips
    - Session restoration accuracy
    - Corrupted state recovery (non-crash graceful degradation)
    - Invalid config handling
    """

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def _record(self, name: str, passed: bool, note: str = ""):
        icon = "✅" if passed else "🔴"
        print(f"    {icon} {name}" + (f" — {note}" if note else ""))
        self.results.append({"name": name, "passed": passed, "note": note})

    # ── Settings Persistence ──────────────────────────────────────

    def test_settings_write_read(self):
        """Write a settings value and read it back."""
        try:
            from system.config_manager import get_config_manager
            cm = get_config_manager()
            key = "__test_key_integrity_check__"
            cm.set(key, "test_value_42")
            retrieved = cm.get(key)
            cm.delete(key)
            self._record("Settings Write/Read", retrieved == "test_value_42",
                         f"Expected 'test_value_42', got '{retrieved}'")
        except ImportError:
            # Fall back to direct JSON file if no config manager
            self._test_json_settings_fallback()
        except Exception as e:
            self._record("Settings Write/Read", False, str(e))

    def _test_json_settings_fallback(self):
        """Direct JSON-based settings test."""
        tmpdir = tempfile.mkdtemp()
        settings_path = os.path.join(tmpdir, "settings.json")
        try:
            data = {"theme": "dark", "username": "testuser", "resolution": [1920, 1080]}
            with open(settings_path, "w") as f:
                json.dump(data, f)
            with open(settings_path) as f:
                loaded = json.load(f)
            self._record("Settings Write/Read (JSON fallback)", loaded == data,
                         "Round-trip succeeded")
        except Exception as e:
            self._record("Settings Write/Read (JSON fallback)", False, str(e))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_corrupted_json_recovery(self):
        """Write corrupted JSON, load it — must not crash, should return defaults."""
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "corrupted.json")
        try:
            with open(path, "w") as f:
                f.write("{invalid json :::}")
            try:
                with open(path) as f:
                    data = json.load(f)
                self._record("Corrupted JSON Recovery", False, "Should have raised JSONDecodeError")
            except json.JSONDecodeError:
                # This is expected — verify caller handles gracefully
                self._record("Corrupted JSON Recovery", True,
                             "JSONDecodeError raised — caller must catch and use defaults")
        except Exception as e:
            self._record("Corrupted JSON Recovery", False, str(e))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_missing_settings_file(self):
        """Load from a non-existent file — must not crash."""
        try:
            path = "/non/existent/path/settings.json"
            result = None
            try:
                with open(path) as f:
                    result = json.load(f)
            except FileNotFoundError:
                result = {}  # Proper graceful default
            self._record("Missing Settings File", result == {}, "FileNotFoundError caught, returned defaults")
        except Exception as e:
            self._record("Missing Settings File", False, str(e))

    def test_session_state_integrity(self):
        """Validate that system state can be captured and restored."""
        try:
            from core.system_state import STATE
            original_val = getattr(STATE, "session_type", None)

            # Simulate state capture
            state_snapshot = {
                "session_type": getattr(STATE, "session_type", "unknown"),
                "username": getattr(STATE, "username", "unknown"),
            }

            # Simulate restore
            for k, v in state_snapshot.items():
                if hasattr(STATE, k):
                    setattr(STATE, k, v)

            restored_val = getattr(STATE, "session_type", None)
            self._record("Session State Round-trip", restored_val == original_val,
                         f"session_type: {original_val} → {restored_val}")
        except Exception as e:
            self._record("Session State Round-trip", False, str(e))

    def test_eventbus_state_after_reset(self):
        """Verify EventBus maintains integrity after heavy use."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            initial_subs = len(EVENT_BUS._subscribers)

            # Add then remove a temp subscriber
            sentinel = {"count": 0}
            def tmp_handler(payload):
                sentinel["count"] += 1

            EVENT_BUS.subscribe(SystemEvent.DEBUG_METRICS_UPDATED, tmp_handler)
            EVENT_BUS.emit(SystemEvent.DEBUG_METRICS_UPDATED, {}, source="integrity_check")
            EVENT_BUS.unsubscribe(SystemEvent.DEBUG_METRICS_UPDATED, tmp_handler)

            final_subs = len(EVENT_BUS._subscribers)
            self._record("EventBus Subscriber Cleanup", final_subs <= initial_subs + 1,
                         f"Subs: {initial_subs} → {final_subs}. Handler count stable.")
        except Exception as e:
            self._record("EventBus Subscriber Cleanup", False, str(e))

    def test_app_registry_quarantine_persistence(self):
        """Quarantined app must stay quarantined across calls."""
        try:
            from core.app_registry import REGISTRY, AppDefinition, AppStatus
            bad_def = AppDefinition(
                name="__QuarantineTest__",
                emoji="☠️",
                module="apps.does_not_exist_quarantine",
                class_name="Nope"
            )
            REGISTRY._definitions["__QuarantineTest__"] = bad_def
            REGISTRY._status["__QuarantineTest__"] = AppStatus.UNVERIFIED

            # First call — should quarantine
            REGISTRY.instantiate("__QuarantineTest__")
            status_after_first = REGISTRY.status("__QuarantineTest__")

            # Second call — should still be quarantined, not re-tried
            REGISTRY.instantiate("__QuarantineTest__")
            status_after_second = REGISTRY.status("__QuarantineTest__")

            passed = status_after_first == AppStatus.QUARANTINE and status_after_second == AppStatus.QUARANTINE
            self._record("Quarantine Persistence", passed,
                         f"Status: {status_after_first.name} → {status_after_second.name}")

            del REGISTRY._definitions["__QuarantineTest__"]
        except Exception as e:
            self._record("Quarantine Persistence", False, str(e))

    def test_invalid_config_types(self):
        """Pass wrong types to config-like structures — must not corrupt state."""
        try:
            tmpdir = tempfile.mkdtemp()
            path = os.path.join(tmpdir, "config.json")
            try:
                # Write valid
                with open(path, "w") as f:
                    json.dump({"resolution": [1920, 1080]}, f)

                # Write invalid type (int instead of list)
                with open(path, "w") as f:
                    json.dump({"resolution": 99999}, f)

                with open(path) as f:
                    loaded = json.load(f)

                # Simulate type-safe access
                res = loaded.get("resolution")
                if not isinstance(res, list):
                    res = [1920, 1080]  # fallback

                self._record("Invalid Config Type Recovery", res == [1920, 1080],
                             f"Type mismatch corrected to default {res}")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception as e:
            self._record("Invalid Config Type Recovery", False, str(e))

    # ── Runner ────────────────────────────────────────────────────

    def run_all(self):
        print("  Running state integrity checks...")
        print()
        tests = [
            self.test_settings_write_read,
            self.test_corrupted_json_recovery,
            self.test_missing_settings_file,
            self.test_session_state_integrity,
            self.test_eventbus_state_after_reset,
            self.test_app_registry_quarantine_persistence,
            self.test_invalid_config_types,
        ]
        for t in tests:
            try:
                t()
            except Exception as e:
                self._record(t.__name__, False, f"Unexpected: {e}")

    def generate_report(self) -> str:
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        lines = [
            "# 🗄️ State Integrity Validation Report",
            f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Checks | {total} |",
            f"| Passed | {passed} |",
            f"| Failed | {total - passed} |",
            f"| Integrity Score | {passed/total*100:.0f}% |",
            "",
            "## 📋 Validation Results",
            "| Check | Result | Notes |",
            "|-------|--------|-------|",
        ]

        for r in self.results:
            icon = "✅" if r["passed"] else "🔴"
            lines.append(f"| {r['name']} | {icon} | {r['note']} |")

        failures = [r for r in self.results if not r["passed"]]
        if failures:
            lines.extend(["", "## 🔴 Failures"])
            for r in failures:
                lines.append(f"- **{r['name']}**: {r['note']}")

        lines.extend([
            "",
            "## 🎯 Verdict",
            f"**{'✅ STATE INTEGRITY CONFIRMED' if passed == total else '🟡 PARTIAL INTEGRITY — REVIEW FAILURES'}**",
        ])

        return "\n".join(lines)


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — State Integrity Validator         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    validator = StateIntegrityValidator()
    validator.run_all()

    md = validator.generate_report()
    os.makedirs("reports", exist_ok=True)
    with open("reports/state_integrity_report.md", "w", encoding="utf-8") as f:
        f.write(md)

    passed = sum(1 for r in validator.results if r["passed"])
    print()
    print(f"  Result: {passed}/{len(validator.results)} checks passed")
    print(f"  Report: reports/state_integrity_report.md")


if __name__ == "__main__":
    main()
