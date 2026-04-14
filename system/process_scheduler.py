# =============================================================
#  process_scheduler.py — Q-Vault OS  |  Process Scheduler
#
#  Round Robin scheduler with process states and priorities
# =============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


# Process states
class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    TERMINATED = "terminated"


@dataclass
class ScheduledProcess:
    """Process with scheduler metadata."""

    pid: int
    name: str
    state: ProcessState = ProcessState.NEW
    priority: int = 5  # 0-10, default 5
    cpu_time: int = 0  # ms used
    memory_allocated: int = 0  # bytes
    memory_limit: int = 64 * 1024 * 1024  # 64MB default
    owner: str = "user"
    created_at: float = field(default_factory=time.time)
    command: str = ""

    def __post_init__(self):
        self.state = ProcessState.READY


class ProcessScheduler(QObject):
    """Round Robin process scheduler."""

    process_started = pyqtSignal(int, str)  # pid, name
    process_terminated = pyqtSignal(int, str)
    state_changed = pyqtSignal(int, str, str)  # pid, old_state, new_state

    def __init__(self, parent=None):
        super().__init__(parent)

        self._next_pid = 1
        self._processes: dict[int, ScheduledProcess] = {}
        self._ready_queue: list[int] = []  # PIDs in READY state
        self._running_pid: Optional[int] = None

        # Time quantum for Round Robin (ms)
        self._time_quantum = 150

        # Start scheduler timer
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.timeout.connect(self._scheduler_tick)
        self._scheduler_timer.start(self._time_quantum)

    def _scheduler_tick(self):
        """Handle Round Robin scheduling tick."""
        # If no process running, pick next from ready queue
        if self._running_pid is None and self._ready_queue:
            self._schedule_next()

        # Increment CPU time for running process
        if self._running_pid is not None:
            proc = self._processes.get(self._running_pid)
            if proc:
                proc.cpu_time += self._time_quantum
                # Check if time quantum exceeded
                if proc.cpu_time >= self._time_quantum * 10:
                    # Move to back of ready queue (Round Robin)
                    self._ready_queue.append(self._running_pid)
                    self._running_pid = None
                    self._schedule_next()

    def _schedule_next(self):
        """Schedule next process from ready queue."""
        if not self._ready_queue:
            return

        # Get next process from ready queue
        pid = self._ready_queue.pop(0)
        proc = self._processes.get(pid)
        if proc and proc.state == ProcessState.READY:
            old_state = proc.state
            proc.state = ProcessState.RUNNING
            self._running_pid = pid
            self.state_changed.emit(pid, old_state.value, proc.state.value)
            self.process_started.emit(pid, proc.name)

    def create_process(
        self, name: str, command: str = "", owner: str = "user", priority: int = 5
    ) -> int:
        """Create a new process."""
        pid = self._next_pid
        self._next_pid += 1

        proc = ScheduledProcess(
            pid=pid,
            name=name,
            command=command,
            owner=owner,
            priority=priority,
        )

        self._processes[pid] = proc
        self._ready_queue.append(pid)

        return pid

    def terminate_process(self, pid: int) -> bool:
        """Terminate a process."""
        proc = self._processes.get(pid)
        if not proc:
            return False

        old_state = proc.state
        proc.state = ProcessState.TERMINATED

        # Remove from queues
        if pid in self._ready_queue:
            self._ready_queue.remove(pid)
        if self._running_pid == pid:
            self._running_pid = None

        self.state_changed.emit(pid, old_state.value, proc.state.value)
        self.process_terminated.emit(pid, proc.name)

        return True

    def set_priority(self, pid: int, priority: int) -> bool:
        """Set process priority (0-10)."""
        proc = self._processes.get(pid)
        if not proc:
            return False
        proc.priority = max(0, min(10, priority))
        return True

    def get_process(self, pid: int) -> Optional[ScheduledProcess]:
        """Get process by PID."""
        return self._processes.get(pid)

    def list_processes(self) -> list[ScheduledProcess]:
        """List all processes."""
        return list(self._processes.values())

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "total_processes": len(self._processes),
            "ready_queue": len(self._ready_queue),
            "running_pid": self._running_pid,
            "time_quantum": self._time_quantum,
        }

    def allocate_memory(self, pid: int, size: int) -> bool:
        """Allocate memory to process."""
        proc = self._processes.get(pid)
        if not proc:
            return False

        if proc.memory_allocated + size > proc.memory_limit:
            return False

        proc.memory_allocated += size
        return True

    def free_memory(self, pid: int) -> int:
        """Free all memory for process. Returns bytes freed."""
        proc = self._processes.get(pid)
        if not proc:
            return 0

        freed = proc.memory_allocated
        proc.memory_allocated = 0
        return freed


# Global scheduler instance
SCHEDULER = ProcessScheduler()
