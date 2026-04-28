import sys
import os
import logging

logger = logging.getLogger(__name__)


from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt, pyqtSlot
import traceback

def global_exception_hook(exctype, value, tb):
    """Authoritative exception catcher for the entire OS."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    
    # Use stabilized logging instead of raw print
    logger.critical(f"[RUNTIME_CRASH] Unhandled Exception: {value}")
    logger.debug(err_msg)
    
    try:
        from system.security_api import get_security_api
        api = get_security_api()
        if api:
            api.report(
                "CRITICAL_SYSTEM_EVENT",
                source="ui_thread",
                detail=f"UNHANDLED_EXCEPTION: {str(value)}",
                severity="critical",
                escalate=True
            )
    except Exception:
        pass

sys.excepthook = global_exception_hook

from system.app_controller import get_app_controller
from components.boot_screen import BootScreen
from components.login_screen import LoginScreen
from components.desktop import Desktop
from components.lock_screen import LockScreen


class QVaultOS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Q-Vault OS")
        self.setMinimumSize(800, 600)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Initialize screen components with parent tracking
        self._boot_screen = BootScreen(parent=self._stack)
        self._login_screen = LoginScreen(parent=self._stack)
        self._desktop_screen = Desktop(parent=self._stack)

        # Add to stack
        self._stack.addWidget(self._boot_screen)
        self._stack.addWidget(self._login_screen)
        self._stack.addWidget(self._desktop_screen)

        screens_map = {
            "boot": self._boot_screen,
            "login": self._login_screen,
            "desktop": self._desktop_screen,
            "lock_class": LockScreen
        }

        # Wire transitions
        self._boot_screen.boot_finished.connect(
            get_app_controller().switch_to_login
        )

        # Initialize router
        app_ctrl = get_app_controller()
        app_ctrl.init_gui(self._stack, screens_map)


def main():
    # Required before QApplication for some drivers
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    
    # Authoritative UI Engine Hook
    from system.theme_manager import THEME_MANAGER
    THEME_MANAGER.apply_global_theme(app)

    window = QVaultOS()
    window.setMinimumSize(1280, 720)
    window.showMaximized()

    # ── Background Pulse ──
    from PyQt5.QtCore import QTimer
    from system.runtime_manager import RUNTIME_MANAGER
    pulse = QTimer(window)
    pulse.timeout.connect(RUNTIME_MANAGER.report_ui_pulse)
    pulse.start(100) 

    sys.exit(app.exec_())

if __name__ == "__main__":
    # Direct execution: bootstrap through run.py's safe entry point
    # Lazy import avoids circular dependency (main ↔ run)
    import importlib
    run_mod = importlib.import_module("run")
    run_mod.start_qvault()

