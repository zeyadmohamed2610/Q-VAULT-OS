import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QFrame, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint, QRect, QSize, QObject
from PyQt5.QtGui import QPainter, QColor, QCursor

# ── Project Imports ──
from core.event_bus import EVENT_BUS, SystemEvent
from system.runtime_manager import RUNTIME_MANAGER
from ui.shell.boot_splash import BootSplash

logger = logging.getLogger("main")

class QVaultOS(QMainWindow):
    def __init__(self):
        super().__init__()
        from ui.widgets.boot_screen import BootScreen
        from ui.widgets.login_screen import LoginScreen
        from ui.widgets.desktop import Desktop
        from system.app_controller import get_app_controller
        
        self.setWindowTitle("Q-Vault OS")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(800, 600)

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
        RUNTIME_MANAGER.check_inactivity()
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
    feedback (Hand for buttons, I-Beam for text, Arrow for others).
    """
    def eventFilter(self, obj, event):
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
        self.pass_input.setPlaceholderText("PASSWORD") 
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
        
        self.btn_unlock = QPushButton("SIGN-IN")
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
        # Center gradient to keep the focus on the bottom UI
        grad = QRadialGradient(QPointF(self.width()/2, self.height() * 0.8), self.width() * 0.8)
        grad.setColorAt(0, QColor(10, 20, 25, 210)) # Lighter near the form
        grad.setColorAt(1, QColor(5, 10, 15, 245))  # Darker towards edges
        
        painter.fillRect(self.rect(), grad)
        
        # Optional: Subtle border for the "glass" sheet if it was a smaller window, 
        # but here it covers the whole screen, so we just stick to the gradient.

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
        
        # Corrected: Connect signals for async response
        if not hasattr(self, "_connected"):
            am.login_failed.connect(self._on_unlock_failed)
            am.state_changed.connect(self._on_auth_state_changed)
            self._connected = True
            
        am.request_unlock(password)

    def _on_unlock_failed(self, error):
        self.error_lbl.setText("ACCESS DENIED")
        self.btn_unlock.setEnabled(True)
        self.btn_unlock.setText("SIGN-IN")
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
            self.btn_unlock.setText("SIGN-IN")

def main():
    from PyQt5.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    # Pre-import WebEngine if available to prevent initialization errors later
    try:
        from PyQt5 import QtWebEngineWidgets
    except ImportError:
        pass

    app = QApplication(sys.argv)
    
    # ── Phase 3: Integrity Boot Splash ──
    splash = BootSplash()
    
    def on_boot_finished():
        from system.theme_manager import THEME_MANAGER
        THEME_MANAGER.apply_global_theme(app)
        
        # Install global cursor management
        cursor_filter = GlobalCursorFilter()
        app.installEventFilter(cursor_filter)
        
        window = QVaultOS()
        window.showFullScreen()
        
    splash.finished.connect(on_boot_finished)
    splash.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
