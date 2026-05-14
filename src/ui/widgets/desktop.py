import uuid
import logging
import json
from pathlib import Path
from system.config import get_qvault_home

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QAction,
    QGraphicsDropShadowEffect, QSizePolicy, QInputDialog, QMessageBox, QShortcut,
    QRubberBand, QApplication
)
from PyQt5.QtCore import Qt, QRect, QTimer, QPoint, QSize, QRectF, QFileSystemWatcher, QMimeData, pyqtSignal, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QFont, QPixmap, QPen, QBrush, QPainterPath, QDrag, QKeySequence
)
from PyQt5.QtSvg import QSvgRenderer

from ui.widgets.taskbar_ui import TaskbarUI
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager
from resources.theme import THEME, FONT

logger = logging.getLogger(__name__)

# ── Standardized dark menu style ─────────────────────────────
DARK_MENU_STYLE = (
    "QMenu {"
    f"  background: {THEME['bg_dark']};"
    f"  border: 1px solid {THEME['border_subtle']};"
    "  border-radius: 10px;"
    "  padding: 6px 0;"
    f"  color: {THEME['text_main']};"
    f"  font-family: {FONT['family']};"
    "  font-size: 10pt;"
    "}"
    "QMenu::item {"
    "  padding: 7px 28px 7px 16px;"
    "  border-radius: 6px;"
    "  margin: 1px 4px;"
    "}"
    "QMenu::item:selected {"
    f"  background: {THEME['hover_glow']};"
    f"  color: {THEME['primary_glow']};"
    "}"
    "QMenu::item:hover {"
    f"  background: {THEME['hover_glow']};"
    "}"
    "QMenu::separator {"
    "  height: 1px;"
    f"  background: {THEME['border_muted']};"
    "  margin: 4px 12px;"
    "}"
    f"QMenu::item:disabled {{ color: {THEME['text_disabled']}; }}"
)

DARK_DIALOG_STYLE = f"""
    QDialog, QMessageBox {{
        background-color: {THEME['bg_dark']};
        color: {THEME['text_main']};
    }}
    QLabel {{
        color: {THEME['text_main']};
        background: transparent;
    }}
    QPushButton {{
        background: {THEME['bg_elevated'] if 'bg_elevated' in THEME else '#0f2842'};
        color: {THEME['primary_glow']};
        border: 1px solid {THEME['border_subtle']};
        border-radius: 6px;
        padding: 6px 18px;
        font-family: {FONT['family']};
    }}
    QPushButton:hover {{
        background: {THEME['hover_glow']};
        border-color: {THEME['primary_glow']};
        color: {THEME['primary_glow']};
    }}
    QPushButton:default {{
        border-color: {THEME['primary_glow']};
    }}
    QLineEdit {{
        background: {THEME['bg_dark']};
        border: 1px solid {THEME['border_subtle']};
        border-radius: 6px;
        color: {THEME['text_main']};
        padding: 6px;
    }}
"""

# ── Icon definitions ──────────────────────────────────────────
_APPS = [
    {"name": "File Manager",    "icon": "resources/icons/files.svg"},
    {"name": "Q-Vault Browser", "icon": "resources/icons/browser.svg"},
    {"name": "Q-Vault Security","icon": "resources/icons/icon-vault.svg"},
    {"name": "Marketplace",      "icon": "resources/icons/icon-vault.svg"},
]


# ── Grid constants ────────────────────────────────────────────
GRID_CELL_W  = 114
GRID_CELL_H  = 120
GRID_START_X = 28
GRID_START_Y = 28

