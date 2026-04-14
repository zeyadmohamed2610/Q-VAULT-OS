# =============================================================
#  task_manager.py — Q-Vault OS  |  Task Manager
#
#  Reads exclusively from PM (ProcessManager singleton).
#  Refreshes automatically via PM.subscribe() — zero polling.
#
#  Columns:  PID | Name | Status | Owner | Age | Command
#  Actions:  Select row → Kill Process button becomes active
# =============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui  import QColor

from core.process_manager import PM, STATUS_RUNNING, STATUS_SLEEPING, STATUS_STOPPED, STATUS_COMPLETED
from system.security_system import SEC, EVT_PROCESS
from assets import theme


# Colour per status
STATUS_COLORS = {
    STATUS_RUNNING:   theme.ACCENT_GREEN,
    STATUS_SLEEPING:  theme.TEXT_DIM,
    STATUS_STOPPED:   theme.ACCENT_RED,
    STATUS_COMPLETED: theme.TEXT_DIM,
}

STYLE = f"""
    QWidget#TaskManager {{
        background: {theme.BG_WINDOW};
    }}
    QTableWidget {{
        background: {theme.BG_DARK};
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 12px;
        gridline-color: {theme.BORDER_DIM};
        border: none;
        selection-background-color: {theme.BG_SELECTED};
    }}
    QHeaderView::section {{
        background: {theme.BG_PANEL};
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        font-weight: bold;
        border: none;
        border-bottom: 1px solid {theme.BORDER_DIM};
        padding: 4px 8px;
    }}
    QTableWidget::item {{ padding: 3px 8px; border: none; }}
    QPushButton#KillBtn {{
        background: {theme.ACCENT_RED};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 18px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#KillBtn:hover  {{ background: #ff6666; }}
    QPushButton#KillBtn:disabled {{
        background: {theme.BORDER_DIM};
        color: {theme.TEXT_DIM};
    }}
    QPushButton#TmBtn {{
        background: transparent;
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 4px;
        padding: 5px 12px;
        font-family: 'Consolas', monospace;
        font-size: 11px;
    }}
    QPushButton#TmBtn:hover {{
        background: {theme.BG_HOVER};
        color: {theme.TEXT_PRIMARY};
    }}
    QLabel#TmHeader {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        padding: 4px 8px;
    }}
    QLabel#TmCount {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 10px;
        padding: 4px 8px;
    }}
"""


