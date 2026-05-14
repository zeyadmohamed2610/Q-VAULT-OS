import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CommandDispatcher:
    """
    Sovereign Command Dispatcher.
    Routes @prefixed commands to registered handlers (plugins or core services).
    """
    def __init__(self):
        self._handlers: Dict[str, Any] = {}

    def register_handler(self, prefix: str, handler: Any):
        """Register a handler for a specific command prefix (e.g., '@git')."""
        if not prefix.startswith("@"):
            prefix = "@" + prefix
        self._handlers[prefix] = handler
        logger.info(f"[DISPATCHER] Registered handler for {prefix}: {type(handler).__name__}")

    def dispatch(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Route the command to the appropriate handler."""
        params = params or {}
        parts = command.split()
        if not parts:
            return {"success": False, "output": "Empty command", "summary": "Error"}
            
        prefix = parts[0]
        if prefix in self._handlers:
            try:
                return self._handlers[prefix].execute(command, params)
            except Exception as e:
                logger.error(f"[DISPATCHER] Execution failed for {command}: {e}")
                return {"success": False, "output": str(e), "summary": "Dispatch Error"}
        
        return {"success": False, "output": f"No handler for {prefix}", "summary": "Unknown Command"}

# Global Singleton
COMMAND_DISPATCHER = CommandDispatcher()
