from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from core.event_bus import EVENT_BUS, EventPayload, SystemEvent

logger = logging.getLogger(__name__)


# ── Detection interval ────────────────────────────────────────────

_DETECT_INTERVAL: int = 10   # ticks between automatic detect() calls


# ── Resource ──────────────────────────────────────────────────────

@dataclass
class Resource:
    """
    One simulated system resource (printer, lock, I/O device, …).

    rid       : unique identifier  (e.g. "R1", "mutex_db")
    name      : human-readable label
    total     : total instances of this resource
    available : currently free instances
    held_by   : PIDs that currently hold ≥1 instance
    waited_by : PIDs blocked waiting for an instance
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


# ── DeadlockManager ───────────────────────────────────────────────

class DeadlockManager:
    """
    Deadlock detection and recovery engine.

    Maintains a Resource Allocation Graph (RAG) and runs DFS-based
    cycle detection.  All public methods are thread-safe (RLock).
    """

    def __init__(self, detect_interval: int = _DETECT_INTERVAL):
        self.resources: Dict[str, Resource] = {}
        self._detect_interval = detect_interval
        self._last_tick: int  = 0
        self._lock            = threading.RLock()
        self._subscribed      = False

        # Tracks how many units each pid holds per resource:
        #   _held[pid][rid] = count
        self._held: Dict[int, Dict[str, int]] = {}

        # Track process priorities for victim selection.
        # Populated when a process calls request() for the first time.
        # Can be seeded externally via set_priority().
        self._priority: Dict[int, int] = {}   # pid → priority (higher = more important)

        logger.info(
            f"[DLM] Initialized — detect_interval={detect_interval} ticks"
        )

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to CLOCK_TICK for automatic detection."""
        if self._subscribed:
            return
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK, self._on_clock_tick)
        self._subscribed = True
        logger.info("[DLM] Started — auto-detect every "
                    f"{self._detect_interval} ticks.")

    def stop(self) -> None:
        """Unsubscribe from CLOCK_TICK."""
        if not self._subscribed:
            return
        EVENT_BUS.unsubscribe(SystemEvent.CLOCK_TICK, self._on_clock_tick)
        self._subscribed = False
        logger.info("[DLM] Stopped.")

    # ── Resource management ───────────────────────────────────────

    def add_resource(self, rid: str, name: str, total: int) -> Resource:
        """
        Register a new resource with `total` available instances.
        Idempotent: calling again with the same rid returns existing resource.
        """
        if total <= 0:
            raise ValueError(f"total must be > 0, got {total}")
        with self._lock:
            if rid in self.resources:
                logger.debug(f"[DLM] Resource '{rid}' already exists — skipping.")
                return self.resources[rid]
            res = Resource(rid=rid, name=name, total=total)
            self.resources[rid] = res
        logger.info(f"[DLM] Resource added: {rid} ({name}) total={total}")
        return res

    def remove_resource(self, rid: str) -> bool:
        """Remove a resource. Returns False if rid unknown or still in use."""
        with self._lock:
            res = self.resources.get(rid)
            if res is None:
                return False
            if res.held_by or res.waited_by:
                logger.warning(
                    f"[DLM] Cannot remove '{rid}' — "
                    f"held_by={res.held_by} waited_by={res.waited_by}"
                )
                return False
            del self.resources[rid]
        logger.info(f"[DLM] Resource removed: {rid}")
        return True

    def set_priority(self, pid: int, priority: int) -> None:
        """
        Seed the process priority for victim selection.
        Higher value = more important = less likely to be chosen as victim.
        """
        with self._lock:
            self._priority[pid] = priority

    # ── Request / Release ─────────────────────────────────────────

    def request(self, pid: int, rid: str,
                priority: int = 5) -> bool:
        """
        Request one instance of resource `rid` for process `pid`.

        Returns
        -------
        True  — resource granted immediately
        False — resource unavailable; pid added to waited_by
        """
        with self._lock:
            res = self.resources.get(rid)
            if res is None:
                logger.error(f"[DLM] request: unknown resource '{rid}'")
                return False

            # Seed priority if not yet known
            self._priority.setdefault(pid, priority)

            if res.available > 0:
                # Grant immediately
                res.available -= 1
                if pid not in res.held_by:
                    res.held_by.append(pid)
                self._held.setdefault(pid, {})[rid] = \
                    self._held.get(pid, {}).get(rid, 0) + 1
                logger.debug(
                    f"[DLM] GRANTED  pid={pid} rid={rid} "
                    f"available={res.available}"
                )
                return True
            else:
                # Block: add to wait list
                if pid not in res.waited_by:
                    res.waited_by.append(pid)
                logger.debug(
                    f"[DLM] BLOCKED  pid={pid} waiting for rid={rid}"
                )
                return False

    def release(self, pid: int, rid: str) -> bool:
        """
        Release one instance of resource `rid` held by `pid`.
        Wakes up the first process in waited_by (if any).

        Returns True if the release was valid.
        """
        with self._lock:
            res = self.resources.get(rid)
            if res is None:
                logger.error(f"[DLM] release: unknown resource '{rid}'")
                return False

            if pid not in res.held_by:
                logger.warning(
                    f"[DLM] release: pid={pid} does not hold '{rid}'"
                )
                return False

            # Decrement held count
            held = self._held.get(pid, {})
            held[rid] = held.get(rid, 1) - 1
            if held[rid] <= 0:
                held.pop(rid, None)
                res.held_by.remove(pid)
            self._held[pid] = held

            res.available += 1

            # Wake the first waiter (FIFO)
            if res.waited_by and res.available > 0:
                next_pid = res.waited_by.pop(0)
                res.available -= 1
                if next_pid not in res.held_by:
                    res.held_by.append(next_pid)
                self._held.setdefault(next_pid, {})[rid] = \
                    self._held.get(next_pid, {}).get(rid, 0) + 1
                logger.debug(
                    f"[DLM] WOKE     pid={next_pid} granted rid={rid}"
                )

            logger.debug(
                f"[DLM] RELEASED pid={pid} rid={rid} "
                f"available={res.available}"
            )
            return True

    def release_all(self, pid: int) -> List[str]:
        """
        Release every resource held by `pid`.
        Returns the list of resource IDs that were released.
        Called by resolve_deadlock() during recovery.
        """
        with self._lock:
            rids = list(self._held.get(pid, {}).keys())

        freed = []
        for rid in rids:
            if self.release(pid, rid):
                freed.append(rid)

        # Also remove pid from any waited_by lists (unblock waiting)
        with self._lock:
            for res in self.resources.values():
                if pid in res.waited_by:
                    res.waited_by.remove(pid)
            self._held.pop(pid, None)
            self._priority.pop(pid, None)

        return freed

    # ── Detection ─────────────────────────────────────────────────

    def detect(self) -> List[List[int]]:
        """
        Run DFS cycle detection on the Resource Allocation Graph.

        Algorithm
        ---------
        1. Build a process→process wait-for graph:
             pid_A waits for pid_B  iff  pid_A is waiting for some
             resource that pid_B currently holds.
        2. Run iterative DFS from every unvisited node.
        3. Collect all back-edges → each back-edge defines a cycle.
        4. Extract minimal cycles using path tracing.

        Returns
        -------
        List[List[int]] — each inner list is one deadlock cycle of PIDs.
                          Empty list means no deadlock.
        """
        with self._lock:
            # Build wait-for graph: pid → set of pids it is waiting on
            wait_for: Dict[int, Set[int]] = {}
            for res in self.resources.values():
                for waiting_pid in res.waited_by:
                    for holding_pid in res.held_by:
                        if waiting_pid != holding_pid:
                            wait_for.setdefault(waiting_pid, set()).add(
                                holding_pid
                            )

        if not wait_for:
            return []

        cycles: List[List[int]] = []
        visited: Set[int] = set()
        rec_stack: List[int] = []    # current DFS path

        def dfs(node: int) -> None:
            visited.add(node)
            rec_stack.append(node)

            for neighbour in wait_for.get(node, set()):
                if neighbour not in visited:
                    dfs(neighbour)
                elif neighbour in rec_stack:
                    # Found a back-edge → extract the cycle
                    cycle_start = rec_stack.index(neighbour)
                    cycle = rec_stack[cycle_start:]
                    # Deduplicate cycles (order-independent)
                    cycle_key = frozenset(cycle)
                    if not any(frozenset(c) == cycle_key for c in cycles):
                        cycles.append(list(cycle))

            rec_stack.pop()

        for node in list(wait_for.keys()):
            if node not in visited:
                dfs(node)

        if cycles:
            logger.warning(
                f"[DLM] DEADLOCK DETECTED — "
                f"{len(cycles)} cycle(s): {cycles}"
            )
            for cycle in cycles:
                EVENT_BUS.emit(
                    SystemEvent.DEADLOCK_DETECTED,
                    data={
                        "cycle":      cycle,
                        "tick":       self._last_tick,
                        "cycle_size": len(cycle),
                        "rag":        self.get_rag(),
                    },
                    source="DeadlockManager",
                )

        return cycles

    # ── Recovery ──────────────────────────────────────────────────

    def resolve_deadlock(self, cycle: List[int]) -> Optional[int]:
        """
        Break a deadlock by terminating the victim process.

        Victim selection:
            Choose the process with the LOWEST priority value in the
            cycle.  Ties are broken by highest PID (newest process).
            This preserves the most important long-running processes.

        Steps
        -----
        1. Pick victim.
        2. release_all(victim) → free all held resources.
        3. Notify ProcessManager to terminate the victim.
        4. Emit DEADLOCK_RESOLVED.

        Returns
        -------
        int  — victim PID
        None — cycle is empty
        """
        if not cycle:
            return None

        with self._lock:
            # Lower priority number = less important = preferred victim
            victim = min(
                cycle,
                key=lambda p: (self._priority.get(p, 5), -p),
            )

        freed_rids = self.release_all(victim)

        # Best-effort: tell ProcessManager to kill the victim.
        # Import lazily to avoid circular imports at module load time.
        try:
            from kernel.process_manager import PM
            PM.kill(victim)
            logger.info(f"[DLM] KILL     pid={victim} via ProcessManager")
        except Exception as exc:
            logger.warning(
                f"[DLM] Could not kill pid={victim} via PM: {exc}"
            )

        logger.warning(
            f"[DLM] DEADLOCK RESOLVED — victim={victim} "
            f"freed={freed_rids} cycle={cycle}"
        )
        EVENT_BUS.emit(
            SystemEvent.DEADLOCK_RESOLVED,
            data={
                "victim":       victim,
                "cycle":        cycle,
                "freed_rids":   freed_rids,
                "tick":         self._last_tick,
            },
            source="DeadlockManager",
        )
        return victim

    def auto_resolve(self) -> List[int]:
        """
        Detect all deadlocks and resolve each one automatically.
        Returns the list of victim PIDs chosen.
        """
        victims = []
        cycles = self.detect()
        for cycle in cycles:
            victim = self.resolve_deadlock(cycle)
            if victim is not None:
                victims.append(victim)
        return victims

    # ── RAG visualization ─────────────────────────────────────────

    def get_rag(self) -> dict:
        """
        Return the Resource Allocation Graph in a format suitable for
        visualization (nodes + directed edges).

        Node types:  "process" | "resource"
        Edge types:  "request"  (process → resource, waiting)
                     "held"     (resource → process, allocated)
        """
        with self._lock:
            nodes = []
            edges = []

            # Resource nodes
            resource_pids: Set[int] = set()
            for res in self.resources.values():
                nodes.append({
                    "id":        f"R:{res.rid}",
                    "type":      "resource",
                    "label":     res.name,
                    "rid":       res.rid,
                    "total":     res.total,
                    "available": res.available,
                })
                for pid in res.held_by:
                    resource_pids.add(pid)
                    edges.append({
                        "from":  f"R:{res.rid}",
                        "to":    f"P:{pid}",
                        "type":  "held",
                        "label": "holds",
                    })
                for pid in res.waited_by:
                    resource_pids.add(pid)
                    edges.append({
                        "from":  f"P:{pid}",
                        "to":    f"R:{res.rid}",
                        "type":  "request",
                        "label": "waits",
                    })

            # Process nodes (only those involved in the RAG)
            for pid in resource_pids:
                nodes.append({
                    "id":       f"P:{pid}",
                    "type":     "process",
                    "label":    f"PID {pid}",
                    "pid":      pid,
                    "priority": self._priority.get(pid, 5),
                })

        return {"nodes": nodes, "edges": edges}

    # ── Query helpers ─────────────────────────────────────────────

    def get_resource_map(self) -> List[dict]:
        """Snapshot of all resources for UI panels."""
        with self._lock:
            return [r.as_dict() for r in self.resources.values()]

    @property
    def stats(self) -> dict:
        with self._lock:
            total_res  = len(self.resources)
            blocked    = set(
                pid for r in self.resources.values()
                for pid in r.waited_by
            )
            holding    = set(
                pid for r in self.resources.values()
                for pid in r.held_by
            )
        return {
            "total_resources":   total_res,
            "processes_holding": len(holding),
            "processes_blocked": len(blocked),
            "detect_interval":   self._detect_interval,
            "last_tick":         self._last_tick,
            "subscribed":        self._subscribed,
        }

    # ── Clock tick handler ────────────────────────────────────────

    def _on_clock_tick(self, payload: EventPayload) -> None:
        """Run detect() every `_detect_interval` ticks automatically."""
        tick = payload.data.get("tick", 0)
        self._last_tick = tick
        if tick > 0 and tick % self._detect_interval == 0:
            logger.debug(f"[DLM] Auto-detect at tick {tick}")
            self.auto_resolve()


# ── Central Singleton ─────────────────────────────────────────────
DEADLOCK_MANAGER = DeadlockManager(detect_interval=_DETECT_INTERVAL)
