# Q-VAULT OS Plugin Template
# Copy this file to ~/.qvault/plugins/your_plugin/

import json

# Plugin manifest - REQUIRED
MANIFEST = {
    "api_version": "1.2.0",
    "name": "My Plugin",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "A sample plugin for Q-VAULT OS",
    "entry_point": "main",
    "permissions": [
        "storage",  # Can save/load data
        "ui",  # Can show notifications
    ],
    "icon": None,  # Optional icon path
    "homepage": None,  # Optional URL
    "signature": None,  # For verified plugins
}


class PluginClass:
    def __init__(self, api):
        self.api = api
        self.name = MANIFEST["name"]

    def on_load(self):
        """Called when plugin is loaded"""
        self.api.log(f"{self.name} loaded!")

        # Example: Show notification
        self.api.ui.notify("Plugin Loaded", f"{self.name} is now active", "success")

        # Example: Load saved config
        setting = self.api.get_config("setting_name", "default_value")
        print(f"Loaded setting: {setting}")

    def on_unload(self):
        """Called when plugin is unloaded"""
        self.api.log(f"{self.name} unloaded!")

        # Example: Save config
        self.api.set_config("last_unload", "true")


def on_load(api):
    """Legacy entry point - use PluginClass instead"""
    return PluginClass(api)


def on_unload():
    """Legacy cleanup"""
    pass


# --- API Reference ---
#
# api.fs          - File system operations
#   api.fs.read(path) -> str
#   api.fs.write(path, content) -> bool
#   api.fs.list_dir(path) -> list
#
# api.process     - Process management
#   api.process.get_processes() -> list
#   api.process.kill_process(pid) -> bool
#
# api.storage     - Plugin data storage
#   api.storage.get_data_dir() -> Path
#   api.storage.save_data(key, value)
#   api.storage.load_data(key, default)
#
# api.ui          - User interface
#   api.ui.notify(title, message, level)
#   api.ui.create_window(title, width, height)
#
# api.security    - Security operations
#   api.security.get_alerts(limit) -> list
#   api.security.log_security_event(event, severity)
#
# api.log(message, level) - Logging
# api.get_config(key, default) - Config
# api.set_config(key, value) - Save config
