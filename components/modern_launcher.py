from assets.theme import *
"""
components/modern_launcher.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS │ Phase 13.6 - High-Fidelity App Launcher

Responsive, grid-based overlay providing a modern entry point for all 
trusted applications.
─────────────────────────────────────────────────────────────────────────────
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QScrollArea, QGraphicsBlurEffect, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont, QPainter, QIcon, QLinearGradient
from core.event_bus import EVENT_BUS, SystemEvent

class AppIconWidget(QFrame):
    """Sleek neon app launcher tile."""
    clicked = pyqtSignal(object)

    def __init__(self, app_def, parent=None):
        super().__init__(parent)
        self.app_def = app_def
        self.setFixedSize(100, 110)
        self.setLineWidth(0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Icon Glyph
        from assets import theme
        self.emoji_lbl = QLabel(app_def.emoji)
        self.emoji_lbl.setAlignment(Qt.AlignCenter)
        self.emoji_lbl.setStyleSheet("font-size: 38px; background: transparent; border: none;")
        layout.addWidget(self.emoji_lbl)
        
        # Name
        self.name_lbl = QLabel(app_def.name)
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setStyleSheet(f"color: {theme.TEXT}; font-family: {theme.FONT_MONO}; font-size: 10px; border: none;")
        layout.addWidget(self.name_lbl)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid {theme.PRIMARY};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.app_def)

class ModernLauncher(QWidget):
    """
    v1.0 Production Launcher Overlay.
    Deep Matte Black with neon accents and intelligent filtering.
    """
    app_launched = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 450)
        self.setObjectName("ModernLauncher")
        
        from assets import theme
        self.setStyleSheet(f"""
            #ModernLauncher {{
                background: rgba(8, 10, 15, 0.98);
                border: 2px solid {theme.PRIMARY};
                border-radius: 20px;
            }}
        """)
        
        # ── Close Button (USER: Distinct and harmonious) ──
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.move(560, 8)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.TEXT_DIM};
                font-size: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ color: {THEME['accent_error']}; }}
        """)
        self.btn_close.clicked.connect(self.hide)

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(30, 40, 30, 30)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        self.root_layout.addLayout(main_layout)
        
        # ── Search Bar ──
        search_container = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Apps, Files, and Services...")
        self.search_bar.setFixedWidth(500)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background: #000;
                color: #fff;
                border: 1px solid {THEME['surface_raised']};
                border-radius: 20px;
                padding: 12px 25px;
                font-family: {theme.FONT_MONO};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.PRIMARY};
            }}
        """)
        self.search_bar.textChanged.connect(self._filter_apps)
        search_container.addWidget(self.search_bar)
        main_layout.addLayout(search_container)
        
        # ── App Grid ──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setContentsMargins(40, 0, 40, 0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        
        # Inner Flow layout wrapper
        self.flow_container = QWidget()
        self.flow_layout = QHBoxLayout(self.flow_container) 
        self.flow_layout.setSpacing(20)
        self.grid_layout.addWidget(self.flow_container)
        
        self.scroll.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll)
        
        # Refresh from registry
        self._refresh_apps()

    def _refresh_apps(self):
        from core.app_registry import REGISTRY
        from core.system_state import STATE
        
        # Clear current
        for i in reversed(range(self.flow_layout.count())):
            item = self.flow_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        session = getattr(STATE, "session_type", "real") or "real"
        apps = REGISTRY.apps_for_session(session)
        
        for app in apps:
            tile = AppIconWidget(app)
            tile.clicked.connect(self._on_app_clicked)
            self.flow_layout.addWidget(tile)

    def _filter_apps(self, query):
        query = query.lower()
        for i in range(self.flow_layout.count()):
            tile = self.flow_layout.itemAt(i).widget()
            if tile:
                match = query in tile.app_def.name.lower()
                tile.setVisible(match)

    def _on_app_clicked(self, app_def):
        EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": app_def.name}, source="ModernLauncher")
        self.app_launched.emit(app_def) # Keep for UI sync if needed
        self.hide()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self._refresh_apps() 
            if self.parent():
                p = self.parent()
                self.move((p.width() - self.width()) // 2, (p.height() - self.height()) // 2)
            self.show()
            self.raise_()
            self.search_bar.setFocus()
            self.search_bar.clear()

    def keyPressEvent(self, event):
        from PyQt5.QtCore import Qt
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)