from __future__ import annotations
import subprocess
import sys
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)

_CARD_STYLE = """
    QFrame#launcher_card {
        background: #040f22;
        border: 1px solid rgba(84,177,198,0.25);
        border-radius: 16px;
    }
"""

_BTN = """
    QPushButton {
        background: rgba(15,40,66,0.6);
        color: #d4e8f0;
        border: 1px solid rgba(84,177,198,0.15);
        border-radius: 10px;
        padding: 10px 0;
        font-family: 'Segoe UI';
        font-size: 10pt;
        text-align: center;
    }
    QPushButton:hover {
        background: rgba(84,177,198,0.18);
        border-color: rgba(84,177,198,0.45);
        color: #7dd3e8;
    }
    QPushButton:pressed { background: rgba(84,177,198,0.28); }
"""

_BTN_DANGER = _BTN + """
    QPushButton {
        color: #f85149;
        border-color: rgba(248,81,73,0.20);
    }
    QPushButton:hover {
        background: rgba(248,81,73,0.15);
        border-color: rgba(248,81,73,0.50);
        color: #ff7b72;
    }
"""


class LauncherPanel(QWidget):
    """
    System launcher popup.
    Signals:
        lock_requested  — caller should trigger session lock
        logout_requested
    """
    lock_requested   = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(230)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("launcher_card")
        card.setStyleSheet(_CARD_STYLE)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        # Header
        title = QLabel("Q-Vault OS")
        title.setFont(QFont("Segoe UI Semibold", 13))
        title.setStyleSheet("color:#54b1c6; background:transparent;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        ver = QLabel("v1.0 · admin")
        ver.setFont(QFont("Segoe UI", 9))
        ver.setStyleSheet("color:#4a6880; background:transparent;")
        ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:rgba(84,177,198,0.10);")
        div.setFixedHeight(1)
        lay.addWidget(div)
        lay.addSpacing(4)

        from components.storage_ui import StorageWidget
        lay.addWidget(StorageWidget())
        lay.addSpacing(8)

        # Session buttons
        for label, fn, style in [
            ("🔒  Lock Screen", self._lock,    _BTN),
            ("💤  Sleep",       self._sleep,   _BTN),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.clicked.connect(fn)
            lay.addWidget(btn)

        lay.addSpacing(4)

        # System buttons
        for label, fn, style in [
            ("↺  Restart",   self._restart,  _BTN),
            ("⏻  Shut Down", self._shutdown, _BTN_DANGER),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(style)
            btn.clicked.connect(fn)
            lay.addWidget(btn)

        outer.addWidget(card)

    # ── Actions ──────────────────────────────────────────────

    def _lock(self):
        self.hide()
        self.lock_requested.emit()

    def _sleep(self):
        self.hide()
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                    check=False
                )
            else:
                subprocess.run(["systemctl", "suspend"], check=False)
        except Exception as exc:
            logger.warning("Sleep failed: %s", exc)

    def _restart(self):
        self.hide()
        try:
            import sys
            import os
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as exc:
            logger.warning("Restart failed: %s", exc)

    def _shutdown(self):
        self.hide()
        try:
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
        except Exception as exc:
            logger.warning("Shutdown failed: %s", exc)

    def popup_above(self, pos: QPoint):
        self.adjustSize()
        self.move(pos.x() - self.width() // 2,
                  pos.y() - self.height() - 12)
        self.show()
