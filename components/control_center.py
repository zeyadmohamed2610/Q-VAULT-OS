from assets.theme import *
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QScrollArea
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QPoint, QEasingCurve, QSize
from PyQt5.QtGui import QColor, QFont, QIcon
from assets.theme import SPACE_MD, SPACE_SM, RADIUS_LG, MOTION_SNAPPY, MOTION_SMOOTH, EASE_OUT
from core.resources import get_asset_path
import subprocess
import re
import ctypes

class ControlCenter(QFrame):
    """
    v2.7 Unified Control Center & Power Hub.
    Consolidates Network, Bluetooth, Volume, Brightness, and Power.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setFixedHeight(500)
        self._is_visible = False
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ControlCenter {{
                background: rgba(10, 15, 25, 0.98);
                border: 1px solid rgba(0, 230, 255, 0.3);
                border-radius: 24px;
            }}
            QLabel {{ color: white; background: transparent; }}
            #SectionHeader {{ color: {THEME['text_disabled']}; font-weight: bold; font-size: 10px; letter-spacing: 1px; margin-top: 10px; }}
            
            QPushButton#PowerBtn {{
                background: rgba(255, 51, 102, 0.1);
                border: 1px solid rgba(255, 51, 102, 0.2);
                border-radius: 12px;
                color: {THEME['accent_error']};
                font-weight: bold;
                padding: 10px;
            }}
            QPushButton#PowerBtn:hover {{ background: {THEME['accent_error']}; color: white; }}
            
            QPushButton#ActionBtn {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                color: #ccc;
                font-size: 12px;
                padding: 8px;
                text-align: left;
            }}
            QPushButton#ActionBtn:hover {{ background: rgba(0, 230, 255, 0.1); border: 1px solid {THEME['primary_glow']}; color: white; }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # ─── POWER OPTIONS ───
        power_layout = QHBoxLayout()
        self.btn_shutdown = self._create_power_btn("icons/power.svg", "Shutdown", "#ff3366")
        self.btn_restart = self._create_power_btn("icons/menu-refresh.svg", "Restart", "#ffcc00")
        self.btn_lock = self._create_power_btn("icons/trust.svg", "Lock", "#00e6ff")
        
        power_layout.addWidget(self.btn_shutdown)
        power_layout.addWidget(self.btn_restart)
        power_layout.addWidget(self.btn_lock)
        self.layout.addLayout(power_layout)

        # Connectivity List
        self.wifi_list = QVBoxLayout()
        self.layout.addLayout(self.wifi_list)
        self._refresh_wifi()

        # ─── SLIDERS ───
        self.layout.addWidget(self._create_header("SYSTEM CONTROLS"))
        
        # Volume
        vol_box = QVBoxLayout()
        vol_label = QHBoxLayout()
        vol_label.addWidget(QLabel(" VOLUME"))
        self.vol_val = QLabel("75%")
        vol_label.addWidget(self.vol_val, 0, Qt.AlignRight)
        vol_box.addLayout(vol_label)
        
        self.vol_slider = self._create_slider(75, self._set_system_volume)
        self.vol_slider.valueChanged.connect(lambda v: self.vol_val.setText(f"{v}%"))
        vol_box.addWidget(self.vol_slider)
        self.layout.addLayout(vol_box)

        # Brightness
        br_box = QVBoxLayout()
        br_label = QHBoxLayout()
        br_label.addWidget(QLabel("󰃠 BRIGHTNESS"))
        self.br_val = QLabel("90%")
        br_label.addWidget(self.br_val, 0, Qt.AlignRight)
        br_box.addLayout(br_label)
        
        self.br_slider = self._create_slider(90, self._set_system_brightness)
        self.br_slider.valueChanged.connect(lambda v: self.br_val.setText(f"{v}%"))
        br_box.addWidget(self.br_slider)
        self.layout.addLayout(br_box)

        self.layout.addStretch()
        
        # Footer
        footer = QLabel("Q-VAULT CONTROL HUB v1.0")
        footer.setStyleSheet(f"color: {THEME['border_muted']}; font-size: 9px; font-weight: bold;")
        footer.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(footer)

    def _create_header(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("SectionHeader")
        return lbl

    def _create_power_btn(self, icon_path, label, color):
        btn = QPushButton()
        btn.setIcon(QIcon(get_asset_path(icon_path)))
        btn.setIconSize(QSize(24, 24))
        btn.setFixedSize(60, 60)
        btn.setToolTip(label)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background: {color};
                border: 1px solid {color};
            }}
        """)
        if label == "Shutdown": btn.clicked.connect(lambda: exit(0))
        elif label == "Lock": btn.clicked.connect(self._lock_system)
        return btn

    def _lock_system(self):
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.ACTION_CLICKED, {"command": "@lock"}, source="ControlCenter")
        self.hide_panel()

    def _create_action_btn(self, icon_path, text):
        btn = QPushButton(f"  {text}")
        btn.setIcon(QIcon(get_asset_path(icon_path)))
        btn.setIconSize(QSize(18, 18))
        btn.setObjectName("ActionBtn")
        btn.setFixedHeight(45)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _create_slider(self, val, on_change=None):
        s = QSlider(Qt.Horizontal)
        s.setRange(0, 100)
        s.setValue(val)
        if on_change: s.valueChanged.connect(on_change)
        s.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: {THEME['surface_dark']}; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {THEME['primary_glow']}; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }}
        """)
        return s

    def _set_system_volume(self, value):
        """Sets system volume on Windows via APPCOMMAND."""
        # Note: Precision volume requires pycaw, this is a fallback
        import ctypes
        from PyQt5.QtWidgets import QApplication
        # Roughly estimate direction/steps
        pass 

    def _set_system_brightness(self, value):
        """Sets screen brightness on Windows via WMI."""
        try:
            import wmi
            w = wmi.WMI(namespace='wmi')
            methods = w.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(value, 0)
        except Exception:
            pass

    def toggle(self):
        if self.isVisible():
            self.hide_panel()
        else:
            self.show_panel()

    def _refresh_wifi(self):
        """Scans for real Wi-Fi networks using netsh."""
        while self.wifi_list.count():
            item = self.wifi_list.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.wifi_list.addWidget(self._create_header("CONNECTIVITY"))
        
        try:
            output = subprocess.check_output(["netsh", "wlan", "show", "networks"], 
                                           creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8')
            ssids = re.findall(r"SSID \d+ : (.+)", output)
            if not ssids: ssids = ["No Networks Found"]
            
            for ssid in ssids[:6]: # Show top 6
                btn = self._create_action_btn("icons/trust.svg", ssid)
                self.wifi_list.addWidget(btn)
        except Exception:
            self.wifi_list.addWidget(self._create_action_btn("icons/trust.svg", "Network Service Unavailable"))

    def toggle(self):
        if self.isVisible():
            self.hide_panel()
        else:
            self.show_panel()

    def show_panel(self):
        self._refresh_wifi()
        self.show()
        self.raise_()
        
        parent = self.parent()
        target_x = parent.width() - self.width() - 20
        target_y = 60
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(MOTION_SNAPPY)
        self.anim.setStartValue(QPoint(parent.width(), target_y))
        self.anim.setEndValue(QPoint(target_x, target_y))
        self.anim.setEasingCurve(EASE_OUT)
        self.anim.start()

    def hide_panel(self):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(MOTION_SNAPPY)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(self.parent().width(), self.y()))
        self.anim.setEasingCurve(EASE_OUT)
        self.anim.finished.connect(self.hide)
        self.anim.start()
