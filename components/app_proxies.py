import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from system.runtime.isolated_widget import IsolatedAppWidget

logger = logging.getLogger(__name__)


class FileExplorerProxy(QWidget):
    """
    Direct (non-isolated) proxy for the File Explorer.
    QFileSystemModel runs natively and doesn't need a subprocess engine.
    Supports an optional start_path to pre-navigate on construction.
    """
    def __init__(self, secure_api=None, parent=None, start_path=None):
        super().__init__(parent)
        self.secure_api = secure_api
        self.setObjectName("AppContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        from apps.file_manager.file_manager_app import FileManagerApp
        self.ui = FileManagerApp(self)
        layout.addWidget(self.ui)

        if start_path:
            self._navigate_to(start_path)

    def _navigate_to(self, path):
        """Navigate the file manager to a specific path."""
        try:
            import os
            if os.path.isdir(path):
                self.ui.current_path = path
                self.ui.view.setRootIndex(self.ui.model.index(path))
                self.ui.path_bar.blockSignals(True)
                self.ui.path_bar.setText(path)
                self.ui.path_bar.blockSignals(False)
        except Exception as e:
            logger.warning(f"[FileExplorerProxy] Failed to navigate to {path}: {e}")


class TerminalProxy(IsolatedAppWidget):
    """Proxy for the Terminal Engine (process-isolated via IPC)."""
    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id="Terminal",
            module_path="apps.terminal.terminal_engine",
            class_name="TerminalEngine",
            secure_api=secure_api,
            parent=parent
        )
        self.setObjectName("AppContainer")

        from apps.terminal.terminal_app import TerminalWidget
        self.terminal = TerminalWidget(self)
        self.set_content(self.terminal)

    def on_start(self):
        """Boot the terminal engine and give focus to the widget."""
        self.terminal.setFocus()
        self.call_remote("boot_terminal")

    def showEvent(self, event):
        """Auto-boot on first show if not already started."""
        super().showEvent(event)
        if not hasattr(self, '_booted'):
            self._booted = True
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.on_start)

    def handle_event(self, event, data):
        """Bridge IPC events to the UI."""
        if not hasattr(self, "terminal"):
            return
        if event == "output_ready":
            self.terminal.append_output(data)
        elif event == "prompt_update":
            self.terminal.update_prompt(data)
        elif event == "password_mode":
            self.terminal.set_password_mode(data)
