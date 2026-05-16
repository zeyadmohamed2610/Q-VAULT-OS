import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QLineEdit, QPushButton, QLabel, QMessageBox, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core.event_bus import EVENT_BUS, SystemEvent
from resources.theme import THEME
from system.vfs import VFS

logger = logging.getLogger(__name__)

def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

class FileExplorerUI(QWidget):
    """
    Sovereign VFS File Explorer v2.0
    Reduces host OS leaks by operating exclusively on the Virtual Filesystem.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")

        self._current_path = "/home/user"
        self._nav_history = ["/home/user"]
        self._nav_idx = 0

        self._setup_ui()
        self._navigate_to("/home/user", add_history=False)

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
        self._btn_forward = btn("→", "Forward", self._go_forward)
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
            b = QPushButton(text)
            b.setObjectName("SidebarBtn")
            b.clicked.connect(lambda: self._navigate_to(path))
            return b

        vbox.addWidget(sidebar_btn("🏠 Home", "/home/user"))
        vbox.addWidget(sidebar_btn("🛡️ Vault", "/vault"))
        vbox.addWidget(sidebar_btn("⚙️ System", "/etc"))
        vbox.addWidget(sidebar_btn("📋 Logs", "/var/log"))
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
        self._status_label = QLabel("Sovereign VFS Active")
        srow.addWidget(self._status_label)
        root.addWidget(sbar)

    def _navigate_to(self, path: str, add_history: bool = True):
        try:
            # Resolve relative paths or cd
            new_path = VFS.cd(path, self._current_path)
            self._current_path = new_path

            if add_history:
                if self._nav_idx < len(self._nav_history) - 1:
                    self._nav_history = self._nav_history[: self._nav_idx + 1]
                self._nav_history.append(self._current_path)
                self._nav_idx = len(self._nav_history) - 1

            self._addr_bar.setText(self._current_path)
            self._update_buttons()
            self._refresh_file_list()
        except Exception as e:
            self._status_label.setText(f"Navigation Error: {e}")

    def _refresh(self):
        self._refresh_file_list()

    def _refresh_file_list(self):
        self._file_list.clear()
        try:
            entries = VFS.ls(".", self._current_path)
            for entry in entries:
                item = QListWidgetItem()
                name = entry["name"]
                if entry["is_dir"]:
                    item.setText(f"📁 {name}/")
                    item.setForeground(QColor(THEME["primary_glow"]))
                else:
                    size = format_size(entry["size"])
                    item.setText(f"📄 {name} ({size})")
                    item.setForeground(QColor(THEME["text_dim"]))
                
                item.setData(Qt.UserRole, name)
                self._file_list.addItem(item)
            self._status_label.setText(f"{len(entries)} items (Virtual)")
        except Exception as e:
            self._status_label.setText(f"VFS Error: {e}")

    def _update_buttons(self):
        self._btn_back.setEnabled(self._nav_idx > 0)
        self._btn_forward.setEnabled(self._nav_idx < len(self._nav_history) - 1)
        self._btn_up.setEnabled(self._current_path != "/")

    def _go_back(self):
        if self._nav_idx > 0:
            self._nav_idx -= 1
            self._navigate_to(self._nav_history[self._nav_idx], add_history=False)

    def _go_forward(self):
        if self._nav_idx < len(self._nav_history) - 1:
            self._nav_idx += 1
            self._navigate_to(self._nav_history[self._nav_idx], add_history=False)

    def _go_up(self):
        if self._current_path != "/":
            self._navigate_to("..")

    def _go_home(self):
        self._navigate_to("/home/user")

    def _on_address_enter(self):
        self._navigate_to(self._addr_bar.text())

    def _on_item_double_click(self, item):
        name = item.data(Qt.UserRole)
        try:
            # Check if it's a directory
            VFS.cd(name, self._current_path)
            self._navigate_to(name)
        except NotADirectoryError:
            self._open_file(name)
        except Exception as e:
            self._status_label.setText(f"Error: {e}")

    def _open_file(self, name: str):
        try:
            content = VFS.cat(name, self._current_path)
            EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
                "title": "Secure Access",
                "message": f"Decrypted: {name}",
                "type": "info"
            }, source="file_explorer")
            QMessageBox.information(self, "Sovereign Viewer", f"Content of {name}:\n\n{content[:1000]}")
        except Exception as e:
            self._status_label.setText(f"Open Error: {e}")

    def _show_context_menu(self, pos):
        item = self._file_list.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.addAction("Open").triggered.connect(lambda: self._on_item_double_click(item))
        menu.addAction("Secure Erase").triggered.connect(lambda: self._delete_item(item.data(Qt.UserRole)))
        menu.exec_(self._file_list.mapToGlobal(pos))

    def _delete_item(self, name: str):
        try:
            VFS.rm(name, self._current_path, recursive=True)
            EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
                "title": "VFS Clean",
                "message": f"Erased {name}",
                "type": "warning"
            }, source="file_explorer")
            self._refresh()
        except Exception as e:
            self._status_label.setText(f"Delete Error: {e}")
