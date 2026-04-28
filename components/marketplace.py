from assets.theme import *
# =============================================================
#  components/marketplace.py — Q-Vault OS
#
#  The Ecosystem Storefront.
#  Browse, Install, and Manage third-party extensions.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea, QLineEdit
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QColor
from core.event_bus import EVENT_BUS, SystemEvent
from system.marketplace.plugin_registry import PLUGIN_REGISTRY

class Marketplace(QFrame):
    """
    Discovery and Management hub for Plugins.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 500)
        self.setObjectName("Marketplace")
        self._drag_pos = None

        # ───── Close Button ─────
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.move(560, 10)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text_disabled']};
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ color: {THEME['accent_error']}; }}
        """)
        self.btn_close.clicked.connect(self.hide)
        
        self.setStyleSheet(f"""
            QFrame#Marketplace {{
                background: {THEME['bg_dark']};
                border: 1px solid rgba(0, 230, 255, 0.2);
                border-radius: 20px;
            }}
            QLineEdit {{
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(0, 230, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 10px;
                font-size: 14px;
            }}
            QScrollArea {{ background: transparent; border: none; }}
            #MarketContent {{ background: transparent; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📦 ECOSYSTEM MARKETPLACE")
        title.setStyleSheet(f"color: {THEME['primary_glow']}; font-weight: bold; font-size: 18px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search for plugins, tools, or integrations...")
        layout.addWidget(self.search)
        
        layout.addSpacing(20)
        
        # Plugin List
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setObjectName("MarketContent")
        self.grid = QVBoxLayout(self.content)
        self.grid.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        
        self._refresh_list()

    def _refresh_list(self):
        # Clear existing safely
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            
        plugins = PLUGIN_REGISTRY.get_all_plugins()
        
        if not plugins:
            empty = QLabel("No plugins found in the repository.")
            empty.setStyleSheet(f"color: {THEME['text_disabled']}; margin-top: 20px;")
            self.grid.addWidget(empty)
            return

        for p in plugins:
            self.grid.addWidget(self._create_plugin_card(p))

    def _create_plugin_card(self, plugin):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 15px;
            }}
            QFrame:hover {{ 
                background: rgba(255, 255, 255, 0.08); 
                border: 1px solid {THEME['primary_glow']};
            }}
        """)
        l = QHBoxLayout(card)
        
        info = QVBoxLayout()
        name = QLabel(f"{plugin['name']} <font color='#666'>v{plugin['version']}</font>")
        name.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        info.addWidget(name)
        
        desc = QLabel(plugin.get("description", "No description provided."))
        desc.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 12px;")
        desc.setWordWrap(True)
        info.addWidget(desc)
        
        l.addLayout(info)
        l.addStretch()
        
        btn = QPushButton("ENABLE" if not plugin["enabled"] else "ACTIVE")
        btn.setFixedWidth(80)
        btn.setEnabled(not plugin["enabled"])
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['primary_glow'] if not plugin['enabled'] else 'rgba(0,255,136,0.2)'};
                color: {'black' if not plugin['enabled'] else THEME['success']};
                border-radius: 6px;
                font-weight: bold;
                padding: 8px;
            }}
        """)
        btn.clicked.connect(lambda: self._enable_plugin(plugin["id"]))
        l.addWidget(btn)
        
        return card

    def _enable_plugin(self, plugin_id):
        if PLUGIN_REGISTRY.enable_plugin(plugin_id):
            self._refresh_list()

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
