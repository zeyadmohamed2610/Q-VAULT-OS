import sys
import os
import logging

logger = logging.getLogger(__name__)


from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt, pyqtSlot
import traceback

R  = "\x1b[38;2;248;81;73m"    # red
D  = "\x1b[38;2;74;104;128m"   # dim
RS = "\x1b[0m"                  # reset

def global_exception_hook(exctype, value, tb):
    """Authoritative exception catcher for the entire OS."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    
    if issubclass(exctype, KeyboardInterrupt):
        # Graceful exit for Ctrl+C
        print(f"\n{D}[SYSTEM]{RS} Termination signal received. Cleaning up...", file=sys.stderr)
        return

    # Force full traceback to console for immediate visibility during boot issues
    print(f"\n{R}[CRITICAL_EXCEPTION]{RS}\n{err_msg}", file=sys.stderr)
    
    # Use stabilized logging
    logger.critical(f"[RUNTIME_CRASH] Unhandled Exception: {exctype.__name__}: {value}")
    logger.debug(err_msg)
    
    try:
        from system.security_api import get_security_api
        api = get_security_api()
        if api:
            api.report(
                "CRITICAL_SYSTEM_EVENT",
                source="ui_thread",
                detail=f"UNHANDLED_EXCEPTION: {str(value)}",
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
        self.setWindowFlags(Qt.FramelessWindowHint)
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



def _create_qvault_cursor():
    """Clean arrow cursor with subtle cyan accent dot."""
    from PyQt5.QtGui import QCursor, QPixmap, QPainter, QColor, QPen, QBrush, QPolygonF
    from PyQt5.QtCore import Qt, QPointF

    size = 24
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    arrow = [
        QPointF(2, 2),
        QPointF(2, 18),
        QPointF(6, 14),
        QPointF(10, 20),
        QPointF(12, 19),
        QPointF(8, 13),
        QPointF(14, 13),
    ]
    poly = QPolygonF(arrow)

    painter.setPen(QPen(QColor(10, 10, 20), 1.5))
    painter.setBrush(QBrush(QColor(220, 235, 242)))
    painter.drawPolygon(poly)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(84, 177, 198, 200)))
    painter.drawEllipse(QPointF(2, 2), 2.5, 2.5)

    painter.end()
    return QCursor(pix, 2, 2)

def main():
    # Hardware acceleration & HiDPI — must be set before QApplication
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
    os.environ.setdefault("QSG_RENDER_LOOP", "threaded")

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Required before QApplication for some drivers
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    app.setOverrideCursor(_create_qvault_cursor())
    
    # Authoritative UI Engine Hook
    from system.theme_manager import THEME_MANAGER
    THEME_MANAGER.apply_global_theme(app)

    # ── Onboarding Check ──
    try:
        from system.config import get_qvault_home
        from pathlib import Path
        onboarding_flag = Path(get_qvault_home()) / ".config" / "onboarding_done"
        if not onboarding_flag.exists():
            from components.onboarding_flow import OnboardingFlow
            flow = OnboardingFlow()
            # Ensure .config directory exists
            onboarding_flag.parent.mkdir(parents=True, exist_ok=True)
            flow.finished.connect(lambda: onboarding_flag.touch())
            flow.exec_()
    except Exception as exc:
        logger.warning("Onboarding check failed: %s", exc)

    # ── Boot Kernel Simulation ──
    try:
        from kernel._boot_pipeline import boot_kernel
        boot_kernel()
    except Exception as exc:
        logger.error("Kernel Simulator failed to boot: %s", exc)

    window = QVaultOS()
    window.setMinimumSize(1280, 720)
    window.showMaximized()

    # ── Initialize QVault Hardware Integration ──
    try:
        from kernel.security.qvault_runtime_bridge import QVAULT_BRIDGE
        QVAULT_BRIDGE.start()
    except Exception as exc:
        logger.error("Failed to initialize QVault runtime bridge: %s", exc)

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
    run_mod.bootstrap()
    run_mod.launch()

