# =============================================================
#  splash_screen.py - Q-Vault OS  |  Startup Splash Screen
# =============================================================

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEasingCurve
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QFont
from PyQt5.QtWidgets import QWidget

from assets import theme


class SplashScreen(QWidget):
    splash_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )  # type: ignore
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # type: ignore
        self.setMinimumSize(600, 400)

        self._animation_progress = 0.0
        self._phase = "fade_in"

        self._setup_ui()
        self._start_animations()

    def _setup_ui(self):
        from PyQt5.QtWidgets import QVBoxLayout, QLabel

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        container = QWidget(self)
        container.setObjectName("SplashContainer")
        container.setStyleSheet(
            f"""
            QWidget#SplashContainer {{
                background: rgba(2, 6, 23, 240);
                border: 1px solid {theme.BORDER_BRIGHT};
                border-radius: 16px;
            }}
            """
        )

        vbox = QVBoxLayout(container)
        vbox.setSpacing(12)
        vbox.setAlignment(Qt.AlignCenter)

        logo = QLabel("Q")
        logo.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.ACCENT_CYAN};
                font-family: 'Consolas', monospace;
                font-size: 120px;
                font-weight: bold;
                background: transparent;
            }}
            """
        )
        logo.setAlignment(Qt.AlignCenter)
        vbox.addWidget(logo)

        title = QLabel("Q-VAULT OS")
        title.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.ACCENT_ICE};
                font-family: 'Consolas', monospace;
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 4px;
                background: transparent;
            }}
            """
        )
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        subtitle = QLabel("Secure Operating System")
        subtitle.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.TEXT_DIM};
                font-family: 'Consolas', monospace;
                font-size: 12px;
                letter-spacing: 2px;
                background: transparent;
            }}
            """
        )
        subtitle.setAlignment(Qt.AlignCenter)
        vbox.addWidget(subtitle)

        version = QLabel("Version 4.0 | Professional Edition")
        version.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.BORDER_DIM};
                font-family: 'Consolas', monospace;
                font-size: 10px;
                background: transparent;
                margin-top: 20px;
            }}
            """
        )
        version.setAlignment(Qt.AlignCenter)
        vbox.addWidget(version)

        layout.addWidget(container, 0, Qt.AlignCenter)

    def _start_animations(self):
        from PyQt5.QtCore import QPropertyAnimation

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(800)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_in_complete)
        self._fade_anim.start()

    def _on_fade_in_complete(self):
        QTimer.singleShot(1500, self._fade_out)

    def _fade_out(self):
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(600)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.finished.connect(self.splash_complete.emit)
        self._fade_anim.start()
