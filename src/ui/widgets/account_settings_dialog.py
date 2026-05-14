import logging
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath

from system.auth_manager import AuthManager
from resources import theme

logger = logging.getLogger(__name__)

# ── Theme Constants ──
_BG       = "#07111f"
_CYAN     = theme.THEME['primary_glow']
_TEXT     = theme.THEME['text_main']
_MUTED    = theme.THEME['text_muted']
_RED      = theme.THEME['accent_error']
_GREEN    = theme.THEME['success']

_INPUT_STYLE = f"""
    QLineEdit {{
        background: rgba(0,0,0,0.45);
        border: 1px solid rgba(0,210,255,0.2);
        border-radius: 8px;
        color: {_TEXT};
        padding: 12px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border: 1px solid {_CYAN};
        background: rgba(0,230,255,0.05);
    }}
"""

_BTN_STYLE = f"""
    QPushButton {{
        background: rgba(0,230,255,0.12);
        border: 1px solid rgba(0,230,255,0.3);
        border-radius: 8px;
        color: {_CYAN};
        padding: 12px;
        font-weight: bold;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background: rgba(0,230,255,0.22);
        border-color: {_CYAN};
    }}
"""

class AccountSettingsDialog(QDialog):
    """
    Sovereign Account Management.
    Allows users to synchronize their display name and master password.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 500)
        self._auth = AuthManager()
        self._setup_ui()

    def _setup_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 400, 500)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Header
        hdr = QLabel("ACCOUNT SETTINGS")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(f"color: {_CYAN}; font-size: 18px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(hdr)

        layout.addSpacing(10)

        # Current Identity Label
        curr = QLabel(f"Current Identity: {self._auth.username or 'Unknown'}")
        curr.setStyleSheet(f"color: {_MUTED}; font-size: 10px; font-weight: 800;")
        layout.addWidget(curr)

        # Fields
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("NEW DISPLAY NAME")
        self.display_name.setText(self._auth.display_name)
        self.display_name.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.display_name)

        layout.addSpacing(10)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background: rgba(0,240,255,0.1);"); layout.addWidget(sep)
        layout.addSpacing(10)

        self.old_pwd = QLineEdit()
        self.old_pwd.setPlaceholderText("CURRENT PASSWORD")
        self.old_pwd.setEchoMode(QLineEdit.Password)
        self.old_pwd.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.old_pwd)

        self.new_pwd = QLineEdit()
        self.new_pwd.setPlaceholderText("NEW SOVEREIGN PASSWORD")
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.new_pwd)

        layout.addStretch()

        # Status Label
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"color: {_RED}; font-size: 11px;")
        layout.addWidget(self.status)

        # Buttons
        btns = QHBoxLayout()
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setStyleSheet(_BTN_STYLE.replace(_CYAN, _MUTED).replace("rgba(0,230,255,0.12)", "transparent"))
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        self.btn_save = QPushButton("SYNC CHANGES")
        self.btn_save.setStyleSheet(_BTN_STYLE)
        self.btn_save.clicked.connect(self._do_sync)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _do_sync(self):
        old_p = self.old_pwd.text()
        new_p = self.new_pwd.text()
        new_n = self.display_name.text().strip()

        if not old_p:
            self.status.setText("Current password required to verify identity.")
            return

        # 1. Verify Identity
        if not self._auth.verify_password(old_p):
            self.status.setText("Verification failed. Incorrect current password.")
            return

        # 2. Sync Display Name
        if new_n:
            self._auth.update_profile(new_n)

        # 3. Sync Password if provided
        if new_p:
            if len(new_p) < 6:
                self.status.setText("New password must be at least 6 characters.")
                return
            success = self._auth.change_password(new_p)
            if not success:
                self.status.setText("Failed to synchronize new password with core.")
                return

        self.status.setText("Identity synchronized successfully!")
        self.status.setStyleSheet(f"color: {_GREEN};")
        self.btn_save.setEnabled(False)
        QTimer.singleShot(1500, self.accept)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(path, QColor(7, 17, 31))
        painter.setPen(QColor(0, 230, 255, 40))
        painter.drawPath(path)
