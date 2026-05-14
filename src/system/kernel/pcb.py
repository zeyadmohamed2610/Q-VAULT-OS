"""
kernel/pcb.py — Q-Vault OS
Process Control Block — the kernel's complete record of one process.
Fields cover: identity, CPU context, scheduling, memory, I/O, multicore, accounting.

OS Theory:
  PCB is the core data structure of every OS.
  Context switch = save current PCB + restore next PCB.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PCB:
    """
    Process Control Block — every field the OS needs to manage a process.
    """
    # ── Identity ─────────────────────────────────────────────────
    pid:             int
    name:            str
    owner:           str            # username owning this process

    # ── State ────────────────────────────────────────────────────
    state:           str = "new"    # new|ready|running|waiting|terminated

    # ── Security ─────────────────────────────────────────────────
    requires_secure_token: bool = False

    # ── CPU Context (saved on context switch out) ─────────────────
    program_counter: int                = 0
    saved_registers: Dict[str, int]     = field(default_factory=lambda: {
        "ax": 0, "bx": 0, "cx": 0, "dx": 0,
        "sp": 0, "bp": 0, "si": 0, "di": 0,
    })

    # ── Scheduling fields ─────────────────────────────────────────
    priority:        int   = 5      # 1 (low) – 10 (high)
    burst_time:      int   = 0      # total CPU ticks needed
    remaining_time:  int   = 0      # burst_time minus ticks executed
    arrival_tick:    int   = 0      # tick process entered READY queue
    waiting_time:    int   = 0      # total ticks in READY state
    turnaround_time: int   = 0      # waiting_time + burst_time

    # ── Memory ───────────────────────────────────────────────────
    memory_base:     int              = 0
    memory_limit:    int              = 0
    page_table:      Dict[int, int]   = field(default_factory=dict)
    swapped_out:     bool             = False

    # ── I/O ──────────────────────────────────────────────────────
    io_request:      Optional[str]    = None
    io_remaining:    int              = 0

    # ── Multicore ────────────────────────────────────────────────
    cpu_id:          int   = -1     # -1 = not on any core
    preferred_core:  int   = -1     # affinity hint (-1 = no preference)

    # ── Accounting ───────────────────────────────────────────────
    cpu_time:        float = 0.0
    created_at:      float = field(default_factory=time.time)

    # ── Context switch ────────────────────────────────────────────

    def save_context(self, registers: dict, pc: int) -> None:
        """Save CPU registers + PC on context switch OUT."""
        self.saved_registers = dict(registers)
        self.program_counter = pc

    def restore_context(self) -> tuple[dict, int]:
        """Return saved registers and PC on context switch IN."""
        return dict(self.saved_registers), self.program_counter

    def as_dict(self) -> dict:
        return {
            "pid":             self.pid,
            "name":            self.name,
            "owner":           self.owner,
            "state":           self.state,
            "priority":        self.priority,
            "burst_time":      self.burst_time,
            "remaining_time":  self.remaining_time,
            "waiting_time":    self.waiting_time,
            "turnaround_time": self.turnaround_time,
            "memory_base":     self.memory_base,
            "memory_limit":    self.memory_limit,
            "cpu_id":          self.cpu_id,
            "swapped_out":     self.swapped_out,
            "program_counter": self.program_counter,
            "requires_secure_token": self.requires_secure_token,
        }

    def __repr__(self) -> str:
        return f"PCB(pid={self.pid}, name={self.name!r}, state={self.state}, prio={self.priority})"
