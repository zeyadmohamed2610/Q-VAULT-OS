from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QApplication, QToolTip
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QRectF, pyqtSignal, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QFont,
    QPixmap, QIcon, QLinearGradient, QBrush, QRadialGradient
)
from PyQt5.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

from resources.theme import THEME, FONT
from ui.widgets.systray.tray_icon import TrayIconButton
from ui.widgets.systray.wifi_panel import WifiPanel
from ui.widgets.systray.bluetooth_panel import BluetoothPanel
from ui.widgets.sound_menu import SoundMenu
from ui.widgets.systray.launcher_panel import LauncherPanel

def _render_svg(rel: str, size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    # Correct path resolution for icons
    # Go up from src/ui/widgets/ to root
    path = Path(__file__).parent.parent.parent.parent / "resources" / rel.replace("resources/", "")
    if path.exists():
        r = QSvgRenderer(str(path))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        r.render(p, QRectF(0, 0, size, size))
        p.end()
    return pix

class _AppIcon(QWidget):
    clicked = pyqtSignal(dict)
    right_clicked = pyqtSignal(dict, QPoint)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(data.get("app_name", "App"))
        self._hov = False
        self._pix = _render_svg(data.get("icon", "icons/icon-vault.svg"), 26)

    def update_data(self, data: dict):
        self.data = data
        self.update()

    def enterEvent(self, e): self._hov = True; self.update()
    def leaveEvent(self, e): self._hov = False; self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.data, event.globalPos())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        if self._hov:
            p.setBrush(QColor(84, 177, 198, 20))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, 12, 12)
        if self.data.get("is_running"):
            ind_w = 24 if self.data.get("active") else 16
            ind_col = QColor(THEME['primary_glow'])
            p.setPen(Qt.NoPen)
            if self.data.get("active"):
                p.setBrush(QColor(THEME['primary_glow'] + "15"))
                p.drawRoundedRect(rect, 12, 12)
            
            p.setBrush(ind_col)
            p.drawRoundedRect(self.width()//2 - ind_w//2, self.height() - 6, ind_w, 3, 1.5, 1.5)
        
        p.drawPixmap(self.width()//2 - 13, self.height()//2 - 13, self._pix)
        p.end()

class _DockClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(100)
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 4, 10, 4); vl.setSpacing(0)
        self._time = QLabel()
        self._time.setStyleSheet(f"color:{THEME['text_main']}; font-weight: 800; font-size: 13px;")
        self._time.setAlignment(Qt.AlignRight)
        self._date = QLabel()
        self._date.setStyleSheet(f"color:{THEME['text_muted']}; font-size: 9px; font-weight: bold;")
        self._date.setAlignment(Qt.AlignRight)
        vl.addWidget(self._time); vl.addWidget(self._date)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000); self._tick()

    def _tick(self):
        now = datetime.now()
        self._time.setText(now.strftime("%H:%M:%S"))
        self._date.setText(now.strftime("%Y.%m.%d"))

