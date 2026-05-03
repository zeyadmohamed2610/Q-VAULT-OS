import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AIActionValidator:
    """
    Gatekeeper for AI actions.
    Implements a strict 'Allow List' and schema verification.
    """
    
    # Define safe actions and their required fields
    SAFE_ACTIONS = {
        "launch": ["app"],
        "close": ["id"],
        "notify": ["message"],
        "focus": ["id"]
    }

    # Dangerous target patterns
    RESTRICTED_TARGETS = ["security", "auth", "kernel", "admin"]

    # Governance Limits
    MAX_ACTIONS_PER_REQUEST = 5
    RATE_LIMIT_DELAY_MS = 200 # Minimum delay between AI actions
    
    _last_action_time = 0
    _action_chain_count = 0

    @classmethod
    def validate(cls, action_type: str, params: Dict[str, Any], is_chain=False) -> Tuple[bool, str]:
        """
        Validates an AI decision before it hits the EventBus.
        Returns (is_safe, reasoning).
        """
        import time
        now = time.time()
        
        # 0. Chain & Rate Limiting
        if not is_chain:
            cls._action_chain_count = 0 # Reset on new user request
            
        cls._action_chain_count += 1
        if cls._action_chain_count > cls.MAX_ACTIONS_PER_REQUEST:
            return False, f"Loop detected: Maximum actions ({cls.MAX_ACTIONS_PER_REQUEST}) exceeded for this request."

        # Minimum delay between automated actions to prevent flooding
        dt = (now - cls._last_action_time) * 1000
        if dt < cls.RATE_LIMIT_DELAY_MS:
            return False, f"Rate limited: Actions are too frequent ({int(dt)}ms < {cls.RATE_LIMIT_DELAY_MS}ms)"
        
        cls._last_action_time = now

        # 1. Check Action Type
        # 1. Check Action Type
        if action_type not in cls.SAFE_ACTIONS:
            return False, f"Unknown or restricted action type: {action_type}"
            
        # 2. Check Required Params
        required = cls.SAFE_ACTIONS[action_type]
        for param in required:
            if param not in params or params[param] is None:
                return False, f"Missing required parameter '{param}' for action '{action_type}'"

        # 3. Security Check: Block restricted targets
        if action_type == "launch":
            app_name = str(params["app"]).lower()
            if any(restricted in app_name for restricted in cls.RESTRICTED_TARGETS):
                return False, f"Access denied: '{app_name}' is a restricted system component."

        # 4. Context Check: Prevent empty actions
        if action_type == "close" and not params["id"]:
            return False, "Action rejected: No target window ID provided."

        return True, "Safe"
