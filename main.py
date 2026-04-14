# =============================================================
#  main.py — Q-Vault OS  |  Entry Point v6
#
#  Boot sequence:
#    0. SplashScreen   (brand splash - optional)
#    1. BootScreen    (animated kernel messages)
#    2. LoginScreen   (fullscreen auth wall)
#    3. Desktop       (full OS environment)
#
#  Logout → back to LoginScreen (boot screen not shown again).
#
#  Run:   python main.py [--demo]
#  Deps:  pip install PyQt5
# =============================================================

import logging
import sys
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt, QTimer

# App version
VERSION = "1.2.0"
VERSION_NAME = "Q-VAULT OS"

# Parse command line arguments
PARSER = argparse.ArgumentParser(description=f"{VERSION_NAME} v{VERSION}")
PARSER.add_argument(
    "--demo",
    action="store_true",
    help="Run in demo mode with auto-login",
)
ARGS = PARSER.parse_args()

from components.splash_screen import SplashScreen
from components.boot_screen import BootScreen
from components.login_screen import LoginScreen
from components.desktop import Desktop


# Stacked widget indices
IDX_BOOT = 0
IDX_LOGIN = 1
IDX_DESKTOP = 2

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
_LOGGING_READY = False
_LOG_FILE: Path | None = None


def _configure_logging() -> Path | None:
    """Initialize logging once, with a safe local fallback."""
    global _LOGGING_READY, _LOG_FILE

    if _LOGGING_READY:
        return _LOG_FILE

    candidates = [
        Path.home() / ".qvault" / "logs" / "system.log",
        Path(__file__).resolve().parent / ".local" / "logs" / "system.log",
    ]

    for log_file in candidates:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8"):
                pass

            logging.basicConfig(
                filename=str(log_file),
                level=logging.INFO,
                format=LOG_FORMAT,
                encoding="utf-8",
                force=True,
            )
            _LOGGING_READY = True
            _LOG_FILE = log_file
            logging.info("Logging initialized at %s", log_file)
            return _LOG_FILE
        except OSError:
            continue

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, force=True)
    _LOGGING_READY = True
    _LOG_FILE = None
    logging.warning("File logging unavailable; falling back to stderr.")
    return None


