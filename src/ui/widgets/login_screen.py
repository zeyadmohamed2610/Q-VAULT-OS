import os
import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt, QRect, QPoint, QPointF, QTimer, QSize
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QRadialGradient, QFont, QIcon

from core.resources import get_asset_path
from resources.theme import THEME


class LoginScreen(QWidget):
    """
    Sovereign Gateway — High-End Authentication Interface.
    v3.0 Cinematic Design.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginGateway")
        
        # Robust Background Loading
        from core.resources import get_asset_path
        bg_path = get_asset_path("qvault_vault.jpg")
        
        self._bg_source = QPixmap()
        if os.path.exists(bg_path):
            self._bg_source.load(bg_path)
        
        self._cached_bg = QPixmap()
        
        # Immediate visual feedback: Set a dark theme background
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #050a10;") 
        
        # Main Layout - Ultra-Compact Floating
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 150)
        layout.setSpacing(20)
        
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        
        # ── Inputs (Zero-Gravity Glass Style) ──
        input_style = f"""
            QLineEdit {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 240, 255, 0.1);
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
                background: rgba(0, 240, 255, 0.05);
            }}
        """
        
        self.user_field = QLineEdit()
        self.user_field.setPlaceholderText("USERNAME")
        self.user_field.setFixedSize(340, 52)
        self.user_field.setStyleSheet(input_style)
        
        # Field Glow
        user_glow = QGraphicsDropShadowEffect()
        user_glow.setBlurRadius(15)
        user_glow.setColor(QColor(0, 240, 255, 40))
        user_glow.setOffset(0, 0)
        self.user_field.setGraphicsEffect(user_glow)
        
        self.pass_field = QLineEdit()
        self.pass_field.setPlaceholderText("PASSWORD")
        self.pass_field.setEchoMode(QLineEdit.Password)
        self.pass_field.setFixedSize(340, 52)
        self.pass_field.setStyleSheet(input_style)
        self.pass_field.returnPressed.connect(self._do_login)
        
        # Field Glow
        pass_glow = QGraphicsDropShadowEffect()
        pass_glow.setBlurRadius(15)
        pass_glow.setColor(QColor(0, 240, 255, 40))
        pass_glow.setOffset(0, 0)
        self.pass_field.setGraphicsEffect(pass_glow)
        
        # Toggle Action
        from PyQt5.QtWidgets import QAction
        eye_path = get_asset_path("icons/eye.svg")
        if os.path.exists(eye_path):
            self.show_pass_action = self.pass_field.addAction(QIcon(eye_path), QLineEdit.TrailingPosition)
        else:
            # Fallback to text-based action if icon is missing
            self.show_pass_action = QAction("SHOW", self)
            self.pass_field.addAction(self.show_pass_action, QLineEdit.TrailingPosition)
        
        self.show_pass_action.setCheckable(True)
        self.show_pass_action.triggered.connect(self._toggle_password)
        
        # ── Floating Action ──
        self.login_btn = QPushButton("SIGN-IN") 
        self.login_btn.setObjectName("PrimaryBtn")
        self.login_btn.setFixedSize(340, 56)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        
        # High Intensity Button Glow
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(40)
        btn_shadow.setColor(QColor(0, 240, 255, 180))
        btn_shadow.setOffset(0, 0)
        self.login_btn.setGraphicsEffect(btn_shadow)
        
        self.login_btn.setStyleSheet(f"""
            QPushButton#PrimaryBtn {{
                background: rgba(0, 240, 255, 0.15);
                border: 2px solid {THEME['primary_glow']};
                border-radius: 16px;
                color: {THEME['primary_glow']};
                font-weight: 900;
                font-size: 15px;
                letter-spacing: 6px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background: rgba(0, 240, 255, 0.3);
                color: white;
            }}
            QPushButton#PrimaryBtn.busy {{
                background: rgba(0, 240, 255, 0.05);
                border-color: rgba(0, 240, 255, 0.4);
                color: rgba(0, 240, 255, 0.6);
            }}
        """)
        self.login_btn.clicked.connect(self._do_login)
        
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"color: {THEME['accent_error']}; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.hide()
        
        layout.addWidget(self.user_field, 0, Qt.AlignCenter)
        layout.addWidget(self.pass_field, 0, Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn, 0, Qt.AlignCenter)
        layout.addWidget(self.error_lbl, 0, Qt.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        if self._cached_bg.isNull() or self._cached_bg.size() != self.size():
            self._cached_bg = self._bg_source.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        p.drawPixmap(0, 0, self._cached_bg)
        
        # Cinematic vignetting
        grad = QRadialGradient(QPointF(self.width()/2, self.height()/2), self.width())
        grad.setColorAt(0, QColor(0, 0, 0, 80))
        grad.setColorAt(0.7, QColor(0, 0, 0, 180))
        grad.setColorAt(1, QColor(0, 0, 0, 240))
        p.fillRect(self.rect(), grad)

    def _toggle_password(self, checked):
        if checked:
            self.pass_field.setEchoMode(QLineEdit.Normal)
        else:
            self.pass_field.setEchoMode(QLineEdit.Password)

    def _do_login(self):
        uid = self.user_field.text()
        pwd = self.pass_field.text()
        if not uid or not pwd:
            self.show_error("CREDENTIALS_REQUIRED")
            return
            
        self.login_btn.setEnabled(False)
        self.login_btn.setText("VERIFYING...")
        self.login_btn.setProperty("class", "busy")
        self.login_btn.style().unpolish(self.login_btn)
        self.login_btn.style().polish(self.login_btn)
        self.setCursor(Qt.WaitCursor)
        
        from system.auth_manager import get_auth_manager
        am = get_auth_manager()
        if am:
            if not hasattr(self, "_connected"):
                am.login_failed.connect(self._on_login_failed)
                am.state_changed.connect(self._on_auth_state_changed)
                self._connected = True
            am.request_login(uid, pwd)
        else:
            logger.error("[LoginScreen] AuthManager not found!")
            self.show_error("SYSTEM_FAULT")
            self.setCursor(Qt.ArrowCursor)

    def _on_login_failed(self, error):
        self.show_error(error.get("message", "AUTH_FAILED"))
        self.login_btn.setEnabled(True)
        self.login_btn.setText("SIGN-IN")
        self.login_btn.setProperty("class", "")
        self.login_btn.style().unpolish(self.login_btn)
        self.login_btn.style().polish(self.login_btn)
        self.setCursor(Qt.ArrowCursor)

    def _on_auth_state_changed(self, new_state, old_state):
        if new_state == "logged_in":
            self.setCursor(Qt.ArrowCursor)
            # LoginScreen is likely hidden by the stack, but good practice

    def show_error(self, text):
        self.error_lbl.setText(text)
        QTimer.singleShot(3000, lambda: self.error_lbl.setText(""))
