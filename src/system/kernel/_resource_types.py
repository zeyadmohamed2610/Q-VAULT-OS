from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Resource:
    """
    One simulated system resource (printer, lock, I/O device, …).
    """
    rid:       str
    name:      str
    total:     int
    available: int              = field(init=False)
    held_by:   List[int]        = field(default_factory=list)
    waited_by: List[int]        = field(default_factory=list)

    def __post_init__(self):
        self.available = self.total

    def as_dict(self) -> dict:
        return {
            "rid":       self.rid,
            "name":      self.name,
            "total":     self.total,
            "available": self.available,
            "held_by":   list(self.held_by),
            "waited_by": list(self.waited_by),
        }