class QVaultOS(QMainWindow):
    """
    Top-level window.  Uses a QStackedWidget so we can
    switch cleanly between boot → login → desktop.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VERSION_NAME + ' v' + VERSION")
        self.setMinimumSize(1024, 600)
        self.resize(1280, 800)
        self.menuBar().hide()
        self.statusBar().hide()

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Demo mode flag
        self._demo_mode = ARGS.demo

        # Desktop is created after successful login
        self._desktop = None

        if self._demo_mode:
            self._init_demo_mode()
        else:
            self._init_normal_mode()

    def _init_demo_mode(self):
        """Initialize in demo mode - skip to desktop with demo user."""
        from core.system_state import STATE

        STATE.current_user = "demo"
        STATE.session_type = "demo"
        # NOTE: STATE.is_root is a method — do NOT assign to it

        self._desktop = Desktop(self)
        self._stack.addWidget(self._desktop)
        self._stack.setCurrentWidget(self._desktop)
        self._desktop.setFocus()

        self._desktop.show_demo_banner(True)

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "Welcome to VERSION_NAME + ' v' + VERSION",
            "Demo Mode Active - You are logged in as 'demo'",
            level="success",
        )
        logging.info("Demo mode initialized")

        # Delayed notifications for guided tour
        QTimer.singleShot(
            1500,
            lambda: NOTIFY.send(
                "Quick Start Guide",
                "Terminal: Try commands like 'ls', 'cd', 'whoami', 'help'",
                level="info",
            ),
        )
        QTimer.singleShot(
            3000,
            lambda: NOTIFY.send(
                "File Explorer",
                "Click on Files icon to browse the virtual filesystem",
                level="info",
            ),
        )
        QTimer.singleShot(
            4500,
            lambda: NOTIFY.send(
                "Security Panel",
                "Access Security to monitor system events in real-time",
                level="info",
            ),
        )

        QTimer.singleShot(500, lambda: self._open_demo_apps())

    def _open_demo_apps(self):
        """Open some apps to demonstrate the system."""
        if self._desktop:
            self._desktop._open_app("Terminal")
            QTimer.singleShot(300, lambda: self._desktop._open_app("Files"))

    def _init_normal_mode(self):
        """Initialize in normal mode - show boot then login."""
        # ── 0. Boot screen ────────────────────────────────────
        self._boot = BootScreen()
        self._boot.boot_complete.connect(self._show_login)
        self._stack.addWidget(self._boot)  # index 0

        # ── 1. Login screen ───────────────────────────────────
        self._login = LoginScreen()
        self._login.login_success.connect(self._on_login)
        self._stack.addWidget(self._login)  # index 1

        # Start at boot screen
        self._stack.setCurrentIndex(IDX_BOOT)

    # ── Boot → Login ──────────────────────────────────────────

    def _show_login(self):
        self._stack.setCurrentIndex(IDX_LOGIN)
        self._login.showEvent(None)

    # ── Login → Desktop ───────────────────────────────────────

    def _on_login(self):
        """Rebuild and show the Desktop after successful login."""
        try:
            _configure_logging()
            logging.info("=== Q-VAULT Login Sequence Started ===")

            if self._desktop is not None:
                logging.info("Removing old desktop instance")
                try:
                    self._stack.removeWidget(self._desktop)
                    self._desktop.deleteLater()
                except Exception as e:
                    logging.warning(f"Error removing old desktop: {e}")

            logging.info("Creating new Desktop instance...")
            try:
                self._desktop = Desktop(self)
                self._stack.addWidget(self._desktop)
                self._stack.setCurrentWidget(self._desktop)
                self._desktop.setFocus()
            except Exception as e:
                logging.exception("Desktop creation failed")
                raise

            logging.info("Desktop created successfully")

            try:
                from system.notification_system import NOTIFY
                from core.system_state import STATE

                NOTIFY.send(
                    "Login successful",
                    f"Welcome, {STATE.username()}. Session: {STATE.session_type}.",
                    level="success",
                )
                logging.info(f"Login complete for user: {STATE.username()}")
            except Exception as e:
                logging.warning(f"Post-login notification failed: {e}")

        except Exception as e:
            import traceback

            _configure_logging()
            logging.exception("LOGIN CRITICAL FAILURE")

            print(f"[CRITICAL] Login failed: {e}")
            print(traceback.format_exc())

            # Safe fallback to login
            try:
                self._stack.setCurrentIndex(IDX_LOGIN)
                if hasattr(self, "_login"):
                    self._login._pass_field.clear()
                    self._login._show_error(f"Desktop failed to load: {str(e)[:80]}")
                    self._login._user_field.setFocus()
            except Exception:
                pass  # Best effort - don't crash the crash handler
            return

    # ── Logout → Login ────────────────────────────────────────

    def show_login(self):
        """Called by Settings or Desktop on logout."""
        from core.system_state import STATE

        STATE.current_user = None
        STATE.session_type = "real"
        self._stack.setCurrentIndex(IDX_LOGIN)
        self._login.showEvent(None)


def main():
    _configure_logging()

    # Install crash handler
    from system.crash_handler import install_handlers

    install_handlers()

    # Install global exception handler with UI feedback
    def exception_hook(exc_type, exc_value, exc_traceback):
        import traceback

        error_msg = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        print(f"[GLOBAL EXCEPTION] {exc_type.__name__}: {exc_value}")
        print(error_msg)

        try:
            logging.error(f"GLOBAL EXCEPTION: {exc_type.__name__}: {exc_value}")
            logging.error(error_msg)
        except Exception:
            pass

        # Try to show error dialog (best effort)
        try:
            from components.error_dialog import show_crash_error
            from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                show_crash_error(exc_type.__name__, str(exc_value), error_msg)
        except Exception:
            pass

    sys.excepthook = exception_hook

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("VERSION_NAME + ' v' + VERSION")

    window = QVaultOS()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
