from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class MemoryBlock:
    """
    One contiguous region of simulated RAM.
    """
    start: int
    size: int
    pid:  Optional[int] = None
    label: str = "free"
    is_secure: bool = False

    @property
    def end(self) -> int:
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
