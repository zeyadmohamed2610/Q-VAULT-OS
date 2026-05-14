from __future__ import annotations
import threading
from dataclasses import dataclass
from typing import List, Optional
from core.event_bus import EVENT_BUS

PAGE_SIZE: int = 64   # bytes per page/frame (simulation unit)

@dataclass
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
    Translates logical (virtual) addresses → physical addresses.
    """

    def __init__(self, total_frames: int = 64):
        self.total_frames    = total_frames
        self._frames: List[Optional[int]] = [None] * total_frames
        self._page_tables: dict = {}
        self._lock = threading.RLock()

    def map(self, pid: int, page: int, frame: int) -> None:
        """Map logical page → physical frame for pid."""
        with self._lock:
            if pid not in self._page_tables:
                self._page_tables[pid] = {}
            self._page_tables[pid][page] = PageTableEntry(page, frame)
            if 0 <= frame < self.total_frames:
                self._frames[frame] = pid

    def translate(self, pid: int, logical_addr: int) -> Optional[int]:
        """Translate logical address → physical address."""
        with self._lock:
            page   = logical_addr // PAGE_SIZE
            offset = logical_addr %  PAGE_SIZE
            pt     = self._page_tables.get(pid, {})
            entry  = pt.get(page)
            if entry is None or not entry.present:
                try:
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
        with self._lock:
            free = [i for i, owner in enumerate(self._frames) if owner is None]
            if len(free) < num_pages:
                return []
            allocated = free[:num_pages]
            for page, frame in enumerate(allocated):
                self.map(pid, page, frame)
            return allocated

    def free_frames(self, pid: int) -> None:
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