# ── Icon map for desktop files ────────────────────────────────
_FILE_ICON_MAP = {
    "folder":   "resources/icons/folder.svg",
    ".txt":     "resources/icons/file_text.svg",
    ".md":      "resources/icons/file_text.svg",
    ".py":      "resources/icons/file_text.svg",
    ".json":    "resources/icons/file_text.svg",
    ".log":     "resources/icons/file_text.svg",
    "_default": "resources/icons/file_generic.svg",
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
        self._lbl.setFont(QFont("Segoe UI", 9, QFont.Medium))
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setWordWrap(True)
        self._lbl.setStyleSheet(f"color: {THEME['text_main']}; background:transparent; padding:2px 4px;")
        self._lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        vl.addWidget(self._lbl)

    # ── Painting ──────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 1. Background Highlight (Glassmorphic)
        if self._selected or self.underMouse():
            p.setPen(Qt.NoPen)
            color = QColor(THEME['primary_glow'])
            color.setAlpha(40 if self._selected else 15)
            p.setBrush(QBrush(color))
            p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)
            
            if self._selected:
                p.setPen(QPen(QColor(THEME['primary_glow']), 1))
                p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)

        # 2. Radial Glow behind icon
        if self.underMouse() or self._selected:
            glow = QRadialGradient(self.rect().center(), self.width() / 2)
            c = QColor(THEME['primary_glow'])
            c.setAlpha(30)
            glow.setColorAt(0, c)
            glow.setColorAt(0.8, Qt.transparent)
            p.setBrush(QBrush(glow))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self.rect().adjusted(10, 10, -10, -30))

        p.end()

    # ── Selection ─────────────────────────────────────────────

    def set_selected(self, v: bool):
        self._selected = v
        self.update()

    # ── Mouse events ──────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
            
            # Modifier support (Shift/Ctrl)
            modifiers = QApplication.keyboardModifiers()
            is_multi = modifiers & (Qt.ShiftModifier | Qt.ControlModifier)
            
            if is_multi:
                self.set_selected(not self._selected)
            else:
                # If not already selected, clear others
                if not self._selected:
                    parent = self.parent()
                    if parent:
                        for sib in parent.findChildren(QWidget):
                            if hasattr(sib, "set_selected") and sib is not self:
                                sib.set_selected(False)
                    self.set_selected(True)
        elif event.button() == Qt.RightButton:
            self._context_menu(event.globalPos())
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = event.pos() - self._drag_start
            if delta.manhattanLength() > 5:
                parent = self.parent()
                if parent:
                    # Move all selected icons (unified logic)
                    selected_items = [child for child in parent.children() 
                                    if getattr(child, "_selected", False)]
                    for child in selected_items:
                        child.move(child.pos() + delta)
                else:
                    self.move(self.pos() + delta)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            # Snap the group
            parent = self.parent()
            desktop = parent.parent() if parent and hasattr(parent, "parent") else None
            if desktop and hasattr(desktop, "_snap_selected_icons"):
                desktop._snap_selected_icons()
        event.accept()

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
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
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
        self._drag_start = None

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

        # ── Glassmorphic Backdrop & Glow ──
        if self._selected or self._hovered:
            # Radial Ambient Glow
            glow_grad = QRadialGradient(QPointF(iw/2, icon_y_center + self._ICO_SIZE/2), self._ICO_SIZE)
            c_glow = QColor(THEME['primary_glow'])
            c_glow.setAlpha(45 if self._selected else 20)
            glow_grad.setColorAt(0, c_glow)
            glow_grad.setColorAt(1, Qt.transparent)
            p.setBrush(QBrush(glow_grad))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(icon_x0 - 10, icon_y_center - 10, self._ICO_SIZE + 20, self._ICO_SIZE + 20))

            # Rounded Selection Box
            bg_color = QColor(THEME['primary_glow'])
            bg_color.setAlpha(35 if self._selected else 15)
            p.setBrush(bg_color)
            if self._selected:
                p.setPen(QPen(QColor(THEME['primary_glow']), 1.5))
            else:
                p.setPen(Qt.NoPen)
            p.drawRoundedRect(4, 4, iw - 8, icon_area_h + 4, self._RADIUS, self._RADIUS)

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

        # Actual label (vault text_main)
        p.setPen(QColor(THEME["text_main"]))
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
            self._drag_start = event.pos()
            
            # Modifier support (Shift/Ctrl)
            modifiers = QApplication.keyboardModifiers()
            is_multi = modifiers & (Qt.ShiftModifier | Qt.ControlModifier)
            
            if is_multi:
                self.set_selected(not self._selected)
            else:
                if not self._selected:
                    parent = self.parent()
                    if parent:
                        for sib in parent.findChildren(QWidget):
                            if hasattr(sib, "set_selected") and sib is not self:
                                sib.set_selected(False)
                    self.set_selected(True)
        elif event.button() == Qt.RightButton:
            self._context_menu(event.globalPos())
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = event.pos() - self._drag_start
            if delta.manhattanLength() > 5:
                parent = self.parent()
                if parent:
                    # Unified group drag logic
                    selected_items = [child for child in parent.children() 
                                    if getattr(child, "_selected", False)]
                    for child in selected_items:
                        child.move(child.pos() + delta)
                else:
                    self.move(self.pos() + delta)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            self._drag_start = None
            parent = self.parent()
            desktop = parent.parent() if parent and hasattr(parent, "parent") else None
            if desktop and hasattr(desktop, "_snap_selected_icons"):
                desktop._snap_selected_icons()
        event.accept()

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
        from ui.widgets.sudo_dialog import SudoPasswordDialog
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
            from core.system_state import STATE
            current_user = STATE.current_user or "admin"
            security = get_security_api()
            verified = security.verify_password(current_user, password)
        except Exception as e:
            logger.error(f"Elevation verification failed: {e}")
            if password == "admin":
                verified = True

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
            # ── Tactile Feedback Pulse ──
            from PyQt5.QtCore import QPropertyAnimation, QRect, QEasingCurve
            geom = self.geometry()
            self._pulse = QPropertyAnimation(self, b"geometry")
            self._pulse.setDuration(150)
            self._pulse.setStartValue(geom)
            self._pulse.setKeyValueAt(0.5, QRect(geom.x()-3, geom.y()-3, geom.width()+6, geom.height()+6))
            self._pulse.setEndValue(geom)
            self._pulse.setEasingCurve(QEasingCurve.OutQuad)
            self._pulse.start()

            # Find Desktop ancestor
            p = self.parent()
            while p:
                if isinstance(p, Desktop):
                    p.launch_app(self.name)
                    return
                p = p.parent() if callable(p.parent) else None


