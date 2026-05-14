"""
kernel/thread_manager.py — Q-Vault OS
Thread management: TCB, Mutex, Counting Semaphore, ThreadManager.

OS Theory:
  Threads share a process's address space but have their own stack.
  Mutex = binary lock for critical sections.
  Semaphore = counting lock (Dijkstra's P/V = wait/signal).
"""
from __future__ import annotations
import itertools
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)
_tid_counter = itertools.count(start=1)

try:
    from core.event_bus import EVENT_BUS
    _HAS_BUS = True
except Exception:
    EVENT_BUS = None
    _HAS_BUS = False

def _emit(event: str, data: dict) -> None:
    if _HAS_BUS and EVENT_BUS:
        try:
            EVENT_BUS.emit(event, data)
        except Exception:
            pass


# ── Thread state ──────────────────────────────────────────────
class ThreadState(Enum):
    NEW        = "new"
    READY      = "ready"
    RUNNING    = "running"
    WAITING    = "waiting"
    TERMINATED = "terminated"


# ── Thread Control Block ──────────────────────────────────────
@dataclass
class TCB:
    """Thread Control Block — per-thread kernel record."""
    tid:             int
    name:            str
    pid:             int
    state:           ThreadState         = ThreadState.NEW
    priority:        int                 = 5
    created_at:      float               = field(default_factory=time.time)
    program_counter: int                 = 0
    saved_registers: Dict[str, int]      = field(default_factory=lambda: {
        "ax": 0, "bx": 0, "cx": 0, "dx": 0,
    })

    def as_dict(self) -> dict:
        return {
            "tid":      self.tid,
            "name":     self.name,
            "pid":      self.pid,
            "state":    self.state.value,
            "priority": self.priority,
        }


# ── Mutex (binary lock) ───────────────────────────────────────
class Mutex:
    """
    Mutual Exclusion lock. Only one thread holds it at a time.
    All others calling acquire() are queued until release() is called.
    """
    def __init__(self, name: str = ""):
        self.name         = name or f"mutex_{id(self)}"
        self._lock        = threading.Lock()
        self._holder_tid: Optional[int] = None
        self._wait_queue: List[int]     = []

    @property
    def is_locked(self) -> bool:
        return self._holder_tid is not None

    @property
    def holder(self) -> Optional[int]:
        return self._holder_tid

    def acquire(self, tid: int) -> bool:
        """Try to acquire. Returns True if succeeded, False if blocked."""
        with self._lock:
            if self._holder_tid is None:
                self._holder_tid = tid
                _emit("sync.mutex_acquired", {"mutex": self.name, "tid": tid})
                return True
            if tid not in self._wait_queue:
                self._wait_queue.append(tid)
            _emit("sync.mutex_blocked",
                  {"mutex": self.name, "tid": tid, "holder": self._holder_tid})
            return False

    def release(self, tid: int) -> Optional[int]:
        """Release mutex. Returns tid of next waiter (if any)."""
        with self._lock:
            if self._holder_tid != tid:
                logger.warning("[Mutex:%s] tid=%d cannot release (held by %s)",
                               self.name, tid, self._holder_tid)
                return None
            next_tid = self._wait_queue.pop(0) if self._wait_queue else None
            self._holder_tid = next_tid
            _emit("sync.mutex_released",
                  {"mutex": self.name, "released_by": tid, "next_holder": next_tid})
            return next_tid

    def as_dict(self) -> dict:
        return {
            "name":       self.name,
            "locked":     self.is_locked,
            "holder_tid": self._holder_tid,
            "wait_queue": list(self._wait_queue),
        }


