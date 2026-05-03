from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional

from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)


# ── Policy identifiers ────────────────────────────────────────────

POLICY_FIRST_FIT = "FIRST_FIT"
POLICY_BEST_FIT  = "BEST_FIT"
POLICY_WORST_FIT = "WORST_FIT"

_VALID_POLICIES = {POLICY_FIRST_FIT, POLICY_BEST_FIT, POLICY_WORST_FIT}

_DEFAULT_RAM_SIZE = 1024   # units


# ── MemoryBlock ───────────────────────────────────────────────────

@dataclass
class MemoryBlock:
    """
    One contiguous region of simulated RAM.

    start : int           — base address (0-based, inclusive)
    size  : int           — length in memory units
    pid   : Optional[int] — owning process; None = free
    label : str           — human-readable tag (e.g. "proc-42" or "free")
    """
    start: int
    size: int
    pid:  Optional[int] = None
    label: str = "free"
    is_secure: bool = False

    # ── Derived helpers ──────────────────────────────────────────

    @property
    def end(self) -> int:
        """Exclusive end address: start + size."""
        return self.start + self.size

    @property
    def is_free(self) -> bool:
        return self.pid is None

    def as_dict(self) -> dict:
        return {
            "start": self.start,
            "end":   self.end,
            "size":  self.size,
            "pid":   self.pid,
            "label": self.label,
            "free":  self.is_free,
            "is_secure": self.is_secure,
        }

    def __repr__(self) -> str:
        tag = self.label if not self.is_free else "FREE"
        return f"MemoryBlock({self.start}–{self.end - 1}, {tag}, {self.size}u)"


# ── MemoryManager ─────────────────────────────────────────────────

