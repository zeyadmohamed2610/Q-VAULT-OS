from assets.theme import *
# =============================================================
#  sudo_dialog.py — Q-Vault OS  |  Sudo Authentication Dialog
#
#  Shows a modal password prompt when the user types "sudo".
#  Caches elevation for 5 minutes via SecurityAPI.
# =============================================================

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont

from system.security_api import get_security_api


_STYLE = f"""
    QDialog#SudoDialog {{
        background: {THEME['bg_dark']};
    }}
    QLabel#SudoTitle {{
        color: {THEME['warning']};
        font-family: 'Consolas', monospace;
        font-size: 14px;
        font-weight: bold;
        background: transparent;
    }}
    QLabel#SudoBody {{
        color: {THEME['text_dim']};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
    }}
    QLabel#SudoError {{
        color: {THEME['accent_error']};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
        min-height: 14px;
    }}
    QLineEdit#SudoPw {{
        background: {THEME['bg_black']};
        color: {THEME['text_main']};
        font-family: 'Consolas', monospace;
        font-size: 13px;
        border: 1px solid {THEME['border_subtle']};
        border-radius: 6px;
        padding: 8px 12px;
    }}
    QLineEdit#SudoPw:focus {{
        border: 1px solid {THEME['warning']};
    }}
    QPushButton#SudoOk {{
        background: {THEME['warning']};
        color: {THEME['bg_black']};
        border: none;
        border-radius: 6px;
        padding: 8px 24px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#SudoOk:hover {{
        background: {THEME['warning_soft']};
    }}
    QPushButton#SudoCancel {{
        background: transparent;
        color: {THEME['text_dim']};
        border: 1px solid {THEME['border_subtle']};
        border-radius: 6px;
        padding: 8px 24px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
    }}
    QPushButton#SudoCancel:hover {{
        background: {THEME['hover_subtle']};
        color: {THEME['text_main']};
    }}
"""


