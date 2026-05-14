import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PluginRegistry:
    """
    Backend Registry for the Q-Vault Ecosystem.
    Manages loading, enabling, and state of system plugins.
    """
    def __init__(self):
        # Mock data for v1.0
        self._plugins = [
            {
                "id": "git_integration",
                "name": "Git Sovereign",
                "version": "1.0.4",
                "description": "Deep Git integration for tracking source code integrity.",
                "enabled": True
            },
            {
                "id": "terminal_ext",
                "name": "Terminal Pro",
                "version": "2.1.0",
                "description": "Enhanced terminal buffers and ANSI-Glow rendering.",
                "enabled": True
            },
            {
                "id": "vscode_bridge",
                "name": "VSCode Link",
                "version": "0.9.0",
                "description": "Synchronize your sovereign workspace with VSCode instances.",
                "enabled": False
            },
            {
                "id": "ai_governance",
                "name": "AI Sentinel",
                "version": "1.5.0",
                "description": "Real-time auditing of AI intent and decision trees.",
                "enabled": True
            }
        ]

    def scan_plugins(self):
        """
        Scans the system/plugins directory for new extensions.
        v1.0 Implementation: Mock scan that validates internal integrity.
        """
        logger.info("Marketplace: Scanning for sovereign extensions...")
        # In a real impl, this would loop through system/plugins/*.py
        pass

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        return self._plugins

    def enable_plugin(self, plugin_id: str) -> bool:
        for p in self._plugins:
            if p["id"] == plugin_id:
                p["enabled"] = True
                logger.info(f"Plugin '{plugin_id}' enabled via Marketplace.")
                return True
        return False

# Global Singleton
PLUGIN_REGISTRY = PluginRegistry()