class MemoryManager:
    """
    Simulated flat-address RAM manager.

    RAM is represented as an ordered list of MemoryBlock objects.
    Blocks are kept sorted by start address at all times.
    Adjacent free blocks are coalesced after every deallocation.

    Thread safety:
        All public methods acquire self._lock (RLock) before mutating
        the block list, so they are safe to call from any thread.
    """

    def __init__(
        self,
        total_size: int = _DEFAULT_RAM_SIZE,
        policy: str = POLICY_FIRST_FIT,
    ):
        if total_size <= 0:
            raise ValueError(f"total_size must be > 0, got {total_size}")
        if policy not in _VALID_POLICIES:
            raise ValueError(f"Unknown policy '{policy}'")

        self._total: int = total_size
        self._policy: str = policy
        self._lock = threading.RLock()

        # Start with one big free block covering all of RAM
        self._blocks: List[MemoryBlock] = [
            MemoryBlock(start=0, size=total_size, pid=None, label="free")
        ]

        self._swapped_pids: dict = {}   # pid → {"size": int, "label": str}
        
        # ── QVault Hardware Integration (Secure RAM) ──
        self.secure_locked: bool = True
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_UNLOCKED, self._unlock_secure_regions)
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_LOCKED, self._lock_secure_regions)
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_DISCONNECTED, self._lock_secure_regions)

        logger.info(
            f"[MEM] Initialized — {total_size} units, policy={policy}"
        )

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
                # When locked, we force-free any secure allocations
                blocks_freed = 0
                for blk in self._blocks:
                    if blk.is_secure and not blk.is_free:
                        logger.warning(f"[MEM] Purging secure block {blk.label} (PID={blk.pid})")
                        blk.pid = None
                        blk.label = "free"
                        blk.is_secure = False
                        blocks_freed += 1
                if blocks_freed:
                    self._coalesce()

    # ── Policy API ────────────────────────────────────────────────

    @property
    def policy(self) -> str:
        return self._policy

    def set_policy(self, policy: str) -> None:
        """
        Hot-swap the allocation policy.
        Takes effect on the next allocate() call.
        Accepts: "FIRST_FIT", "BEST_FIT", "WORST_FIT"
        """
        p = policy.upper().replace(" ", "_")
        if p not in _VALID_POLICIES:
            raise ValueError(
                f"Unknown policy '{policy}'. Valid: {sorted(_VALID_POLICIES)}"
            )
        with self._lock:
            old, self._policy = self._policy, p
        logger.info(f"[MEM] Policy switched: {old} → {p}")

    # ── Core allocation API ───────────────────────────────────────

    def allocate(self, pid: int, size: int, label: str = "", is_secure: bool = False) -> Optional[MemoryBlock]:
        """
        Find a free block for `pid` using the active policy.

        Parameters
        ----------
        pid   : process ID that will own the block
        size  : number of memory units required (must be > 0)
        label : optional human-readable tag (defaults to "proc-<pid>")

        Returns
        -------
        MemoryBlock  — the allocated block on success
        None         — if no contiguous free region is large enough
                       (also emits MEMORY_FULL)
        """
        if size <= 0:
            raise ValueError(f"size must be > 0, got {size}")

        tag = label or f"proc-{pid}"

        with self._lock:
            if is_secure and self.secure_locked:
                logger.error(f"[MEM] ALLOC REJECTED — Secure region is locked (PID={pid})")
                return None

            candidate_idx = self._find_free_block(size)

            if candidate_idx is None:
                free = self.total_free()
                logger.warning(
                    f"[MEM] FULL — PID {pid} requested {size}u, "
                    f"only {free}u free (policy={self._policy})"
                )
                EVENT_BUS.emit(
                    SystemEvent.MEMORY_FULL,
                    data={
                        "pid":       pid,
                        "requested": size,
                        "available": free,
                        "policy":    self._policy,
                    },
                    source="MemoryManager",
                )
                return None

            # Split the chosen free block
            chosen = self._blocks[candidate_idx]
            allocated = MemoryBlock(
                start=chosen.start,
                size=size,
                pid=pid,
                label=tag,
                is_secure=is_secure,
            )

            remainder_size = chosen.size - size
            # Replace the old block with the new allocated one
            self._blocks[candidate_idx] = allocated

            if remainder_size > 0:
                # Insert the leftover free fragment right after
                remainder = MemoryBlock(
                    start=chosen.start + size,
                    size=remainder_size,
                    pid=None,
                    label="free",
                )
                self._blocks.insert(candidate_idx + 1, remainder)

        logger.info(
            f"[MEM] ALLOC  — PID {pid} | {size}u @ {allocated.start} "
            f"(policy={self._policy})"
        )
        EVENT_BUS.emit(
            SystemEvent.MEMORY_ALLOCATED,
            data={
                "pid":    pid,
                "start":  allocated.start,
                "size":   size,
                "label":  tag,
                "policy": self._policy,
                "free":   self.total_free(),
                "used":   self.total_used(),
            },
            source="MemoryManager",
        )
        return allocated

    def deallocate(self, pid: int) -> int:
        """
        Free ALL blocks owned by `pid`.

        Returns
        -------
        int — number of units freed (0 if pid had no allocations)
        """
        with self._lock:
            blocks_freed = 0
            bytes_freed  = 0

            for blk in self._blocks:
                if blk.pid == pid:
                    blk.pid   = None
                    blk.label = "free"
                    blocks_freed += 1
                    bytes_freed  += blk.size

            if blocks_freed:
                self._coalesce()

        if blocks_freed == 0:
            logger.debug(f"[MEM] DEALLOC — PID {pid} had no allocations.")
            return 0

        logger.info(
            f"[MEM] FREE   — PID {pid} | {bytes_freed}u freed "
            f"({blocks_freed} block(s))"
        )
        EVENT_BUS.emit(
            SystemEvent.MEMORY_FREED,
            data={
                "pid":          pid,
                "blocks_freed": blocks_freed,
                "bytes_freed":  bytes_freed,
                "free":         self.total_free(),
                "used":         self.total_used(),
            },
            source="MemoryManager",
        )
        return bytes_freed

    # Compatibility alias used by stress test suite
    def free(self, pid: int) -> int:
        """Alias for deallocate()."""
        return self.deallocate(pid)

    # ── Query API ─────────────────────────────────────────────────

    def get_memory_map(self) -> List[dict]:
        """
        Return a snapshot of the full block list for UI visualization.
        Each dict is the result of MemoryBlock.as_dict().
        """
        with self._lock:
            return [blk.as_dict() for blk in self._blocks]

    def get_fragmentation_ratio(self) -> float:
        """
        External fragmentation ratio:
            1 - (largest_free_block / total_free)

        Returns 0.0 when RAM is fully free or no free blocks exist.
        Values near 1.0 indicate severe fragmentation.
        """
        with self._lock:
            free_blocks = [blk.size for blk in self._blocks if blk.is_free]

        if not free_blocks:
            return 0.0

        total = sum(free_blocks)
        if total == 0:
            return 0.0

        largest = max(free_blocks)
        return round(1.0 - (largest / total), 6)

    def total_free(self) -> int:
        """Total free memory units across all free blocks."""
        with self._lock:
            return sum(blk.size for blk in self._blocks if blk.is_free)

    def total_used(self) -> int:
        """Total allocated memory units."""
        return self._total - self.total_free()

    @property
    def total_size(self) -> int:
        """Total RAM capacity in units."""
        return self._total

    @property
    def stats(self) -> dict:
        """Observability snapshot for debug / UI widgets."""
        frag = self.get_fragmentation_ratio()
        free = self.total_free()
        used = self.total_used()
        with self._lock:
            num_free_blocks  = sum(1 for b in self._blocks if b.is_free)
            num_alloc_blocks = sum(1 for b in self._blocks if not b.is_free)
        return {
            "policy":            self._policy,
            "total":             self._total,
            "used":              used,
            "free":              free,
            "utilization":       round(used / self._total, 4),
            "fragmentation":     frag,
            "num_free_blocks":   num_free_blocks,
            "num_alloc_blocks":  num_alloc_blocks,
            "total_blocks":      num_free_blocks + num_alloc_blocks,
        }

    # ── Internal helpers ──────────────────────────────────────────

    def _find_free_block(self, size: int) -> Optional[int]:
        """
        Return the *index* into self._blocks of the chosen free block,
        or None if no suitable block exists.

        Called with self._lock already held.
        """
        candidates = [
            (i, blk) for i, blk in enumerate(self._blocks)
            if blk.is_free and blk.size >= size
        ]
        if not candidates:
            return None

        if self._policy == POLICY_FIRST_FIT:
            # Lowest start address that fits (list is sorted by start)
            return candidates[0][0]

        elif self._policy == POLICY_BEST_FIT:
            # Smallest block that still fits → minimum wasted space
            return min(candidates, key=lambda x: x[1].size)[0]

        elif self._policy == POLICY_WORST_FIT:
            # Largest block available → leaves biggest possible remainder
            return max(candidates, key=lambda x: x[1].size)[0]

        # Unreachable; fallback to first-fit
        return candidates[0][0]


    # ── Compaction ─────────────────────────────────────────────────

    def compact(self) -> int:
        """
        Compaction: move all allocated blocks together to eliminate
        external fragmentation. Returns bytes recovered.

        OS Theory: Compaction = defragmentation for contiguous allocation.
        """
        with self._lock:
            allocated = [b for b in self._blocks if not b.is_free]
            holes     = [b for b in self._blocks if b.is_free]
            if not holes:
                return 0

            recovered = sum(b.size for b in holes)
            cursor    = 0
            new_blocks = []
            for blk in allocated:
                blk.start = cursor
                cursor    += blk.size
                new_blocks.append(blk)

            if cursor < self._total:
                new_blocks.append(MemoryBlock(
                    start=cursor, size=self._total - cursor,
                    pid=None, label="free"
                ))

            self._blocks = new_blocks
            try:
                from core.event_bus import EVENT_BUS
                EVENT_BUS.emit("memory.compacted",
                               {"recovered_bytes": recovered})
            except Exception:
                pass
            logger.info("[MEMORY] Compacted: recovered %d bytes", recovered)
            return recovered

    # ── Swapping ───────────────────────────────────────────────────

    def swap_out(self, pid: int) -> bool:
        """
        Swap process OUT of RAM (free its block, mark as swapped).
        OS Theory: Allows overcommitting RAM by moving inactive
        processes to disk storage temporarily.
        """
        with self._lock:
            block = next((b for b in self._blocks if b.pid == pid), None)
            if block is None:
                return False
            self._swapped_pids[pid] = {"size": block.size, "label": block.label}
            block.pid   = None
            block.label = "free"
            self._coalesce()
            try:
                from core.event_bus import EVENT_BUS
                EVENT_BUS.emit("memory.swap_out",
                               {"pid": pid, "size": block.size})
            except Exception:
                pass
            logger.info("[MEMORY] Swap OUT: pid=%d (%d bytes freed)", pid, block.size)
            return True

    def swap_in(self, pid: int):
        """
        Swap process back INTO RAM. Re-allocates using current policy.
        """
        with self._lock:
            info = self._swapped_pids.pop(pid, None)
            if info is None:
                return None
            block = self.allocate(pid, info["size"], info["label"])
            if block:
                try:
                    from core.event_bus import EVENT_BUS
                    EVENT_BUS.emit("memory.swap_in", {"pid": pid})
                except Exception:
                    pass
                logger.info("[MEMORY] Swap IN: pid=%d", pid)
            else:
                logger.warning("[MEMORY] Swap IN failed (no space): pid=%d", pid)
                self._swapped_pids[pid] = info   # put back
            return block

    def get_swapped(self) -> list:
        """Return list of processes currently swapped to disk."""
        return [{"pid": pid, **info} for pid, info in self._swapped_pids.items()]

    def _coalesce(self) -> None:
        """
        Merge adjacent free blocks into single larger ones.
        This eliminates false fragmentation after deallocations.

        Called with self._lock already held.
        Blocks must already be sorted by start address.
        """
        merged: List[MemoryBlock] = []
        for blk in self._blocks:
            if merged and merged[-1].is_free and blk.is_free:
                # Extend the last free block instead of appending
                merged[-1] = MemoryBlock(
                    start=merged[-1].start,
                    size=merged[-1].size + blk.size,
                    pid=None,
                    label="free",
                )
            else:
                merged.append(blk)
        self._blocks = merged




