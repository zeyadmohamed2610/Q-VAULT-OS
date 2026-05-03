import uuid
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QAction,
    QGraphicsDropShadowEffect, QSizePolicy, QInputDialog, QMessageBox, QShortcut
)
from PyQt5.QtCore import Qt, QRect, QTimer, QPoint, QSize, QRectF, QFileSystemWatcher, QMimeData, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QFont, QPixmap, QPen, QBrush, QPainterPath, QDrag, QKeySequence
)
from PyQt5.QtSvg import QSvgRenderer

from components.taskbar_ui import TaskbarUI
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager
from assets.design_tokens import COLORS

logger = logging.getLogger(__name__)

# ── Standardized dark menu style ─────────────────────────────
DARK_MENU_STYLE = (
    "QMenu {"
    "  background: #0b1929;"
    "  border: 1px solid rgba(0, 200, 255, 0.2);"
    "  border-radius: 10px;"
    "  padding: 6px 0;"
    "  color: #d4e8f0;"
    "  font-family: 'Segoe UI';"
    "  font-size: 10pt;"
    "}"
    "QMenu::item {"
    "  padding: 7px 28px 7px 16px;"
    "  border-radius: 6px;"
    "  margin: 1px 4px;"
    "}"
    "QMenu::item:selected {"
    "  background: rgba(0, 200, 255, 0.15);"
    "  color: #00e6ff;"
    "}"
    "QMenu::item:hover {"
    "  background: rgba(0, 200, 255, 0.08);"
    "}"
    "QMenu::separator {"
    "  height: 1px;"
    "  background: rgba(255, 255, 255, 0.08);"
    "  margin: 4px 12px;"
    "}"
    "QMenu::item:disabled { color: #3a5568; }"
)

DARK_DIALOG_STYLE = """
    QDialog, QMessageBox {
        background-color: #0b162d;
        color: #d4e8f0;
    }
    QLabel {
        color: #d4e8f0;
        background: transparent;
    }
    QPushButton {
        background: #0f2842;
        color: #54b1c6;
        border: 1px solid rgba(84,177,198,0.35);
        border-radius: 6px;
        padding: 6px 18px;
        font-family: 'Segoe UI';
    }
    QPushButton:hover {
        background: rgba(84,177,198,0.18);
        border-color: rgba(84,177,198,0.6);
        color: #7dd3e8;
    }
    QPushButton:default {
        border-color: #54b1c6;
    }
    QLineEdit {
        background: #0b162d;
        border: 1px solid rgba(84,177,198,0.3);
        border-radius: 6px;
        color: #d4e8f0;
        padding: 6px;
    }
"""

# ── Icon definitions ──────────────────────────────────────────
_APPS = [
    {"name": "Terminal",        "icon": "assets/icons/terminal.svg"},
    {"name": "File Manager",    "icon": "assets/icons/files.svg"},
    {"name": "Trash",           "icon": "assets/icons/trash.svg"},
    {"name": "Q-Vault Browser", "icon": "assets/icons/browser.svg"},
    {"name": "Q-Vault Security","icon": "assets/icons/icon-vault.svg"},
    {"name": "Kernel Monitor",  "icon": "assets/icons/kernel_monitor.svg"},
]


# ── Grid constants ────────────────────────────────────────────
GRID_CELL_W  = 110
GRID_CELL_H  = 120
GRID_START_X = 20
GRID_START_Y = 20

# ── Icon map for desktop files ────────────────────────────────
_FILE_ICON_MAP = {
    "folder":   "assets/icons/folder.svg",
    ".txt":     "assets/icons/file_text.svg",
    ".md":      "assets/icons/file_text.svg",
    ".py":      "assets/icons/file_text.svg",
    ".json":    "assets/icons/file_text.svg",
    ".log":     "assets/icons/file_text.svg",
    "_default": "assets/icons/file_generic.svg",
}

def _icon_for_path(path: Path) -> str:
    if path.is_dir():
        return _FILE_ICON_MAP["folder"]
    return _FILE_ICON_MAP.get(path.suffix.lower(), _FILE_ICON_MAP["_default"])


# ── Desktop File Icon Widget ──────────────────────────────────

