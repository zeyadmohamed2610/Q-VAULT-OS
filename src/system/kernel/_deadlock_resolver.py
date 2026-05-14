from __future__ import annotations
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .deadlock_manager import DeadlockManager

logger = logging.getLogger(__name__)

class DeadlockResolver:
    """
    Handles victim selection and deadlock resolution.
    """

    @staticmethod
    def resolve(manager: 'DeadlockManager', cycle: List[int]) -> Optional[int]:
        """
        Break a deadlock by terminating the victim process.
        """
        from core.event_bus import EVENT_BUS, SystemEvent
        
        if not cycle:
            return None

        # Lower priority number = preferred victim
        victim = min(
            cycle,
            key=lambda p: (manager._priority.get(p, 5), -p),
        )

        freed_rids = manager.release_all(victim)

        # Signal ProcessManager
        try:
            from system.kernel.process_manager import PM
            PM.kill(victim)
            logger.info(f"[DLM] KILL pid={victim} via ProcessManager")
        except Exception as exc:
            logger.warning(f"[DLM] Could not kill pid={victim} via PM: {exc}")

        logger.warning(f"[DLM] DEADLOCK RESOLVED — victim={victim} freed={freed_rids}")
        
        EVENT_BUS.emit(
            SystemEvent.DEADLOCK_RESOLVED,
            data={
                "victim":       victim,
                "cycle":        cycle,
                "freed_rids":   freed_rids,
                "tick":         manager._last_tick,
            },
            source="DeadlockManager",
        )
        return victim
