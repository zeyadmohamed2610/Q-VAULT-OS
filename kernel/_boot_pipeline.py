"""
_boot_pipeline.py — Q-Vault OS Pre-Flight Boot System
=====================================================
Class-based boot checks with failure isolation, timing,
and structured reporting. Each check runs independently —
a failure in one does NOT prevent the others from running.

v2 additions:
  • KernelBootPhase — initialises the full kernel simulation
    layer (clock, memory, interrupts, scheduler, dispatcher,
    multicore, deadlock) after the core system checks pass.
  • boot_kernel() is a non-critical phase: a failure prints
    a warning but does NOT abort the OS boot sequence.
"""
import importlib
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# BootCheck — unchanged from v1
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# Original check functions — untouched
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# KernelBootPhase  ← NEW
# ═══════════════════════════════════════════════════════════════

# Accessor helpers — each module exposes its singleton via a
# get_*() factory so the boot layer never hard-imports the
# singleton name directly (avoids circular import issues and
# makes mocking in tests trivial).

def _get_clock():
    from kernel.simulation_clock import SIMULATION_CLOCK
    return SIMULATION_CLOCK

def _get_memory_manager():
    from kernel.memory_manager import MEMORY_MANAGER
    return MEMORY_MANAGER

def _get_interrupt_manager():
    from kernel.interrupt_manager import INTERRUPT_MANAGER
    return INTERRUPT_MANAGER

def _get_scheduler():
    from kernel.scheduler import SCHEDULER
    return SCHEDULER

def _get_dispatcher():
    from kernel.dispatcher import DISPATCHER
    return DISPATCHER

def _get_multicore_engine():
    from kernel.multicore_engine import MULTICORE_ENGINE
    return MULTICORE_ENGINE

def _get_deadlock_manager():
    from kernel.deadlock_manager import DEADLOCK_MANAGER
    return DEADLOCK_MANAGER


# ── Kernel module import smoke-test ──────────────────────────

KERNEL_MODULES = [
    "kernel.simulation_clock",
    "kernel.memory_manager",
    "kernel.interrupt_manager",
    "kernel.scheduler",
    "kernel.dispatcher",
    "kernel.multicore_engine",
    "kernel.deadlock_manager",
]


def check_kernel_imports():
    """Verify all kernel modules are importable before init."""
    failures = []
    for m in KERNEL_MODULES:
        try:
            importlib.import_module(m)
        except Exception as e:
            failures.append(f"{m} -> {e}")
    if failures:
        raise RuntimeError("; ".join(failures))


# ── Main kernel boot function ─────────────────────────────────

def boot_kernel():
    """
    Phase: Initialize Kernel Simulation Layer.

    Startup order (strict — later stages depend on earlier ones):
      1. Memory Manager   — RAM must exist before processes spawn
      2. Interrupt Manager — must be ready before clock fires
      3. Scheduler        — must be configured before dispatcher
      4. Dispatcher       — listens for PROC_SCHEDULED
      5. Multicore Engine — listens for CLOCK_TICK (utilization)
      6. Deadlock Manager — listens for CLOCK_TICK (auto-detect)
      7. Simulation Clock — started LAST; its tick drives everything

    Configuration applied:
      • Scheduler  → ROUND_ROBIN algorithm, quantum = 3 ticks
      • Memory     → FIRST_FIT policy, 1024 units
      • Multicore  → 4 cores, migration_threshold = 0.30
      • Timer IRQ  → every 5 ticks (InterruptManager default)
      • Deadlock   → auto-detect every 10 ticks (default)

    Seed allocations (simulated system processes):
      • systemd  (PID=1)  → 64 units  @ priority 10
      • kthreadd (PID=2)  → 32 units  @ priority 9
      • sshd     (PID=3)  → 48 units  @ priority 7
    """
    # ── Step 1: Memory Manager ───────────────────────────────
    mm = _get_memory_manager()
    mm.set_policy("FIRST_FIT")

    # ── Step 2: Interrupt Manager ────────────────────────────
    irq = _get_interrupt_manager()
    irq.start()         # subscribe to CLOCK_TICK + MEMORY_FULL

    # ── Step 3: Scheduler ────────────────────────────────────
    sched = _get_scheduler()
    sched.set_algorithm("RR")   # ROUND_ROBIN

    # ── Step 4: Dispatcher ───────────────────────────────────
    disp = _get_dispatcher()
    disp.start()        # subscribe to PROC_SCHEDULED

    # ── Step 5: Multicore Engine ─────────────────────────────
    mce = _get_multicore_engine()
    mce.set_core_count(4)
    mce.start()         # subscribe to CLOCK_TICK

    # ── Step 6: Deadlock Manager ─────────────────────────────
    dlm = _get_deadlock_manager()
    dlm.start()         # subscribe to CLOCK_TICK

    # ── Step 7: Seed system process memory allocations ───────
    # These mirror the boot processes already in ProcessManager.
    # Allocations are best-effort; failure is non-fatal.
    _seed_system_memory(mm)

    # ── Step 8: Scheduler start (subscribes to CLOCK_TICK) ───
    sched.start()

    # ── Step 9: Clock — MUST be last ─────────────────────────
    # Every other component is now ready to handle ticks.
    clock = _get_clock()
    clock.start()

    print("  [KERNEL] Kernel Simulation Layer: ONLINE")
    print(f"  [KERNEL] Clock started  — interval: {clock.tick_interval_ms}ms/tick")
    print(f"  [KERNEL] Scheduler      — algorithm: {sched.algorithm}")
    print(f"  [KERNEL] Memory         — {mm.total_size}u FIRST_FIT")
    print(f"  [KERNEL] Multicore      — {mce.core_count} cores")


