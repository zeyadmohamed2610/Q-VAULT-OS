import logging
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger("system.runtime.quarantine")

class QuarantineManager:
    """
    Sovereign Isolation Layer (Phase 17.1).
    Manages apps that have been flagged as 'suspicious' or 'untrusted'.
    """
    def __init__(self):
        self._quarantined_instances = set()

    def isolate(self, instance_id: str, reason: str):
        """Moves an application instance into the Quarantine state."""
        if instance_id not in self._quarantined_instances:
            self._quarantined_instances.add(instance_id)
            logger.critical(f"[Quarantine] ISOLATING {instance_id}. Reason: {reason}")
            
            # Notify the system to disable this app's network/API access
            EVENT_BUS.emit(SystemEvent.EVENT_APP_CRASHED, {
                "instance_id": instance_id, 
                "state": "QUARANTINED",
                "reason": reason
            })

    def is_isolated(self, instance_id: str) -> bool:
        return instance_id in self._quarantined_instances

    def release(self, instance_id: str):
        """Lifts the isolation after manual review."""
        if instance_id in self._quarantined_instances:
            self._quarantined_instances.remove(instance_id)
            logger.info(f"[Quarantine] RELEASED {instance_id}")

# Global Singleton
QUARANTINE = QuarantineManager()
