import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QFrame, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint, QRect, QSize, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QCursor, QTextCursor

# ── Project Imports ──
from core.event_bus import EVENT_BUS, SystemEvent
from system.runtime_manager import RUNTIME_MANAGER
from ui.widgets.splash_screen import SplashScreen as BootSplash

logger = logging.getLogger("main")

class QVaultOS(QMainWindow):
    def __init__(self):
        super().__init__()
        from ui.widgets.boot_screen import BootScreen
        from ui.widgets.login_screen import LoginScreen
        from ui.widgets.desktop import Desktop
        from system.app_controller import get_app_controller
        
        self.setWindowTitle("Q-Vault Sovereign OS")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(800, 600)
        
        # Ensure a base background to prevent white screen
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(10, 15, 20))
        self.setPalette(p)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Initialize screen components
        self._boot_screen = BootScreen(parent=self._stack)
        self._login_screen = LoginScreen(parent=self._stack)
        self._desktop_screen = Desktop(parent=self._stack)

        self._stack.addWidget(self._boot_screen)
        self._stack.addWidget(self._login_screen)
        self._stack.addWidget(self._desktop_screen)

        self.screens_map = {
            "boot": self._boot_screen,
            "login": self._login_screen,
            "desktop": self._desktop_screen,
        }

        # ── Sovereign Lockdown Overlay ──
        self._lockdown_overlay = LockdownOverlay(self)
        self._lockdown_overlay.hide()

        # Initialize router
        app_ctrl = get_app_controller()
        app_ctrl.init_gui(self._stack, self.screens_map)

        EVENT_BUS.subscribe("ui.permission_response", self._check_lock_status)
        
        self._pulse_timer = None
        self.installEventFilter(self)

    def showEvent(self, event):
        super().showEvent(event)
        if self._pulse_timer is None:
            self._pulse_timer = QTimer(self)
            self._pulse_timer.timeout.connect(self._system_pulse)
            self._pulse_timer.start(1000)

    def _system_pulse(self):
        RUNTIME_MANAGER.report_ui_pulse()
        # RUNTIME_MANAGER.check_inactivity() # Consistently handled by AuthManager
        self._check_lock_status()

    def _check_lock_status(self, _=None):
        if RUNTIME_MANAGER.is_system_locked:
            self._show_lockdown()
        else:
            self._hide_lockdown()

    def _show_lockdown(self):
        self._lockdown_overlay.setGeometry(self.rect())
        self._lockdown_overlay.show()
        self._lockdown_overlay.raise_()

    def _hide_lockdown(self):
        self._lockdown_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._lockdown_overlay.isHidden():
            self._lockdown_overlay.setGeometry(self.rect())

class GlobalCursorFilter(QObject):
    """
    Monitors all application events to enforce consistent cursor 
    feedback and report system activity to AuthManager.
    """
    def eventFilter(self, obj, event):
        from system.auth_manager import get_auth_manager
        am = get_auth_manager()
        
        # Report activity on any user-driven event
        if am and event.type() in [QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.MouseMove, QEvent.Wheel]:
            am.report_activity()

        if event.type() == QEvent.Enter:
            if isinstance(obj, QPushButton):
                obj.setCursor(Qt.PointingHandCursor)
            elif isinstance(obj, QLineEdit):
                obj.setCursor(Qt.IBeamCursor)
        elif event.type() == QEvent.Leave:
            if isinstance(obj, (QPushButton, QLineEdit)):
                obj.setCursor(Qt.ArrowCursor)
        return super().eventFilter(obj, event)