def _seed_system_memory(mm) -> None:
    """
    Allocate simulated RAM for the three permanent boot processes.
    Non-fatal: ImportError or allocation failure is silently swallowed
    so a full RAM (e.g. tiny test config) does not abort the boot.
    """
    _BOOT_ALLOCS = [
        (1, "systemd",  64),
        (2, "kthreadd", 32),
        (3, "sshd",     48),
    ]
    for pid, label, size in _BOOT_ALLOCS:
        try:
            blk = mm.allocate(pid=pid, size=size, label=label)
            if blk:
                print(f"  [KERNEL] MEM seed: {label} (PID={pid}) → {size}u @ {blk.start}")
            else:
                print(f"  [KERNEL] MEM seed: {label} — allocation failed (RAM full?)")
        except Exception as exc:
            print(f"  [KERNEL] MEM seed: {label} — skipped ({exc})")


# ═══════════════════════════════════════════════════════════════
# Pipeline Runner — extended with kernel phase
# ═══════════════════════════════════════════════════════════════

def run_all_checks() -> bool:
    """
    Run the full boot pipeline in two phases:

    Phase A — Core system checks (critical)
      All existing checks, behaviour unchanged from v1.

    Phase B — Kernel simulation layer (non-critical)
      Kernel module import check, then full kernel init.
      Failure prints a warning but does NOT abort the boot —
      the OS can still start; kernel features will be degraded.
    """

    # ── Phase A: Core system checks (original — unchanged) ───
    phase_a = [
        BootCheck("Core Imports",   check_imports,      critical=True),
        BootCheck("Security API",   check_security_api, critical=True),
        BootCheck("Event Bus",      check_event_bus,    critical=True),
        BootCheck("Runtime Manager",check_runtime,      critical=True),
    ]

    # ── Phase B: Kernel simulation layer (new) ────────────────
    phase_b = [
        BootCheck("Kernel Imports", check_kernel_imports, critical=False),
        BootCheck("Kernel Init",    boot_kernel,          critical=False),
    ]

    all_checks = phase_a + phase_b

    print("\n=== Q-VAULT PRE-FLIGHT BOOT CHECK ===\n")

    # ── Run Phase A ───────────────────────────────────────────
    print("  ── Phase A: Core System ──")
    phase_a_failed = False
    for c in phase_a:
        c.run()
        _print_check(c)
        if not c.ok and c.critical:
            phase_a_failed = True

    # ── Run Phase B (only if Phase A critical checks passed) ──
    print()
    print("  ── Phase B: Kernel Simulation Layer ──")
    if phase_a_failed:
        print("  [SKIP] Core system checks failed — skipping kernel init.")
        for c in phase_b:
            c.ok = False
            c.error = "Skipped: Phase A critical failure"
            c.elapsed_ms = 0
            _print_check(c)
    else:
        kernel_import_ok = True
        for c in phase_b:
            # Don't run kernel init if the import check failed
            if c.name == "Kernel Init" and not kernel_import_ok:
                c.ok = False
                c.error = "Skipped: kernel imports unavailable"
                c.elapsed_ms = 0
                _print_check(c)
                continue
            c.run()
            _print_check(c)
            if c.name == "Kernel Imports" and not c.ok:
                kernel_import_ok = False

    # ── Summary ───────────────────────────────────────────────
    passed          = sum(1 for c in all_checks if c.ok)
    critical_failed = sum(1 for c in all_checks if not c.ok and c.critical)
    total           = len(all_checks)

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


def _print_check(c: BootCheck) -> None:
    """Format and print a single BootCheck result."""
    if c.ok:
        tag = "[OK]  "
    elif c.critical:
        tag = "[FAIL]"
    else:
        tag = "[WARN]"

    line = f"  {tag}  {c.name} ({c.elapsed_ms}ms)"
    if c.error:
        line += f"\n           -> {c.error}"
    print(line)


# ── Standalone entry point ────────────────────────────────────

if __name__ == "__main__":
    if not run_all_checks():
        sys.exit(1)
