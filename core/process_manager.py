import time
import itertools
import threading
import logging
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QTimer
from core.event_bus import EVENT_BUS, SystemEvent


# ── Process status constants ──────────────────────────────────
STATUS_RUNNING = "running"
STATUS_SLEEPING = "sleeping"
STATUS_STOPPED = "stopped"
STATUS_COMPLETED = "completed"


class Process:
    """One entry in the process table."""

    def __init__(self, pid: int, name: str, argv: list[str], owner: str, status: str):
        self.pid = pid
        self.name = name  # command name only (e.g. "ls")
        self.argv = argv  # full command list (e.g. ["ls", "-la", "/home"])
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

    - Emits SystemEvent.PROC_* facts via global EventBus.
    """

    # ── Phase 13.9: Monotonic Unique PID Sequence ──
    # Prevents "Patience Attacks" or PID-reuse bypasses.
    _PID_SEQUENCE = itertools.count(start=int(time.time()))
    
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
        self._procs: dict[int, Process] = {}  # pid -> Process
        self._lock = threading.RLock()
        self.logger = logging.getLogger("core.process_manager")

        # Seed boot processes
        boot_start = time.time() - 180  # pretend they started 3 min ago
        for name, argv, owner, status in self._BOOT:
            pid = next(self._counter)
            p = Process(pid, name, argv, owner, status)
            p.started = boot_start
            self._procs[pid] = p

    # ── Internal ──────────────────────────────────────────────

    def _notify(self, event_type: SystemEvent, proc: Process):
        """Broadcast state changes to all system subscribers."""
        EVENT_BUS.emit(event_type, {"process": proc.as_dict(), "pid": proc.pid}, source="process_manager")

    # ── Spawn ─────────────────────────────────────────────────

    def spawn(
        self,
        argv: list[str],
        owner: str = "system",
        background: bool = False,
        sim_duration_ms: int = 0,
        is_system: bool = False,
        is_persistent: bool = False,
        executable: str = None,
    ) -> int:
        """
        Register a new process. Supports REAL execution via `executable`.
        `argv` must be a list of strings.
        """
        import shlex
        with self._lock:
            pid = next(self._PID_SEQUENCE)
            name = argv[0] if argv else "unknown"
            status = STATUS_RUNNING

            p = Process(pid, name, argv, owner, status)
            p.is_system = is_system
            p.is_persistent = is_persistent

        # Real Execution (Phase 1)
        if executable:
            import subprocess
            import logging

            try:
                # Decide between synchronous and asynchronous
                if background:
                    p.handle = subprocess.Popen(
                        argv,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                    )
                    self.logger.info(f"[PM] Spawned ASYNC (Popen): {name} (PID: {pid}) owner={owner}")
                else:
                    # Synchronous run
                    res = subprocess.run(
                        argv,
                        capture_output=True,
                        text=True
                    )
                    p.handle = res
                    p.status = STATUS_COMPLETED
                    self.logger.info(f"[PM] Spawned SYNC (run): {name} (PID: {pid}) code={res.returncode}")
            except Exception as e:
                p.status = STATUS_STOPPED
                self.logger.error(f"[PM] Failed to spawn {name}: {e}")
                raise RuntimeError(f"Process spawn failed: {e}")

            self._procs[pid] = p
            self._notify(SystemEvent.PROC_SPAWNED, p)

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
        with self._lock:
            p = self._procs.get(pid)
            if p and p.status == STATUS_RUNNING:
                p.status = STATUS_COMPLETED
                self._notify(SystemEvent.PROC_COMPLETED, p)
                # Remove after a short grace period
                QTimer.singleShot(5000, lambda _pid=pid: self._reap(_pid))

    def _reap(self, pid: int):
        with self._lock:
            if pid in self._procs:
                p = self._procs.pop(pid)
                self._notify(SystemEvent.PROC_GC, p)

    # ── Kill ──────────────────────────────────────────────────

    def kill(self, pid: int) -> bool:
        """
        Transition process to STOPPED, notify observers,
        then remove it. Returns True if found.
        """
        with self._lock:
            p = self._procs.get(pid)
            if not p or p.status in [STATUS_STOPPED, STATUS_COMPLETED]:
                return False
            
            if p._timer:
                p._timer.stop()
                p._timer = None
            
            # Phase 13.7: Terminate real handle
            if p.handle:
                try:
                    p.handle.terminate()
                except Exception as e:
                    self.logger.warning(f"[PM] Error terminating handle for PID {pid}: {e}")
            
            p.status = STATUS_STOPPED
            self._notify(SystemEvent.PROC_STOPPED, p)
            QTimer.singleShot(300, lambda _pid=pid: self._reap(_pid))
            return True

    def kill_all_by_owner(self, owner: str):
        """Mass termination for application cleanup (Lifecycle-Safe)."""
        with self._lock:
            pids_to_kill = [pid for pid, p in self._procs.items() if p.owner == owner]
            for pid in pids_to_kill:
                self.kill(pid)

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
