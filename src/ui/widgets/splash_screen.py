import os
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEasingCurve, QPointF
from PyQt5.QtGui import QColor, QRadialGradient, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtSvg import QSvgWidget

from resources import theme
from core.resources import get_asset_path


class SplashScreen(QWidget):
    splash_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.resize(800, 500)
        
        # Setup background painting
        bg_path = get_asset_path("qvault_vault.jpg")
        self._bg_source = QPixmap()
        if os.path.exists(bg_path):
            self._bg_source.load(bg_path)
        self._cached_bg = QPixmap()

        self._setup_ui()
        self._start_animations()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        container = QWidget(self)
        container.setFixedSize(800, 450)
        container.setStyleSheet("background: transparent;")

        vbox = QVBoxLayout(container)
        vbox.setSpacing(20)
        vbox.setAlignment(Qt.AlignCenter)

        # SVG Logo
        logo_path = get_asset_path("icons/qvault_logo.svg")
        if os.path.exists(logo_path):
            logo = QSvgWidget(logo_path)
            logo.setFixedSize(140, 140)
            
            # Glow effect
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(50)
            glow.setColor(QColor(0, 240, 255, 180))
            glow.setOffset(0, 0)
            logo.setGraphicsEffect(glow)
            vbox.addWidget(logo, 0, Qt.AlignCenter)
        else:
            # Fallback
            logo = QLabel("Q")
            logo.setStyleSheet(f"color: {theme.CYAN_BRIGHT}; font-family: 'Consolas', monospace; font-size: 80px; font-weight: bold; background: transparent; letter-spacing: 4px;")
            logo.setAlignment(Qt.AlignCenter)
            vbox.addWidget(logo, 0, Qt.AlignCenter)

        # Title
        title = QLabel("Q-VAULT SOVEREIGN")
        title.setStyleSheet(f"""
            color: {theme.CYAN};
            font-family: 'Inter', 'Segoe UI', 'Consolas', monospace;
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 4px;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # Title Glow
        t_glow = QGraphicsDropShadowEffect()
        t_glow.setBlurRadius(20)
        t_glow.setColor(QColor(0, 240, 255, 120))
        t_glow.setOffset(0, 0)
        title.setGraphicsEffect(t_glow)
        vbox.addWidget(title)

        # Subtitle
        subtitle = QLabel("SOVEREIGN INTELLIGENCE GATEWAY")
        subtitle.setStyleSheet(f"""
            color: {theme.TEXT_SEC};
            font-family: 'Inter', 'Segoe UI', 'Consolas', monospace;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 6px;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        vbox.addWidget(subtitle)

        # Version
        version = QLabel("v1.0.0-SOVEREIGN | CORE INITIALIZATION")
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.3);
            font-family: 'Inter', 'Segoe UI', 'Consolas', monospace;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 3px;
            background: transparent;
            margin-top: 40px;
        """)
        version.setAlignment(Qt.AlignCenter)
        vbox.addWidget(version)

        layout.addWidget(container, 0, Qt.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Fill solid base
        p.fillRect(self.rect(), QColor("#020408"))
        
        # Draw background image if available
        if not self._cached_bg.isNull() or not self._bg_source.isNull():
            if self._cached_bg.isNull() or self._cached_bg.size().width() < self.width():
                self._cached_bg = self._bg_source.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Perfect centering
            target_rect = self._cached_bg.rect()
            target_rect.moveCenter(self.rect().center())
            p.drawPixmap(target_rect, self._cached_bg)
        
        # Apply heavy cinematic vignetting and color tint
        grad = QRadialGradient(QPointF(self.width()/2, self.height()/2), self.width() * 0.8)
        grad.setColorAt(0, QColor(2, 4, 8, 140))     # Center more visible
        grad.setColorAt(0.7, QColor(2, 4, 8, 230))   # Fast falloff
        grad.setColorAt(1, QColor(0, 0, 0, 255))     # Deep black edges
        p.fillRect(self.rect(), grad)

        # Draw a glowing border around the splash screen
        border_pen = p.pen()
        border_pen.setColor(QColor(0, 240, 255, 60))
        border_pen.setWidth(1)
        p.setPen(border_pen)
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def _start_animations(self):
        from PyQt5.QtCore import QPropertyAnimation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(1200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_in_complete)
        self._fade_anim.start()

    def _on_fade_in_complete(self):
        # Hold for a moment
        QTimer.singleShot(2200, self._fade_out)

    def _fade_out(self):
        self.splash_complete.emit()
        self.close()

