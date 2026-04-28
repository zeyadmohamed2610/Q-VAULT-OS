import json
import os
from pathlib import Path

class SettingsEngine:
    """
    Subprocess-level logic for OS Settings (Phase B).
    Manages persistence via governed filesystem access.
    """
    def __init__(self, secure_api):
        self.api = secure_api
        self.settings_file = "config.json"

    def get_settings(self):
        """Load settings from the governed sandbox storage."""
        try:
            if self.api.fs.exists(self.settings_file):
                data = self.api.fs.read_file(self.settings_file)
                return {"status": "success", "value": json.loads(data)}
            else:
                return {"status": "success", "value": {"theme": "dark", "notifications": True}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_settings(self, new_settings: dict):
        """Save settings (enforcing jail integrity)."""
        try:
            data = json.dumps(new_settings, indent=2)
            # api.fs.write_file should exist in the SecureAPI whitelist
            # If not, it will be blocked by the IPC gate
            self.api.fs.write_file(self.settings_file, data)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": f"Save failed: {str(e)}"}
