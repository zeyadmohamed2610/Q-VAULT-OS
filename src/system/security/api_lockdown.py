import logging
from enum import Enum
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger("system.security.api_lockdown")

class LockdownLevel(Enum):
    NONE = 0      # Normal operations
    LEVEL_1 = 1   # Restricted high-risk calls
    LEVEL_2 = 2   # Critical lockdown (All write ops disabled)
    FULL = 3      # Total API severance (Emergency)

class APILockdown:
    """
    Sovereign API Lockdown Controller (Phase 18.3).
    Mediates access to SecureAPI endpoints during perceived threats.
    """
    def __init__(self):
        self._current_level = LockdownLevel.NONE
        
        # Subscribe to emergency events
        EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_LOCKED, self._on_system_locked)

    def set_level(self, level: LockdownLevel):
        self._current_level = level
        logger.warning(f"[Lockdown] API Security Level shifted to: {level.name}")
        
        if level == LockdownLevel.FULL:
            EVENT_BUS.emit(SystemEvent.SESSION_LOCKED, {"reason": "SECURITY_EMERGENCY"})

    def is_call_allowed(self, endpoint_name: str) -> bool:
        """Determines if a specific API call is permitted under current lockdown level."""
        if self._current_level == LockdownLevel.NONE:
            return True
            
        if self._current_level == LockdownLevel.FULL:
            return False
            
        # Example: Restricted endpoints in Level 1/2
        restricted = ["delete_secret", "change_password", "export_keys"]
        if self._current_level.value >= LockdownLevel.LEVEL_1.value:
            if endpoint_name in restricted:
                return False
                
        return True

    def _on_system_locked(self, payload):
        # Auto-reset to Level 1 when system is locked
        self.set_level(LockdownLevel.LEVEL_1)

# Global Singleton
API_LOCKDOWN = APILockdown()
