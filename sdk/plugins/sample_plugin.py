# Q-VAULT OS Plugin Template (v2.0 Event-Driven)
# Copy this file to ~/.qvault/plugins/your_plugin/

from sdk.api import api
from sdk.events import APP_LAUNCHED, LOGIN_SUCCESS

# Plugin manifest - REQUIRED
MANIFEST = {
    "api_version": "2.0.0",
    "name": "Sample Plugin",
    "version": "1.0.0",
    "author": "Q-Vault Developer",
    "description": "Demonstrates the new Event-Driven SDK architecture.",
}

class SamplePlugin:
    def __init__(self):
        self.name = MANIFEST["name"]

    def on_load(self):
        """Called when plugin is loaded into the OS."""
        api.notify("Plugin Active", f"{self.name} has been initialized.", "success")
        
        # Subscribe to system facts (Event-Driven)
        api.subscribe(APP_LAUNCHED, self.handle_app_launch)
        api.subscribe(LOGIN_SUCCESS, self.handle_login)

        # Emit an action (Request)
        # api.launch_app("terminal") 

    def handle_app_launch(self, data):
        """Reaction to APP_LAUNCHED fact."""
        module = data.get("module", "unknown")
        print(f"[SamplePlugin] Reacting to launch: {module}")

    def handle_login(self, data):
        """Reaction to LOGIN_SUCCESS fact."""
        user = data.get("username", "user")
        api.notify("Welcome", f"Hello {user}! Plugin is watching.")

def on_load(host_api=None):
    """Entry point called by the System Manager."""
    plugin = SamplePlugin()
    plugin.on_load()
    return plugin
