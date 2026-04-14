# =============================================================
#  process_manager.py — Q-Vault OS  |  Process Manager v2
#
#  Changes vs v1:
#    • Full status lifecycle:  running → stopped → completed
#    • Every process stores full argv (name + args string)
#    • Observer callbacks: any subscriber is notified on every
#      state change so the terminal can print "[PID] Done"
#      and the Task Manager (Phase 3) can auto-refresh
#    • Background jobs get a QTimer that fires after a
#      simulated runtime and marks them "completed", then
#      fires the "done" observer so the terminal sees it
#    • kill() transitions status to "stopped" before removal
# =============================================================

import time
import itertools
from typing import Callable

from PyQt5.QtCore import QTimer


# ── Process status constants ──────────────────────────────────
STATUS_RUNNING = "running"
STATUS_SLEEPING = "sleeping"
STATUS_STOPPED = "stopped"
STATUS_COMPLETED = "completed"


class Process:
    """One entry in the process table."""

    def __init__(self, pid: int, name: str, argv: str, owner: str, status: str):
        self.pid = pid
        self.name = name  # command name only (e.g. "ls")
        self.argv = argv  # full command string (e.g. "ls -la /home")
        self.owner = owner
        self.status = status
        self.started = time.time()
        self._timer = None  # QTimer for background completion
        self.is_system = False  # New: system daemon flag
        self.is_persistent = False  # New: auto-restart flag
        self.handle = None  # New: subprocess.Popen handle

    def age_str(self) -> str:
        """Human-readable elapsed time since process started."""
        secs = int(time.time() - self.started)
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m{secs % 60:02d}s"
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"

    def as_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "argv": self.argv,
            "owner": self.owner,
            "status": self.status,
            "age": self.age_str(),
        }


class ProcessManager:
    """
    Singleton process table.

    Observer API
    ─────────────
    subscribe(cb)     — cb(event, proc) called on every state change
                        event is one of: "spawn", "done", "stopped", "gc"
    unsubscribe(cb)
    """

    # Boot processes that always appear in the table
    _BOOT = [
        ("systemd", "/sbin/init", "root", STATUS_SLEEPING),
        ("kthreadd", "[kthreadd]", "root", STATUS_SLEEPING),
        ("sshd", "/usr/sbin/sshd -D", "root", STATUS_SLEEPING),
        ("dbus", "/usr/bin/dbus-daemon --system", "root", STATUS_SLEEPING),
        ("qvault-wm", "qvault-wm --session default", "user", STATUS_RUNNING),
        ("qsh", "qsh --login", "user", STATUS_RUNNING),
    ]

    def __init__(self):
        self._counter = itertools.count(start=1)
        self._procs: dict[int, Process] = {}  # pid → Process
        self._observers: list[Callable] = []

        # Seed boot processes
        boot_start = time.time() - 180  # pretend they started 3 min ago
        for name, argv, owner, status in self._BOOT:
            pid = next(self._counter)
            p = Process(pid, name, argv, owner, status)
            p.started = boot_start
            self._procs[pid] = p

    # ── Observer ──────────────────────────────────────────────

    def subscribe(self, cb: Callable):
        if cb not in self._observers:
            self._observers.append(cb)

    def unsubscribe(self, cb: Callable):
        self._observers = [o for o in self._observers if o is not cb]

    def _notify(self, event: str, proc: Process):
        for cb in self._observers:
            try:
                cb(event, proc)
            except Exception:
                pass  # never let an observer crash the PM

    # ── Spawn ─────────────────────────────────────────────────

    def spawn(
        self,
        argv: str,
        owner: str = "user",
        background: bool = False,
        sim_duration_ms: int = 0,
        is_system: bool = False,
        is_persistent: bool = False,
        executable: str = None,
    ) -> int:
        """
        Register a new process. Supports REAL execution via `executable`.
        """
        pid = next(self._counter)
        name = argv.split()[0] if argv.split() else argv
        status = STATUS_RUNNING

        p = Process(pid, name, argv, owner, status)
        p.is_system = is_system
        p.is_persistent = is_persistent

        # Real Execution (Phase 1)
        if executable:
            import subprocess
            import logging

            try:
                p.handle = subprocess.Popen(
                    [executable],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                logging.info(f"[PM] Spawned real process: {name} (PID: {pid})")
            except Exception as e:
                p.status = STATUS_STOPPED
                print(f"[kernel] Failed to launch real process {name}: {e}")
                logging.error(f"[PM] Failed to spawn {name}: {e}")

        self._procs[pid] = p
        self._notify("spawn", p)

        if background and sim_duration_ms > 0:
            # After sim_duration_ms the job finishes automatically
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda _pid=pid: self._complete(_pid))
            timer.start(sim_duration_ms)
            p._timer = timer  # keep reference so it isn't GC'd

        elif not background:
            # Foreground commands complete immediately after spawn
            # (we mark them completed right away but keep them briefly
            #  visible so the Task Manager can show a flash of activity)
            QTimer.singleShot(800, lambda _pid=pid: self._complete(_pid))

        self._gc()
        return pid

    def _complete(self, pid: int):
        p = self._procs.get(pid)
        if p and p.status == STATUS_RUNNING:
            p.status = STATUS_COMPLETED
            self._notify("done", p)
            # Remove after a short grace period
            QTimer.singleShot(5000, lambda _pid=pid: self._reap(_pid))

    def _reap(self, pid: int):
        p = self._procs.pop(pid, None)
        if p:
            self._notify("gc", p)

    # ── Kill ──────────────────────────────────────────────────

    def kill(self, pid: int) -> bool:
        """
        Transition process to STOPPED, notify observers,
        then remove it. Returns True if found.
        """
        p = self._procs.get(pid)
        if not p:
            return False
        if p._timer:
            p._timer.stop()
        p.status = STATUS_STOPPED
        self._notify("stopped", p)
        QTimer.singleShot(300, lambda _pid=pid: self._reap(_pid))
        return True

    # ── Query ─────────────────────────────────────────────────

    def all_procs(self) -> list[dict]:
        return [p.as_dict() for p in self._procs.values()]

    def background_jobs(self) -> list[dict]:
        boot_names = {b[0] for b in self._BOOT}
        return [
            p.as_dict()
            for p in self._procs.values()
            if p.status == STATUS_RUNNING and p.name not in boot_names
        ]

    def get(self, pid: int) -> Process | None:
        return self._procs.get(pid)

    # ── GC: trim very old completed entries ───────────────────

    def _gc(self):
        cutoff = time.time() - 120  # 2-minute window
        stale = [
            pid
            for pid, p in self._procs.items()
            if p.status == STATUS_COMPLETED and p.started < cutoff
        ]
        for pid in stale:
            self._procs.pop(pid, None)


# ── Module singleton ──────────────────────────────────────────
PM = ProcessManager()