class SudoDialog(QDialog):
    """
    Modal password dialog for sudo elevation.
    Returns QDialog.Accepted if password verified, Rejected otherwise.
    """

    def __init__(self, command: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("SudoDialog")
        self.setWindowTitle("Authenticate")
        self.setModal(True)
        self.setFixedWidth(400)
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setStyleSheet(_STYLE)
        self._attempts = 0
        self._api = get_security_api()
        self._build_ui(command)

    def _build_ui(self, command: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        icon = QLabel("[sudo]")
        icon.setStyleSheet(
            f"font-size:14px; font-weight:bold; "
            f"color:{THEME['warning']}; background:transparent;"
        )
        title = QLabel("sudo -- Authentication Required")
        title.setObjectName("SudoTitle")
        hdr.addWidget(icon)
        hdr.addWidget(title, stretch=1)
        layout.addLayout(hdr)

        # User info
        user = self._api.get_current_user()
        uname = user.username if user else "user"
        cmd_text = f"  Command: {command}" if command else ""
        body = QLabel(
            f"[sudo] Password for {uname}:{cmd_text}\n"
            f"Elevation cached for 5 minutes after success."
        )
        body.setObjectName("SudoBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        # Password field
        self._pw = QLineEdit()
        self._pw.setObjectName("SudoPw")
        self._pw.setEchoMode(QLineEdit.Password)
        self._pw.setPlaceholderText("Enter your password...")
        self._pw.returnPressed.connect(self._try_auth)
        layout.addWidget(self._pw)

        # Error label
        self._err = QLabel("")
        self._err.setObjectName("SudoError")
        layout.addWidget(self._err)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SudoCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Authenticate")
        btn_ok.setObjectName("SudoOk")
        btn_ok.clicked.connect(self._try_auth)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        # Already-active cache notice
        if self._api.sudo_granted:
            rem = self._api.sudo_remaining()
            note = QLabel(f"[i]  Sudo already active ({rem}s remaining)")
            note.setStyleSheet(
                f"color:{THEME['success']}; font-family:'Consolas',monospace;"
                f"font-size:10px; background:transparent;"
            )
            layout.addWidget(note)

        self._pw.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(THEME['bg_dark']))
        painter.setPen(QColor(THEME['warning']))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

    def _try_auth(self):
        pw = self._pw.text()
        if not pw:
            self._err.setText("password cannot be empty")
            return

        # If sudo already cached, accept immediately
        if self._api.sudo_granted:
            self.accept()
            return

        granted = self._api.sudo_request(pw)
        if granted:
            self._err.setText("")
            self.accept()
        else:
            self._attempts += 1
            self._pw.clear()
            remaining = 3 - self._attempts
            if self._attempts >= 3:
                self._err.setText(
                    f"[!]  {self._attempts} failed attempts. access denied."
                )
                QTimer.singleShot(1500, self.reject)
            else:
                self._err.setText(
                    f"[x]  incorrect password. {remaining} attempt(s) remaining."
                )
            self._shake()

    def _shake(self):
        offsets = [8, -8, 6, -6, 3, -3, 0]
        self._shake_step(offsets)

    def _shake_step(self, offsets: list):
        if not offsets:
            return
        self.move(self.x() + offsets[0], self.y())
        QTimer.singleShot(35, lambda: self._shake_step(offsets[1:]))


def ask_sudo(command: str = "", parent=None) -> bool:
    """
    Show the sudo dialog.  Returns True if elevation was granted.
    If sudo is already cached, returns True without prompting.
    """
    api = get_security_api()
    if api.sudo_granted:
        return True
    dlg = SudoDialog(command=command, parent=parent)
    return dlg.exec_() == QDialog.Accepted


# ── Generic password dialog for "Run as Administrator" ───────────────────────

class SudoPasswordDialog(QDialog):
    """
    Generic dark-themed password dialog.
    Used for 'Run as Administrator' and any custom elevation prompts.
    Exposes get_password() after accept().
    """

    def __init__(self, title: str = "Authentication Required",
                 message: str = "Enter your password:",
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 240)
        self.setModal(True)
        self._password = ""
        self._build_ui(title, message)

        # Center on screen
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    def _build_ui(self, title: str, message: str):
        from PyQt5.QtGui import QPainter, QColor, QPalette
        container = QWidget(self)
        container.setGeometry(0, 0, 380, 240)
        container.setAutoFillBackground(True)

        pal = container.palette()
        pal.setColor(QPalette.Window, QColor(11, 25, 41))
        container.setPalette(pal)

        container.setStyleSheet("""
            QWidget {
                background-color: #0b1929;
                color: #d4e8f0;
            }
            QLabel { background: transparent; border: none; color: #d4e8f0; }
            QLineEdit {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(0, 200, 255, 0.3);
                border-radius: 8px;
                color: white;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #00e6ff; }
            QPushButton {
                background: rgba(0,180,255,0.15);
                border: 1px solid rgba(0,200,255,0.3);
                border-radius: 8px;
                color: #00e6ff;
                padding: 7px 22px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(0,180,255,0.3); }
            QPushButton#BtnCancel {
                background: transparent;
                color: rgba(255,255,255,0.4);
                border: 1px solid rgba(255,255,255,0.1);
            }
            QPushButton#BtnCancel:hover { background: rgba(255,255,255,0.07); color: white; }
        """)

        vl = QVBoxLayout(container)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(10)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_title.setStyleSheet("color: #00e6ff; background: transparent;")

        lbl_msg = QLabel(message)
        lbl_msg.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 11px; background: transparent;")
        lbl_msg.setWordWrap(True)

        self._pw_field = QLineEdit()
        self._pw_field.setEchoMode(QLineEdit.Password)
        self._pw_field.setPlaceholderText("Password…")
        self._pw_field.returnPressed.connect(self._on_ok)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnCancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Authenticate")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)

        vl.addWidget(lbl_title)
        vl.addWidget(lbl_msg)
        vl.addSpacing(4)
        vl.addWidget(self._pw_field)
        vl.addStretch()
        vl.addLayout(btn_row)

        self._pw_field.setFocus()

    def _on_ok(self):
        self._password = self._pw_field.text()
        self.accept()

    def get_password(self) -> str:
        return self._password

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
        painter.fillPath(path, QColor(11, 25, 41))
        painter.setPen(QPen(QColor(0, 200, 255, 55), 1.0))
        painter.drawPath(path)
        painter.end()
