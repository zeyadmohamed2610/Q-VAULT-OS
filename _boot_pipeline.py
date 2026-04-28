"""
_boot_pipeline.py — Q-Vault OS Pre-Flight Boot System
=====================================================
Class-based boot checks with failure isolation, timing,
and structured reporting. Each check runs independently —
a failure in one does NOT prevent the others from running.
"""
import importlib
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class BootCheck:
    """Single isolated boot check with timing, error capture, and severity."""

    def __init__(self, name: str, fn, critical: bool = True):
        self.name = name
        self.fn = fn
        self.critical = critical
        self.ok = False
        self.error = None
        self.elapsed_ms = 0

    def run(self):
        t0 = time.perf_counter()
        try:
            self.fn()
            self.ok = True
        except Exception as e:
            self.error = str(e)
        self.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)


# ── Individual Check Functions ──────────────────────────────

CORE_MODULES = [
    "components.boot_screen",
    "components.login_screen",
    "components.desktop",
    "components.lock_screen",
    "system.app_controller",
    "system.runtime_manager",
    "core.event_bus",
    "system.security_api",
    "system.auth_manager",
]


def check_imports():
    failures = []
    for m in CORE_MODULES:
        try:
            importlib.import_module(m)
        except Exception as e:
            failures.append(f"{m} -> {e}")
    if failures:
        raise RuntimeError("; ".join(failures))


def check_security_api():
    from system.security_api import get_security_api
    api = get_security_api()
    if not hasattr(api, "is_secure_mode"):
        raise RuntimeError("Security API missing expected interface")


def check_event_bus():
    from core.event_bus import EVENT_BUS
    if EVENT_BUS is None:
        raise RuntimeError("EVENT_BUS singleton is None")


def check_runtime():
    from system.runtime_manager import RUNTIME_MANAGER
    if RUNTIME_MANAGER is None:
        raise RuntimeError("RUNTIME_MANAGER singleton is None")


# ── Pipeline Runner ─────────────────────────────────────────

def run_all_checks() -> bool:
    checks = [
        BootCheck("Core Imports", check_imports, critical=True),
        BootCheck("Security API", check_security_api, critical=True),
        BootCheck("Event Bus", check_event_bus, critical=True),
        BootCheck("Runtime Manager", check_runtime, critical=True),
    ]

    print("\n=== Q-VAULT PRE-FLIGHT BOOT CHECK ===\n")

    for c in checks:
        c.run()
        if c.ok:
            status = "OK"
            tag = f"[{status}]"
        else:
            status = "FAIL" if c.critical else "WARN"
            tag = f"[{status}]"
            
        line = f"  {tag:6s}  {c.name} ({c.elapsed_ms}ms)"
        if c.error:
            line += f"\n           -> {c.error}"
        print(line)

    passed = sum(1 for c in checks if c.ok)
    critical_failed = sum(1 for c in checks if not c.ok and c.critical)
    total = len(checks)

    print(f"\n  Result: {passed}/{total} checks passed.")

    if critical_failed == 0:
        if passed < total:
            print("  BOOT SUCCESS (with warnings)\n")
        else:
            print("  BOOT SUCCESS\n")
        return True
    else:
        print(f"  BOOT FAILED ({critical_failed} critical checks failed)\n")
        return False


if __name__ == "__main__":
    if not run_all_checks():
        sys.exit(1)
