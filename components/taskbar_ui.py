from assets.theme import *
import psutil
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QPoint
from PyQt5.QtGui import QIcon, QFont, QPainter, QColor
from core.resources import get_asset_path
from datetime import datetime

class KaliMetricWidget(QWidget):
    """Kali Linux style metric with a small bar."""
    def __init__(self, label, color):
        super().__init__()
        self.label_text = label
        self.color = QColor(color)
        self.value = 0
        self.setFixedWidth(85)
        self.setFixedHeight(30)
        
    def update_value(self, val):
        self.value = val
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw Label
        painter.setPen(QColor("#888"))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(0, 10, f"{self.label_text}")
        
        # Draw Bar Background
        bg_color = QColor(self.color)
        bg_color.setAlpha(30)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 15, 75, 4, 2, 2)
        
        # Draw Value Bar
        painter.setBrush(self.color)
        w = int(75 * (self.value / 100.0))
        painter.drawRoundedRect(0, 15, w, 4, 2, 2)
        
        # Draw Percentage
        painter.setPen(self.color)
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.drawText(50, 10, f"{int(self.value)}%")

class TaskbarAppButton(QPushButton):
    def __init__(self, app_id, title, is_active=False, parent=None):
        super().__init__(title[:12], parent)
        self.app_id = app_id
        self.setCheckable(True)
        self.setChecked(is_active)
        self.setFixedSize(110, 32)
        self._apply_style(is_active)

    def _apply_style(self, is_active):
        bg = "rgba(0, 230, 255, 0.15)" if is_active else "rgba(255, 255, 255, 0.05)"
        border = f"1px solid {THEME['primary_glow']}66" if is_active else "1px solid rgba(255,255,255,0.1)"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border};
                border-radius: 4px;
                color: white;
                font-size: 10px;
            }}
        """)

class TaskbarUI(QFrame):
    start_clicked = pyqtSignal()
    app_clicked = pyqtSignal(str)
    shortcut_clicked = pyqtSignal(str)
    search_triggered = pyqtSignal(str) # Legacy fallback
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setObjectName("TaskbarUI")
        self.setStyleSheet(f"#TaskbarUI {{ background: rgba(10, 12, 18, 0.98); border-top: 1px solid rgba(0, 230, 255, 0.1); }}")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 0, 15, 0)
        self.layout.setSpacing(12)

        # ── Left: Start + Shortcuts ──
        self.btn_start = QPushButton(" Q-VAULT")
        self.btn_start.setFixedSize(85, 30)
        self.btn_start.setFont(QFont("Consolas", 9, QFont.Bold))
        self.btn_start.setStyleSheet(f"QPushButton {{ background: {THEME['primary_glow']}; color: black; border-radius: 4px; }}")
        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.layout.addWidget(self.btn_start)

        self.layout.addWidget(self._create_shortcut("icons/terminal.svg", "terminal"))
        self.layout.addWidget(self._create_shortcut("icons/files.svg", "files"))

        self.layout.addStretch(1)

        # ── Center: Active Apps ──
        self.apps_container = QWidget()
        self.apps_layout = QHBoxLayout(self.apps_container)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.apps_container)

        self.layout.addStretch(1)

        # ── Right: [Metrics | Clock | WiFi | Power] ──
        # Ordered so Power is at the very edge (far right)
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(20)

        # 1. Metrics (Kali Style)
        self.metric_cpu = KaliMetricWidget("CPU", "#00ff88")
        self.metric_ram = KaliMetricWidget("RAM", "#00e6ff")
        self.right_layout.addWidget(self.metric_cpu)
        self.right_layout.addWidget(self.metric_ram)

        # 2. Clock
        self.lbl_clock = QLabel("00:00")
        self.lbl_clock.setStyleSheet("color: white; font-family: 'Consolas'; font-size: 13px; font-weight: bold; padding: 0 8px;")
        self.right_layout.addWidget(self.lbl_clock)

        # 3. WiFi (Pure Icon)
        self.btn_wifi = QPushButton()
        self.btn_wifi.setIcon(QIcon(get_asset_path("icons/trust.svg"))) # Shield icon looks like signal bars
        self.btn_wifi.setIconSize(QSize(20, 20))
        self.btn_wifi.setFixedSize(36, 36)
        self.btn_wifi.setCursor(Qt.PointingHandCursor)
        self.btn_wifi.setStyleSheet(f"QPushButton {{ background: transparent; color: {THEME['primary_glow']}; border: none; }} QPushButton:hover {{ background: rgba(0, 230, 255, 0.1); border-radius: 18px; }}")
        self.btn_wifi.clicked.connect(self._show_wifi)
        self.right_layout.addWidget(self.btn_wifi)

        # 4. Power (Control) - Furthest Right
        self.btn_control = QPushButton()
        self.btn_control.setIcon(QIcon(get_asset_path("icons/power.svg")))
        self.btn_control.setIconSize(QSize(18, 18))
        self.btn_control.setFixedSize(32, 32)
        self.btn_control.setCursor(Qt.PointingHandCursor)
        self.btn_control.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,50,50,0.1); border-radius: 16px; }")
        self.btn_control.clicked.connect(lambda: self.shortcut_clicked.emit("control"))
        self.right_layout.addWidget(self.btn_control)

        self.layout.addWidget(self.right_container)

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_telemetry)
        self.timer.start(1000)

    def _update_telemetry(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.metric_cpu.update_value(cpu)
        self.metric_ram.update_value(ram)
        self.lbl_clock.setText(datetime.now().strftime("%I:%M %p"))

    def _show_wifi(self):
        from components.network_menu import NetworkMenu
        if not hasattr(self, "net_menu"):
            self.net_menu = NetworkMenu(self.window())
        pos = self.btn_wifi.mapToGlobal(QPoint(0, 0))
        self.net_menu.move(pos.x() - self.net_menu.width() + 65, pos.y() - self.net_menu.height() - 10)
        self.net_menu.show()

    def update_state(self, state):
        while self.apps_layout.count():
            item = self.apps_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        apps = state.get("apps", [])
        active_id = state.get("active_id")
        for app in apps:
            btn = TaskbarAppButton(app['id'], app['title'], is_active=(app['id'] == active_id))
            btn.clicked.connect(lambda _, aid=app['id']: self.app_clicked.emit(aid))
            self.apps_layout.addWidget(btn)

    def _create_shortcut(self, icon_path, action_id):
        btn = QPushButton()
        btn.setIcon(QIcon(get_asset_path(icon_path)))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(36, 36)
        btn.setStyleSheet("QPushButton { background: transparent; } QPushButton:hover { background: rgba(255,255,255,0.05); border-radius: 18px; }")
        btn.clicked.connect(lambda: self.shortcut_clicked.emit(action_id))
        return btn
