from __future__ import annotations

import logging
import threading
from typing import List, Optional

from core.event_bus import EVENT_BUS, SystemEvent
from ._memory_types import MemoryBlock
from ._memory_allocator import MemoryAllocator
from ._memory_compactor import MemoryCompactor

logger = logging.getLogger(__name__)

# ── Policy identifiers ────────────────────────────────────────────
POLICY_FIRST_FIT = "FIRST_FIT"
POLICY_BEST_FIT  = "BEST_FIT"
POLICY_WORST_FIT = "WORST_FIT"

_VALID_POLICIES = {POLICY_FIRST_FIT, POLICY_BEST_FIT, POLICY_WORST_FIT}
_DEFAULT_RAM_SIZE = 1024

class MemoryManager:
    """
    Simulated flat-address RAM manager (Refactored v5).
    Acts as a Facade over Specialized Helpers (Allocator, Compactor).
    """

    def __init__(
        self,
        total_size: int = _DEFAULT_RAM_SIZE,
        policy: str = POLICY_FIRST_FIT,
    ):
        self._total: int = total_size
        self._policy: str = policy
        self._lock = threading.RLock()

        # Start with one big free block covering all of RAM
        self._blocks: List[MemoryBlock] = [
            MemoryBlock(start=0, size=total_size, pid=None, label="free")
        ]

        self._swapped_pids: dict = {}
        self.secure_locked: bool = True
        
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_UNLOCKED, self._unlock_secure_regions)
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_LOCKED, self._lock_secure_regions)
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_DISCONNECTED, self._lock_secure_regions)

        logger.info(f"[MEM] Initialized — {total_size} units, policy={policy}")

    # ── Internal Event Handlers ───────────────────────────────────

    def _unlock_secure_regions(self, payload):
        with self._lock:
            if self.secure_locked:
                self.secure_locked = False
                logger.info("[MEM] SECURE REGION UNLOCKED")

    def _lock_secure_regions(self, payload):
        with self._lock:
            if not self.secure_locked:
                self.secure_locked = True
                logger.warning("[MEM] SECURE REGION LOCKED")
                blocks_freed = 0
                for blk in self._blocks:
                    if blk.is_secure and not blk.is_free:
                        blk.pid = None
                        blk.label = "free"
                        blk.is_secure = False
                        blocks_freed += 1
                if blocks_freed:
                    MemoryAllocator.coalesce(self._blocks)

    # ── Public API ────────────────────────────────────────────────

    @property
    def policy(self) -> str:
        return self._policy

    @property
    def total_size(self) -> int:
        return self._total

    def set_policy(self, policy: str) -> None:
        p = policy.upper().replace(" ", "_")
        if p not in _VALID_POLICIES:
            raise ValueError(f"Unknown policy '{policy}'")
        with self._lock:
            self._policy = p
        logger.info(f"[MEM] Policy switched → {p}")

    def allocate(self, pid: int, size: int, label: str = "", is_secure: bool = False) -> Optional[MemoryBlock]:
        with self._lock:
            # 1. Quota Check
            quota = getattr(self, "_quota_per_pid", self._total // 4)
            current_usage = sum(blk.size for blk in self._blocks if blk.pid == pid)
            if current_usage + size > quota:
                logger.error(f"[MEM] QUOTA EXCEEDED (PID={pid})")
                return None

            if is_secure and self.secure_locked:
                logger.error(f"[MEM] ALLOC REJECTED — Secure region locked")
                return None

            # 2. Delegate Finding
            candidate_idx = MemoryAllocator.find_free_block(self, size)
            if candidate_idx is None:
                EVENT_BUS.emit(SystemEvent.MEMORY_FULL, {"pid": pid, "requested": size}, source="MemoryManager")
                return None

            # 3. Perform Split
            chosen = self._blocks[candidate_idx]
            allocated = MemoryBlock(chosen.start, size, pid, label or f"proc-{pid}", is_secure)
            self._blocks[candidate_idx] = allocated
            
            remainder_size = chosen.size - size
            if remainder_size > 0:
                self._blocks.insert(candidate_idx + 1, MemoryBlock(chosen.start + size, remainder_size))

            EVENT_BUS.emit(SystemEvent.MEMORY_ALLOCATED, {"pid": pid, "size": size}, source="MemoryManager")
            return allocated

    def deallocate(self, pid: int) -> int:
        with self._lock:
            bytes_freed = 0
            for blk in self._blocks:
                if blk.pid == pid:
                    bytes_freed += blk.size
                    blk.pid = None
                    blk.label = "free"
                    blk.is_secure = False
            
            if bytes_freed > 0:
                MemoryAllocator.coalesce(self._blocks)
                EVENT_BUS.emit(SystemEvent.MEMORY_FREED, {"pid": pid, "bytes_freed": bytes_freed}, source="MemoryManager")
            return bytes_freed

    def compact(self) -> int:
        with self._lock:
            return MemoryCompactor.compact(self)

    # ── Stats & Map ───────────────────────────────────────────────

    def get_memory_map(self) -> List[dict]:
        with self._lock:
            return [blk.as_dict() for blk in self._blocks]

    def total_free(self) -> int:
        with self._lock:
            return sum(blk.size for blk in self._blocks if blk.is_free)

    def total_used(self) -> int:
        return self._total - self.total_free()

    @property
    def stats(self) -> dict:
        used = self.total_used()
        free = self.total_free()
        with self._lock:
            free_blocks = [b.size for b in self._blocks if b.is_free]
            frag = 1.0 - (max(free_blocks) / free) if free_blocks and free > 0 else 0.0
            
        return {
            "policy": self._policy,
            "total": self._total,
            "used": used,
            "free": free,
            "utilization": round(used / self._total, 4),
            "fragmentation": round(frag, 4),
            "total_blocks": len(self._blocks)
        }

# ── Central Singleton ─────────────────────────────────────────────
MEMORY_MANAGER = MemoryManager()
