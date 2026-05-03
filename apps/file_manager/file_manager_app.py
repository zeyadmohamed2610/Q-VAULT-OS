import os
import shutil
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QSplitter, QFrame, QMenu, QAction,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QScrollArea,
    QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap

from system.config import get_qvault_home
from system.trash_manager import move_to_trash
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

STYLE = """
QWidget { background: #0b1320; color: #c9d1d9; }
QPushButton {
    background: rgba(33, 38, 45, 0.8); color: #c9d1d9; border: 1px solid rgba(48, 54, 61, 0.5);
    border-radius: 4px; padding: 4px 10px; font-size: 12px;
}
QPushButton:hover { background: rgba(48, 54, 61, 0.9); }
QPushButton:pressed { background: rgba(31, 111, 235, 0.8); }
QLineEdit {
    background: #161b22; color: #c9d1d9; border: 1px solid rgba(48, 54, 61, 0.5);
    border-radius: 4px; padding: 4px 8px;
}
QListWidget {
    background: #0d1117; color: #c9d1d9; border: 1px solid rgba(48, 54, 61, 0.5);
    border-radius: 4px;
}
QListWidget::item { padding: 4px 8px; border-radius: 3px; }
QListWidget::item:selected { background: rgba(31, 111, 235, 0.8); color: white; }
QListWidget::item:hover { background: rgba(33, 38, 45, 0.8); }
QLabel { color: #c9d1d9; }
QSplitter::handle { background: rgba(48, 54, 61, 0.5); }
"""


def _icon_for(path: Path) -> str:
    """Return an emoji for a path."""
    if path.is_dir():
        name = path.name.lower()
        if name == "desktop":   return "🖥️ "
        if name == "documents": return "📄 "
        if name == "downloads": return "⬇️ "
        if name == "pictures":  return "🖼️ "
        if name == ".trash":    return "🗑️ "
        return "📁 "
    ext = path.suffix.lower()
    if ext in (".txt", ".md", ".log"): return "📝 "
    if ext in (".py", ".js", ".ts", ".c", ".cpp", ".h"): return "💻 "
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg"): return "🖼️ "
    if ext in (".zip", ".tar", ".gz", ".7z"): return "📦 "
    if ext in (".mp3", ".wav", ".flac"): return "🎵 "
    if ext in (".mp4", ".avi", ".mkv"): return "🎬 "
    return "📄 "




# ── File icon system (SVG per type) ──────────────────────────
ICON_MAP_FM = {
    "folder":   "assets/icons/folder.svg",
    ".txt":     "assets/icons/file_text.svg",
    ".md":      "assets/icons/file_text.svg",
    ".py":      "assets/icons/file_text.svg",
    ".js":      "assets/icons/file_text.svg",
    ".ts":      "assets/icons/file_text.svg",
    ".json":    "assets/icons/file_text.svg",
    ".html":    "assets/icons/file_text.svg",
    ".css":     "assets/icons/file_text.svg",
    ".c":       "assets/icons/file_text.svg",
    ".cpp":     "assets/icons/file_text.svg",
    ".h":       "assets/icons/file_text.svg",
    "_default": "assets/icons/file_generic.svg",
}


def get_file_icon(path: Path, size: int = 48) -> QPixmap:
    """Return a scaled QPixmap for a file or folder using SVG icon map."""
    svg = ICON_MAP_FM["folder"] if path.is_dir() else ICON_MAP_FM.get(
        path.suffix.lower(), ICON_MAP_FM["_default"]
    )
    pix = QPixmap(svg)
    if pix.isNull():
        pix = QPixmap(size, size)
        pix.fill(QColor("#0b162d"))
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

# ── Context menu style (vault palette) ───────────────────────
CONTEXT_MENU_STYLE = (
    "QMenu{background:#0b162d;"
    "border:1px solid rgba(84,177,198,0.20);"
    "border-radius:10px;padding:6px 0;"
    "color:#d4e8f0;font-family:\'Segoe UI\';font-size:10pt;}"
    "QMenu::item{padding:7px 28px 7px 16px;"
    "border-radius:6px;margin:1px 4px;}"
    "QMenu::item:selected{background:rgba(84,177,198,0.15);color:#7dd3e8;}"
    "QMenu::separator{height:1px;background:rgba(84,177,198,0.10);margin:4px 12px;}"
    "QMenu::section{color:#4a6880;font-size:9pt;padding:4px 16px 2px;}"
    "QMenu::item:disabled{color:#4a6880;}"
)

