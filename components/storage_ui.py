import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QTreeWidget, QTreeWidgetItem, 
    QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.event_bus import EVENT_BUS, SystemEvent
from core.filesystem import FS
from core.system_state import STATE
from assets import theme

logger = logging.getLogger(__name__)

class StorageUI(QWidget):
    """Modern Storage View UI component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StorageView")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._make_left_panel())
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([380, 260])
        root.addWidget(splitter, stretch=1)

        # Refresh FS tree periodically
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_fs_tree)
        self._refresh_timer.start(5000)

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background:{theme.BG_PANEL};border-bottom:1px solid {theme.BORDER_DIM};")
        row = QHBoxLayout(bar); row.setContentsMargins(12, 0, 12, 0)
        row.addWidget(QLabel("💾  Storage Monitor"))
        row.addStretch()
        btn_ref = QPushButton("⟳ Refresh")
        btn_ref.clicked.connect(self._refresh_fs_tree)
        row.addWidget(btn_ref)
        return bar

    def _make_left_panel(self) -> QWidget:
        w = QWidget(); col = QVBoxLayout(w)
        col.addWidget(QLabel("DRIVES"))
        # Simplified drive list for UI
        col.addStretch()
        return w

    def _make_right_panel(self) -> QWidget:
        w = QWidget(); col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        
        self._fs_tree = QTreeWidget()
        self._fs_tree.setHeaderLabels(["Name", "Perms", "Owner", "Size"])
        col.addWidget(self._fs_tree, stretch=1)
        
        self._refresh_fs_tree()
        return w

    def _refresh_fs_tree(self):
        if not self.isVisible(): return
        self._fs_tree.clear()
        # In a real Event-Driven app, this would request data from the FS Engine
        root_item = QTreeWidgetItem(["/", "drwxr-xr-x", "root", "—"])
        self._fs_tree.addTopLevelItem(root_item)
        self._fs_tree.expandAll()

class StorageWidget(QWidget):
    """Compact disk usage display for small panels."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._lbl = QLabel("STORAGE: Loading...")
        self._lbl.setStyleSheet("color:#4a6880; font-size:9pt;")
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet("""
            QProgressBar { background: rgba(84,177,198,0.1); border-radius: 3px; border: none; }
            QProgressBar::chunk { background: #54b1c6; border-radius: 3px; }
        """)
        layout.addWidget(self._bar)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(10000)
        self._refresh()

    def _refresh(self):
        import shutil
        from system.config import get_qvault_home
        try:
            total, used, free = shutil.disk_usage(get_qvault_home())
            pct = int((used / total) * 100)
            used_gb = used / (1024**3)
            total_gb = total / (1024**3)
            self._lbl.setText(f"STORAGE: {used_gb:.1f}GB / {total_gb:.1f}GB ({pct}%)")
            self._bar.setValue(pct)
        except Exception:
            self._lbl.setText("STORAGE: Unavailable")