class LockdownOverlay(QWidget):
    """
    Sovereign Lockdown Screen — Cinematic Re-auth interface.
    v2.5 Professional Glass: Frosted Backdrop + Radial Depth.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        from resources.theme import THEME
        self.setObjectName("LockdownOverlay")
        # Semi-transparent dark glass base
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 150)
        layout.setSpacing(20)
        
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        
        # ── Minimalist Floating Container ──
        self.container = QWidget()
        self.container.setFixedWidth(340)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(20)
        
        # ── Input (Zero-Gravity Glass Style) ──
        input_style = f"""
            QLineEdit {{
                background: rgba(0, 0, 0, 0.6);
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 14px;
                color: #f0f9ff;
                padding: 12px 18px;
                font-family: 'Inter', 'Segoe UI';
                font-size: 14px;
                selection-background-color: {THEME['primary_glow']};
                selection-color: black;
            }}
            QLineEdit:focus {{
                border: 1px solid {THEME['primary_glow']};
                background: rgba(0, 240, 255, 0.08);
            }}
        """
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("VAULT KEY") 
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(52)
        self.pass_input.setStyleSheet(input_style)
        self.pass_input.returnPressed.connect(self._attempt_unlock)
        
        # Glow
        pass_glow = QGraphicsDropShadowEffect()
        pass_glow.setBlurRadius(25)
        pass_glow.setColor(QColor(0, 240, 255, 50))
        pass_glow.setOffset(0, 0)
        self.pass_input.setGraphicsEffect(pass_glow)
        
        self.btn_unlock = QPushButton("AUTHORIZE")
        self.btn_unlock.setObjectName("PrimaryBtn")
        self.btn_unlock.setFixedHeight(56)
        self.btn_unlock.setCursor(Qt.PointingHandCursor)
        
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(45)
        btn_shadow.setColor(QColor(0, 240, 255, 180))
        btn_shadow.setOffset(0, 0)
        self.btn_unlock.setGraphicsEffect(btn_shadow)
        
        self.btn_unlock.setStyleSheet(f"""
            QPushButton#PrimaryBtn {{
                background: rgba(0, 240, 255, 0.18);
                border: 2px solid {THEME['primary_glow']};
                border-radius: 16px;
                color: {THEME['primary_glow']};
                font-weight: 900;
                font-size: 15px;
                letter-spacing: 6px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background: rgba(0, 240, 255, 0.35);
                color: white;
            }}
            QPushButton#PrimaryBtn.busy {{
                background: rgba(0, 240, 255, 0.05);
                border-color: rgba(0, 240, 255, 0.4);
                color: rgba(0, 240, 255, 0.6);
            }}
        """)
        self.btn_unlock.clicked.connect(self._attempt_unlock)
        
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"color: {THEME['accent_error']}; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.hide()
        
        container_layout.addWidget(self.pass_input)
        container_layout.addWidget(self.btn_unlock)
        container_layout.addWidget(self.error_lbl)
        
        layout.addWidget(self.container)

    def paintEvent(self, event):
        from PyQt5.QtGui import QRadialGradient
        from PyQt5.QtCore import QPointF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create professional dark glass depth
        grad = QRadialGradient(QPointF(self.width()/2, self.height() * 0.8), self.width() * 0.8)
        grad.setColorAt(0, QColor(10, 20, 25, 210))
        grad.setColorAt(1, QColor(5, 10, 15, 245))
        
        painter.fillRect(self.rect(), grad)

    def _attempt_unlock(self):
        password = self.pass_input.text()
        if not password: return
        from system.auth_manager import get_auth_manager
        am = get_auth_manager()
        
        self.btn_unlock.setEnabled(False)
        self.btn_unlock.setText("VERIFYING...")
        self.btn_unlock.setProperty("class", "busy")
        self.btn_unlock.style().unpolish(self.btn_unlock)
        self.btn_unlock.style().polish(self.btn_unlock)
        self.setCursor(Qt.WaitCursor)
        
        if not hasattr(self, "_connected"):
            am.login_failed.connect(self._on_unlock_failed)
            am.state_changed.connect(self._on_auth_state_changed)
            self._connected = True
            
        am.request_unlock(password)

    def _on_unlock_failed(self, error):
        self.error_lbl.setText("IDENTITY VERIFICATION FAILED")
        self.btn_unlock.setEnabled(True)
        self.btn_unlock.setText("AUTHORIZE")
        self.btn_unlock.setProperty("class", "")
        self.btn_unlock.style().unpolish(self.btn_unlock)
        self.btn_unlock.style().polish(self.btn_unlock)
        self.setCursor(Qt.ArrowCursor)
        self.pass_input.clear()

    def _on_auth_state_changed(self, new_state, old_state):
        if new_state == "logged_in":
            self.pass_input.clear()
            self.error_lbl.setText("")
            self.setCursor(Qt.ArrowCursor)
            self.hide()
            self.btn_unlock.setEnabled(True)
            self.btn_unlock.setText("AUTHORIZE")

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global handler for unhandled exceptions to prevent silent crashes."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("UNHANDLED CRITICAL EXCEPTION:", exc_info=(exc_type, exc_value, exc_traceback))
    # We could show a 'System Error' dialog here if QApplication is running
    try:
        from PyQt5.QtWidgets import QMessageBox
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Q-Vault Sovereign - System Error")
            msg.setText("A critical runtime error has occurred.")
            msg.setInformativeText(f"{exc_value}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("background-color: #0b1929; color: #d4e8f0;")
            msg.exec_()
    except Exception:
        pass

sys.excepthook = handle_exception

def main():
    print(">>> [MAIN.PY] Entering main()...")
    logger.info("[Startup] Entering main function in main.py")
    from PyQt5.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
    except Exception as e:
        logger.critical(f"[Startup] FATAL ERROR during QApplication creation: {e}")
        sys.exit(1)
    
    window = None
    splash = BootSplash()
    
    def on_boot_finished():
        nonlocal window
        logger.info("[Startup] Boot splash finished. Initializing QVaultOS...")
        
        from system.theme_manager import THEME_MANAGER
        THEME_MANAGER.apply_global_theme(app)
        
        cursor_filter = GlobalCursorFilter()
        app.installEventFilter(cursor_filter)
        
        try:
            window = QVaultOS()
            logger.info("[Startup] QVaultOS initialized successfully. Showing window...")
            window.showFullScreen()
            app.setQuitOnLastWindowClosed(True)
        except Exception as e:
            logger.critical(f"[Startup] CRITICAL FAILURE during QVaultOS initialization: {e}")
            import traceback
            logger.critical(traceback.format_exc())
            sys.exit(1)
        
    splash.splash_complete.connect(on_boot_finished)
    splash.show()
    print(">>> [MAIN.PY] Splash shown. Entering event loop...")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
