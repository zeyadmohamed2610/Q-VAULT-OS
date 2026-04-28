# =============================================================
#  components/task_manager_ui.py — Q-Vault OS  |  Task Manager UI
#
#  Pure View component. No direct system calls.
#  Communicates via EventBus.
# =============================================================

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.event_bus import EVENT_BUS, SystemEvent
from core.process_manager import PM
from assets import theme

logger = logging.getLogger(__name__)

class TaskManagerUI(QWidget):
    """Modern Task Manager UI component."""

    COLS = ["PID", "Name", "Status", "Owner", "Age", "Command"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_toolbar())
        self._table = self._make_table()
        root.addWidget(self._table, stretch=1)
        root.addWidget(self._make_statusbar())

        self._refresh()
        
        # Subscribe to process events
        EVENT_BUS.subscribe(SystemEvent.PROC_SPAWNED, self._on_pm_event)
        EVENT_BUS.subscribe(SystemEvent.PROC_COMPLETED, self._on_pm_event)
        EVENT_BUS.subscribe(SystemEvent.PROC_STOPPED, self._on_pm_event)
        EVENT_BUS.subscribe(SystemEvent.PROC_GC, self._on_pm_event)

    def _make_toolbar(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("AppToolbar")
        row = QHBoxLayout(bar); row.setContentsMargins(8, 6, 8, 6)
        row.addWidget(QLabel("⚙  Process List"))
        row.addStretch()
        
        self._kill_btn = QPushButton("⛔  Kill Process")
        self._kill_btn.setObjectName("KillBtn"); self._kill_btn.setEnabled(False)
        self._kill_btn.clicked.connect(self._kill_selected)
        row.addWidget(self._kill_btn)
        return bar

    def _make_table(self) -> QTableWidget:
        t = QTableWidget(0, len(self.COLS))
        t.setHorizontalHeaderLabels(self.COLS)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setSelectionMode(QTableWidget.SingleSelection)
        t.verticalHeader().setVisible(False)
        t.itemSelectionChanged.connect(self._on_selection_changed)
        return t

    def _make_statusbar(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("AppStatusbar"); bar.setFixedHeight(22)
        row = QHBoxLayout(bar); row.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel("Ready"); self._status_lbl.setObjectName("StatusLabel")
        row.addWidget(self._status_lbl)
        return bar

    def _on_pm_event(self, _):
        self._refresh()

    def _refresh(self):
        procs = PM.all_procs()
        self._table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            self._table.setItem(row, 0, QTableWidgetItem(str(p["pid"])))
            self._table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self._table.setItem(row, 2, QTableWidgetItem(p["status"]))
            self._table.setItem(row, 3, QTableWidgetItem(p["owner"]))
            self._table.setItem(row, 4, QTableWidgetItem(str(p.get("age", "—"))))
            self._table.setItem(row, 5, QTableWidgetItem(p["argv"]))
            self._table.item(row, 0).setData(Qt.UserRole, p["pid"])

    def _on_selection_changed(self):
        selected = bool(self._table.selectedItems())
        self._kill_btn.setEnabled(selected)

    def _kill_selected(self):
        row = self._table.currentRow()
        if row < 0: return
        pid = self._table.item(row, 0).data(Qt.UserRole)
        # Request kill via EventBus
        EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "kill_proc", "pid": pid}, source="task_manager_ui")