class DesktopFileIcon(QWidget):
    """
    90×100 icon representing a file or folder on the Desktop.
    • Single-click: select (cyan border)
    • Double-click: open (emit signal)
    • Drag: move to new grid cell
    • Right-click: Open / Rename / Trash context menu
    """
    double_clicked = pyqtSignal(object)   # emits Path
    moved          = pyqtSignal(object, object)  # Path, QPoint

    def __init__(self, path: Path, grid_pos: QPoint, parent=None):
        super().__init__(parent)
        self.path      = path
        self.grid_pos  = grid_pos
        self._selected = False
        self._drag_start = None

        self.setFixedSize(90, 100)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(5, 6, 5, 4)
        vl.setSpacing(4)
        vl.setAlignment(Qt.AlignCenter)

        # SVG icon (52×52)
        ico_lbl = QLabel()
        pix = _load_svg(_icon_for_path(path), 52)
        ico_lbl.setPixmap(pix)
        ico_lbl.setAlignment(Qt.AlignCenter)
        ico_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        vl.addWidget(ico_lbl)

        # Name label
        name = path.name
        display = (name[:11] + "…") if len(name) > 12 else name
        self._lbl = QLabel(display)
        self._lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setWordWrap(True)
        # Drop shadow for readability on any wallpaper
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(4)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 1)
        self._lbl.setGraphicsEffect(shadow)
        self._lbl.setStyleSheet("color: white; background:transparent; padding:1px 3px; border-radius:3px;")
        self._lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        vl.addWidget(self._lbl)

    # ── Selection ─────────────────────────────────────────────

    def set_selected(self, v: bool):
        from assets.theme import THEME
        self._selected = v
        if v:
            glow = THEME['primary_glow']
            self.setStyleSheet(
                f"DesktopFileIcon{{background: rgba(0, 230, 255, 0.15);"
                f"border: 1px solid {glow}; border-radius: 8px;}}"
            )
            self._lbl.setStyleSheet(
                f"color: white; background: {glow};"
                "padding: 1px 3px; border-radius: 3px;"
            )
        else:
            self.setStyleSheet("")
            self._lbl.setStyleSheet("color: white; background:transparent; padding:1px 3px; border-radius:3px;")
        self.update()

    # ── Mouse events ──────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
            # Deselect siblings
            parent = self.parent()
            if parent:
                for sib in parent.findChildren(DesktopFileIcon):
                    if sib is not self:
                        sib.set_selected(False)
            self.set_selected(True)
        elif event.button() == Qt.RightButton:
            self._context_menu(event.globalPos())
        event.accept()

    def mouseMoveEvent(self, event):
        if (self._drag_start is not None and
                (event.pos() - self._drag_start).manhattanLength() > 8):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.path))
            drag.setMimeData(mime)
            pix = QPixmap(self.size())
            pix.fill(Qt.transparent)
            self.render(pix)
            drag.setPixmap(pix)
            drag.setHotSpot(event.pos())
            drag.exec_(Qt.MoveAction)
            self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.path)

    # ── Context menu ──────────────────────────────────────────

    def _context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        menu.addAction("📂 Open" if self.path.is_dir() else "📄 Open",
                       lambda: self.double_clicked.emit(self.path))
        menu.addSeparator()
        menu.addAction("✏️  Rename", self._rename)
        menu.addAction("🗑️  Move to Trash", self._move_to_trash)
        menu.exec_(global_pos)

    def _rename(self):
        from PyQt5.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Rename")
        dlg.setLabelText("New name:")
        dlg.setTextValue(self.path.name)
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        if dlg.exec_():
            name = dlg.textValue().strip()
            if name and name != self.path.name:
                try:
                    new_path = self.path.parent / name
                    self.path.rename(new_path)
                    self.path = new_path
                    display = (name[:11] + "…") if len(name) > 12 else name
                    self._lbl.setText(display)
                except Exception as exc:
                    from PyQt5.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Rename Failed")
                    msg.setText(str(exc))
                    msg.setStyleSheet(DARK_DIALOG_STYLE)
                    msg.exec_()

    def _move_to_trash(self):
        try:
            from system.trash_manager import move_to_trash
            move_to_trash(str(self.path))
            self.deleteLater()
        except Exception as exc:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(str(exc))
            msg.setStyleSheet(DARK_DIALOG_STYLE)
            msg.exec_()

# Pre-render SVG → QPixmap cache
_ICON_CACHE: dict[str, QPixmap] = {}

def _load_svg(rel_path: str, size: int = 56) -> QPixmap:
    """Load SVG from path relative to project root, cache the result."""
    if rel_path in _ICON_CACHE:
        return _ICON_CACHE[rel_path]
    base = Path(__file__).parent.parent
    full = base / rel_path
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    if full.exists():
        renderer = QSvgRenderer(str(full))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p, QRectF(0, 0, size, size))
        p.end()
    _ICON_CACHE[rel_path] = pix
    return pix


# ── Desktop Icon Widget ───────────────────────────────────────