class FileManagerApp(QWidget):
    def __init__(self, secure_api=None, parent=None):
        super().__init__(parent)
        self.secure_api = secure_api
        self.setObjectName("FileManagerApp")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(STYLE)

        self._base_dir = Path(get_qvault_home()).resolve()
        self._current_path = self._base_dir
        self._history: list = []
        self._fwd_stack: list = []
        self._clipboard: Path | None = None
        self._cut_mode = False

        self._setup_ui()
        self._navigate(self._base_dir, record=False)
        self._subscribe_events()

    # ── UI Build ──────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        tb = QHBoxLayout()
        tb.setContentsMargins(8, 6, 8, 6)
        tb.setSpacing(6)
        self._btn_back = QPushButton("←")
        self._btn_back.setFixedSize(28, 28)
        self._btn_back.setToolTip("Back")
        self._btn_back.clicked.connect(self._go_back)
        tb.addWidget(self._btn_back)
        self._btn_fwd = QPushButton("→")
        self._btn_fwd.setFixedSize(28, 28)
        self._btn_fwd.setToolTip("Forward")
        self._btn_fwd.clicked.connect(self._go_forward)
        tb.addWidget(self._btn_fwd)
        self._btn_up = QPushButton("↑")
        self._btn_up.setFixedSize(28, 28)
        self._btn_up.setToolTip("Up")
        self._btn_up.clicked.connect(self._go_up)
        tb.addWidget(self._btn_up)
        self._path_bar = QLineEdit()
        self._path_bar.returnPressed.connect(self._on_path_bar_enter)
        tb.addWidget(self._path_bar, 1)
        self._btn_refresh = QPushButton("⟳")
        self._btn_refresh.setFixedSize(28, 28)
        self._btn_refresh.clicked.connect(self.refresh)
        tb.addWidget(self._btn_refresh)
        main_layout.addLayout(tb)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #30363d;")
        main_layout.addWidget(sep)

        # Splitter: sidebar | file list
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # Sidebar
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(160)
        self._sidebar.setStyleSheet(STYLE + "QListWidget { border-right: 1px solid #30363d; border-radius: 0; }")
        self._sidebar.itemClicked.connect(self._on_sidebar_click)
        self._build_sidebar()
        splitter.addWidget(self._sidebar)

        # File list
        self._file_list = QListWidget()
        self._file_list.setViewMode(QListWidget.IconMode)
        self._file_list.setIconSize(QSize(48, 48))
        self._file_list.setGridSize(QSize(90, 90))
        self._file_list.setResizeMode(QListWidget.Adjust)
        self._file_list.setMovement(QListWidget.Static)
        self._file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._file_list.itemDoubleClicked.connect(self._on_double_click)
        self._file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._show_context_menu)
        self._file_list.installEventFilter(self)
        splitter.addWidget(self._file_list)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)

        # Status bar
        self._status_bar = QLabel("Ready")
        self._status_bar.setStyleSheet(
            "color: #8b949e; background: #161b22; border-top: 1px solid #30363d;"
            "padding: 3px 10px; font-size: 11px;"
        )
        main_layout.addWidget(self._status_bar)

    def _build_sidebar(self):
        self._sidebar.clear()
        shortcuts = [
            ("🏠 Home",       self._base_dir),
            ("🖥️  Desktop",   self._base_dir / "Desktop"),
            ("📄 Documents",  self._base_dir / "Documents"),
            ("⬇️  Downloads",  self._base_dir / "Downloads"),
            ("🖼️  Pictures",   self._base_dir / "Pictures"),
            ("🗑️  Trash",      self._base_dir / ".trash"),
        ]
        for label, path in shortcuts:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(path))
            item.setSizeHint(QSize(150, 32))
            self._sidebar.addItem(item)

    # ── Navigation ────────────────────────────────────────────

    def _navigate(self, path: Path, record=True):
        if not isinstance(path, Path):
            path = Path(path)
        path = path.resolve()
        if not str(path).startswith(str(self._base_dir)):
            return
        if record and self._current_path != path:
            self._history.append(self._current_path)
            self._fwd_stack.clear()
        self._current_path = path
        self._path_bar.setText(str(path))
        self._load_dir(path)

    def _load_dir(self, path: Path):
        self._file_list.clear()
        try:
            entries = sorted(path.iterdir(),
                             key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            self._status_bar.setText("Permission denied")
            return
        except Exception as exc:
            self._status_bar.setText(f"Error: {exc}")
            return

        dirs = [e for e in entries if e.is_dir()]
        files = [e for e in entries if not e.is_dir()]

        for entry in dirs + files:
            item = QListWidgetItem(entry.name)
            item.setData(Qt.UserRole, str(entry))
            item.setToolTip(str(entry))
            # SVG icon
            icon_pix = get_file_icon(entry, 48)
            item.setIcon(QIcon(icon_pix))
            if entry.is_dir():
                item.setForeground(QColor("#58a6ff"))
            self._file_list.addItem(item)

        total = len(dirs) + len(files)
        self._status_bar.setText(f"{total} item{'s' if total != 1 else ''}  ({len(dirs)} folders, {len(files)} files)")

    def _go_back(self):
        if not self._history:
            return
        self._fwd_stack.append(self._current_path)
        self._navigate(self._history.pop(), record=False)

    def _go_forward(self):
        if not self._fwd_stack:
            return
        self._history.append(self._current_path)
        self._navigate(self._fwd_stack.pop(), record=False)

    def _go_up(self):
        parent = self._current_path.parent
        if str(parent).startswith(str(self._base_dir)) or parent == self._base_dir:
            self._navigate(parent)

    def _on_path_bar_enter(self):
        p = Path(self._path_bar.text())
        if p.is_dir():
            self._navigate(p)

    def _on_sidebar_click(self, item):
        path_str = item.data(Qt.UserRole)
        if path_str:
            self._navigate(Path(path_str))

    def refresh(self):
        self._load_dir(self._current_path)

    # ── File Operations ───────────────────────────────────────

    def _selected_paths(self) -> list:
        paths = []
        for item in self._file_list.selectedItems():
            p = item.data(Qt.UserRole)
            if p:
                paths.append(Path(p))
        return paths

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "Filename:")
        if ok and name:
            t = self._current_path / name
            try:
                t.touch()
                self.refresh()
                EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": str(t)}, source="FileManager")
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            t = self._current_path / name
            try:
                t.mkdir(parents=True)
                self.refresh()
                EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": str(t)}, source="FileManager")
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _rename_selected(self):
        paths = self._selected_paths()
        if not paths:
            return
        p = paths[0]
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=p.name)
        if ok and name.strip() and name.strip() != p.name:
            dest = p.parent / name.strip()
            try:
                p.rename(dest)
                self.refresh()
                EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": str(dest)}, source="FileManager")
            except Exception as exc:
                QMessageBox.critical(self, "Rename Failed", str(exc))

    def _trash_selected(self):
        paths = self._selected_paths()
        for p in paths:
            try:
                move_to_trash(str(p))
                EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": str(p)}, source="FileManager")
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Cannot move '{p.name}' to trash:\n{exc}")
        self.refresh()

    def _show_properties(self, path: Path):
        import datetime
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Properties — {path.name}")
        dlg.setFixedWidth(340)
        dlg.setStyleSheet("background:#0b162d; color:#d4e8f0;")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 16, 20, 16)
        vl.setSpacing(8)
        try:
            s = path.stat()
            info = {
                "Name":     path.name,
                "Type":     "Folder" if path.is_dir() else "File",
                "Location": str(path.parent),
                "Size":     f"{s.st_size:,} bytes" if path.is_file() else "—",
                "Created":  f"{datetime.datetime.fromtimestamp(s.st_ctime):%Y-%m-%d %H:%M:%S}",
                "Modified": f"{datetime.datetime.fromtimestamp(s.st_mtime):%Y-%m-%d %H:%M:%S}",
            }
            for k, v in info.items():
                row = QLabel(f"<b style=\'color:#54b1c6\'>{k}:</b>&nbsp;&nbsp;{v}")
                row.setWordWrap(True)
                row.setStyleSheet("background:transparent;")
                vl.addWidget(row)
        except Exception as exc:
            vl.addWidget(QLabel(str(exc)))
        btn = QPushButton("Close")
        btn.setStyleSheet(
            "background:#0f2842;color:#54b1c6;"
            "border:1px solid #2f6183;border-radius:6px;padding:6px 16px;"
        )
        btn.clicked.connect(dlg.accept)
        vl.addWidget(btn, alignment=Qt.AlignRight)
        dlg.exec_()

    # ── Context Menus ─────────────────────────────────────────

    def _show_context_menu(self, pos):
        selected = self._selected_paths()
        global_pos = self._file_list.mapToGlobal(pos)

        if selected:
            self._item_context_menu(global_pos, selected)
        else:
            self._empty_context_menu(global_pos)

    def _item_context_menu(self, global_pos, paths):
        from PyQt5.QtWidgets import QAction
        menu = QMenu(self)
        menu.setStyleSheet(CONTEXT_MENU_STYLE)

        if len(paths) == 1:
            p0 = paths[0]
            label = "📂  Open" if p0.is_dir() else "📄  Open"
            act_open = QAction(label, self)
            if p0.is_dir():
                act_open.triggered.connect(lambda: self._navigate(p0))
            else:
                act_open.triggered.connect(lambda: self._on_double_click(
                    self._file_list.currentItem()))
            menu.addAction(act_open)
            menu.addSeparator()

        act_cut  = QAction("✂️  Cut",   self); act_cut.triggered.connect(lambda: self._clipboard_cut(paths))
        act_copy = QAction("📋  Copy",  self); act_copy.triggered.connect(lambda: self._clipboard_copy(paths))
        act_paste= QAction("📌  Paste", self); act_paste.setEnabled(bool(self._clipboard))
        act_paste.triggered.connect(self._paste)
        menu.addActions([act_cut, act_copy, act_paste])
        menu.addSeparator()

        act_rename = QAction("✏️  Rename", self)
        act_rename.triggered.connect(self._rename_selected)
        menu.addAction(act_rename)

        act_trash = QAction("🗑️  Move to Trash", self)
        act_trash.triggered.connect(self._trash_selected)
        menu.addAction(act_trash)
        menu.addSeparator()

        if len(paths) == 1:
            act_props = QAction("ℹ️  Properties", self)
            act_props.triggered.connect(lambda: self._show_properties(paths[0]))
            menu.addAction(act_props)

        menu.exec_(global_pos)

    def _empty_context_menu(self, global_pos):
        from PyQt5.QtWidgets import QAction
        menu = QMenu(self)
        menu.setStyleSheet(CONTEXT_MENU_STYLE)

        act_nf = QAction("📄  New File", self)
        act_nf.triggered.connect(self._new_file)
        menu.addAction(act_nf)

        act_nd = QAction("📂  New Folder", self)
        act_nd.triggered.connect(self._new_folder)
        menu.addAction(act_nd)
        menu.addSeparator()

        act_paste = QAction("📌  Paste", self)
        act_paste.setEnabled(bool(self._clipboard))
        act_paste.triggered.connect(self._paste)
        menu.addAction(act_paste)
        menu.addSeparator()

        act_ref = QAction("⟳  Refresh", self)
        act_ref.triggered.connect(self.refresh)
        menu.addAction(act_ref)

        act_term = QAction("🖥️  Open Terminal Here", self)
        act_term.triggered.connect(self._open_terminal_here)
        menu.addAction(act_term)

        menu.exec_(global_pos)

    def _clipboard_cut(self, paths):
        self._clipboard = paths[0] if paths else None
        self._cut_mode = True

    def _clipboard_copy(self, paths):
        self._clipboard = paths[0] if paths else None
        self._cut_mode = False

    def _paste(self):
        if not self._clipboard or not self._clipboard.exists():
            return
        dest = self._current_path / self._clipboard.name
        try:
            if self._cut_mode:
                shutil.move(str(self._clipboard), str(dest))
                self._clipboard = None
            else:
                if self._clipboard.is_dir():
                    shutil.copytree(str(self._clipboard), str(dest))
                else:
                    shutil.copy2(str(self._clipboard), str(dest))
            self.refresh()
            EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": str(dest)}, source="FileManager")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    # ── Keyboard Shortcuts ────────────────────────────────────

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self._file_list and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key == Qt.Key_Delete:
                self._trash_selected(); return True
            if key == Qt.Key_F2:
                self._rename_selected(); return True
            if key == Qt.Key_F5:
                self.refresh(); return True
            if key == Qt.Key_Backspace:
                self._go_back(); return True
            if mods == Qt.ControlModifier and key == Qt.Key_A:
                self._file_list.selectAll(); return True
        return super().eventFilter(obj, event)

    def _on_double_click(self, item):
        path_str = item.data(Qt.UserRole)
        if not path_str:
            return
        p = Path(path_str)
        if p.is_dir():
            self._navigate(p)
        else:
            QMessageBox.information(self, "Open With",
                f"Open With… (placeholder)\n\n{p.name}")

    # ── Event Bus ─────────────────────────────────────────────

    def _subscribe_events(self):
        try:
            EVENT_BUS.subscribe(SystemEvent.FS_CHANGED, self._on_fs_changed)
        except Exception:
            pass

    def _on_fs_changed(self, payload):
        try:
            changed_path = Path(payload.data.get("path", ""))
            # Only refresh if the changed path is in our current directory
            if (str(changed_path).startswith(str(self._current_path)) or
                    changed_path.parent == self._current_path):
                QTimer.singleShot(100, self.refresh)
        except Exception:
            pass

    def _open_terminal_here(self):
        """Emit event to open Terminal pre-cd'd to current FM path."""
        try:
            EVENT_BUS.emit(SystemEvent.REQ_TERMINAL_OPEN_HERE,
                           {"path": str(self._current_path)},
                           source="FileManager")
        except Exception as exc:
            logger.warning("Open Terminal Here failed: %s", exc)

    def closeEvent(self, event):

        try:
            EVENT_BUS.unsubscribe(SystemEvent.FS_CHANGED, self._on_fs_changed)
        except Exception:
            pass
        super().closeEvent(event)
