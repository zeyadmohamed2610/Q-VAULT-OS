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
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor

from system.security_api import get_security_api


_STYLE = f"""
    QDialog#SudoDialog {{
        background: {theme.BG_PANEL};
    }}
    QLabel#SudoTitle {{
        color: {theme.ACCENT_AMBER};
        font-family: 'Consolas', monospace;
        font-size: 14px;
        font-weight: bold;
        background: transparent;
    }}
    QLabel#SudoBody {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
    }}
    QLabel#SudoError {{
        color: {theme.ACCENT_RED};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
        min-height: 14px;
    }}
    QLineEdit#SudoPw {{
        background: {theme.BG_DARK};
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 13px;
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 6px;
        padding: 8px 12px;
    }}
    QLineEdit#SudoPw:focus {{
        border: 1px solid {theme.ACCENT_AMBER};
    }}
    QPushButton#SudoOk {{
        background: {theme.ACCENT_AMBER};
        color: {theme.BG_DARK};
        border: none;
        border-radius: 6px;
        padding: 8px 24px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#SudoOk:hover {{
        background: #ffd080;
    }}
    QPushButton#SudoCancel {{
        background: transparent;
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 6px;
        padding: 8px 24px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
    }}
    QPushButton#SudoCancel:hover {{
        background: {theme.BG_HOVER};
        color: {theme.TEXT_PRIMARY};
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
            f"color:{theme.ACCENT_AMBER}; background:transparent;"
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
                f"color:{theme.ACCENT_GREEN}; font-family:'Consolas',monospace;"
                f"font-size:10px; background:transparent;"
            )
            layout.addWidget(note)

        self._pw.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_PANEL))
        painter.setPen(QColor(theme.ACCENT_AMBER))
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
