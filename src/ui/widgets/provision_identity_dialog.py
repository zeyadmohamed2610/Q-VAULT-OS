import logging
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath

from system.security_controller import get_security_controller

logger = logging.getLogger(__name__)

# ── Theme Constants ──
_BG       = "#07111f"
_CYAN     = "#00e6ff"
_TEXT     = "#cce8f4"
_MUTED    = "rgba(180,220,240,0.45)"
_RED      = "#ff5f5f"
_GREEN    = "#3dffa0"

_INPUT_STYLE = f"""
    QLineEdit {{
        background: rgba(0,0,0,0.45);
        border: 1px solid rgba(0,210,255,0.2);
        border-radius: 8px;
        color: {_TEXT};
        padding: 12px;
        font-size: 13px;
        font-family: 'Consolas', monospace;
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
        font-family: 'Segoe UI';
        font-size: 13px;
    }}
    QPushButton:hover {{
        background: rgba(0,230,255,0.22);
        border-color: {_CYAN};
    }}
    QPushButton:disabled {{
        background: rgba(255,255,255,0.05);
        color: rgba(255,255,255,0.2);
    }}
"""

class ProvisionIdentityDialog(QDialog):
    """
    Sovereign Identity Provisioning UI.
    Allows creation of new administrative users in the Rust Security Core.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 520)
        self._setup_ui()
        self._controller = get_security_controller()
        if self._controller:
            self._controller.provision_finished.connect(self._on_provision_finished)

    def _setup_ui(self):
        container = QWidget(self)
        container.setGeometry(0, 0, 420, 520)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        hdr = QLabel("PROVISION IDENTITY")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(f"color: {_CYAN}; font-size: 18px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(hdr)

        sub = QLabel("Establish a new sovereign administrative credential.")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        layout.addWidget(sub)

        layout.addSpacing(10)

        # Fields
        self.uname = QLineEdit()
        self.uname.setPlaceholderText("NEW USERNAME")
        self.uname.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.uname)

        self.pwd = QLineEdit()
        self.pwd.setPlaceholderText("SOVEREIGN PASSWORD")
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.pwd)

        self.pwd_confirm = QLineEdit()
        self.pwd_confirm.setPlaceholderText("CONFIRM PASSWORD")
        self.pwd_confirm.setEchoMode(QLineEdit.Password)
        self.pwd_confirm.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self.pwd_confirm)

        layout.addStretch()

        # Status Label
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: #ff5f5f; font-size: 11px;")
        layout.addWidget(self.status)

        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ background: rgba(255,255,255,0.05); border: none; border-radius: 2px; }} QProgressBar::chunk {{ background: {_CYAN}; }}")
        self.progress.hide()
        layout.addWidget(self.progress)

        # Buttons
        btns = QHBoxLayout()
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setStyleSheet(_BTN_STYLE.replace(_CYAN, _MUTED).replace("rgba(0,230,255,0.12)", "transparent"))
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        self.btn_create = QPushButton("CREATE IDENTITY")
        self.btn_create.setStyleSheet(_BTN_STYLE)
        self.btn_create.clicked.connect(self._do_provision)
        btns.addWidget(self.btn_create)
        layout.addLayout(btns)

    def _do_provision(self):
        uname = self.uname.text().strip()
        pwd = self.pwd.text()
        conf = self.pwd_confirm.text()

        if not uname or not pwd:
            self.status.setText("All fields are required.")
            return
        
        if pwd != conf:
            self.status.setText("Passwords do not match.")
            return
            
        if len(pwd) < 8:
            self.status.setText("Password must be at least 8 characters.")
            return

        self.btn_create.setEnabled(False)
        self.status.setText("Provisioning in sovereign core...")
        self.status.setStyleSheet(f"color: {_CYAN};")
        self.progress.show()
        self.progress.setRange(0, 0) # Indeterminate

        if self._controller:
            self._controller.provision_user(uname, pwd, "admin")
        else:
            self._on_provision_finished({"success": False, "message": "Security Controller unavailable"})

    def _on_provision_finished(self, result: dict):
        self.progress.hide()
        self.btn_create.setEnabled(True)

        if result.get("success"):
            self.status.setText("Identity provisioned successfully!")
            self.status.setStyleSheet(f"color: {_GREEN};")
            QTimer.singleShot(1500, self.accept)
        else:
            msg = result.get("message", "Provisioning failed")
            self.status.setText(f"ERROR: {msg}")
            self.status.setStyleSheet(f"color: {_RED};")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        painter.fillPath(path, QColor(7, 17, 31))
        painter.setPen(QColor(0, 230, 255, 60))
        painter.drawPath(path)
