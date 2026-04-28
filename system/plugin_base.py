import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PluginAction:
    """Represents a discrete action a plugin can perform."""
    def __init__(self, action_id: str, description: str, is_sensitive: bool = False):
        self.action_id = action_id
        self.description = description
        self.is_sensitive = is_sensitive

class BasePlugin(ABC):
    """
    Abstract Base Class for all Q-Vault Plugins.
    v3.1 'Execution Partner' Framework.
    """
    def __init__(self):
        self.plugin_id = self.__class__.__name__.lower()
        self.is_active = False

    @abstractmethod
    def on_activate(self):
        """Called when system starts or plugin is loaded."""
        pass

    @abstractmethod
    def on_deactivate(self):
        """Called when system shuts down."""
        pass

    @abstractmethod
    def get_proactive_actions(self) -> List[Dict[str, Any]]:
        """
        Returns a list of suggested actions based on local plugin context.
        Example: [{'id': 'git_sync', 'title': 'Sync Repo', 'confidence': 0.85}]
        """
        return []

    @abstractmethod
    def can_handle_command(self, command: str) -> bool:
        """Checks if this plugin can execute a specific @command."""
        return False

    @abstractmethod
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the logic for a command.
        Returns: {'success': bool, 'output': str, 'summary': str}
        """
        return {"success": False, "output": "Not implemented", "summary": "N/A"}