class TaskbarUI(QWidget):
    start_clicked = pyqtSignal()
    app_clicked   = pyqtSignal(str)
    close_app     = pyqtSignal(str)
    new_instance_requested = pyqtSignal(str)
    run_as_admin_requested = pyqtSignal(str) # app_name
    open_launcher = pyqtSignal()
    pin_app = pyqtSignal(str)
    unpin_app = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("SuspendedDock")
        self._tabs: dict[str, _AppIcon] = {}
        self._repositioning = False
        self._build_ui()
        self._reposition()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 12)
        
        self.pill = QFrame()
        self.pill.setFixedHeight(58)
        self.pill.setStyleSheet(f"""
            QFrame {{
                background: rgba(8, 12, 20, 220);
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 29px;
            }}
        """)
        il = QHBoxLayout(self.pill)
        il.setContentsMargins(12, 0, 12, 0); il.setSpacing(4)
        
        self.logo_btn = QPushButton()
        self.logo_btn.setFixedSize(40, 40)
        self.logo_btn.setObjectName("SystemLogo")
        self.logo_btn.setCursor(Qt.PointingHandCursor)
        self.logo_btn.setToolTip("Sovereign Command Center")
        
        # Load qvault_logo.svg as icon
        _logo_pix = _render_svg("icons/qvault_logo.svg", 28)
        if not _logo_pix.isNull():
            self.logo_btn.setIcon(QIcon(_logo_pix))
            self.logo_btn.setIconSize(QSize(28, 28))
        else:
            self.logo_btn.setText("Q")
        
        self.logo_btn.setStyleSheet(f"""
            #SystemLogo {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                            stop:0 rgba(0, 230, 255, 0.15), stop:1 transparent);
                border: 1px solid rgba(0, 230, 255, 0.3);
                border-radius: 20px;
                color: {THEME['primary_glow']};
                font-weight: 900; font-size: 18px;
            }}
            #SystemLogo:hover {{
                background: rgba(0, 230, 255, 0.25);
                border-color: {THEME['primary_glow']};
                border-width: 1.5px;
            }}
            #SystemLogo:pressed {{
                background: rgba(0, 230, 255, 0.35);
            }}
        """)
        
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        self.pulse_effect = QGraphicsOpacityEffect(self.logo_btn)
        self.logo_btn.setGraphicsEffect(self.pulse_effect)
        self.pulse_anim = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_anim.setDuration(2500)
        self.pulse_anim.setStartValue(0.65)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.start()

        self.logo_btn.clicked.connect(self._on_logo_clicked)
        il.addWidget(self.logo_btn)

        sep1 = QFrame()
        sep1.setFixedSize(1, 28); sep1.setStyleSheet("background: rgba(0, 240, 255, 0.15);")
        il.addWidget(sep1)

        self._app_list_w = QWidget()
        self._app_list_l = QHBoxLayout(self._app_list_w)
        self._app_list_l.setContentsMargins(0, 0, 0, 0); self._app_list_l.setSpacing(2)
        il.addWidget(self._app_list_w)

        sep2 = QFrame()
        sep2.setFixedSize(1, 28); sep2.setStyleSheet("background: rgba(0, 240, 255, 0.15);")
        il.addWidget(sep2)

        self._systray_w = QWidget()
        self._systray_l = QHBoxLayout(self._systray_w)
        self._systray_l.setContentsMargins(5, 0, 5, 0); self._systray_l.setSpacing(8)
        il.addWidget(self._systray_w)
        
        self._init_systray()
        il.addWidget(_DockClock())
        
        # ── v2.0 Peek / Show Desktop Button ──
        self.peek_btn = QPushButton()
        self.peek_btn.setFixedSize(12, 36)
        self.peek_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 230, 255, 0.05);
                border-left: 1px solid rgba(0, 230, 255, 0.2);
                border-radius: 0;
            }}
            QPushButton:hover {{ background: rgba(0, 230, 255, 0.2); }}
        """)
        self.peek_btn.clicked.connect(lambda: self.app_clicked.emit("__PEEK__"))
        il.addWidget(self.peek_btn)
        
        outer.addWidget(self.pill, alignment=Qt.AlignCenter)
        self._init_launcher()

    def contextMenuEvent(self, event):
        """Right-click taskbar to open system controls."""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background: {THEME['bg_dark']}; border: 1px solid {THEME['border_color']}; color: white; padding: 4px; border-radius: 8px; }}")
        
        tm_act = menu.addAction("🛠  Sovereign Task Manager")
        tm_act.triggered.connect(self._launch_task_manager)
        
        menu.addSeparator()
        
        settings_act = menu.addAction("⚙  Core Configurations")
        settings_act.triggered.connect(lambda: self.new_instance_requested.emit("Core Configurations"))
        
        menu.exec_(event.globalPos())

    def _launch_task_manager(self):
        self.new_instance_requested.emit("System Intelligence") # Or a dedicated Task Manager if we registered one

    def _init_systray(self):
        self._wifi_btn = TrayIconButton("resources/icons/wifi.svg", "Wi-Fi")
        self._wifi_panel = WifiPanel()
        self._wifi_btn.clicked.connect(lambda: self._wifi_panel.popup_near(self._wifi_btn.mapToGlobal(QPoint(0,0))))

        self._bt_btn = TrayIconButton("resources/icons/bluetooth.svg", "Bluetooth")
        self._bt_panel = BluetoothPanel()
        self._bt_btn.clicked.connect(lambda: self._bt_panel.popup_near(self._bt_btn.mapToGlobal(QPoint(0,0))))

        self._sound_btn = TrayIconButton("resources/icons/sound.svg", "Sound")
        self._sound_menu = SoundMenu()
        self._sound_btn.clicked.connect(lambda: self._sound_menu.popup_near(self._sound_btn.mapToGlobal(QPoint(0,0))))

        for btn in (self._wifi_btn, self._bt_btn, self._sound_btn):
            btn.setFixedSize(30, 30)
            self._systray_l.addWidget(btn)

    def _init_launcher(self):
        self._launcher_panel = LauncherPanel()

    def _on_logo_clicked(self):
        self.start_clicked.emit()
        self.open_launcher.emit()
        self._launcher_panel.popup_above(self.logo_btn.mapToGlobal(QPoint(18, 0)))

    def update_state(self, state):
        apps_data = state.get("apps", [])
        current_ids = set(self._tabs.keys())
        incoming_ids = {a.get("aid", a["app_name"]) for a in apps_data}
        
        for aid in current_ids - incoming_ids:
            widget = self._tabs.pop(aid)
            self._app_list_l.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
            
        for a in apps_data:
            aid = a.get("aid", a["app_name"])
            if aid in self._tabs:
                self._tabs[aid].update_data(a)
            else:
                icon = _AppIcon(a)
                icon.clicked.connect(self._on_app_clicked)
                icon.right_clicked.connect(self._on_app_right_clicked)
                self._tabs[aid] = icon
                self._app_list_l.addWidget(icon)
        self._reposition()

    def _on_app_clicked(self, data):
        if not data.get("is_running"):
            self.new_instance_requested.emit(data["app_name"])
            return

        instance_id = data["instances"][0]
        self.app_clicked.emit(instance_id)

    def _on_app_right_clicked(self, data, pos):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        # Apply professional glassmorphic menu style
        menu.setStyleSheet(f"""
            QMenu {{
                background: rgba(15, 25, 35, 235);
                border: 1px solid {THEME['primary_glow']}33;
                border-radius: 12px;
                padding: 6px;
                color: {THEME['text_main']};
                font-family: 'Inter', 'Segoe UI';
                font-size: 13px;
            }}
            QMenu::item {{
                padding: 8px 32px 8px 12px;
                border-radius: 6px;
                margin: 2px 0;
            }}
            QMenu::item:selected {{
                background: {THEME['primary_glow']}22;
                color: {THEME['primary_glow']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {THEME['primary_glow']}11;
                margin: 6px 10px;
            }}
        """)
        
        app_name = data.get("app_name", "Application")
        
        # ── 1. Execution Controls ──
        if data.get("is_running"):
            act_focus = menu.addAction(f"🗔  Focus {app_name}")
            act_focus.triggered.connect(lambda: self.app_clicked.emit(data["instances"][0]))
            
            act_new = menu.addAction(f"➕  New Instance")
            act_new.triggered.connect(lambda: self.new_instance_requested.emit(app_name))
            
            menu.addSeparator()
            
            act_term = menu.addAction("✕  Terminate Interface")
            act_term.triggered.connect(lambda: self.close_app.emit(data["instances"][0]))
            
            act_kill = menu.addAction("💀  CRITICAL PURGE")
            act_kill.setToolTip("Force kill all processes associated with this app.")
            act_kill.triggered.connect(lambda: self._emit_kill(data["instances"][0]))
        else:
            act_init = menu.addAction(f"🚀  Initialize {app_name}")
            act_init.triggered.connect(lambda: self.new_instance_requested.emit(app_name))
            
        act_admin = menu.addAction("🛡️  Run as Administrator")
        act_admin.triggered.connect(lambda: self.run_as_admin_requested.emit(app_name))
        
        menu.addSeparator()
        
        # ── 2. Persistence Controls ──
        is_pinned = data.get("is_pinned", False)
        pin_text = "📌  Unanchor from Workspace" if is_pinned else "📌  Anchor to Workspace"
        act_pin = menu.addAction(pin_text)
        if is_pinned:
            act_pin.triggered.connect(lambda: self.unpin_app.emit(app_name))
        else:
            act_pin.triggered.connect(lambda: self.pin_app.emit(app_name))
            
        menu.exec_(pos)

    def _emit_kill(self, iid):
        """Kernel-level hard kill bypass."""
        from system.runtime_manager import RUNTIME_MANAGER
        # 1. Trigger the Kernel Kill
        RUNTIME_MANAGER.kill(iid)
        # 2. Force immediate cleanup of the simulation worker
        RUNTIME_MANAGER.unregister(iid)

    def _reposition(self):
        if self._repositioning: return
        self._repositioning = True
        try:
            par = self.parent()
            if not par: return
            
            # If we are in a layout, the layout handles positioning.
            # We only use setGeometry for floating/absolute positioning.
            if par.layout() and par.layout().indexOf(self) != -1:
                self._repositioning = False
                return

            sw = par.width()
            sh = par.height()
            self.adjustSize()
            w = self.pill.sizeHint().width() + 40
            w = min(sw - 40, w)
            self.setGeometry((sw - w)//2, sh - 76, w, 76)
        finally: self._repositioning = False

    def resizeEvent(self, e): self._reposition()
