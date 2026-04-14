# =============================================================
#  file_explorer.py — Q-Vault OS  |  Real File Explorer v4
#
#  Real filesystem with sandbox + trash support
# =============================================================

import os
import pathlib
import shutil
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QInputDialog,
    QMessageBox,
    QMenu,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap

from assets import theme
from system.sandbox_system import SANDBOX, TRASH_DIR, ensure_trash_exists
from system.security_input import validate_path


USER_HOME = pathlib.Path.home()
HOST_OS = "Windows" if os.name == "nt" else "Linux"


def format_size(size: int) -> str:
    """Format file size in human readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_date(timestamp: float) -> str:
    """Format date from timestamp."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M")


# Performance guard: max items shown before truncating
_MAX_DISPLAY_ITEMS = 2000

class RealFileExplorer(QWidget):
    """Real file explorer that interfaces with the host filesystem."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileExplorer")
        self.setStyleSheet(theme.FILE_EXPLORER_STYLE)

        self._current_path = str(USER_HOME)
        self._nav_history = [str(USER_HOME)]
        self._nav_idx = 0
        self._clipboard = []
        self._clipboard_action = None

        self._setup_ui()
        self._navigate_to(str(USER_HOME), add_history=False)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_toolbar())
        # Sidebar + file list in horizontal panel
        _mid = QWidget()
        _mid_layout = QHBoxLayout(_mid)
        _mid_layout.setContentsMargins(0, 0, 0, 0)
        _mid_layout.setSpacing(0)
        _mid_layout.addWidget(self._make_sidebar())
        _mid_layout.addWidget(self._make_main_panel(), stretch=1)
        root.addWidget(_mid, stretch=1)
        root.addWidget(self._make_statusbar())

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-bottom:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(4)

        def btn(label, tip, slot, w=32):
            b = QPushButton(label)
            b.setObjectName("FEBtn")
            b.setToolTip(tip)
            b.setFixedWidth(w)
            b.clicked.connect(slot)
            return b

        self._btn_back = btn("←", "Back", self._go_back)
        self._btn_forward = btn("→", "Forward", self._go_forward)
        self._btn_up = btn("↑", "Up", self._go_up)
        btn_refresh = btn("⟳", "Refresh", self._refresh)
        btn_home = btn("⌂", "Home", self._go_home)

        self._addr_bar = QLineEdit(self._current_path)
        self._addr_bar.setObjectName("AddrBar")
        self._addr_bar.setStyleSheet(
            f"background:{theme.BG_DARK}; color:{theme.TEXT_PRIMARY}; border:1px solid {theme.BORDER_DIM}; padding:4px;"
        )
        self._addr_bar.returnPressed.connect(self._on_address_enter)

        row.addWidget(self._btn_back)
        row.addWidget(self._btn_forward)
        row.addWidget(self._btn_up)
        row.addWidget(btn_refresh)
        row.addWidget(btn_home)
        row.addWidget(self._addr_bar, stretch=1)

        return bar

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-right:1px solid {theme.BORDER_DIM};"
        )

        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(2)

        def sidebar_btn(text, path):
            btn = QPushButton(text)
            btn.setObjectName("SidebarBtn")
            btn.setStyleSheet(
                f"QPushButton#SidebarBtn {{"
                f"  text-align:left; padding: 7px 10px;"
                f"  color:{theme.TEXT_DIM}; background:transparent;"
                f"  border:none; border-radius: 5px;"
                f"  font-family: {theme.FONT_MONO}; font-size: 11px;"
                f"}}"
                f"QPushButton#SidebarBtn:hover {{"
                f"  background:{theme.BG_HOVER}; color:{theme.TEXT_PRIMARY};"
                f"}}"
            )
            btn.clicked.connect(lambda: self._navigate_to(path))
            return btn

        vbox.addWidget(sidebar_btn("🏠 Home", str(USER_HOME)))
        vbox.addWidget(sidebar_btn("🖥️ Desktop", str(USER_HOME / "Desktop")))
        vbox.addWidget(sidebar_btn("📁 Documents", str(USER_HOME / "Documents")))
        vbox.addWidget(sidebar_btn("⬇️ Downloads", str(USER_HOME / "Downloads")))
        vbox.addWidget(sidebar_btn("🎵 Music", str(USER_HOME / "Music")))
        vbox.addWidget(sidebar_btn("🖼️ Pictures", str(USER_HOME / "Pictures")))
        vbox.addWidget(sidebar_btn("🎬 Videos", str(USER_HOME / "Videos")))

        vbox.addStretch()

        root_label = QLabel("SYSTEM")
        root_label.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px; font-weight:bold; padding:8px;"
        )
        vbox.addWidget(root_label)

        if HOST_OS == "Windows":
            vbox.addWidget(sidebar_btn("💾 C:", "C:\\"))
        else:
            vbox.addWidget(sidebar_btn("📂 Root", "/"))

        return sidebar

    def _make_main_panel(self) -> QWidget:
        splitter = QSplitter(Qt.Horizontal)

        self._file_list = QListWidget()
        self._file_list.setStyleSheet(
            f"background:{theme.BG_WINDOW}; color:{theme.TEXT_PRIMARY};"
            f"border:none; font-family:Consolas;"
        )
        self._file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._file_list.itemDoubleClicked.connect(self._on_item_double_click)
        self._file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._show_context_menu)

        # Enable drag and drop
        self._file_list.setAcceptDrops(True)
        self._file_list.setDragEnabled(True)
        self._file_list.setDragDropMode(QListWidget.DragDrop)
        self._file_list.setDefaultDropAction(Qt.MoveAction)

        splitter.addWidget(self._file_list)
        splitter.setSizes([600, 200])

        return splitter

    def _make_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-top:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px;")

        row.addWidget(self._status_label)
        row.addStretch()

        return bar

    def _navigate_to(self, path: str, add_history: bool = True):
        # Validate path to prevent traversal attacks
        is_safe, resolved = validate_path(path)
        if not is_safe:
            self._status_label.setText(
                f"Access denied: Invalid path (traversal blocked)"
            )
            return

        if not os.path.exists(resolved):
            self._status_label.setText(f"Path not found: {path}")
            return

        if not os.path.isdir(resolved):
            return

        self._current_path = resolved

        if add_history and self._nav_idx < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[: self._nav_idx + 1]
        if add_history:
            self._nav_history.append(self._current_path)
            self._nav_idx = len(self._nav_history) - 1

        self._addr_bar.setText(self._current_path)
        self._update_buttons()
        self._refresh_file_list()

    def _refresh(self):
        self._navigate_to(self._current_path, add_history=False)

    def _refresh_file_list(self):
        self._file_list.clear()

        try:
            entries = sorted(
                os.scandir(self._current_path), key=lambda e: (not e.is_dir(), e.name)
            )
        except PermissionError:
            self._status_label.setText("Permission denied")
            return
        except Exception as e:
            self._status_label.setText(f"Error: {str(e)}")
            return

        count = 0
        for entry in entries:
            try:
                item = QListWidgetItem()
                stat = entry.stat()
                name = entry.name
                is_dir = entry.is_dir()

                if is_dir:
                    item.setText(f"📁 {name}/")
                    item.setForeground(Qt.cyan)
                else:
                    size = format_size(stat.st_size)
                    ext = os.path.splitext(name)[1].lower()

                    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                        icon = "🖼️"
                    elif ext in [".py", ".txt", ".md", ".json"]:
                        icon = "📄"
                    elif ext in [".exe", ".msi"]:
                        icon = "⚙️"
                    else:
                        icon = "📄"

                    item.setText(f"{icon} {name}  ({size})")

                item.setData(Qt.UserRole, entry.path)
                self._file_list.addItem(item)
                count += 1
            except (PermissionError, OSError):
                pass

        self._status_label.setText(f"{count} items")

    def _update_buttons(self):
        self._btn_back.setEnabled(self._nav_idx > 0)
        self._btn_forward.setEnabled(self._nav_idx < len(self._nav_history) - 1)
        self._btn_up.setEnabled(
            os.path.dirname(self._current_path) != self._current_path
        )

    def _go_back(self):
        if self._nav_idx > 0:
            self._nav_idx -= 1
            self._navigate_to(self._nav_history[self._nav_idx], add_history=False)

    def _go_forward(self):
        if self._nav_idx < len(self._nav_history) - 1:
            self._nav_idx += 1
            self._navigate_to(self._nav_history[self._nav_idx], add_history=False)

    def _go_up(self):
        parent = os.path.dirname(self._current_path)
        if parent != self._current_path:
            self._navigate_to(parent)

    def _go_home(self):
        self._navigate_to(str(USER_HOME))

    def _on_address_enter(self):
        self._navigate_to(self._addr_bar.text())

    def _on_item_double_click(self, item):
        path = item.data(Qt.UserRole)
        if os.path.isdir(path):
            self._navigate_to(path)
        else:
            self._open_file(path)

    def _open_file(self, path: str):
        try:
            if HOST_OS == "Windows":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open file: {str(e)}")

    def _show_context_menu(self, pos):
        item = self._file_list.itemAt(pos)
        if not item:
            return

        path = item.data(Qt.UserRole)
        menu = QMenu(self)

        act_open = menu.addAction("Open")
        act_open.triggered.connect(
            lambda: self._open_file(path)
            if not os.path.isdir(path)
            else self._navigate_to(path)
        )

        menu.addSeparator()

        act_rename = menu.addAction("Rename")
        act_rename.triggered.connect(lambda: self._rename_item(path))

        act_copy = menu.addAction("Copy")
        act_copy.triggered.connect(lambda: self._copy_item(path))

        act_paste = menu.addAction("Paste")
        act_paste.triggered.connect(lambda: self._paste_item(path))

        menu.addSeparator()

        act_delete = menu.addAction("Delete")
        act_delete.triggered.connect(lambda: self._delete_item(path))

        menu.exec_(self._file_list.mapToGlobal(pos))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            path = os.path.join(self._current_path, name)
            try:
                os.makedirs(path, exist_ok=True)
                self._refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot create folder: {str(e)}")

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if ok and name:
            path = os.path.join(self._current_path, name)
            try:
                pathlib.Path(path).touch()
                self._refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot create file: {str(e)}")

    def _rename_item(self, path: str):
        name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
        if ok and new_name and new_name != name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try:
                os.rename(path, new_path)
                self._refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot rename: {str(e)}")

    def _delete_item(self, path: str):
        if not SANDBOX.is_path_safe(path):
            QMessageBox.warning(self, "Blocked", "Cannot delete system files!")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Move {os.path.basename(path)} to trash?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                if SANDBOX.move_to_trash(path):
                    self._send_notification(
                        "File deleted", f"Moved to trash: {os.path.basename(path)}"
                    )
                    self._refresh()
                else:
                    QMessageBox.warning(self, "Error", "Failed to move to trash")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot delete: {str(e)}")

    def _send_notification(self, title: str, message: str):
        try:
            from system.notification_system import NOTIFY

            NOTIFY.send(title, message, level="info")
        except Exception:
            pass

    def _copy_item(self, path: str):
        self._clipboard = [path]
        self._clipboard_action = "copy"
        self._status_label.setText(f"Copied: {os.path.basename(path)}")

    def _paste_item(self, target_dir: str = None):
        if not self._clipboard or not self._clipboard_action:
            return

        dest = target_dir or self._current_path

        for src in self._clipboard:
            name = os.path.basename(src)
            dst = os.path.join(dest, name)

            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot copy: {str(e)}")

        self._refresh()
        self._status_label.setText(f"Pasted {len(self._clipboard)} item(s)")


# ── Class alias expected by app_registry ────────────────────
FileExplorer = RealFileExplorer
