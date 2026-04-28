# =============================================================
#  components/app_proxies.py — Q-Vault OS  |  App UI Proxies
#
#  Consolidated UI Proxies for Process-Isolated Applications.
#  These run in the Main Process and communicate with Apps in 
#  subprocesses via the IPC Bridge.
# =============================================================

import logging
from PyQt5.QtCore import Qt
from system.runtime.isolated_widget import IsolatedAppWidget

logger = logging.getLogger(__name__)

class FileExplorerProxy(IsolatedAppWidget):
    """Proxy for the File Explorer Engine."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Files",
            module_path="apps.file_explorer_engine",
            class_name="FileEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")
        # ── FIXED: Build actual UI ──
        from apps.file_manager.file_manager_app import FileManagerApp
        self.ui = FileManagerApp(self)
        self.set_content(self.ui)

class TerminalProxy(IsolatedAppWidget):
    """Proxy for the Terminal Engine."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Terminal",
            module_path="apps.terminal.terminal_engine",
            class_name="TerminalEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")
        # ── FIXED: Build actual UI ──
        from apps.terminal.terminal_app import TerminalWidget
        self.terminal = TerminalWidget(self)
        self.set_content(self.terminal)

    def handle_event(self, event, data):
        """Bridge IPC events to the UI."""
        if not hasattr(self, "terminal"): return
        if event == "output_ready":
            self.terminal.append_output(data)
        elif event == "prompt_update":
            self.terminal.update_prompt(data)
        elif event == "password_mode":
            self.terminal.set_password_mode(data)

class TaskManagerProxy(IsolatedAppWidget):
    """Proxy for the Task Manager Engine."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="System Monitor",
            module_path="apps.task_manager_engine",
            class_name="TaskManagerEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")
        # ── FIXED: Build actual UI ──
        from apps.system_monitor.app import SystemMonitorWidget
        self.ui = SystemMonitorWidget(self.secure_api, self)
        self.set_content(self.ui)
        self.ui.on_start() # Trigger telemetry

class SettingsProxy(IsolatedAppWidget):
    """Proxy for the Settings Engine."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Settings",
            module_path="apps.settings_engine",
            class_name="SettingsEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")

class MarketplaceProxy(IsolatedAppWidget):
    """Proxy for the Zero-Trust Marketplace."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Marketplace",
            module_path="apps.marketplace_engine",
            class_name="MarketplaceEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")

class NetworkToolsProxy(IsolatedAppWidget):
    """Proxy for Network Tools."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Network",
            module_path="apps.network_engine",
            class_name="NetworkEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")

class SecurityMonitorProxy(IsolatedAppWidget):
    """Proxy for the Security Engine."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Security",
            module_path="apps.security_engine",
            class_name="SecurityEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")
class ChromeProxy(IsolatedAppWidget):
    """Proxy to launch native Google Chrome."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Google Chrome",
            module_path="components.app_proxies",
            class_name="ChromeLauncher",
            secure_api=secure_api,
            parent=parent
        )
        import webbrowser
        webbrowser.open("https://www.google.com")
        self.close() # Close proxy since it's just a launcher

class FirefoxProxy(IsolatedAppWidget):
    """Proxy to launch native Mozilla Firefox."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Mozilla Firefox",
            module_path="components.app_proxies",
            class_name="FirefoxLauncher",
            secure_api=secure_api,
            parent=parent
        )
        import webbrowser
        # Force firefox if possible, else default
        webbrowser.open("https://www.mozilla.org")
        self.close()

# Helper classes for the registry to find
class ChromeLauncher:
    def __init__(self, *args, **kwargs): pass
    def show(self): pass

class FirefoxLauncher:
    def __init__(self, *args, **kwargs): pass
    def show(self): pass
