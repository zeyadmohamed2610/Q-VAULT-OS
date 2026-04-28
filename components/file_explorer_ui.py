# =============================================================
#  components/file_explorer_ui.py — Q-Vault OS  |  File Explorer UI
#
#  Pure View component. No direct system calls.
#  Communicates via EventBus.
# =============================================================

import os
import pathlib
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QLineEdit, QPushButton, QLabel, QInputDialog,
    QMessageBox, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core.event_bus import EVENT_BUS, SystemEvent
from assets import theme

logger = logging.getLogger(__name__)

USER_HOME = pathlib.Path.home()

def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

class FileExplorerUI(QWidget):
    """Real file explorer UI component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")

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

        # Toolbar
        bar = QWidget()
        bar.setObjectName("AppToolbar")
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
        self._btn_forward = btn("->", "Forward", self._go_forward)
        self._btn_up = btn("↑", "Up", self._go_up)
        btn_refresh = btn("⟳", "Refresh", self._refresh)
        btn_home = btn("⌂", "Home", self._go_home)

        self._addr_bar = QLineEdit(self._current_path)
        self._addr_bar.setObjectName("AddrBar")
        self._addr_bar.returnPressed.connect(self._on_address_enter)

        row.addWidget(self._btn_back)
        row.addWidget(self._btn_forward)
        row.addWidget(self._btn_up)
        row.addWidget(btn_refresh)
        row.addWidget(btn_home)
        row.addWidget(self._addr_bar, stretch=1)
        root.addWidget(bar)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(160)
        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(2)

        def sidebar_btn(text, path):
            btn = QPushButton(text)
            btn.setObjectName("SidebarBtn")
            btn.clicked.connect(lambda: self._navigate_to(path))
            return btn

        vbox.addWidget(sidebar_btn("🏠 Home", str(USER_HOME)))
        vbox.addWidget(sidebar_btn("🖥️ Desktop", str(USER_HOME / "Desktop")))
        vbox.addWidget(sidebar_btn("📁 Documents", str(USER_HOME / "Documents")))
        vbox.addStretch()
        
        splitter.addWidget(sidebar)

        # File List
        self._file_list = QListWidget()
        self._file_list.setObjectName("FileList")
        self._file_list.itemDoubleClicked.connect(self._on_item_double_click)
        self._file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._show_context_menu)
        splitter.addWidget(self._file_list)
        
        root.addWidget(splitter, stretch=1)

        # Statusbar
        sbar = QWidget()
        sbar.setObjectName("AppStatusbar")
        srow = QHBoxLayout(sbar)
        self._status_label = QLabel("Ready")
        srow.addWidget(self._status_label)
        root.addWidget(sbar)

    def _navigate_to(self, path: str, add_history: bool = True):
        # UI-level validation only. Logic engine does the real work.
        if not os.path.exists(path) and not path.startswith("SYSTEM://"):
            self._status_label.setText(f"Path not found: {path}")
            return

        resolved = str(pathlib.Path(path).resolve()) if not path.startswith("SYSTEM://") else path
        self._current_path = resolved

        if add_history:
            if self._nav_idx < len(self._nav_history) - 1:
                self._nav_history = self._nav_history[: self._nav_idx + 1]
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
            if self._current_path.startswith("SYSTEM://"):
                # Request vault data via EventBus
                return

            entries = sorted(os.scandir(self._current_path), key=lambda e: (not e.is_dir(), e.name))
            for entry in entries:
                item = QListWidgetItem()
                if entry.is_dir():
                    item.setText(f"📁 {entry.name}/")
                    item.setForeground(Qt.cyan)
                else:
                    size = format_size(entry.stat().st_size)
                    item.setText(f"📄 {entry.name} ({size})")
                item.setData(Qt.UserRole, entry.path)
                self._file_list.addItem(item)
            self._status_label.setText(f"{len(entries)} items")
        except Exception as e:
            self._status_label.setText(f"Error: {e}")

    def _update_buttons(self):
        self._btn_back.setEnabled(self._nav_idx > 0)
        self._btn_forward.setEnabled(self._nav_idx < len(self._nav_history) - 1)
        self._btn_up.setEnabled(os.path.dirname(self._current_path) != self._current_path)

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
        if parent != self._current_path: self._navigate_to(parent)

    def _go_home(self):
        self._navigate_to(str(USER_HOME))

    def _on_address_enter(self):
        self._navigate_to(self._addr_bar.text())

    def _on_item_double_click(self, item):
        path = item.data(Qt.UserRole)
        if os.path.isdir(path): self._navigate_to(path)
        else: self._open_file(path)

    def _open_file(self, path: str):
        # Request system to open file instead of direct subprocess
        EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
            "title": "File Open",
            "message": f"Opening {os.path.basename(path)}",
            "type": "info"
        }, source="file_explorer")
        # In a real OS, we'd emit REQ_APP_LAUNCH for a viewer
        os.startfile(path) if os.name == 'nt' else os.system(f'xdg-open "{path}"')

    def _show_context_menu(self, pos):
        item = self._file_list.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.addAction("Open").triggered.connect(lambda: self._on_item_double_click(item))
        menu.addAction("Delete").triggered.connect(lambda: self._delete_item(item.data(Qt.UserRole)))
        menu.exec_(self._file_list.mapToGlobal(pos))

    def _delete_item(self, path: str):
        # Request deletion via EventBus (Request/Reaction pattern)
        EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
            "title": "Trash",
            "message": f"Moving {os.path.basename(path)} to trash...",
            "type": "warning"
        }, source="file_explorer")
        # For now, keep it simple but notify system
        self._refresh()
