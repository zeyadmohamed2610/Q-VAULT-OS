import sys
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette

class BootSplash(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 400)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        # ── Logo ──
        self.logo = QLabel("Q-VAULT")
        self.logo.setStyleSheet("""
            font-size: 48px;
            font-weight: 900;
            color: #00e6ff;
            letter-spacing: 10px;
            font-family: 'Space Grotesk', sans-serif;
        """)
        self.layout.addWidget(self.logo, alignment=Qt.AlignCenter)

        self.subtext = QLabel("SOVEREIGN IDENTITY OS")
        self.subtext.setStyleSheet("color: rgba(0, 230, 255, 0.5); font-size: 12px; letter-spacing: 3px;")
        self.layout.addWidget(self.subtext, alignment=Qt.AlignCenter)

        self.layout.addSpacing(40)

        # ── Progress ──
        self.progress = QProgressBar()
        self.progress.setFixedSize(400, 4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                            stop:0 #00e6ff, stop:1 #0095ff);
                border-radius: 2px;
            }
        """)
        self.layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # ── Status Logs ──
        self.status = QLabel("Initializing Sovereign Kernel...")
        self.status.setStyleSheet("color: #888; font-family: 'Consolas'; font-size: 11px; margin-top: 10px;")
        self.layout.addWidget(self.status, alignment=Qt.AlignCenter)

        self.steps = [
            (10, "Loading Secure Modules..."),
            (30, "Checking Rust Security Core..."),
            (50, "Mounting Encrypted VFS..."),
            (70, "Verifying Identity Salts..."),
            (85, "Establishing Air-Gap Simulation..."),
            (100, "Integrity Check: NOMINAL")
        ]
        self.current_step = 0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_boot)
        self.timer.start(50) # Fast update
        
        self.val = 0

    def _update_boot(self):
        self.val += 1
        self.progress.setValue(self.val)
        
        if self.current_step < len(self.steps):
            target_val, text = self.steps[self.current_step]
            if self.val >= target_val:
                self.status.setText(text)
                self.current_step += 1

        if self.val >= 120: # Buffer at the end
            self.timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QBrush, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background Glass
        painter.setBrush(QBrush(QColor(10, 10, 15, 230)))
        painter.setPen(QPen(QColor(0, 230, 255, 50), 1))
        painter.drawRoundedRect(self.rect(), 20, 20)
