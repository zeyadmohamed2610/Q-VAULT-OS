import logging
import shutil
import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QDialog, QFormLayout, QMessageBox,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QColor, QFont

from system.config import get_qvault_home
from system.trash_manager import list_trash, restore_from_trash
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

STYLE = """
QWidget { background: #0d1117; color: #c9d1d9; }
QPushButton {
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 4px; padding: 4px 12px; font-size: 12px;
}
QPushButton:hover { background: #30363d; }
QPushButton:disabled { color: #484f58; border-color: #21262d; }
QPushButton#btnEmpty {
    background: rgba(248,81,73,0.15); border-color: #f85149; color: #f85149;
}
QPushButton#btnEmpty:hover { background: rgba(248,81,73,0.3); }
QListWidget {
    background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 4px;
}
QListWidget::item { padding: 8px 12px; border-radius: 3px; }
QListWidget::item:selected { background: #1f6feb; color: white; }
QListWidget::item:hover { background: #21262d; }
"""


class TrashApp(QWidget):
    def __init__(self, secure_api=None, parent=None):
        super().__init__(parent)
        self.secure_api = secure_api
        self.setObjectName("TrashApp")
        self.setStyleSheet(STYLE)
        self._trash_dir = Path(get_qvault_home()) / ".trash"
        self._trash_dir.mkdir(parents=True, exist_ok=True)
        self._setup_ui()
        self.refresh()
        self._subscribe()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("🗑️  Trash")
        title.setFont(QFont("", 14, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self._count_badge = QLabel()
        self._count_badge.setStyleSheet(
            "background:#30363d; border-radius:10px; padding:2px 8px; font-size:11px;")
        header.addWidget(self._count_badge)
        layout.addLayout(header)

        # Toolbar
        tb = QHBoxLayout()
        self._btn_restore = QPushButton("⟲ Restore")
        self._btn_restore.setEnabled(False)
        self._btn_restore.clicked.connect(self._restore_selected)
        tb.addWidget(self._btn_restore)
        tb.addStretch()
        self._btn_empty = QPushButton("🗑 Empty Trash")
        self._btn_empty.setObjectName("btnEmpty")
        self._btn_empty.clicked.connect(self._empty_trash)
        tb.addWidget(self._btn_empty)
        layout.addLayout(tb)

        # File list
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._show_properties)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self._list, 1)

        # Empty state label (hidden when there are items)
        self._empty_label = QLabel("🗑️\n\nTrash is Empty")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color:#484f58; font-size:16px;")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        # Status
        self._status = QLabel()
        self._status.setStyleSheet("color:#8b949e; font-size:11px;")
        layout.addWidget(self._status)

    def refresh(self):
        self._list.clear()
        try:
            items = list_trash()
        except Exception as exc:
            logger.error("Trash refresh error: %s", exc)
            items = []

        for name in sorted(items):
            item_path = self._trash_dir / name
            meta_path = self._trash_dir / f"{name}.meta"
            original = ""
            deleted_date = ""
            if meta_path.exists():
                try:
                    import json
                    with open(meta_path) as f:
                        meta = json.load(f)
                    original = meta.get("original_path", "")
                except Exception:
                    pass
            try:
                mtime = item_path.stat().st_mtime
                deleted_date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            icon = "📁 " if item_path.is_dir() else "📄 "
            display = f"{icon}{name}"
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.UserRole, name)
            list_item.setData(Qt.UserRole + 1, original)
            list_item.setData(Qt.UserRole + 2, deleted_date)
            list_item.setToolTip(f"Original: {original}\nDeleted: {deleted_date}")
            self._list.addItem(list_item)

        count = len(items)
        self._count_badge.setText(f"{count} item{'s' if count != 1 else ''}")
        self._btn_empty.setEnabled(count > 0)

        if count == 0:
            self._list.hide()
            self._empty_label.show()
            self._status.setText("Trash is empty")
        else:
            self._empty_label.hide()
            self._list.show()
            self._status.setText(f"{count} item{'s' if count != 1 else ''} in trash")

    def _on_selection_changed(self):
        has_sel = len(self._list.selectedItems()) > 0
        self._btn_restore.setEnabled(has_sel)

    def _selected_names(self) -> list:
        return [item.data(Qt.UserRole) for item in self._list.selectedItems()]

    def _restore_selected(self):
        for name in self._selected_names():
            try:
                ok = restore_from_trash(name)
                if ok:
                    EVENT_BUS.emit(SystemEvent.FS_CHANGED, {"path": name}, source="Trash")
                else:
                    QMessageBox.warning(self, "Restore", f"Could not restore '{name}'")
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))
        self.refresh()
        self._emit_trash_state()

    def _delete_permanently(self, names: list):
        if not names:
            return
        reply = QMessageBox.question(
            self, "Delete Permanently",
            f"Permanently delete {len(names)} item(s)?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        for name in names:
            item_path = self._trash_dir / name
            meta_path = self._trash_dir / f"{name}.meta"
            try:
                if item_path.is_dir():
                    shutil.rmtree(str(item_path))
                elif item_path.exists():
                    item_path.unlink()
                if meta_path.exists():
                    meta_path.unlink(missing_ok=True)
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))
        self.refresh()
        self._emit_trash_state()

    def _empty_trash(self):
        items = list_trash()
        if not items:
            return
        reply = QMessageBox.question(
            self, "Empty Trash",
            f"Permanently delete all {len(items)} item(s) in Trash?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(str(self._trash_dir))
            self._trash_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
        self.refresh()
        self._emit_trash_state()

    def _show_properties(self, item):
        name = item.data(Qt.UserRole)
        original = item.data(Qt.UserRole + 1)
        deleted_date = item.data(Qt.UserRole + 2)
        dlg = QDialog(self)
        dlg.setWindowTitle("Properties")
        dlg.setStyleSheet(STYLE)
        form = QFormLayout(dlg)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(8)
        form.addRow("Name:",          QLabel(name))
        form.addRow("Original Path:", QLabel(original or "(unknown)"))
        form.addRow("Deleted:",       QLabel(deleted_date or "(unknown)"))
        item_path = self._trash_dir / name
        if item_path.exists():
            try:
                size = item_path.stat().st_size if item_path.is_file() else sum(
                    f.stat().st_size for f in item_path.rglob("*") if f.is_file())
                form.addRow("Size:", QLabel(f"{size:,} bytes"))
            except Exception:
                pass
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        form.addRow(btn)
        dlg.exec_()

    def _context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu
        items_sel = self._selected_names()
        if not items_sel:
            return
        menu = QMenu(self)
        menu.setStyleSheet("QMenu{background:#161b22;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;}QMenu::item:selected{background:#1f6feb;}")
        menu.addAction("⟲ Restore", self._restore_selected)
        menu.addAction("❌ Delete Permanently", lambda: self._delete_permanently(items_sel))
        if len(items_sel) == 1:
            item = self._list.selectedItems()[0]
            menu.addSeparator()
            menu.addAction("ℹ️  Properties", lambda: self._show_properties(item))
        menu.exec_(self._list.mapToGlobal(pos))

    def _subscribe(self):
        try:
            EVENT_BUS.subscribe(SystemEvent.FS_CHANGED, self._on_fs_changed)
        except Exception:
            pass

    def _on_fs_changed(self, payload):
        QTimer.singleShot(150, self.refresh)
        QTimer.singleShot(200, self._emit_trash_state)

    def _emit_trash_state(self):
        """Emit trash state change so Desktop can update icon."""
        try:
            trash_dir = Path(get_qvault_home()) / ".trash"
            items = [f for f in trash_dir.iterdir() if not f.name.endswith(".meta")]
            EVENT_BUS.emit(SystemEvent.EVT_TRASH_STATE_CHANGED, {"has_items": len(items) > 0})
        except Exception as exc:
            logger.warning("_emit_trash_state failed: %s", exc)

    def closeEvent(self, event):
        try:
            EVENT_BUS.unsubscribe(SystemEvent.FS_CHANGED, self._on_fs_changed)
        except Exception:
            pass
        super().closeEvent(event)
