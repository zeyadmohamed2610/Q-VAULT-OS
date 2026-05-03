import os
import json
import logging
import importlib.util
from typing import Dict, Any, List, Optional
from core.event_bus import EVENT_BUS, SystemEvent
from system.config import get_qvault_home

logger = logging.getLogger(__name__)

class PluginRegistry:
    """
    Manages the installation and runtime state of external plugins.
    Ensures plugins stay within the SDK boundaries.
    """
    def __init__(self):
        self.plugin_dir = os.path.join(get_qvault_home(), "plugins")
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            
        self._plugins: Dict[str, Dict[str, Any]] = {}
        self._loaded_modules: Dict[str, Any] = {}
        
        # 🧪 v2.7 Mock Marketplace Content
        self._plugins["neural_viz"] = {
            "id": "neural_viz", "name": "Neural Network Visualizer", "version": "1.0.4",
            "description": "Real-time visualization of LLM attention heads and logic branching.",
            "entry_point": "main.py", "enabled": False, "path": ""
        }
        self._plugins["quantum_shield"] = {
            "id": "quantum_shield", "name": "Quantum Shield v2", "version": "2.1.0",
            "description": "Hardens the security core against adversarial prompt injection.",
            "entry_point": "init.py", "enabled": True, "path": ""
        }
        self._plugins["flow_gen"] = {
            "id": "flow_gen", "name": "Flow Architect", "version": "0.9.5",
            "description": "Generates complex autonomous workflows using natural language.",
            "entry_point": "plugin.py", "enabled": False, "path": ""
        }
        
        logger.info(f"[PLUGIN_REGISTRY] Initialized. Scanning {self.plugin_dir}")

    def scan_plugins(self):
        """Discovers plugins in the plugins directory."""
        for entry in os.scandir(self.plugin_dir):
            if entry.is_dir():
                manifest_path = os.path.join(entry.path, "manifest.json")
                if os.path.exists(manifest_path):
                    self._register_plugin(entry.name, manifest_path)

    def _register_plugin(self, plugin_id: str, manifest_path: str):
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
                
            # Basic validation
            required = ["name", "version", "entry_point"]
            if not all(k in manifest for k in required):
                logger.warning(f"[PLUGIN_REGISTRY] Invalid manifest for {plugin_id}")
                return
                
            manifest["id"] = plugin_id
            manifest["path"] = os.path.dirname(manifest_path)
            manifest["enabled"] = False
            
            self._plugins[plugin_id] = manifest
            logger.info(f"[PLUGIN_REGISTRY] Registered: {manifest['name']} v{manifest['version']}")
            EVENT_BUS.emit(SystemEvent.EVT_PLUGIN_INSTALLED, manifest, source="PluginRegistry")
            
        except Exception as e:
            logger.error(f"[PLUGIN_REGISTRY] Failed to register {plugin_id}: {e}")

    def enable_plugin(self, plugin_id: str) -> bool:
        """Dynamically loads and activates a plugin."""
        if plugin_id not in self._plugins: return False
        
        manifest = self._plugins[plugin_id]
        if manifest["enabled"]: return True
        
        try:
            entry_path = os.path.join(manifest["path"], manifest["entry_point"])
            module_name = f"plugins.{plugin_id}"
            
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call entry point (initialize method)
            if hasattr(module, "initialize"):
                module.initialize()
                
            self._loaded_modules[plugin_id] = module
            manifest["enabled"] = True
            
            logger.info(f"[PLUGIN_REGISTRY] Activated plugin: {manifest['name']}")
            EVENT_BUS.emit(SystemEvent.EVT_PLUGIN_ACTIVATED, {"id": plugin_id}, source="PluginRegistry")
            return True
            
        except Exception as e:
            logger.error(f"[PLUGIN_REGISTRY] Failed to enable {plugin_id}: {e}")
            EVENT_BUS.emit(SystemEvent.EVT_PLUGIN_ERROR, {"id": plugin_id, "error": str(e)}, source="PluginRegistry")
            return False

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        return list(self._plugins.values())

# Global Instance
PLUGIN_REGISTRY = PluginRegistry()