# =============================================================
# PAGING + MMU SIMULATION
# =============================================================
from dataclasses import dataclass as _dc, field as _fld
from typing import List as _List, Optional as _Opt

PAGE_SIZE: int = 64   # bytes per page/frame (simulation unit)


@_dc
class PageTableEntry:
    """One row in a process page table."""
    page_number:  int
    frame_number: int           # physical frame; -1 = not mapped
    present:      bool = True
    dirty:        bool = False

    def as_dict(self) -> dict:
        return {
            "page":    self.page_number,
            "frame":   self.frame_number,
            "present": self.present,
            "dirty":   self.dirty,
        }


class MMU:
    """
    Memory Management Unit (simulation).

    Translates logical (virtual) addresses → physical addresses
    via per-process page tables.

    logical_address  = page_number * PAGE_SIZE + offset
    physical_address = frame_number * PAGE_SIZE + offset

    Page fault emitted when page not present.
    """

    def __init__(self, total_frames: int = 64):
        import threading as _thr
        self.total_frames    = total_frames
        self._frames: _List[_Opt[int]] = [None] * total_frames
        self._page_tables: dict = {}
        self._lock = _thr.RLock()

    def map(self, pid: int, page: int, frame: int) -> None:
        """Map logical page → physical frame for pid."""
        with self._lock:
            if pid not in self._page_tables:
                self._page_tables[pid] = {}
            self._page_tables[pid][page] = PageTableEntry(page, frame)
            if 0 <= frame < self.total_frames:
                self._frames[frame] = pid

    def translate(self, pid: int, logical_addr: int) -> _Opt[int]:
        """
        Translate logical address → physical address.
        Returns None on page fault.
        """
        with self._lock:
            page   = logical_addr // PAGE_SIZE
            offset = logical_addr %  PAGE_SIZE
            pt     = self._page_tables.get(pid, {})
            entry  = pt.get(page)
            if entry is None or not entry.present:
                try:
                    from core.event_bus import EVENT_BUS
                    EVENT_BUS.emit("memory.page_fault",
                                   {"pid": pid, "page": page, "logical": logical_addr})
                except Exception:
                    pass
                return None
            return entry.frame_number * PAGE_SIZE + offset

    def get_page_table(self, pid: int) -> list:
        with self._lock:
            return [e.as_dict() for e in self._page_tables.get(pid, {}).values()]

    def allocate_frames(self, pid: int, num_pages: int) -> list:
        """Allocate num_pages free frames for pid. Returns frame numbers."""
        with self._lock:
            free = [i for i, owner in enumerate(self._frames) if owner is None]
            if len(free) < num_pages:
                return []
            allocated = free[:num_pages]
            for page, frame in enumerate(allocated):
                self.map(pid, page, frame)
            return allocated

    def free_frames(self, pid: int) -> None:
        """Release all frames owned by pid."""
        with self._lock:
            self._frames = [None if owner == pid else owner
                            for owner in self._frames]
            self._page_tables.pop(pid, None)

    def memory_map(self) -> list:
        with self._lock:
            return [{"frame": i, "pid": owner, "free": owner is None}
                    for i, owner in enumerate(self._frames)]

    def stats(self) -> dict:
        with self._lock:
            used = sum(1 for f in self._frames if f is not None)
            return {
                "total_frames": self.total_frames,
                "used_frames":  used,
                "free_frames":  self.total_frames - used,
                "utilization":  round(used / self.total_frames, 3),
            }


MMU_INSTANCE = MMU(total_frames=64)

# ── Central Singleton ─────────────────────────────────────────────
MEMORY_MANAGER = MemoryManager(
    total_size=_DEFAULT_RAM_SIZE,
    policy=POLICY_FIRST_FIT,
)
