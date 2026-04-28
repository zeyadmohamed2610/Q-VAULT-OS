from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from assets.theme import THEME

class VolumeOSD(QFrame):
    """A professional Volume OSD overlay that appears during volume changes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 40)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(10, 12, 18, 0.95);
                border: 1px solid {THEME['primary_glow']}66;
                border-radius: 20px;
            }}
            QLabel {{ color: white; font-family: 'Consolas'; font-size: 11px; font-weight: bold; }}
            QProgressBar {{
                background: rgba(255, 255, 255, 0.05);
                border: none;
                height: 4px;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {THEME['primary_glow']};
                border-radius: 2px;
            }}
        """)
        
        self.layout = QHBoxLayout(self)
        self.icon_lbl = QLabel("🔊")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.val_lbl = QLabel("0%")
        
        self.layout.addWidget(self.icon_lbl)
        self.layout.addWidget(self.bar)
        self.layout.addWidget(self.val_lbl)
        
        self.hide()
        self.timer = QTimer()
        self.timer.timeout.connect(self.hide_osd)

    def show_volume(self, value):
        self.bar.setValue(value)
        self.val_lbl.setText(f"{value}%")
        self.show()
        self.raise_()
        
        # Center at top
        if self.parent():
            pw = self.parent().width()
            self.move((pw - self.width()) // 2, 80)
            
        self.timer.start(2000) # Hide after 2s

    def hide_osd(self):
        self.hide()