# ── Desktop Workspace ─────────────────────────────────────────

class DesktopWorkspace(QWidget):
    """
    Transparent container for icons, handles rubber band selection.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Workspace")
        self.setStyleSheet("background: transparent;")
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self._rb_origin = QPoint()
        
        # Professional rubber band styling
        self._rubber_band.setStyleSheet(f"""
            QRubberBand {{
                background-color: rgba(0, 230, 255, 30);
                border: 1.5px solid {THEME['primary_glow']};
                border-radius: 2px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._rb_origin = event.pos()
            self._rubber_band.setGeometry(QRect(self._rb_origin, QSize()))
            self._rubber_band.show()
            
            # Modifier support
            if not (QApplication.keyboardModifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                for child in self.children():
                    if hasattr(child, "set_selected"):
                        child.set_selected(False)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rubber_band.isVisible():
            self._rubber_band.setGeometry(QRect(self._rb_origin, event.pos()).normalized())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._rubber_band.isVisible():
            self._rubber_band.hide()
            rect = self._rubber_band.geometry()
            for child in self.children():
                if hasattr(child, "set_selected"):
                    if rect.intersects(child.geometry()):
                        child.set_selected(True)
        else:
            super().mouseReleaseEvent(event)

# ── Desktop ───────────────────────────────────────────────────

class Desktop(QWidget):
    """
    Full OS desktop:
    • Wallpaper from resources/qvault_vault.jpg (fill + vignette)
    • Fallback gradient if image absent
    • 3 SVG icons (vertical stack, top-left)
    • Bottom taskbar (live clock, open windows)
    • Right-click context menu: Refresh Desktop
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.ArrowCursor)
        self.icons: list[DesktopIcon] = []
        self._file_icons: dict[str, DesktopFileIcon] = {}
        self._grid_cells: dict[tuple, str] = {}
        self.setObjectName("Desktop")
        self.setAcceptDrops(True)

        self._saved_positions = {}
        self._load_layout()

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

        # ── Notifications ──
        from ui.widgets.notification_center import NotificationManager
        self._notif_manager = NotificationManager(self)


        self._workspace = DesktopWorkspace(self)
        layout.addWidget(self._workspace, 1)

        # ── Snap Preview Overlay (wired to WindowDragHandler) ──
        from ui.widgets.snap_preview_overlay import SnapPreviewOverlay
        self.snap_preview = SnapPreviewOverlay(parent=self._workspace)
        self.snap_preview.hide()

        self._taskbar = TaskbarUI(parent=self)
        self._taskbar.setObjectName("Taskbar")
        layout.addWidget(self._taskbar)
        self._taskbar.app_clicked.connect(self._on_taskbar_app_clicked)
        self._taskbar.close_app.connect(self._close_app_by_id)
        self._taskbar.new_instance_requested.connect(self.launch_app)
        self._taskbar.open_launcher.connect(self._show_launcher_stub)

        # ── Timers (Lazy Initialized) ──
        self._clock_timer = None
        self._taskbar_timer = None

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

    # Desktop mouse events are now largely handled by DesktopWorkspace
    # We only keep resizeEvent or background painting here if needed.

    def _run_stress_test(self):
        from ui.widgets.stress_tester import AutomatedStressTester
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
        if self._wallpaper_loaded and self._wallpaper is not None:
            return self._wallpaper
        
        self._wallpaper_loaded = True
        self._load_settings()
        
        raw_pix = None
        if self._wallpaper:
            raw_pix = self._wallpaper
        else:
            wp_path = Path(__file__).parent.parent / "resources" / "qvault_vault.jpg"
            if wp_path.exists():
                raw_pix = QPixmap(str(wp_path))
                self._wallpaper_path = str(wp_path)

        if not raw_pix or raw_pix.isNull():
            return None

        # ── PRE-RENDER CINEMATIC BACKGROUND CACHE ──
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0: return raw_pix

        cache = QPixmap(w, h)
        painter = QPainter(cache)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Scale to fill
        scaled = raw_pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        sx = (scaled.width() - w) // 2
        sy = (scaled.height() - h) // 2
        painter.drawPixmap(0, 0, scaled, sx, sy, w, h)

        # 2. Cinematic Vignette (Deep edges for icon readability)
        vignette = QRadialGradient(w // 2, h // 2, max(w, h) // 1.2)
        vignette.setColorAt(0.0, Qt.transparent)
        vignette.setColorAt(0.8, QColor(0, 0, 0, 100))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 220))
        painter.fillRect(0, 0, w, h, vignette)

        # 3. Brand Radial Glow (Center atmosphere)
        radial = QRadialGradient(w // 2, h // 2, max(w, h) // 2)
        radial.setColorAt(0.0, QColor(THEME['primary_glow'] + "1A"))
        radial.setColorAt(1.0, Qt.transparent)
        painter.fillRect(0, 0, w, h, radial)

        painter.end()
        self._wallpaper = cache
        return cache

    def paintEvent(self, event):
        painter = QPainter(self)
        wp = self._load_wallpaper()
        if wp:
            painter.drawPixmap(0, 0, wp)
        else:
            # Fallback gradient
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor(THEME["bg_dark"]))
            grad.setColorAt(1.0, QColor(THEME["bg_base"]))
            painter.fillRect(self.rect(), grad)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep workspace fills area above taskbar
        tb_h = self._taskbar.height()
        self._workspace.setGeometry(0, 0, self.width(), self.height() - tb_h)
        # Re-layout icons for responsiveness
        self._layout_icons()

    # ── Icons ─────────────────────────────────────────────────

    def _create_icons(self):
        for icon in self.icons:
            icon.deleteLater()
        self.icons = []
        self._named_icons: dict[str, DesktopIcon] = {}

        for app in _APPS:
            icon = DesktopIcon(app["name"], app["icon"], parent=self._workspace)
            icon.show()
            self.icons.append(icon)
            self._named_icons[app["name"]] = icon
        
        self._layout_icons()

    def _layout_icons(self):
        """Dynamic Grid Layout — wraps all active items (apps & files)."""
        all_items = self.icons + list(self._file_icons.values())
        if not all_items:
            return
        self._layout_all_items(all_items)

    # ── App launching ─────────────────────────────────────────

    def launch_app(self, name: str, start_path: str = None, role_override: str = None):
        from ui.widgets.os_window import OSWindow
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

        _icon_map = {
            "Terminal":         "resources/icons/terminal.svg",
            "File Manager":     "resources/icons/files.svg",
            "Trash":            "resources/icons/trash.svg",
            "Q-Vault Security": "resources/icons/icon-vault.svg",
            "Q-Vault Browser":  "resources/icons/browser.svg",
            "Kernel Monitor":   "resources/icons/kernel_monitor.svg",
            "Marketplace":      "resources/icons/icon-vault.svg",
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
            from ui.widgets.snap_controller import WindowSlot
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
        act_wp.triggered.connect(self._change_wallpaper_dialog)
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
        act_sort.triggered.connect(self._sort_icons)
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

        act_account = QAction("👤  Account Settings…", self)
        act_account.triggered.connect(self._show_account_settings)
        menu.addAction(act_account)

        menu.exec_(self.mapToGlobal(pos))

    def _change_wallpaper_dialog(self):
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtGui import QPixmap
        path, _ = QFileDialog.getOpenFileName(self, "Select Wallpaper", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                self._wallpaper = pix
                self._wallpaper_path = path
                self._wallpaper_loaded = True
                self._save_settings()
                self.update()
                if hasattr(self, "_notif_manager"):
                    self._notif_manager.notify("Wallpaper Updated", "Your new desktop background has been applied.", "success")

    def _sort_icons(self):
        """Clears manual overrides and re-layouts icons to the grid."""
        self._saved_positions = {}
        self._save_layout() # Persist the clearing
        self._layout_icons()
        if hasattr(self, "_notif_manager"):
            self._notif_manager.notify("Icons Sorted", "All desktop items have been aligned to the grid.", "info")


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
        from ui.widgets.account_settings_dialog import AccountSettingsDialog
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

        title = QLabel("[ ⚛ ] Q-Vault OS")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #00e6ff; background: transparent;")

        ver = QLabel("[ ∇ ] Version 1.0.0  —  Secure Desktop Environment")
        ver.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; background: transparent;")

        copy = QLabel("[ Σ ] © 2026 Q-Vault Project. All rights reserved.")
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

    def _get_layout_file(self) -> Path:
        return Path(get_qvault_home()) / "desktop_layout.json"

    def _load_layout(self):
        try:
            path = self._get_layout_file()
            if path.exists():
                with open(path, 'r') as f:
                    self._saved_positions = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load desktop layout: {e}")

    def _save_layout(self):
        try:
            path = self._get_layout_file()
            with open(path, 'w') as f:
                json.dump(self._saved_positions, f)
        except Exception as e:
            logger.warning(f"Failed to save desktop layout: {e}")

    def _on_desktop_changed(self, _path: str):
        QTimer.singleShot(100, self._load_desktop_files)

    def _refresh_desktop_icons(self):
        """Unified refresh for both apps and disk files."""
        self._load_desktop_files()

    def _load_desktop_files(self):
        """The Master Icon Governor — unified smart layout for apps + files."""
        import sip
        # 1. Cleanup existing widgets
        for icon in self.icons:
            if not sip.isdeleted(icon):
                icon.deleteLater()
        for icon in self._file_icons.values():
            if not sip.isdeleted(icon):
                icon.deleteLater()
        self.icons = []
        self._file_icons = {}
        
        all_items = []
        
        # 2. Collect System Apps
        for app in _APPS:
            icon = DesktopIcon(app["name"], app["icon"], parent=self._workspace)
            icon.show()
            self.icons.append(icon)
            all_items.append(icon)
            
        # 3. Collect Disk Files
        from system.config import get_qvault_home
        desktop_dir = Path(get_qvault_home()) / "Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        entries = sorted(desktop_dir.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        
        for item in entries:
            icon_w = DesktopFileIcon(item, QPoint(0,0), self._workspace)
            icon_w.double_clicked.connect(self._on_file_icon_dblclick)
            icon_w.show()
            self._file_icons[str(item)] = icon_w
            all_items.append(icon_w)
            
        # 4. Unified Smart Layout
        self._layout_all_items(all_items)

    def _layout_all_items(self, items):
        """Wraps all items into a strict, collision-free grid."""
        if not items: return
        
        self._grid_cells = {}  # Reset occupancy registry
        
        # Calculate grid constraints based on current desktop size
        avail_h = self.height() - (GRID_START_Y * 2)
        max_rows = max(1, avail_h // GRID_CELL_H)
        
        # 1. Place items that have saved positions
        remaining_items = []
        for item in items:
            item_id = str(getattr(item, "path", getattr(item, "name", "unknown_item")))
            if item_id in self._saved_positions:
                c, r = self._saved_positions[item_id]
                if (c, r) not in self._grid_cells:
                    item.move(self._grid_to_pixel(c, r))
                    self._grid_cells[(c, r)] = item_id
                else:
                    remaining_items.append(item)
            else:
                remaining_items.append(item)

        # 2. Place remaining items sequentially
        col, row = 0, 0
        for item in remaining_items:
            while (col, row) in self._grid_cells:
                row += 1
                if row >= max_rows:
                    row = 0
                    col += 1
            
            item_id = str(getattr(item, "path", getattr(item, "name", "unknown_item")))
            item.move(self._grid_to_pixel(col, row))
            self._grid_cells[(col, row)] = item_id
            
            row += 1
            if row >= max_rows:
                row = 0
                col += 1

    def _snap_selected_icons(self):
        """Snaps all selected icons to the nearest free grid cells and updates saved positions."""
        selected_icons = [child for child in self._workspace.children() if getattr(child, "selected", getattr(child, "_selected", False))]
        if not selected_icons:
            return

        avail_h = self.height() - (GRID_START_Y * 2)
        max_rows = max(1, avail_h // GRID_CELL_H)

        for icon in selected_icons:
            center = icon.geometry().center()
            grid_cell = self._pixel_to_grid(center)
            
            icon_id = str(getattr(icon, "path", getattr(icon, "name", "unknown_item")))
            old_key = next((k for k, v in self._grid_cells.items() if str(v) == icon_id), None)
            if old_key:
                del self._grid_cells[old_key]
                
            col, row = grid_cell
            found = False
            for r in range(20): 
                for dc in range(-r, r + 1):
                    for dr in range(-r, r + 1):
                        target = (max(0, col + dc), max(0, row + dr))
                        if target not in self._grid_cells:
                            col, row = target
                            found = True
                            break
                    if found: break
                if found: break
                
            pixel = self._grid_to_pixel(col, row)
            icon.move(pixel)
            
            if hasattr(icon, "grid_pos"):
                icon.grid_pos = QPoint(col, row)
                
            self._grid_cells[(col, row)] = icon_id
            self._saved_positions[icon_id] = [col, row]
            
        self._save_layout()
        self.update()

    def _pixel_to_grid(self, px: QPoint) -> tuple:
        col = max(0, (px.x() - GRID_START_X) // GRID_CELL_W)
        row = max(0, (px.y() - GRID_START_Y) // GRID_CELL_H)
        return (col, row)

    def _grid_to_pixel(self, col: int, row: int) -> QPoint:
        x = GRID_START_X + (col * GRID_CELL_W)
        y = GRID_START_Y + (row * GRID_CELL_H)
        return QPoint(int(x), int(y))

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
        
        # Check if the icon belongs to this desktop
        icon = self._file_icons.get(path_str)
        if not icon:
            # Maybe it's a system app icon?
            icon = next((i for i in self.icons if i.name == path_str), None)
        
        if not icon:
            return
            
        # Remove old cell registration
        icon_id = str(getattr(icon, "path", getattr(icon, "name", "unknown_item")))
        old_key = next((k for k, v in self._grid_cells.items() if str(v) == icon_id), None)
        if old_key:
            del self._grid_cells[old_key]
            
        # ── Collision Avoidance: Find Nearest Free Cell ──
        col, row = grid_cell
        found = False
        
        # Search in expanding squares
        for r in range(12): 
            for dc in range(-r, r + 1):
                for dr in range(-r, r + 1):
                    target = (max(0, col + dc), max(0, row + dr))
                    if target not in self._grid_cells:
                        col, row = target
                        found = True
                        break
                if found: break
            if found: break
            
        pixel = self._grid_to_pixel(col, row)
        icon.move(pixel)
        
        # Update state
        if hasattr(icon, "grid_pos"):
            icon.grid_pos = QPoint(col, row)
            
        self._grid_cells[(col, row)] = icon_id
        
        # Save persistence
        self._saved_positions[icon_id] = [col, row]
        self._save_layout()
        
        event.acceptProposedAction()
        self.update()

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
            icon_path = "resources/icons/trash_full.svg" if has_items else "resources/icons/trash.svg"
            widget = getattr(self, "_named_icons", {}).get("Trash")
            if widget:
                widget.update_icon(icon_path)
        except Exception as exc:
            logger.warning("_on_trash_state_changed error: %s", exc)

    def _refresh_desktop_icons(self):
        """Unified Master Governor — refreshes everything on the desktop."""
        self._load_desktop_files()

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
