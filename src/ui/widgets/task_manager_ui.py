import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor

from core.event_bus import EVENT_BUS, SystemEvent
from core.process_manager import PM
from resources import theme

logger = logging.getLogger(__name__)

class TaskManagerUI(QWidget):
    """Modern Task Manager UI component."""

    COLS = ["PID", "Name", "Status", "Owner", "Age", "Command"]

    _refresh_signal = pyqtSignal()

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
        
        self._refresh_signal.connect(self._refresh, Qt.QueuedConnection)
        
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
        
        # Premium Styling
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setFrameShape(QTableWidget.NoFrame)
        t.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.THEME['bg_dark']};
                alternate-background-color: {theme.THEME['surface_dark']};
                color: {theme.THEME['text_main']};
                gridline-color: transparent;
                selection-background-color: {theme.THEME['hover_glow']};
                selection-color: {theme.THEME['primary_glow']};
                font-family: {theme.FONT['mono']};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {theme.THEME['bg_black']};
                color: {theme.THEME['text_muted']};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {theme.THEME['border_subtle']};
                font-family: {theme.FONT['family']};
                font-weight: bold;
                text-transform: uppercase;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
        """)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return t

    def _make_statusbar(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("AppStatusbar"); bar.setFixedHeight(22)
        row = QHBoxLayout(bar); row.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel("Ready"); self._status_lbl.setObjectName("StatusLabel")
        row.addWidget(self._status_lbl)
        return bar

    def _on_pm_event(self, _):
        self._refresh_signal.emit()

    def _refresh(self):
        procs = PM.all_procs()
        self._table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            self._table.setItem(row, 0, QTableWidgetItem(str(p["pid"])))
            self._table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self._table.setItem(row, 2, QTableWidgetItem(p["status"]))
            self._table.setItem(row, 3, QTableWidgetItem(p["owner"]))
            self._table.setItem(row, 4, QTableWidgetItem(str(p.get("age", "—"))))
            self._table.setItem(row, 5, QTableWidgetItem(str(p.get("argv", ""))))
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
