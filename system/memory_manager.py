# =============================================================
#  memory_manager.py — Q-Vault OS  |  Virtual Memory Manager
#
#  Simulated memory system with allocation tracking
# =============================================================

from dataclasses import dataclass
from typing import Optional
import time


# Memory constants (in bytes)
TOTAL_MEMORY = 512 * 1024 * 1024  # 512MB virtual RAM
DEFAULT_PROCESS_LIMIT = 64 * 1024 * 1024  # 64MB per process


@dataclass
class MemoryBlock:
    """Represents an allocated memory block."""

    block_id: int
    pid: int
    size: int
    allocated_at: float
    data: Optional[bytes] = None


class MemoryManager:
    """Virtual memory manager."""

    def __init__(self):
        self._total_memory = TOTAL_MEMORY
        self._used_memory = 0
        self._allocations: dict[int, list[MemoryBlock]] = {}  # pid -> blocks
        self._next_block_id = 1

    def allocate(self, pid: int, size: int) -> bool:
        """Allocate memory for a process."""
        if self._used_memory + size > self._total_memory:
            return False

        if pid not in self._allocations:
            self._allocations[pid] = []

        block = MemoryBlock(
            block_id=self._next_block_id,
            pid=pid,
            size=size,
            allocated_at=time.time(),
            data=b"\x00" * size,  # Simulate allocated memory
        )

        self._next_block_id += 1
        self._allocations[pid].append(block)
        self._used_memory += size

        return True

    def free(self, pid: int) -> int:
        """Free all memory for a process. Returns bytes freed."""
        if pid not in self._allocations:
            return 0

        freed = sum(block.size for block in self._allocations[pid])
        del self._allocations[pid]
        self._used_memory -= freed

        return freed

    def get_process_memory(self, pid: int) -> int:
        """Get total memory allocated to a process."""
        if pid not in self._allocations:
            return 0
        return sum(block.size for block in self._allocations[pid])

    def get_stats(self) -> dict:
        """Get memory statistics."""
        return {
            "total": self._total_memory,
            "used": self._used_memory,
            "free": self._total_memory - self._used_memory,
            "used_percent": (self._used_memory / self._total_memory) * 100,
        }

    def get_process_stats(self, pid: int) -> dict:
        """Get per-process memory stats."""
        allocated = self.get_process_memory(pid)
        return {
            "pid": pid,
            "allocated": allocated,
            "limit": DEFAULT_PROCESS_LIMIT,
            "usage_percent": (allocated / DEFAULT_PROCESS_LIMIT) * 100,
        }


# Global memory manager
MEM_MGR = MemoryManager()
