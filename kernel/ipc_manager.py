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
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)
_ipc_id = itertools.count(start=100)

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


# ── Shared Memory ─────────────────────────────────────────────
class SharedMemory:
    """
    Named shared memory segment. Multiple processes attach to it
    and read/write a common buffer (no kernel involvement after setup).
    Requires external synchronization (Mutex/Semaphore).
    """
    def __init__(self, name: str, size: int):
        self.name       = name
        self.size       = size
        self._data: Any = None
        self._lock      = threading.RLock()
        self._attached: List[int] = []

    def attach(self, pid: int) -> None:
        if pid not in self._attached:
            self._attached.append(pid)
            _emit("ipc.shm_attached", {"shm": self.name, "pid": pid})

    def detach(self, pid: int) -> None:
        if pid in self._attached:
            self._attached.remove(pid)

    def write(self, pid: int, data: Any) -> bool:
        with self._lock:
            if pid not in self._attached:
                return False
            self._data = data
            _emit("ipc.shm_write", {"shm": self.name, "pid": pid})
            return True

    def read(self, pid: int) -> Any:
        with self._lock:
            if pid not in self._attached:
                return None
            return self._data

    def as_dict(self) -> dict:
        return {
            "name":     self.name,
            "size":     self.size,
            "attached": list(self._attached),
            "has_data": self._data is not None,
        }


# ── Message Queue ─────────────────────────────────────────────
@dataclass
class Message:
    sender_pid:   int
    receiver_pid: int    # 0 = broadcast
    msg_type:     str
    data:         Any
    timestamp:    float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {
            "sender":   self.sender_pid,
            "receiver": self.receiver_pid,
            "type":     self.msg_type,
            "data":     str(self.data)[:80],
        }


class MessageQueue:
    """
    FIFO message queue. Messages are copied to kernel space.
    Sender does not block. Receiver blocks if queue is empty.
    """
    def __init__(self, name: str, maxsize: int = 100):
        self.name     = name
        self.maxsize  = maxsize
        self._queue: Deque[Message] = deque()
        self._lock    = threading.RLock()

    def send(self, msg: Message) -> bool:
        with self._lock:
            if len(self._queue) >= self.maxsize:
                logger.warning("[MQ:%s] full — dropping message", self.name)
                return False
            self._queue.append(msg)
            _emit("ipc.mq_sent",
                  {"queue": self.name, "sender": msg.sender_pid, "type": msg.msg_type})
            return True

    def receive(self, pid: int) -> Optional[Message]:
        """Dequeue first message addressed to pid or broadcast (0)."""
        with self._lock:
            for i, msg in enumerate(self._queue):
                if msg.receiver_pid == pid or msg.receiver_pid == 0:
                    del self._queue[i]
                    _emit("ipc.mq_received", {"queue": self.name, "receiver": pid})
                    return msg
            return None

    def as_dict(self) -> dict:
        with self._lock:
            return {
                "name":     self.name,
                "length":   len(self._queue),
                "maxsize":  self.maxsize,
                "messages": [m.as_dict() for m in list(self._queue)[:5]],
            }


# ── Pipe ──────────────────────────────────────────────────────
class Pipe:
    """
    Unidirectional byte-stream pipe. writer_pid → [buffer] → reader_pid.
    Writer blocks when buffer full, reader blocks when empty.
    """
    BUFFER_SIZE = 4096

    def __init__(self, name: str, writer_pid: int, reader_pid: int):
        self.name       = name
        self.writer_pid = writer_pid
        self.reader_pid = reader_pid
        self._buffer: Deque[str] = deque()
        self._lock      = threading.RLock()
        self._closed    = False

    def write(self, data: str) -> bool:
        with self._lock:
            if self._closed:
                return False
            if sum(len(s) for s in self._buffer) + len(data) > self.BUFFER_SIZE:
                return False   # pipe full
            self._buffer.append(data)
            _emit("ipc.pipe_write", {"pipe": self.name, "bytes": len(data)})
            return True

    def read(self) -> Optional[str]:
        with self._lock:
            if not self._buffer:
                return None
            data = self._buffer.popleft()
            _emit("ipc.pipe_read", {"pipe": self.name, "bytes": len(data)})
            return data

    def close(self) -> None:
        self._closed = True

    def as_dict(self) -> dict:
        with self._lock:
            return {
                "name":       self.name,
                "writer_pid": self.writer_pid,
                "reader_pid": self.reader_pid,
                "buffered":   sum(len(s) for s in self._buffer),
                "closed":     self._closed,
            }


# ── IPC Manager ───────────────────────────────────────────────
class IPCManager:
    """Kernel IPC subsystem — manages all SHM, message queues, and pipes."""

    def __init__(self):
        self._shm:    Dict[str, SharedMemory]   = {}
        self._queues: Dict[str, MessageQueue]   = {}
        self._pipes:  Dict[str, Pipe]           = {}
        logger.info("[IPC_MANAGER] Initialized.")

    def create_shared_memory(self, name: str, size: int = 4096) -> SharedMemory:
        shm = SharedMemory(name, size)
        self._shm[name] = shm
        return shm

    def create_message_queue(self, name: str, maxsize: int = 100) -> MessageQueue:
        mq = MessageQueue(name, maxsize)
        self._queues[name] = mq
        return mq

    def create_pipe(self, writer_pid: int, reader_pid: int) -> Pipe:
        name = f"pipe_{writer_pid}_to_{reader_pid}"
        pipe = Pipe(name, writer_pid, reader_pid)
        self._pipes[name] = pipe
        return pipe

    def get_shm(self, name: str) -> Optional[SharedMemory]:
        return self._shm.get(name)

    def get_queue(self, name: str) -> Optional[MessageQueue]:
        return self._queues.get(name)

    def stats(self) -> dict:
        return {
            "shared_memory":  len(self._shm),
            "message_queues": len(self._queues),
            "pipes":          len(self._pipes),
        }

    def snapshot(self) -> dict:
        return {
            "shm":    [s.as_dict() for s in self._shm.values()],
            "queues": [q.as_dict() for q in self._queues.values()],
            "pipes":  [p.as_dict() for p in self._pipes.values()],
        }


IPC_MANAGER = IPCManager()
