from __future__ import annotations
import logging
from typing import List, Set, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .deadlock_manager import DeadlockManager

logger = logging.getLogger(__name__)

class DeadlockDetector:
    """
    RAG (Resource Allocation Graph) cycle detection logic.
    """

    @staticmethod
    def detect(manager: 'DeadlockManager') -> List[List[int]]:
        """
        Run DFS cycle detection on the Resource Allocation Graph.
        """
        from core.event_bus import EVENT_BUS, SystemEvent
        
        # Build wait-for graph: pid → set of pids it is waiting on
        wait_for: Dict[int, Set[int]] = {}
        for res in manager.resources.values():
            for waiting_pid in res.waited_by:
                for holding_pid in res.held_by:
                    if waiting_pid != holding_pid:
                        wait_for.setdefault(waiting_pid, set()).add(holding_pid)

        if not wait_for:
            return []

        cycles: List[List[int]] = []
        visited: Set[int] = set()
        rec_stack: List[int] = []

        def dfs(node: int) -> None:
            visited.add(node)
            rec_stack.append(node)

            for neighbour in wait_for.get(node, set()):
                if neighbour not in visited:
                    dfs(neighbour)
                elif neighbour in rec_stack:
                    # Found cycle
                    cycle_start = rec_stack.index(neighbour)
                    cycle = rec_stack[cycle_start:]
                    cycle_key = frozenset(cycle)
                    if not any(frozenset(c) == cycle_key for c in cycles):
                        cycles.append(list(cycle))

            rec_stack.pop()

        for node in list(wait_for.keys()):
            if node not in visited:
                dfs(node)

        if cycles:
            logger.warning(f"[DLM] DEADLOCK DETECTED — {len(cycles)} cycle(s): {cycles}")
            for cycle in cycles:
                EVENT_BUS.emit(
                    SystemEvent.DEADLOCK_DETECTED,
                    data={
                        "cycle": cycle,
                        "tick": manager._last_tick,
                        "cycle_size": len(cycle),
                        "rag": manager.get_rag(),
                    },
                    source="DeadlockManager",
                )

        return cycles
