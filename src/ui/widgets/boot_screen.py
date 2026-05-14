from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from resources.theme import THEME

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
        from resources.theme import THEME
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: #000;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # 1. Immediate UI Component Definition
        self.lbl_logo = QLabel("Q-VAULT")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setFont(QFont("Segoe UI", 42, QFont.Bold))
        self.lbl_logo.setStyleSheet(f"color: {THEME['primary_glow']}; letter-spacing: 12px; margin-top: 40px;")

        self.lbl_sub = QLabel("SOVEREIGN ARCHITECTURE v1.0")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setStyleSheet("color: rgba(0,230,255,0.4); font-size: 10px; letter-spacing: 5px; font-weight: bold;")

        self.prog_container = QWidget()
        self.prog_container.setFixedWidth(400)
        self.prog_container.setFixedHeight(4)
        self.prog_container.setStyleSheet(f"background: rgba(0, 230, 255, 0.05); border-radius: 2px;")
        
        self.prog_bar = QFrame(self.prog_container)
        self.prog_bar.setGeometry(0, 0, 0, 4)
        self.prog_bar.setStyleSheet(f"background: {THEME['primary_glow']}; border-radius: 2px;")

        self.lbl_status = QLabel("INITIALIZING...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 11px; font-family: 'Consolas'; margin-top: 10px;")

        self.spinner = QLabel("·  ·  ·")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 14px; margin-top: 5px;")

        # 2. Layout Assembly
        layout.addStretch(1)
        layout.addWidget(self.lbl_logo)
        layout.addWidget(self.lbl_sub)
        layout.addSpacing(60)
        layout.addWidget(self.prog_container, alignment=Qt.AlignCenter)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.spinner)
        layout.addStretch(1)

        # 3. State & Timers
        self._stage = 0
        self._dots = 0
        
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._spin)
        self._spin_timer.start(250)

        QTimer.singleShot(500, self._next_stage)

    def _spin(self):
        frames = ["·  ·  ·", "●  ·  ·", "·  ●  ·", "·  ·  ●"]
        self._dots = (self._dots + 1) % len(frames)
        self.spinner.setText(frames[self._dots])

    def _next_stage(self):
        if self._stage >= len(BOOT_STAGES):
            self.lbl_status.setText("SYSTEM READY")
            self.prog_bar.setFixedWidth(400)
            QTimer.singleShot(800, self.boot_finished.emit)
            return

        _, msg, delay = BOOT_STAGES[self._stage]
        self.lbl_status.setText(f">> {msg.upper()}")
        
        # Animate progress bar
        target_w = int(400 * ((self._stage + 1) / len(BOOT_STAGES)))
        from PyQt5.QtCore import QPropertyAnimation, QRect
        self._anim = QPropertyAnimation(self.prog_bar, b"geometry")
        self._anim.setDuration(delay)
        self._anim.setEndValue(QRect(0, 0, target_w, 4))
        self._anim.start()

        self._stage += 1
        QTimer.singleShot(delay + 50, self._next_stage)
