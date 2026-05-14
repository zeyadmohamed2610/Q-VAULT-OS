from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Set

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from ._resource_types import Resource
from ._deadlock_detector import DeadlockDetector
from ._deadlock_resolver import DeadlockResolver

logger = logging.getLogger(__name__)

_DETECT_INTERVAL: int = 10

class DeadlockManager:
    """
    Deadlock detection and recovery engine (Refactored v5).
    Facade over specialized detector and resolver helpers.
    """

    def __init__(self, detect_interval: int = _DETECT_INTERVAL):
        self.resources: Dict[str, Resource] = {}
        self._detect_interval = detect_interval
        self._last_tick: int  = 0
        self._lock            = threading.RLock()
        self._subscribed      = False
        
        self._held: Dict[int, Dict[str, int]] = {}
        self._priority: Dict[int, int] = {}
        self._base_priority: Dict[int, int] = {}

        logger.info(f"[DLM] Initialized — interval={detect_interval} ticks")

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        if self._subscribed: return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK,    self._on_clock_tick)
        EVENT_BUS.subscribe(SystemEvent.PROC_STOPPED,   self._on_proc_death)
        EVENT_BUS.subscribe(SystemEvent.PROC_COMPLETED, self._on_proc_death)
        self._subscribed = True

    def stop(self) -> None:
        if not self._subscribed: return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK,    self._on_clock_tick)
        EVENT_BUS.unsubscribe(SystemEvent.PROC_STOPPED,   self._on_proc_death)
        EVENT_BUS.unsubscribe(SystemEvent.PROC_COMPLETED, self._on_proc_death)
        self._subscribed = False

    def _on_proc_death(self, payload: EventPayload) -> None:
        pid = payload.data.get("pid")
        if pid is not None:
            self.release_all(pid)

    # ── Resource Management ───────────────────────────────────────

    def add_resource(self, rid: str, name: str, total: int) -> Resource:
        with self._lock:
            if rid not in self.resources:
                self.resources[rid] = Resource(rid=rid, name=name, total=total)
            return self.resources[rid]

    def remove_resource(self, rid: str) -> bool:
        with self._lock:
            res = self.resources.get(rid)
            if res and not (res.held_by or res.waited_by):
                del self.resources[rid]
                return True
            return False

    def request(self, pid: int, rid: str, priority: int = 5) -> bool:
        with self._lock:
            res = self.resources.get(rid)
            if not res: return False

            if pid not in self._base_priority:
                self._base_priority[pid] = priority
                self._priority[pid] = priority

            if res.available > 0:
                res.available -= 1
                if pid not in res.held_by: res.held_by.append(pid)
                self._held.setdefault(pid, {})[rid] = self._held.get(pid, {}).get(rid, 0) + 1
                return True
            else:
                if pid not in res.waited_by: res.waited_by.append(pid)
                # Priority Inheritance
                req_prio = self._priority.get(pid, priority)
                for holder in res.held_by:
                    if req_prio > self._priority.get(holder, 5):
                        self._priority[holder] = req_prio
                return False

    def release(self, pid: int, rid: str) -> bool:
        with self._lock:
            res = self.resources.get(rid)
            if not res or pid not in res.held_by: return False

            held = self._held.get(pid, {})
            held[rid] = held.get(rid, 1) - 1
            if held[rid] <= 0:
                held.pop(rid, None)
                res.held_by.remove(pid)
            res.available += 1
            
            if pid in self._base_priority:
                self._priority[pid] = self._base_priority[pid]

            if res.waited_by and res.available > 0:
                nxt = res.waited_by.pop(0)
                res.available -= 1
                if nxt not in res.held_by: res.held_by.append(nxt)
                self._held.setdefault(nxt, {})[rid] = self._held.get(nxt, {}).get(rid, 0) + 1
            return True

    def release_all(self, pid: int) -> List[str]:
        with self._lock:
            rids = list(self._held.get(pid, {}).keys())
            freed = [rid for rid in rids if self.release(pid, rid)]
            for res in self.resources.values():
                if pid in res.waited_by: res.waited_by.remove(pid)
            self._held.pop(pid, None)
            self._priority.pop(pid, None)
            self._base_priority.pop(pid, None)
            return freed

    # ── Detection & Resolution ────────────────────────────────────

    def detect(self) -> List[List[int]]:
        with self._lock:
            return DeadlockDetector.detect(self)

    def resolve_deadlock(self, cycle: List[int]) -> Optional[int]:
        with self._lock:
            return DeadlockResolver.resolve(self, cycle)

    def auto_resolve(self) -> List[int]:
        cycles = self.detect()
        return [self.resolve_deadlock(c) for c in cycles if c]

    # ── Observability ─────────────────────────────────────────────

    def get_rag(self) -> dict:
        with self._lock:
            nodes, edges = [], []
            pids: Set[int] = set()
            for res in self.resources.values():
                nodes.append({"id": f"R:{res.rid}", "type": "resource", "label": res.name})
                for p in res.held_by:
                    pids.add(p)
                    edges.append({"from": f"R:{res.rid}", "to": f"P:{p}", "type": "held"})
                for p in res.waited_by:
                    pids.add(p)
                    edges.append({"from": f"P:{p}", "to": f"R:{res.rid}", "type": "request"})
            for p in pids:
                nodes.append({"id": f"P:{p}", "type": "process", "label": f"PID {p}"})
            return {"nodes": nodes, "edges": edges}

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "total_resources": len(self.resources),
                "detect_interval": self._detect_interval,
                "last_tick": self._last_tick
            }

    def _on_clock_tick(self, payload: EventPayload) -> None:
        tick = payload.data.get("tick", 0)
        self._last_tick = tick
        if tick > 0 and tick % self._detect_interval == 0:
            self.auto_resolve()

# ── Singleton ─────────────────────────────────────────────────────
DEADLOCK_MANAGER = DeadlockManager()
