"""
kernel/ipc_manager.py — Q-Vault OS
Inter-Process Communication: Shared Memory, Message Queue, Pipe.

OS Theory:
  SharedMemory  — fastest IPC; common physical pages mapped to multiple processes.
  MessageQueue  — kernel-buffered FIFO; sender/receiver decoupled.
  Pipe          — byte-stream; one writer, one reader (unidirectional).
"""
from __future__ import annotations
import itertools
import logging
import threading
from collections import deque
from typing import Any, Dict, List, Optional, Set

from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

def _emit(event: Any, data: dict) -> None:
    if EVENT_BUS:
        try:
            EVENT_BUS.emit(event, data, source="ipc_manager")
        except Exception:
            pass


# ── Shared Memory ─────────────────────────────────────────────

class SharedMemory:
    """Named shared memory segment with ACL protection."""
    def __init__(self, name: str, size: int, owner_pid: int):
        self.name       = name
        self.size       = size
        self.owner_pid  = owner_pid
        self._data: Any = None
        self._lock      = threading.RLock()
        self._authorized_pids: Set[int] = {owner_pid}

    def authorize(self, target_pid: int):
        self._authorized_pids.add(target_pid)

    def write(self, pid: int, data: Any) -> bool:
        with self._lock:
            if pid not in self._authorized_pids: return False
            self._data = data
            _emit("ipc.shm_write", {"shm": self.name, "pid": pid})
            return True

    def read(self, pid: int) -> Any:
        with self._lock:
            if pid not in self._authorized_pids: return None
            return self._data

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "size": self.size,
            "owner": self.owner_pid,
            "auth_count": len(self._authorized_pids)
        }


# ── Message Queue ─────────────────────────────────────────────

class MessageQueue:
    """Kernel-buffered FIFO queue."""
    def __init__(self, name: str, owner_pid: int, maxsize: int = 100):
        self.name = name
        self.owner_pid = owner_pid
        self._queue: deque = deque(maxlen=maxsize)
        self._lock = threading.RLock()
        self._authorized_pids: Set[int] = {owner_pid}

    def authorize(self, target_pid: int):
        self._authorized_pids.add(target_pid)

    def send(self, pid: int, message: Any) -> bool:
        with self._lock:
            if pid not in self._authorized_pids: return False
            self._queue.append(message)
            _emit("ipc.mq_sent", {"queue": self.name, "pid": pid})
            return True

    def receive(self, pid: int) -> Optional[Any]:
        with self._lock:
            if pid not in self._authorized_pids: return None
            if not self._queue: return None
            return self._queue.popleft()

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "owner": self.owner_pid,
            "count": len(self._queue),
            "max": self._queue.maxlen
        }


# ── Pipe ──────────────────────────────────────────────────────

class Pipe:
    """Byte-stream pipe (Kernel-simulated)."""
    def __init__(self, name: str, owner_pid: int):
        self.name = name
        self.owner_pid = owner_pid
        self._buffer = b""
        self._lock = threading.RLock()
        self._authorized_pids: Set[int] = {owner_pid}

    def authorize(self, target_pid: int):
        self._authorized_pids.add(target_pid)

    def write(self, pid: int, data: bytes) -> int:
        with self._lock:
            if pid not in self._authorized_pids: return 0
            self._buffer += data
            return len(data)

    def read(self, pid: int, n: int = -1) -> bytes:
        with self._lock:
            if pid not in self._authorized_pids: return b""
            if n < 0:
                out = self._buffer
                self._buffer = b""
            else:
                out = self._buffer[:n]
                self._buffer = self._buffer[n:]
            return out

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "owner": self.owner_pid,
            "buffer_size": len(self._buffer)
        }


# ── IPC Manager ───────────────────────────────────────────────

class IPCManager:
    """Kernel IPC subsystem with mandatory Access Control and Lifecycle Cleanup."""

    def __init__(self):
        self._shm:    Dict[str, SharedMemory]   = {}
        self._queues: Dict[str, MessageQueue]   = {}
        self._pipes:  Dict[str, Pipe]           = {}
        self._lock = threading.RLock()
        
        if EVENT_BUS:
            EVENT_BUS.subscribe(SystemEvent.PROC_STOPPED, self._on_proc_death)
            EVENT_BUS.subscribe(SystemEvent.PROC_COMPLETED, self._on_proc_death)
            
        logger.info("[IPC_MANAGER] Hardened with Lifecycle-Aware Cleanup.")

    def _on_proc_death(self, payload: Any):
        """Reap all IPC objects owned by the dead process."""
        pid = payload.data.get("pid")
        if pid is None: return

        with self._lock:
            # Cleanup Shared Memory
            to_delete = [name for name, shm in self._shm.items() if shm.owner_pid == pid]
            for name in to_delete:
                del self._shm[name]
                logger.debug(f"[IPC] Reaped SHM '{name}' (Owner PID {pid} died)")

            # Cleanup Queues
            to_delete = [name for name, mq in self._queues.items() if mq.owner_pid == pid]
            for name in to_delete:
                del self._queues[name]
                logger.debug(f"[IPC] Reaped MQ '{name}' (Owner PID {pid} died)")

            # Cleanup Pipes
            to_delete = [name for name, p in self._pipes.items() if p.owner_pid == pid]
            for name in to_delete:
                del self._pipes[name]
                logger.debug(f"[IPC] Reaped Pipe '{name}' (Owner PID {pid} died)")

    def create_shared_memory(self, name: str, owner_pid: int, size: int = 4096) -> SharedMemory:
        with self._lock:
            shm = SharedMemory(name, size, owner_pid)
            self._shm[name] = shm
            return shm

    def create_message_queue(self, name: str, owner_pid: int, maxsize: int = 100) -> MessageQueue:
        with self._lock:
            mq = MessageQueue(name, owner_pid, maxsize)
            self._queues[name] = mq
            return mq

    def create_pipe(self, name: str, owner_pid: int) -> Pipe:
        with self._lock:
            p = Pipe(name, owner_pid)
            self._pipes[name] = p
            return p

    def stats(self) -> dict:
        with self._lock:
            return {
                "shared_memory":  len(self._shm),
                "message_queues": len(self._queues),
                "pipes":          len(self._pipes),
            }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "shm":    [s.as_dict() for s in self._shm.values()],
                "queues": [q.as_dict() for q in self._queues.values()],
                "pipes":  [p.as_dict() for p in self._pipes.values()],
            }

IPC_MANAGER = IPCManager()