class TaskManager(QWidget):

    COLS = ["PID", "Name", "Status", "Owner", "Age", "Command"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskManager")
        self.setStyleSheet(STYLE)

        # ── Layout ────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_toolbar())

        self._table = self._make_table()
        root.addWidget(self._table, stretch=1)

        root.addWidget(self._make_statusbar())

        # ── Initial population ────────────────────────────────
        self._refresh()

        # ── Subscribe to PM — refresh on every process event ─
        PM.subscribe(self._on_pm_event)

        # ── Age column needs a periodic tick (every 2 s) ──────
        self._age_timer = QTimer(self)
        self._age_timer.timeout.connect(self._refresh_ages)
        self._age_timer.start(2000)

    def closeEvent(self, event):
        PM.unsubscribe(self._on_pm_event)
        self._age_timer.stop()
        super().closeEvent(event)

    # ── PM observer ───────────────────────────────────────────

    def _on_pm_event(self, event: str, proc):
        """Refresh the entire table on any process state change."""
        self._refresh()

    # ── Toolbar ───────────────────────────────────────────────

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL};"
            f"border-bottom:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)

        title = QLabel("⚙  Process List")
        title.setObjectName("TmHeader")
        row.addWidget(title)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("TmCount")
        row.addWidget(self._count_lbl)

        row.addStretch()

        self._kill_btn = QPushButton("⛔  Kill Process")
        self._kill_btn.setObjectName("KillBtn")
        self._kill_btn.setEnabled(False)
        self._kill_btn.clicked.connect(self._kill_selected)
        row.addWidget(self._kill_btn)

        flag_btn = QPushButton("🚩  Flag Suspicious")
        flag_btn.setObjectName("TmBtn")
        flag_btn.clicked.connect(self._flag_selected)
        row.addWidget(flag_btn)

        return bar

    # ── Table ─────────────────────────────────────────────────

    def _make_table(self) -> QTableWidget:
        t = QTableWidget(0, len(self.COLS))
        t.setHorizontalHeaderLabels(self.COLS)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setSelectionMode(QTableWidget.SingleSelection)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setShowGrid(True)
        t.verticalHeader().setVisible(False)

        hdr = t.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # PID
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Name
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Owner
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Age
        hdr.setSectionResizeMode(5, QHeaderView.Stretch)           # Command

        t.itemSelectionChanged.connect(self._on_selection_changed)
        return t

    # ── Status bar ────────────────────────────────────────────

    def _make_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(22)
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL};"
            f"border-top:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel("Select a process to interact with it.")
        self._status_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px;"
            f"font-family:'Consolas',monospace;"
        )
        row.addWidget(self._status_lbl)
        return bar

    # ── Populate table from PM ────────────────────────────────

    def _refresh(self):
        procs = PM.all_procs()
        self._table.setRowCount(len(procs))

        for row, p in enumerate(procs):
            status_color = QColor(STATUS_COLORS.get(p["status"], theme.TEXT_DIM))

            def cell(text: str, color: str = theme.TEXT_PRIMARY) -> QTableWidgetItem:
                item = QTableWidgetItem(str(text))
                item.setForeground(QColor(color))
                return item

            self._table.setItem(row, 0, cell(str(p["pid"]),   theme.TEXT_DIM))
            self._table.setItem(row, 1, cell(p["name"],       theme.ACCENT_CYAN))
            self._table.setItem(row, 2, cell(p["status"],     STATUS_COLORS.get(p["status"], theme.TEXT_DIM)))
            self._table.setItem(row, 3, cell(p["owner"],      theme.TEXT_PRIMARY))
            self._table.setItem(row, 4, cell(p.get("age","—"), theme.TEXT_DIM))
            self._table.setItem(row, 5, cell(p["argv"],       theme.TEXT_DIM))

            # Store PID in the row for kill/flag actions
            self._table.item(row, 0).setData(Qt.UserRole, p["pid"])

        running = sum(1 for p in procs if p["status"] == STATUS_RUNNING)
        self._count_lbl.setText(
            f"{len(procs)} processes  |  {running} running"
        )

    def _refresh_ages(self):
        """Update only the Age column without rebuilding the whole table."""
        procs = PM.all_procs()
        if len(procs) != self._table.rowCount():
            self._refresh()
            return
        for row, p in enumerate(procs):
            item = self._table.item(row, 4)
            if item:
                item.setText(p.get("age", "—"))

    # ── Selection ─────────────────────────────────────────────

    def _on_selection_changed(self):
        selected = bool(self._table.selectedItems())
        self._kill_btn.setEnabled(selected)
        if selected:
            row = self._table.currentRow()
            pid  = self._table.item(row, 0).data(Qt.UserRole)
            name = self._table.item(row, 1).text()
            self._status_lbl.setText(
                f"Selected: [{pid}] {name}  —  "
                "press Kill to terminate or Flag to report"
            )

    def _selected_pid_name(self) -> tuple[int, str] | tuple[None, None]:
        row = self._table.currentRow()
        if row < 0:
            return None, None
        pid_item = self._table.item(row, 0)
        if not pid_item:
            return None, None
        return pid_item.data(Qt.UserRole), self._table.item(row, 1).text()

    # ── Actions ───────────────────────────────────────────────

    def _kill_selected(self):
        pid, name = self._selected_pid_name()
        if pid is None:
            return
        proc = PM.get(pid)
        # Don't allow killing boot/system processes
        if proc and proc.owner == "root" and proc.name in {
            "systemd", "kthreadd", "sshd", "dbus"
        }:
            self._status_lbl.setText(
                f"⚠  Cannot kill system process [{pid}] {name}."
            )
            return
        ok = PM.kill(pid)
        if ok:
            self._status_lbl.setText(f"✓  Sent SIGTERM to [{pid}] {name}.")
        else:
            self._status_lbl.setText(f"⚠  Process [{pid}] not found.")

    def _flag_selected(self):
        pid, name = self._selected_pid_name()
        if pid is None:
            return
        SEC.report(
            EVT_PROCESS,
            source="task_manager",
            detail=f"Operator flagged process [{pid}] '{name}' as suspicious.",
            escalate=True,
        )
        self._status_lbl.setText(
            f"🚩  [{pid}] {name} reported to Security System."
        )
