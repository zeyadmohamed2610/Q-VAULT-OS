# =============================================================
#  anti_memory_dump.py — Q-VAULT OS  |  Anti-Memory Dump Protection
#
#  Protect sensitive data from memory dumping attempts
# =============================================================

import os
import sys
import time
import hashlib
import secrets
import threading
from typing import Any, Optional, List
from collections import deque
from weakref import WeakValueDictionary

CHUNK_SIZE = 64
MAX_ACCESS_COUNT = 10
SENSITIVE_ACCESS_WINDOW = 30


class SecureBuffer:
    """
    Secure buffer for storing sensitive data.
    Splits data into chunks and tracks access patterns.
    """

    def __init__(self, data: str, label: str = "default"):
        self._label = label
        self._chunks: List[bytes] = self._split_into_chunks(data.encode())
        self._access_times: deque = deque(maxlen=100)
        self._access_count = 0
        self._created_at = time.time()
        self._last_access = time.time()
        self._wiped = False

    def _split_into_chunks(self, data: bytes) -> List[bytes]:
        """Split data into random-sized chunks."""
        chunks = []
        remaining = data
        while remaining:
            size = min(CHUNK_SIZE + secrets.randbelow(32), len(remaining))
            chunks.append(remaining[:size])
            remaining = remaining[size:]
        return chunks

    def access(self) -> Optional[str]:
        """Access the data, recording access pattern."""
        if self._wiped:
            return None

        self._access_times.append(time.time())
        self._access_count += 1
        self._last_access = time.time()
        return self._reconstruct()

    def _reconstruct(self) -> str:
        """Reconstruct data from chunks."""
        return b"".join(self._chunks).decode("utf-8", errors="ignore")

    def wipe(self):
        """Securely wipe all chunks."""
        for i in range(len(self._chunks)):
            self._chunks[i] = b"\x00" * len(self._chunks[i])
        self._chunks.clear()
        self._wiped = True

    def is_suspicious_access(self) -> bool:
        """Check if access pattern is suspicious."""
        if self._access_count < MAX_ACCESS_COUNT:
            return False

        cutoff = time.time() - SENSITIVE_ACCESS_WINDOW
        recent = [t for t in self._access_times if t > cutoff]
        return len(recent) >= MAX_ACCESS_COUNT

    def get_access_count(self) -> int:
        """Get total access count."""
        return self._access_count


class AntiMemoryDump:
    """
    Protect sensitive data from memory dumping.
    Monitors access patterns and detects dump attempts.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._buffers: WeakValueDictionary = WeakValueDictionary()
        self._buffer_counter = 0
        self._suspicious_reads = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._start_monitoring()

    def _start_monitoring(self):
        """Start memory monitoring."""
        self._monitoring = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """Background cleanup for expired buffers."""
        while self._monitoring:
            self._cleanup_expired()
            time.sleep(60)

    def _cleanup_expired(self):
        """Cleanup expired sensitive data."""
        expired_keys = []
        cutoff = time.time() - 300

        with self._lock:
            for key, buf in self._buffers.items():
                if buf._last_access < cutoff:
                    expired_keys.append(key)

        for key in expired_keys:
            self.wipe(key)

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self._monitoring = False

    def store(self, data: str, label: str = "default") -> str:
        """
        Store sensitive data in secure buffer.
        Returns buffer ID.
        """
        with self._lock:
            buf = SecureBuffer(data, label)
            buf_id = f"buf_{self._buffer_counter}"
            self._buffer_counter += 1

            self._buffers[buf_id] = buf
            return buf_id

    def retrieve(self, buffer_id: str) -> Optional[str]:
        """Retrieve data from secure buffer."""
        with self._lock:
            if buffer_id not in self._buffers:
                return None

            buf = self._buffers[buffer_id]

            if buf.is_suspicious_access():
                self._suspicious_reads += 1
                self._trigger_dump_alert()

            return buf.access()

    def wipe(self, buffer_id: str) -> bool:
        """Wipe a specific buffer."""
        with self._lock:
            if buffer_id in self._buffers:
                self._buffers[buffer_id].wipe()
                del self._buffers[buffer_id]
                return True
        return False

    def wipe_all(self):
        """Wipe all buffers."""
        with self._lock:
            for buf in self._buffers.values():
                buf.wipe()
            self._buffers.clear()

    def _trigger_dump_alert(self):
        """Trigger alert for suspicious memory access."""
        from system.security_system import SEC, EVT_INTRUSION
        from system.notification_system import NOTIFY

        detail = f"Suspicious memory read pattern detected. {self._suspicious_reads} rapid accesses."

        SEC.report(
            EVT_INTRUSION,
            source="anti_memory_dump",
            detail=detail,
            escalate=True,
        )

        NOTIFY.send(
            "MEMORY DUMP DETECTED",
            detail,
            level="danger",
        )

    def obfuscate_name(self, name: str) -> str:
        """Obfuscate a variable name in memory."""
        hash_obj = hashlib.sha256(name.encode())
        return f"_q_{hash_obj.hexdigest()[:16]}"

    def get_stats(self) -> dict:
        """Get memory protection statistics."""
        with self._lock:
            return {
                "active_buffers": len(self._buffers),
                "suspicious_reads": self._suspicious_reads,
                "monitoring": self._monitoring,
            }


ANTI_MEMORY_DUMP = AntiMemoryDump()


def secure_store(data: str, label: str = "default") -> str:
    """Convenience function to store sensitive data."""
    return ANTI_MEMORY_DUMP.store(data, label)


def secure_retrieve(buffer_id: str) -> Optional[str]:
    """Convenience function to retrieve sensitive data."""
    return ANTI_MEMORY_DUMP.retrieve(buffer_id)


def secure_wipe(buffer_id: str) -> bool:
    """Convenience function to wipe sensitive data."""
    return ANTI_MEMORY_DUMP.wipe(buffer_id)
