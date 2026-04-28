from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from assets.theme import THEME

BOOT_STAGES = [
    ("Q-Vault OS",              "Initializing Q-Vault Core...",    100),
    ("Q-Vault OS",              "Mounting Secure Sandbox...",      100),
    ("Q-Vault OS",              "Verifying Cryptographic Engine...", 100),
    ("Q-Vault OS",              "Launching Workspace Manager...",  100),
    ("Q-Vault OS",              "System Ready.",                   100),
]

class BootScreen(QWidget):
    boot_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background: #000;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # Logo
        self.lbl_logo = QLabel("Q-VAULT")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setFont(QFont("Consolas", 36, QFont.Bold))
        self.lbl_logo.setStyleSheet(f"color: {THEME['primary_glow']}; letter-spacing: 6px;")

        self.lbl_sub = QLabel("SECURE DESKTOP ENVIRONMENT")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setStyleSheet("color: rgba(0,170,255,0.5); font-size: 11px; letter-spacing: 4px;")

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 12px; font-family: Consolas;")

        # Spinner dots
        self.spinner = QLabel("·  ·  ·")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 20px; letter-spacing: 4px;")

        layout.addWidget(self.lbl_logo)
        layout.addWidget(self.lbl_sub)
        layout.addSpacing(30)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.spinner)

        self._stage = 0
        self._dots = 0

        # Spinner timer
        self._spin_timer = QTimer()
        self._spin_timer.timeout.connect(self._spin)
        self._spin_timer.start(250)

        # Start boot sequence
        QTimer.singleShot(400, self._next_stage)

    def _spin(self):
        frames = ["·  ·  ·", "●  ·  ·", "·  ●  ·", "·  ·  ●"]
        self._dots = (self._dots + 1) % len(frames)
        self.spinner.setText(frames[self._dots])

    def _next_stage(self):
        if self._stage >= len(BOOT_STAGES):
            self._spin_timer.stop()
            self.lbl_status.setText("[ OK ] System ready.")
            QTimer.singleShot(600, self.boot_finished.emit)
            return

        _, msg, delay = BOOT_STAGES[self._stage]
        self.lbl_status.setText(f"[ .... ] {msg}")
        self._stage += 1
        QTimer.singleShot(delay, self._next_stage)
