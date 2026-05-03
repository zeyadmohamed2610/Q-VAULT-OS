from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QApplication, QToolTip
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QFont,
    QPixmap, QIcon, QLinearGradient, QBrush
)
from PyQt5.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

# Systray components imported lazily in _build_ui

from assets.theme import THEME

# ── Palette (design_tokens) ───────────────────────────────────
_BG      = QColor(THEME["bg_dark"])
_BG.setAlpha(240)
_CYAN    = QColor(THEME["primary_glow"])
_BORDER  = QColor(THEME["primary_glow"])
_BORDER.setAlpha(46)
_STEEL   = QColor(THEME["primary_deep"])
_TEXT    = QColor(THEME["text_main"])
_MUTED   = QColor(THEME["text_muted"])
_DIV     = QColor(THEME["primary_glow"])
_DIV.setAlpha(30)
_CLOSE_H = QColor(THEME["error_bright"])
_CLOSE_H.setAlpha(80)

_BASE_DIR = Path(__file__).parent.parent


def _render_svg(rel: str, size: int) -> QPixmap:
    """Render SVG file to a transparent QPixmap of given size."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    path = _BASE_DIR / rel
    if path.exists():
        r = QSvgRenderer(str(path))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        r.render(p, QRectF(0, 0, size, size))
        p.end()
    return pix


# ── Zone 1: Logo Button ───────────────────────────────────────

class _LogoButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Q-Vault OS")
        self._hov = False
        self._pix = _render_svg("assets/icons/qvault_logo.svg", 28)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def enterEvent(self, e):
        self._hov = True; self.update()

    def leaveEvent(self, e):
        self._hov = False; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hov:
            p.setBrush(QColor(84, 177, 198, 55))
            p.setPen(QPen(_CYAN, 1.2))
            p.drawEllipse(1, 1, 34, 34)
        # Center icon (28px inside 36px button)
        ox = (36 - 28) // 2
        oy = (36 - 28) // 2
        p.drawPixmap(ox, oy, self._pix)
        p.end()


# ── Zone 2: App Tab ───────────────────────────────────────────

class _AppTab(QWidget):
    close_requested        = pyqtSignal(str)
    focus_requested        = pyqtSignal(str)
    new_instance_requested = pyqtSignal(str)

    def __init__(self, app_id: str, label: str, icon_path: str | None, parent=None):
        super().__init__(parent)
        self.app_id   = app_id
        self._active  = False
        self._hov     = False

        self.setFixedHeight(36)
        self.setMinimumWidth(100)
        self.setMaximumWidth(180)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(5)

        # Icon (16 × 16)
        if icon_path:
            ico = _render_svg(icon_path, 16)
            ico_lbl = QLabel()
            ico_lbl.setPixmap(ico)
            ico_lbl.setFixedSize(16, 16)
            ico_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(ico_lbl)

        # Label
        self._label = label  # for context menu
        self._lbl = QLabel(label[:18])
        self._lbl.setFont(QFont("Segoe UI", 10))
        self._lbl.setStyleSheet("color:#d4e8f0; background:transparent;")
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._lbl)

        # × close
        self._close = QPushButton("×")
        self._close.setFixedSize(16, 16)
        self._close.setCursor(Qt.PointingHandCursor)
        self._close.setStyleSheet("""
            QPushButton {
                background:transparent; color:#4a6880;
                border:none; outline:none; font-size:14px;
                border-radius:8px; padding:0;
            }
            QPushButton:hover { background:rgba(248,81,73,0.30); color:#f85149; }
        """)
        self._close.clicked.connect(lambda: self.close_requested.emit(self.app_id))
        layout.addWidget(self._close)

    def contextMenuEvent(self, event):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#0b162d;border:1px solid rgba(84,177,198,0.20);"
            "border-radius:8px;padding:4px 0;color:#d4e8f0;"
            "font-family:'Segoe UI';font-size:10pt;}"
            "QMenu::item{padding:6px 20px;border-radius:4px;margin:1px 4px;}"
            "QMenu::item:selected{background:rgba(84,177,198,0.15);}"
        )
        act_new = QAction(f"New {self._label} Window", self)
        act_new.triggered.connect(lambda: self.new_instance_requested.emit(self.app_id))
        act_close = QAction("Close", self)
        act_close.triggered.connect(lambda: self.close_requested.emit(self.app_id))
        menu.addAction(act_new)
        menu.addSeparator()
        menu.addAction(act_close)
        menu.exec_(event.globalPos())

    def set_active(self, v: bool):
        if self._active != v:
            self._active = v
            self.update()

    def enterEvent(self, e):
        self._hov = True; self.update()

    def leaveEvent(self, e):
        self._hov = False; self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.focus_requested.emit(self.app_id)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(0, 0, r.width(), r.height(), 8, 8)

        if self._active:
            p.fillPath(path, QColor(84, 177, 198, 65))
            p.setPen(QPen(_CYAN, 1.0))
            p.drawPath(path)
            # Active underline
            mid = r.width() // 2
            p.fillRect(mid - 14, r.height() - 3, 28, 2, QColor(84, 177, 198, 240))
        elif self._hov:
            p.fillPath(path, QColor(84, 177, 198, 35))
        else:
            p.fillPath(path, QColor(15, 40, 66, 110))
        p.end()
        super().paintEvent(event)


# ── Zone 3: Clock ─────────────────────────────────────────────

class _DockClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(88)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        self._time = QLabel()
        self._time.setFont(QFont("Segoe UI Semibold", 12))
        self._time.setStyleSheet("color:#d4e8f0; background:transparent;")
        self._time.setAlignment(Qt.AlignCenter)

        self._date = QLabel()
        self._date.setFont(QFont("Segoe UI", 8))
        self._date.setStyleSheet("color:#4a6880; background:transparent;")
        self._date.setAlignment(Qt.AlignCenter)

        vl.addWidget(self._time)
        vl.addWidget(self._date)

        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    def _tick(self):
        now = datetime.now()
        self._time.setText(now.strftime("%I:%M:%S %p"))
        self._date.setText(now.strftime("%a %d %b"))

    def set_time(self, s: str):
        """Legacy shim: accept a time string from outside."""
        self._time.setText(s)


# ── Divider ───────────────────────────────────────────────────

def _divider() -> QFrame:
    d = QFrame()
    d.setFrameShape(QFrame.VLine)
    d.setFixedWidth(1)
    d.setFixedHeight(28)
    d.setStyleSheet("background:rgba(84,177,198,0.12); border:none;")
    return d



# ── Airplane Mode Button ──────────────────────────────────────

class _AirplaneBtn(QPushButton):
    """Toggles airplane mode: disables WiFi + BT tray buttons."""
    def __init__(self, wifi_btn, bt_btn, parent=None):
        super().__init__("✈", parent)
        self._wifi = wifi_btn
        self._bt   = bt_btn
        self._on   = False
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Airplane Mode")
        self.setFont(QFont("Segoe UI", 13))
        self.setStyleSheet(
            "QPushButton{background:transparent;border:none;outline:none;border-radius:6px;color:#4a6880;}"
            "QPushButton:hover{background:rgba(84,177,198,0.12);}"
        )
        self.clicked.connect(self._toggle)

    def _toggle(self):
        self._on = not self._on
        col = "#f85149" if self._on else "#4a6880"
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;outline:none;"
            f"border-radius:6px;color:{col};}}"
            "QPushButton:hover{background:rgba(84,177,198,0.12);}"
        )
        enabled = not self._on
        self._wifi.setEnabled(enabled)
        self._wifi.set_active(enabled)
        self._bt.setEnabled(enabled)
        self._bt.set_active(enabled)
        from PyQt5.QtWidgets import QToolTip
        msg = ("✈ Airplane Mode ON — WiFi & Bluetooth disabled"
               if self._on else "✈ Airplane Mode OFF")
        QToolTip.showText(self.mapToGlobal(self.rect().center()), msg)


# ── MAIN DOCK ─────────────────────────────────────────────────

class TaskbarUI(QWidget):
    """
    Suspended Dock — pill-shaped floating bar, 12 px above screen bottom.
    Dynamically widens as app tabs are added.

    Signals
    -------
    open_launcher  — logo button clicked
    close_app(id)  — × on a tab
    focus_app(id)  — tab body clicked
    app_clicked(id)— alias for focus_app (legacy compat)
    start_clicked  — unused legacy compat
    """
    open_launcher          = pyqtSignal()
    new_instance_requested = pyqtSignal(str)  # right-click tab -> new window
    close_app        = pyqtSignal(str)
    focus_app        = pyqtSignal(str)
    app_clicked      = pyqtSignal(str)   # legacy alias
    start_clicked    = pyqtSignal()      # legacy compat

    _PILL_R  = 26   # border-radius for pill shape
    _H       = 52   # total dock height
    _GAP     = 12   # px from screen bottom

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setObjectName("SuspendedDock")

        self._tabs: dict[str, _AppTab] = {}
        self._clock_widget: _DockClock | None = None
        self._repositioning = False  # recursion guard for _reposition

        self._build_ui()
        self._reposition()

    # ── Build ─────────────────────────────────────────────────

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 8, 14, 8)
        outer.setSpacing(0)

        inner = QWidget()
        inner.setAttribute(Qt.WA_TranslucentBackground)
        il = QHBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(8)

        # Zone 1: Logo
        self._logo = _LogoButton()
        self._logo.clicked.connect(self._on_logo)
        # Note: launcher panel wired in _init_launcher() after build
        il.addWidget(self._logo)
        il.addWidget(_divider())
        il.addSpacing(4)

        # Zone 2: App tabs (dynamic)
        self._tabs_w = QWidget()
        self._tabs_w.setAttribute(Qt.WA_TranslucentBackground)
        self._tabs_l = QHBoxLayout(self._tabs_w)
        self._tabs_l.setContentsMargins(0, 0, 0, 0)
        self._tabs_l.setSpacing(4)
        self._tabs_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        il.addWidget(self._tabs_w)

        il.addSpacing(4)
        il.addWidget(_divider())

        # Zone 3: SysTray slot (PROMPT 3 populates this)
        self._systray_w = QWidget()
        self._systray_w.setAttribute(Qt.WA_TranslucentBackground)
        self._systray_l = QHBoxLayout(self._systray_w)
        self._systray_l.setContentsMargins(4, 0, 4, 0)
        self._systray_l.setSpacing(4)
        self._systray_w.setObjectName("systray_slot")
        il.addWidget(self._systray_w)

        # Populate systray zone (WiFi, BT, Airplane)
        self._init_systray()

        il.addWidget(_divider())
        il.addSpacing(4)

        # Zone 4: Clock
        self._clock_widget = _DockClock()
        il.addWidget(self._clock_widget)

        outer.addWidget(inner)

        # Wire launcher panel
        self._init_launcher()

    # ── Pill paint ────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        path = QPainterPath()
        path.addRoundedRect(0, 0, r.width(), r.height(), self._PILL_R, self._PILL_R)

        # Base fill
        p.fillPath(path, _BG)

        # Border
        p.setPen(QPen(_BORDER, 1.0))
        p.drawPath(path)

        # Glass top highlight
        hl = QLinearGradient(0, 0, 0, 14)
        hl.setColorAt(0, QColor(255, 255, 255, 18))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(path, QBrush(hl))

        p.end()

    # ── Positioning ───────────────────────────────────────────

    def _reposition(self):
        """Re-center dock horizontally, always 12 px from bottom."""
        if self._repositioning:
            return
        self._repositioning = True
        try:
            par = self.parent()
            if par and par.width() > 0:
                sw, sh = par.width(), par.height()
            else:
                screen = QApplication.primaryScreen().geometry()
                sw, sh = screen.width(), screen.height()
            self.setFixedHeight(self._H)
            self.adjustSize()
            w = max(520, min(self.sizeHint().width() + 60, int(sw * 0.90)))
            x = (sw - w) // 2
            y = sh - self._H - self._GAP
            self.setGeometry(x, y, w, self._H)
        finally:
            self._repositioning = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._repositioning:
            self._reposition()

    # ── Tab management ────────────────────────────────────────

    def register_app(self, app_id: str, label: str, icon_path: str | None = None):
        """Add a tab for a newly opened window."""
        if app_id in self._tabs:
            return
        tab = _AppTab(app_id, label, icon_path)
        tab.close_requested.connect(self._on_tab_close)
        tab.focus_requested.connect(self._on_tab_focus)
        tab.new_instance_requested.connect(self.new_instance_requested)
        self._tabs[app_id] = tab
        self._tabs_l.addWidget(tab)
        self._reposition()

    def unregister_app(self, app_id: str):
        """Remove a tab when its window closes."""
        tab = self._tabs.pop(app_id, None)
        if tab:
            self._tabs_l.removeWidget(tab)
            tab.deleteLater()
            self._reposition()

    def set_active_app(self, app_id: str | None):
        """Highlight the tab for the focused window."""
        for aid, tab in self._tabs.items():
            tab.set_active(aid == app_id)

    # ── Legacy shims ──────────────────────────────────────────

    def update_clock(self, time_str: str):
        """Legacy: accept time string from external timer. Disabled to prevent dual-timer flicker."""
        pass

    def update_state(self, state: dict):
        """Legacy: rebuild tabs from {'apps': [...], 'active_id': ...}."""
        apps      = state.get("apps", [])
        active_id = state.get("active_id")
        current   = set(self._tabs.keys())
        incoming  = {a["id"] for a in apps}

        # Remove stale
        for aid in current - incoming:
            self.unregister_app(aid)

        # Add new
        for a in apps:
            if a["id"] not in self._tabs:
                self.register_app(a["id"], a.get("title", a["id"]))

        self.set_active_app(active_id)

    def _init_systray(self):
        """Populate the systray zone: WiFi + BT + Airplane Mode."""
        from components.systray.tray_icon import TrayIconButton
        from components.systray.wifi_panel import WifiPanel
        from components.systray.bluetooth_panel import BluetoothPanel
        from components.sound_menu import SoundMenu

        # WiFi — real SVG icon
        self._wifi_btn = TrayIconButton("assets/icons/wifi.svg", "Wi-Fi")
        self._wifi_panel = WifiPanel()
        self._wifi_btn.clicked.connect(self._show_wifi_panel)

        # Bluetooth — real SVG icon
        self._bt_btn = TrayIconButton("assets/icons/bluetooth.svg", "Bluetooth")
        self._bt_panel = BluetoothPanel()
        self._bt_btn.clicked.connect(self._show_bt_panel)

        # Sound
        self._sound_btn = TrayIconButton("assets/icons/sound.svg", "Sound")
        self._sound_menu = SoundMenu()
        self._sound_btn.clicked.connect(self._show_sound_menu)

        # Airplane
        self._airplane_btn = _AirplaneBtn(self._wifi_btn, self._bt_btn)

        for btn in (self._wifi_btn, self._bt_btn, self._sound_btn, self._airplane_btn):
            self._systray_l.addWidget(btn)

    def _show_wifi_panel(self):
        pos = self._wifi_btn.mapToGlobal(self._wifi_btn.rect().bottomLeft())
        self._wifi_panel.popup_near(pos)

    def _show_bt_panel(self):
        pos = self._bt_btn.mapToGlobal(self._bt_btn.rect().bottomLeft())
        self._bt_panel.popup_near(pos)

    def _show_sound_menu(self):
        pos = self._sound_btn.mapToGlobal(self._sound_btn.rect().bottomLeft())
        self._sound_menu.popup_near(pos)

    def _init_launcher(self):
        """Wire the Q-Vault logo button to the LauncherPanel."""
        from components.systray.launcher_panel import LauncherPanel
        self._launcher_panel = LauncherPanel()
        self._launcher_panel.lock_requested.connect(self._request_lock)
        # Reconnect logo to open launcher (overrides _on_logo)
        try:
            self._logo.clicked.disconnect(self._on_logo)
        except Exception:
            pass
        self._logo.clicked.connect(self._open_launcher)

    def _open_launcher(self):
        pos = self._logo.mapToGlobal(self._logo.rect().center())
        self._launcher_panel.popup_above(pos)

    def _request_lock(self):
        try:
            from core.event_bus import EVENT_BUS
            EVENT_BUS.emit("auth.lock_request", {})
        except Exception as exc:
            logger.warning("Lock request failed: %s", exc)

    def get_systray_layout(self):

        """Returns the systray zone layout for PROMPT 3."""
        return self._systray_l

    # ── Signal routing ────────────────────────────────────────

    def _open_account_settings(self):
        try:
            from components.account_settings_dialog import AccountSettingsDialog
            dlg = AccountSettingsDialog(parent=self.parent())
            dlg.exec_()
        except Exception as e:
            logger.warning("Could not open account settings: %s", e)

    def _on_logo(self):
        self.open_launcher.emit()
        self.start_clicked.emit()

    def _on_tab_close(self, app_id: str):
        self.close_app.emit(app_id)

    def _on_tab_focus(self, app_id: str):
        self.focus_app.emit(app_id)
        self.app_clicked.emit(app_id)