# ── Semaphore (counting) ──────────────────────────────────────
class Semaphore:
    """
    Counting Semaphore — Dijkstra's P (wait) / V (signal).
    Allows up to `initial` concurrent acquisitions.
    """
    def __init__(self, name: str, initial: int = 1):
        if initial < 0:
            raise ValueError("Semaphore initial count must be >= 0")
        self.name         = name
        self._count       = initial
        self._lock        = threading.Lock()
        self._wait_queue: List[int] = []

    @property
    def count(self) -> int:
        return self._count

    def wait(self, tid: int) -> bool:
        """P operation. Returns True if proceeds, False if blocked."""
        with self._lock:
            if self._count > 0:
                self._count -= 1
                _emit("sync.semaphore_acquired",
                      {"sem": self.name, "tid": tid, "count": self._count})
                return True
            self._wait_queue.append(tid)
            _emit("sync.semaphore_blocked", {"sem": self.name, "tid": tid})
            return False

    def signal(self, tid: int) -> Optional[int]:
        """V operation. Returns tid of unblocked thread (if any)."""
        with self._lock:
            if self._wait_queue:
                next_tid = self._wait_queue.pop(0)
                _emit("sync.semaphore_released",
                      {"sem": self.name, "unblocked": next_tid, "count": self._count})
                return next_tid
            self._count += 1
            _emit("sync.semaphore_released",
                  {"sem": self.name, "unblocked": None, "count": self._count})
            return None

    def as_dict(self) -> dict:
        return {
            "name":       self.name,
            "count":      self._count,
            "wait_queue": list(self._wait_queue),
        }


# ── Thread Manager ────────────────────────────────────────────
class ThreadManager:
    """Kernel thread management: create TCBs, manage Mutex/Semaphore."""

    def __init__(self):
        self._lock        = threading.RLock()
        self._threads:    Dict[int, TCB]        = {}
        self._mutexes:    Dict[str, Mutex]      = {}
        self._semaphores: Dict[str, Semaphore]  = {}
        logger.info("[THREAD_MANAGER] Initialized.")

    def create_thread(self, name: str, pid: int, priority: int = 5) -> TCB:
        tid = next(_tid_counter)
        tcb = TCB(tid=tid, name=name, pid=pid, priority=priority,
                  state=ThreadState.READY)
        with self._lock:
            self._threads[tid] = tcb
        _emit("thread.created", {"tid": tid, "name": name, "pid": pid})
        return tcb

    def terminate_thread(self, tid: int) -> None:
        with self._lock:
            tcb = self._threads.get(tid)
            if tcb:
                tcb.state = ThreadState.TERMINATED
                _emit("thread.terminated", {"tid": tid})

    def set_state(self, tid: int, state: ThreadState) -> None:
        with self._lock:
            tcb = self._threads.get(tid)
            if tcb:
                old = tcb.state
                tcb.state = state
                _emit("thread.state_changed",
                      {"tid": tid, "from": old.value, "to": state.value})

    def list_threads(self, pid: int = None) -> List[dict]:
        with self._lock:
            items = list(self._threads.values())
            if pid is not None:
                items = [t for t in items if t.pid == pid]
            return [t.as_dict() for t in items]

    def create_mutex(self, name: str) -> Mutex:
        m = Mutex(name)
        self._mutexes[name] = m
        return m

    def get_mutex(self, name: str) -> Optional[Mutex]:
        return self._mutexes.get(name)

    def list_mutexes(self) -> List[dict]:
        return [m.as_dict() for m in self._mutexes.values()]

    def create_semaphore(self, name: str, initial: int = 1) -> Semaphore:
        s = Semaphore(name, initial)
        self._semaphores[name] = s
        return s

    def get_semaphore(self, name: str) -> Optional[Semaphore]:
        return self._semaphores.get(name)

    def list_semaphores(self) -> List[dict]:
        return [s.as_dict() for s in self._semaphores.values()]

    def stats(self) -> dict:
        with self._lock:
            states: Dict[str, int] = {}
            for tcb in self._threads.values():
                states[tcb.state.value] = states.get(tcb.state.value, 0) + 1
            return {
                "total_threads": len(self._threads),
                "by_state":      states,
                "mutexes":       len(self._mutexes),
                "semaphores":    len(self._semaphores),
            }


THREAD_MANAGER = ThreadManager()
