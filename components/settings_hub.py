from assets.theme import *
# =============================================================
#  components/settings_hub.py — Q-Vault OS
#
#  Centralized System Configuration.
#  Manages AI, Workflows, Themes, and Shortcuts.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget, QScrollArea
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont
from core.event_bus import EVENT_BUS, SystemEvent

class SettingsHub(QFrame):
    """
    The main control center for OS personalization.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(700, 500)
        self.setObjectName("SettingsHub")
        self._drag_pos = None

        # ───── Close Button ─────
        self.btn_close = QPushButton("X", self)
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.move(658, 10)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.1);
                color: {THEME['primary_glow']};
                font-weight: bold;
                border: 1px solid rgba(0, 230, 255, 0.4);
                border-radius: 8px;
                font-size: 16px;
                font-family: 'Arial', sans-serif;
            }}
            QPushButton:hover {{ background: {THEME['accent_error']}; color: white; border: none; }}
        """)
        self.btn_close.clicked.connect(self.hide)
        self.btn_close.raise_() 
        
        self.setStyleSheet(f"""
            QFrame#SettingsHub {{
                background: {THEME['surface_mid']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px;
            }}
            #Sidebar {{
                background: rgba(255, 255, 255, 0.03);
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {THEME['text_muted']};
                text-align: left;
                padding: 12px 20px;
                font-size: 13px;
                border-radius: 0;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 0.05); color: white; }}
            QPushButton#Active {{
                background: rgba(255, 255, 255, 0.08);
                color: {THEME['primary_glow']};
                border-left: 3px solid {THEME['primary_glow']};
            }}
            QLabel#Title {{ color: white; font-size: 18px; font-weight: bold; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ── Sidebar ──
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        
        logo = QLabel("⚙ SETTINGS")
        logo.setStyleSheet("color: white; font-weight: bold; padding: 0 20px 20px 20px;")
        sidebar_layout.addWidget(logo)
        
        self.btn_ai = self._add_nav_item(sidebar_layout, "Intelligence", 0)
        self.btn_wf = self._add_nav_item(sidebar_layout, "Workflows", 1)
        self.btn_sc = self._add_nav_item(sidebar_layout, "Shortcuts", 2)
        self.btn_ap = self._add_nav_item(sidebar_layout, "Appearance", 3)
        
        sidebar_layout.addStretch()
        layout.addWidget(self.sidebar)
        
        # ── Content Area ──
        self.content_container = QFrame()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        self.title = QLabel("Intelligence")
        self.title.setObjectName("Title")
        content_layout.addWidget(self.title)
        
        self.pages = QStackedWidget()
        
        # Wrap pages in a scroll area for responsiveness
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.pages)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.pages.addWidget(self._create_ai_page())        # Index 0
        self.pages.addWidget(self._create_workflow_page())  # Index 1
        self.pages.addWidget(self._create_shortcut_page())  # Index 2
        self.pages.addWidget(self._create_appearance_page())# Index 3
        
        content_layout.addWidget(self.scroll)
        layout.addWidget(self.content_container)

    def _add_nav_item(self, layout, name, index):
        btn = QPushButton(name)
        btn.clicked.connect(lambda: self._switch_tab(index))
        layout.addWidget(btn)
        if index == 0: btn.setObjectName("Active")
        return btn

    def _switch_tab(self, index):
        self.pages.setCurrentIndex(index)
        # Update styling
        for i, btn in enumerate(self.sidebar.findChildren(QPushButton)):
            if i == index: btn.setObjectName("Active")
            else: btn.setObjectName("")
        self.sidebar.setStyleSheet(self.sidebar.styleSheet()) # Force refresh
        
        titles = ["Intelligence", "Workflows", "Shortcuts", "Appearance"]
        if index < len(titles):
            self.title.setText(titles[index])

    def _create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        info = QLabel("Configure the autonomous behavior of Q-Vault OS.")
        info.setStyleSheet(f"color: {THEME['text_disabled']};")
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Simple Toggles (Placeholders)
        layout.addWidget(self._create_setting_row("Enable Reasoning Engine", True))
        layout.addWidget(self._create_setting_row("Continuous Learning", True))
        layout.addWidget(self._create_setting_row("External LLM Bridge", False))
        
        layout.addStretch()
        return page

    def _create_workflow_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Manage automated system behaviors."))
        
        layout.addWidget(self._create_setting_row("Auto-Optimization", True))
        layout.addWidget(self._create_setting_row("Security Hardening", True))
        layout.addWidget(self._create_setting_row("Log Rotation", False))
        
        layout.addStretch()
        return page

    def _create_shortcut_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Global System Shortcuts"))
        
        sc_layout = QVBoxLayout()
        sc_layout.addWidget(QLabel("Ctrl + Space:  Command Palette"))
        sc_layout.addWidget(QLabel("Ctrl + T:      Open Terminal"))
        sc_layout.addWidget(QLabel("Ctrl + L:      Toggle Launcher"))
        layout.addLayout(sc_layout)
        
        layout.addStretch()
        return page

    def _create_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Personalize your environment."))
        
        layout.addWidget(self._create_setting_row("Dark Mode", True))
        layout.addWidget(self._create_setting_row("Glassmorphism Effects", True))
        layout.addWidget(self._create_setting_row("Dynamic Wallpapers", False))
        
        layout.addStretch()
        return page

    def _create_setting_row(self, name, enabled):
        row = QFrame()
        row.setStyleSheet("background: rgba(255,255,255,0.02); border-radius: 8px; padding: 10px;")
        l = QHBoxLayout(row)
        l.addWidget(QLabel(name))
        l.addStretch()
        btn = QPushButton("ON" if enabled else "OFF")
        btn.setFixedWidth(50)
        btn.setStyleSheet(f"color: {THEME['success'] if enabled else THEME['text_muted']}; font-weight: bold;")
        l.addWidget(btn)
        return row

    def show_centered(self, parent_rect: QRect):
        x = (parent_rect.width() - self.width()) // 2
        y = (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()

    # ───── DRAGGING LOGIC ─────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.pos() - self._drag_pos
            self.move(self.pos() + delta)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