class DesktopIcon(QWidget):
    """
    90×100 px desktop icon.
    • SVG icon 56×56 rendered in a rounded rect
    • Label 11pt Segoe UI below, with drop-shadow for readability
    • Single-click: cyan selection ring
    • Hover: subtle cyan glow
    • Double-click: launch app
    """

    _ICO_SIZE   = 56   # px  — icon render size
    _W, _H      = 90, 100
    _C_BG_SEL   = QColor(84, 177, 198, 38)   # rgba(84,177,198,0.15)
    _C_BG_HOV   = QColor(84, 177, 198, 20)   # rgba(84,177,198,0.08)
    _C_RING     = QColor(84, 177, 198, 200)   # 2 px cyan ring
    _RADIUS     = 12

    def __init__(self, name: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._icon_path = icon_path
        self._selected  = False
        self._hovered   = False
        self._pixmap: QPixmap | None = None

        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"Double-click to open {name}")
        self.setMouseTracking(True)

        # Load SVG
        self._pixmap = _load_svg(icon_path, self._ICO_SIZE)

    # ── State helpers ─────────────────────────────────────────

    def set_selected(self, v: bool):
        if self._selected != v:
            self._selected = v
            self.update()

    def set_hovered(self, v: bool):
        if self._hovered != v:
            self._hovered = v
            self.update()

    # ── Painting ──────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        iw = self._W
        icon_area_h = 68    # pixels for icon zone
        icon_y0 = 4
        icon_x0 = (iw - self._ICO_SIZE) // 2
        icon_y_center = icon_y0 + (icon_area_h - self._ICO_SIZE) // 2

        # ── Background highlight ──
        if self._selected:
            p.setBrush(self._C_BG_SEL)
            pen = QPen(self._C_RING, 2)
            p.setPen(pen)
            p.drawRoundedRect(2, 2, iw - 4, icon_area_h + 4, self._RADIUS, self._RADIUS)
        elif self._hovered:
            p.setBrush(self._C_BG_HOV)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(2, 2, iw - 4, icon_area_h + 4, self._RADIUS, self._RADIUS)

        # ── SVG icon ──
        if self._pixmap and not self._pixmap.isNull():
            p.drawPixmap(icon_x0, icon_y_center, self._pixmap)

        # ── Label ──
        font = QFont("Segoe UI", 9)
        font.setWeight(QFont.Medium)
        p.setFont(font)

        label_rect = QRect(0, icon_y0 + icon_area_h + 2, iw, 28)

        # Drop shadow for wallpaper readability
        p.setPen(QColor(0, 0, 0, 140))
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (0, 1)):
            p.drawText(label_rect.adjusted(dx, dy, dx, dy),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                       self.name)

        # Actual label (vault text_primary)
        p.setPen(QColor(COLORS["text_primary"]))
        p.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.name)

        p.end()

    # ── Mouse events ──────────────────────────────────────────

    def enterEvent(self, event):
        self.set_hovered(True)

    def leaveEvent(self, event):
        self.set_hovered(False)

    def update_icon(self, svg_path: str):
        """Hot-swap the SVG icon (e.g. trash empty ↔ full)."""
        self._pixmap = _load_svg(svg_path, self._ICO_SIZE)
        self._icon_path = svg_path
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Deselect siblings
            parent = self.parent()
            if parent:
                for sib in parent.findChildren(DesktopIcon):
                    if sib is not self:
                        sib.set_selected(False)
            self.set_selected(True)
        elif event.button() == Qt.RightButton:
            self._context_menu(event.globalPos())

    def _context_menu(self, global_pos):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)

        act_open = QAction(f"Open {self.name}", self)
        act_open.triggered.connect(self.mouseDoubleClickEvent.__func__ and
                                   (lambda: self._launch()))
        act_open.triggered.connect(self._launch)
        menu.addAction(act_open)

        if self.name.lower() in ("terminal",):
            menu.addSeparator()
            act_admin = QAction("🔑  Run as Administrator", self)
            act_admin.triggered.connect(self._launch_as_admin)
            menu.addAction(act_admin)

        menu.exec_(global_pos)

    def _launch(self):
        p = self.parent()
        while p:
            if isinstance(p, Desktop):
                p.launch_app(self.name)
                return
            p = p.parent() if callable(p.parent) else None

    def _launch_as_admin(self):
        from components.sudo_dialog import SudoPasswordDialog
        dlg = SudoPasswordDialog(
            title="Administrator Access",
            message="Enter your password to open Terminal as administrator:",
            parent=self
        )
        if dlg.exec_() != dlg.Accepted:
            return
        password = dlg.get_password()

        verified = False
        try:
            from system.security_api import get_security_api
            security = get_security_api()
            if security:
                verified = security.verify_password("admin", password)
        except Exception:
            pass

        if not verified:
            try:
                from system.auth_manager import AUTH_MANAGER
                verified = AUTH_MANAGER.verify_admin_password(password)
            except Exception:
                pass

        if verified:
            p = self.parent()
            while p:
                if isinstance(p, Desktop):
                    p.launch_app(self.name, role_override="admin")
                    return
                p = p.parent() if callable(p.parent) else None
        else:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Authentication Failed")
            msg.setText("❌  Incorrect administrator password.")
            msg.setStyleSheet(
                "QMessageBox{background:#0b1929;color:#d4e8f0;}"
                "QLabel{color:#d4e8f0;} QPushButton{background:#1a2f4a;"
                "color:#7dd3e8;border:1px solid rgba(0,200,255,0.3);"
                "border-radius:6px;padding:6px 18px;}"
            )
            msg.exec_()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Find Desktop ancestor
            p = self.parent()
            while p:
                if isinstance(p, Desktop):
                    p.launch_app(self.name)
                    return
                p = p.parent() if callable(p.parent) else None


