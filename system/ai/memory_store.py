import json
import os
import logging
from typing import Dict, Any, List
from system.config import get_qvault_home

logger = logging.getLogger(__name__)

class MemoryStore:
    """
    Persistent storage for AI learning patterns.
    Simple frequency-based tracking of app usage and frequent intents.
    """
    def __init__(self):
        self.save_path = os.path.join(get_qvault_home(), "ai_memory.json")
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[MEMORY] Failed to load: {e}")
        return {
            "app_usage": {},
            "common_intents": {},
            "last_seen": 0
        }

    def save(self):
        try:
            with open(self.save_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"[MEMORY] Failed to save: {e}")

    def record_app_launch(self, app_name: str):
        usage = self.data["app_usage"]
        usage[app_name] = usage.get(app_name, 0) + 1
        self.save()

    def record_intent(self, intent_text: str):
        intents = self.data["common_intents"]
        intents[intent_text] = intents.get(intent_text, 0) + 1
        self.save()

    def get_frequent_apps(self, limit=3) -> List[str]:
        usage = self.data["app_usage"]
        sorted_apps = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        return [app for app, count in sorted_apps[:limit]]
