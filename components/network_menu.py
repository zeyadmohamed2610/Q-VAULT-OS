from assets.theme import *
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea
from PyQt5.QtCore import Qt
from tools.system_control_helper import SystemControlHelper

class NetworkMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(220)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(10, 15, 25, 0.98);
                border: 1px solid {THEME['primary_glow']}44;
                border-radius: 12px;
                color: white;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: #ddd;
                text-align: left;
                padding: 10px;
                border-radius: 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{ 
                background-color: rgba(0, 230, 255, 0.1); 
                color: {THEME['primary_glow']}; 
            }}
            #RefreshBtn {{
                background: rgba(0, 230, 255, 0.05);
                text-align: center;
                color: {THEME['primary_glow']};
                font-weight: bold;
            }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        header = QLabel("WIRELESS NETWORKS")
        header.setStyleSheet(f"color: {THEME['primary_glow']}; font-weight: bold; font-size: 10px; letter-spacing: 1px; padding-bottom: 5px;")
        self.layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.content = QWidget()
        self.grid = QVBoxLayout(self.content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content)
        self.layout.addWidget(self.scroll)

        self.refresh_btn = QPushButton("REFRESH SCAN")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.clicked.connect(self._refresh)
        self.layout.addWidget(self.refresh_btn)

        self._refresh()

    def _refresh(self):
        # Clear
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        networks = SystemControlHelper.get_wifi_networks()
        for net in networks:
            lock = "🔒" if net.get("secure", True) else "🔓"
            strength = net.get("strength", "░░░░")
            btn = QPushButton(f"{strength}  {net['name']}  {lock}")
            btn.clicked.connect(lambda _, n=net["name"]: self._connect(n))
            self.grid.addWidget(btn)

    def _connect(self, name):
        self.hide()
        try:
            from system.app_controller import get_app_controller
            ctrl = get_app_controller()
            if ctrl and hasattr(ctrl, "notification_manager"):
                ctrl.notification_manager.notify(f"Authenticating with {name}...", "Network")
        except Exception:
            pass