# ── Desktop ───────────────────────────────────────────────────

class Desktop(QWidget):
    """
    Full OS desktop:
    • Wallpaper from assets/qvault_vault.jpg (fill + vignette)
    • Fallback gradient if image absent
    • 3 SVG icons (vertical stack, top-left)
    • Bottom taskbar (live clock, open windows)
    • Right-click context menu: Refresh Desktop
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CrossCursor)
        self.icons: list[DesktopIcon] = []
        self._file_icons: dict[str, DesktopFileIcon] = {}
        self._grid_cells: dict[tuple, str] = {}
        self.setObjectName("Desktop")
        self.setAcceptDrops(True)

        # Try to connect runtime manager
        try:
            from system.runtime_manager import RUNTIME_MANAGER
            RUNTIME_MANAGER.set_desktop_parent(self)
        except Exception:
            pass

        # ── Layout ──
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._workspace = QWidget(self)
        self._workspace.setObjectName("Workspace")
        self._workspace.setStyleSheet("background: transparent;")
        layout.addWidget(self._workspace, 1)

        # ── Snap Preview Overlay (wired to WindowDragHandler) ──
        from components.snap_preview_overlay import SnapPreviewOverlay
        self.snap_preview = SnapPreviewOverlay(parent=self._workspace)
        self.snap_preview.hide()

        self._taskbar = TaskbarUI(parent=self)
        self._taskbar.setObjectName("Taskbar")
        layout.addWidget(self._taskbar)
        self._taskbar.app_clicked.connect(self._on_taskbar_app_clicked)
        self._taskbar.close_app.connect(self._close_app_by_id)
        self._taskbar.new_instance_requested.connect(self.launch_app)
        self._taskbar.open_launcher.connect(self._show_launcher_stub)

        # ── Timers ──
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        self._taskbar_timer = QTimer(self)
        self._taskbar_timer.timeout.connect(self._update_taskbar_apps)
        self._taskbar_timer.start(500)

        # ── Wallpaper cache ──
        self._wallpaper: QPixmap | None = None
        self._wallpaper_loaded = False
        self._wallpaper_path: str = ""

        # ── Event bus subscriptions ──
        try:
            EVENT_BUS.subscribe(SystemEvent.REQ_TERMINAL_OPEN_HERE, self._on_open_terminal_here)
            EVENT_BUS.subscribe(SystemEvent.EVT_TRASH_STATE_CHANGED, self._on_trash_state_changed)
            EVENT_BUS.subscribe(SystemEvent.STATE_CHANGED, self._on_state_changed)
        except Exception:
            pass

        # ── Stress Testing ──
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        self._stress_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._stress_shortcut.activated.connect(self._run_stress_test)

        # ── Context menu ──
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._desktop_menu)

        # ── Icons ──
        self._create_icons()

        # ── Desktop file watcher ──
        self._setup_desktop_watcher()
        self._load_desktop_files()

    def _run_stress_test(self):
        from components.stress_tester import AutomatedStressTester
        if not hasattr(self, "_stress_tester"):
            self._stress_tester = AutomatedStressTester(self)
        self._stress_tester.start()

        # Command Palette removed

    # ── Settings persistence ──────────────────────────────────

    def _settings(self):
        from PyQt5.QtCore import QSettings
        return QSettings("QVault", "Desktop")

    def _save_settings(self):
        s = self._settings()
        if self._wallpaper is not None:
            # Save the wallpaper path if we know it
            wp_path = getattr(self, "_wallpaper_path", "")
            if wp_path:
                s.setValue("wallpaper_path", str(wp_path))
        s.sync()

    def _load_settings(self):
        s = self._settings()
        saved_wp = s.value("wallpaper_path", "")
        if saved_wp and Path(saved_wp).exists():
            pix = QPixmap(saved_wp)
            if not pix.isNull():
                self._wallpaper = pix
                self._wallpaper_loaded = True
                self._wallpaper_path = saved_wp
                logger.info("[Desktop] Loaded wallpaper from settings: %s", saved_wp)

    # ── Wallpaper ─────────────────────────────────────────────

    def _load_wallpaper(self) -> QPixmap | None:
        if self._wallpaper_loaded:
            return self._wallpaper
        self._wallpaper_loaded = True
        # Check persisted custom wallpaper first
        self._load_settings()
        if self._wallpaper:
            return self._wallpaper
        wp_path = Path(__file__).parent.parent / "assets" / "qvault_vault.jpg"
        if wp_path.exists():
            pix = QPixmap(str(wp_path))
            if not pix.isNull():
                self._wallpaper = pix
                self._wallpaper_path = str(wp_path)
                return pix
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        wp = self._load_wallpaper()
        if wp:
            # Scale to fill, crop center
            scaled = wp.scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            x = (scaled.width()  - self.width())  // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            # Fallback gradient
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor(COLORS["bg_void"]))
            grad.setColorAt(0.5, QColor(COLORS["bg_surface"]))
            grad.setColorAt(1.0, QColor(COLORS["bg_base"]))
            painter.fillRect(self.rect(), grad)

        # Vignette overlay (bottom darker, top slightly dark)
        vignette = QLinearGradient(0, self.height(), 0, 0)
        vignette.setColorAt(0.0, QColor(1, 2, 14, 180))   # bottom
        vignette.setColorAt(0.3, QColor(1, 2, 14, 60))
        vignette.setColorAt(1.0, QColor(1, 2, 14, 100))   # top
        painter.fillRect(self.rect(), vignette)

        # Subtle cyan radial glow at center (brand accent)
        cx, cy = self.width() // 2, self.height() // 2
        radial = QRadialGradient(cx, cy, max(self.width(), self.height()) // 2)
        radial.setColorAt(0.0, QColor(84, 177, 198, 18))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), radial)

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep workspace fills area above taskbar
        tb_h = self._taskbar.height()
        self._workspace.setGeometry(0, 0, self.width(), self.height() - tb_h)

    # ── Icons ─────────────────────────────────────────────────

    def _create_icons(self):
        for icon in self.icons:
            icon.deleteLater()
        self.icons = []
        self._named_icons: dict[str, DesktopIcon] = {}

        x, y = 28, 28
        for app in _APPS:
            icon = DesktopIcon(app["name"], app["icon"], parent=self._workspace)
            icon.move(x, y)
            icon.show()
            self.icons.append(icon)
            self._named_icons[app["name"]] = icon
            y += 116  # vertical stack spacing

    # ── App launching ─────────────────────────────────────────

    def launch_app(self, name: str, start_path: str = None, role_override: str = None):
        from components.os_window import OSWindow
        from system.app_factory import create_app_by_name

        wm = get_window_manager()

        # Focus if already open
        existing = wm.find_by_title(name)
        if existing:
            wm.focus_window(existing.window_id)
            if start_path and hasattr(existing.content_widget, "change_directory"):
                existing.content_widget.change_directory(start_path)
            return existing

        kwargs = {}
        if start_path:
            kwargs["start_path"] = start_path
        if role_override:
            kwargs["role_override"] = role_override
        try:
            widget = create_app_by_name(name, parent=self._workspace, **kwargs)
        except Exception as exc:
            logger.exception("[Desktop] Error boundary caught crash launching '%s': %s", name, exc)
            widget = None
        if widget is None:
            logger.error("Failed to create app: %s", name)
            self._show_launch_error(name)
            return None

        win_id = str(uuid.uuid4())
        window = OSWindow(win_id, name, widget, parent=self._workspace)
        window.window_title = name
        wm.register_window(window)

        window.resize(860, 560)
        count = max(0, len(getattr(wm, "_windows", {})) - 1)
        offset = 60 + (count % 6) * 38
        window.move(offset, offset)
        window.show()

        # Register in Suspended Dock
        _icon_map = {
            "Terminal":         "assets/icons/terminal.svg",
            "File Manager":     "assets/icons/files.svg",
            "Trash":            "assets/icons/trash.svg",
            "Q-Vault Security": "assets/icons/icon-vault.svg",
            "Q-Vault Browser":  "assets/icons/browser.svg",
            "Kernel Monitor":   "assets/icons/kernel_monitor.svg",
        }
        self._taskbar.register_app(win_id, name, _icon_map.get(name))

        # Wire window close → unregister from dock
        _orig_close = window.closeEvent
        def _patched_close(ev, _wid=win_id, _oc=_orig_close):
            self._taskbar.unregister_app(_wid)
            _oc(ev)
        window.closeEvent = _patched_close

        self._update_taskbar_apps()
        return window

    def _on_state_changed(self, payload):
        """Handle STATE_CHANGED events — drives the snap preview overlay."""
        evt = payload.data.get("type", "")
        if evt == "snap_preview":
            from components.snap_controller import WindowSlot
            from PyQt5.QtCore import QRect
            slot = payload.data.get("slot")
            ws = self._workspace.rect()
            pw, ph = ws.width(), ws.height()
            rect_map = {
                WindowSlot.MAXIMIZED:     QRect(0, 0, pw, ph),
                WindowSlot.HALF_LEFT:     QRect(0, 0, pw // 2, ph),
                WindowSlot.HALF_RIGHT:    QRect(pw // 2, 0, pw // 2, ph),
                WindowSlot.QUARTER_TL:    QRect(0, 0, pw // 2, ph // 2),
                WindowSlot.QUARTER_TR:    QRect(pw // 2, 0, pw // 2, ph // 2),
                WindowSlot.QUARTER_BL:    QRect(0, ph // 2, pw // 2, ph // 2),
                WindowSlot.QUARTER_BR:    QRect(pw // 2, ph // 2, pw // 2, ph // 2),
            }
            target = rect_map.get(slot)
            if target:
                self.snap_preview.show_preview(target)
        elif evt == "snap_preview_hide":
            self.snap_preview.hide_preview()

    def _show_launch_error(self, app_name: str):
        """Show a non-blocking dark error toast when an app fails to launch."""
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer
        toast = QLabel(f"⚠  Could not open '{app_name}' — check logs for details.", self)
        toast.setStyleSheet(
            "QLabel { background: #1a0a0a; color: #ff6b6b;"
            "border: 1px solid rgba(255,80,80,0.4); border-radius: 8px;"
            "padding: 10px 18px; font-size: 11pt; }"
        )
        toast.adjustSize()
        toast.move(self.width() // 2 - toast.width() // 2, self.height() - 100)
        toast.show()
        QTimer.singleShot(4000, toast.deleteLater)

    # ── Taskbar helpers ───────────────────────────────────────

    def _update_clock(self):
        from PyQt5.QtCore import QTime
        self._taskbar.update_clock(QTime.currentTime().toString("hh:mm:ss"))

    def _update_taskbar_apps(self):
        wm = get_window_manager()
        apps = []
        active_id = None
        for win_id, win in list(getattr(wm, "_windows", {}).items()):
            # Include visible OR minimized windows
            if win.isVisible() or getattr(win, "is_minimized", False):
                title = getattr(win, "window_title", win_id)
                apps.append({"id": win_id, "title": title})
                if win.hasFocus():
                    active_id = win_id
        self._taskbar.update_state({"apps": apps, "active_id": active_id})

    def _on_taskbar_app_clicked(self, win_id: str):
        from core.event_bus import EVENT_BUS, SystemEvent
        wm = get_window_manager()
        if wm._active == win_id and not getattr(wm._windows.get(win_id), "is_minimized", False):
            # Already active? Minimize it!
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_MINIMIZE, {"id": win_id}, source="Taskbar")
        else:
            # Not active or minimized? Focus/Restore it!
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS, {"id": win_id}, source="Taskbar")

    # ── Context menu ──────────────────────────────────────────

    _MENU_STYLE = DARK_MENU_STYLE

    def _desktop_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(self._MENU_STYLE)

        # ── Appearance ──────────────────────────────────────────
        act_wp = QAction("🎨  Change Wallpaper…", self)
        act_wp.setEnabled(False)
        menu.addAction(act_wp)
        menu.addSeparator()

        # ── New ─────────────────────────────────────────────────
        act_nf = QAction("📄  New File", self)
        act_nf.triggered.connect(self._desktop_new_file)
        menu.addAction(act_nf)

        act_nd = QAction("📁  New Folder", self)
        act_nd.triggered.connect(self._desktop_new_folder)
        menu.addAction(act_nd)
        menu.addSeparator()

        # ── View ─────────────────────────────────────────────────
        act_ref = QAction("⟳  Refresh Desktop", self)
        act_ref.triggered.connect(self._create_icons)
        menu.addAction(act_ref)

        act_sort = QAction("⇅  Sort Icons", self)
        act_sort.setEnabled(False)
        menu.addAction(act_sort)
        menu.addSeparator()

        # ── Apps ─────────────────────────────────────────────────
        act_term = QAction("🖥️  Open Terminal Here", self)
        act_term.triggered.connect(self._open_terminal_at_desktop)
        menu.addAction(act_term)
        menu.addSeparator()

        # ── System ───────────────────────────────────────────────
        act_about = QAction("ℹ️  About Q-Vault OS", self)
        act_about.triggered.connect(self._show_about)
        menu.addAction(act_about)

        menu.addSeparator()
        act_account = QAction("👤  Account Settings…", self)
        act_account.triggered.connect(self._show_account_settings)
        menu.addAction(act_account)

        menu.exec_(self.mapToGlobal(pos))

    def _desktop_new_file(self):
        from PyQt5.QtWidgets import QInputDialog
        from system.config import get_qvault_home
        dlg = QInputDialog(self)
        dlg.setWindowTitle("New File")
        dlg.setLabelText("File name:")
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        if dlg.exec_():
            name = dlg.textValue().strip()
            if name:
                target = Path(get_qvault_home()) / "Desktop" / name
                try:
                    target.touch()
                    self._refresh_desktop_icons()
                except Exception as exc:
                    logger.error("Desktop new file failed: %s", exc)

    def _desktop_new_folder(self):
        from PyQt5.QtWidgets import QInputDialog
        from system.config import get_qvault_home
        dlg = QInputDialog(self)
        dlg.setWindowTitle("New Folder")
        dlg.setLabelText("Folder name:")
        dlg.setStyleSheet(DARK_DIALOG_STYLE)
        if dlg.exec_():
            name = dlg.textValue().strip()
            if name:
                target = Path(get_qvault_home()) / "Desktop" / name
                try:
                    target.mkdir(parents=True, exist_ok=True)
                    self._refresh_desktop_icons()
                except Exception as exc:
                    logger.error("Desktop new folder failed: %s", exc)



    def _show_account_settings(self):
        from components.account_settings_dialog import AccountSettingsDialog
        dlg = AccountSettingsDialog(parent=self)
        dlg.exec_()

    def _show_about(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.setFixedSize(360, 220)

        container = QWidget(dlg)
        container.setGeometry(0, 0, 360, 220)
        container.setStyleSheet("""
            QWidget {
                background: #0b1929;
                border: 1px solid rgba(0, 200, 255, 0.25);
                border-radius: 12px;
            }
            QLabel { background: transparent; color: white; }
            QPushButton {
                background: rgba(0,180,255,0.15);
                border: 1px solid rgba(0,200,255,0.3);
                border-radius: 8px;
                color: #00e6ff;
                padding: 6px 24px;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(0,180,255,0.3); }
        """)

        vl = QVBoxLayout(container)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(8)

        title = QLabel("Q-Vault OS")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #00e6ff; background: transparent;")

        ver = QLabel("Version 1.0.0  —  Secure Desktop Environment")
        ver.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")

        copy = QLabel("© 2025 Q-Vault Project. All rights reserved.")
        copy.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; background: transparent;")

        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        btn.setCursor(Qt.PointingHandCursor)

        vl.addWidget(title)
        vl.addWidget(ver)
        vl.addSpacing(8)
        vl.addWidget(copy)
        vl.addStretch()
        hl = QHBoxLayout()
        hl.addStretch()
        hl.addWidget(btn)
        vl.addLayout(hl)

        # Center on parent
        parent_center = self.rect().center()
        dlg.move(self.mapToGlobal(parent_center) - QPoint(180, 110))
        dlg.exec_()



    # ── Desktop file system ─────────────────────────────────

    def _setup_desktop_watcher(self):
        from system.config import get_qvault_home
        desktop_path = str(Path(get_qvault_home()) / "Desktop")
        Path(desktop_path).mkdir(parents=True, exist_ok=True)
        self._watcher = QFileSystemWatcher([desktop_path])
        self._watcher.directoryChanged.connect(self._on_desktop_changed)

    def _on_desktop_changed(self, _path: str):
        QTimer.singleShot(100, self._load_desktop_files)

    def _load_desktop_files(self):
        from system.config import get_qvault_home
        desktop = Path(get_qvault_home()) / "Desktop"
        desktop.mkdir(exist_ok=True)

        # Remove icons for deleted files
        existing = {str(p) for p in desktop.iterdir()}
        for path_str in list(self._file_icons.keys()):
            if path_str not in existing:
                try:
                    self._file_icons[path_str].deleteLater()
                except Exception:
                    pass
                del self._file_icons[path_str]
                # Remove from grid
                cell_key = next((k for k,v in self._grid_cells.items() if v == path_str), None)
                if cell_key:
                    del self._grid_cells[cell_key]

        # Add icons for new files (folders first, then files)
        entries = sorted(desktop.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        col, row = 0, 0
        for item in entries:
            path_str = str(item)
            if path_str in self._file_icons:
                continue
            # Find next free cell (column fills left side vertically)
            while (col, row) in self._grid_cells:
                row += 1
                if self._grid_to_pixel(col, row).y() + GRID_CELL_H > self._workspace.height() - 100:
                    col += 1
                    row = 0
            pixel = self._grid_to_pixel(col, row)
            icon_w = DesktopFileIcon(item, QPoint(col, row), self._workspace)
            icon_w.move(pixel)
            icon_w.double_clicked.connect(self._on_file_icon_dblclick)
            icon_w.show()
            self._file_icons[path_str] = icon_w
            self._grid_cells[(col, row)] = path_str
            row += 1

    def _grid_to_pixel(self, col: int, row: int) -> QPoint:
        # Left column: app icons. Desktop files start at col=1 to avoid overlap
        x = GRID_START_X + (col + 1) * GRID_CELL_W
        y = GRID_START_Y + row * GRID_CELL_H
        return QPoint(x, y)

    def _pixel_to_grid(self, px: QPoint) -> tuple:
        col = max(0, (px.x() - GRID_START_X - GRID_CELL_W) // GRID_CELL_W)
        row = max(0, (px.y() - GRID_START_Y) // GRID_CELL_H)
        return (col, row)

    def _on_file_icon_dblclick(self, path):
        if path.is_dir():
            self.launch_app("File Manager", start_path=str(path))
        else:
            self.launch_app("Terminal")

    # ── Drag & Drop ──────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        path_str = event.mimeData().text()
        drop_pos = event.pos()
        grid_cell = self._pixel_to_grid(drop_pos)
        icon = self._file_icons.get(path_str)
        if not icon:
            return
        # Remove old cell
        old_key = next((k for k,v in self._grid_cells.items() if v == path_str), None)
        if old_key:
            del self._grid_cells[old_key]
        # Find free cell near drop point
        col, row = grid_cell
        while (col, row) in self._grid_cells:
            col += 1
        pixel = self._grid_to_pixel(col, row)
        icon.move(pixel)
        icon.grid_pos = QPoint(col, row)
        self._grid_cells[(col, row)] = path_str
        event.acceptProposedAction()

    # ── Terminal context helpers ──────────────────────────────

    def _open_terminal_at_desktop(self):
        from system.config import get_qvault_home
        desktop_path = str(Path(get_qvault_home()) / "Desktop")
        self.launch_app("Terminal", start_path=desktop_path)

    def _on_open_terminal_here(self, payload):
        try:
            data = payload.data if hasattr(payload, "data") else payload
            path = data.get("path", "") if isinstance(data, dict) else ""
            if path:
                self.launch_app("Terminal", start_path=path)
        except Exception as exc:
            logger.warning("_on_open_terminal_here error: %s", exc)

    def _on_trash_state_changed(self, payload):
        """Swap Trash desktop icon between empty/full state."""
        try:
            data = payload.data if hasattr(payload, "data") else payload
            has_items = data.get("has_items", False) if isinstance(data, dict) else False
            icon_path = "assets/icons/trash_full.svg" if has_items else "assets/icons/trash.svg"
            widget = getattr(self, "_named_icons", {}).get("Trash")
            if widget:
                widget.update_icon(icon_path)
        except Exception as exc:
            logger.warning("_on_trash_state_changed error: %s", exc)

    def _refresh_desktop_icons(self):
        for icon in list(self._file_icons.values()):
            try:
                icon.deleteLater()
            except Exception:
                pass
        self._file_icons.clear()
        self._grid_cells.clear()
        self._load_desktop_files()
        self._create_icons()

    # ── Dock helpers (wired to taskbar signals) ───────────────

    def _close_app_by_id(self, win_id: str):
        """Close a window from the taskbar × button."""
        wm = get_window_manager()
        win = getattr(wm, "_windows", {}).get(win_id)
        if win:
            win.close()
        self._taskbar.unregister_app(win_id)

    def _show_launcher_stub(self):
        from PyQt5.QtWidgets import QToolTip
        pos = self._taskbar.mapToGlobal(QPoint(40, 0))
        QToolTip.showText(pos, "Q-Vault OS  |  3 Apps Active")

    # ── Session ───────────────────────────────────────────────

    def set_user(self, username: str):
        logger.info("Desktop: session active for '%s'", username)
        try:
            from system.config import is_first_run, mark_first_run_complete
            if is_first_run():
                mark_first_run_complete()
        except Exception:
            pass
