import logging
import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from assets import theme

logger = logging.getLogger(__name__)

# Maximum audit log lines to display
_MAX_AUDIT_LINES = 50


class SecurityDashboard(QWidget):
    """
    Security dashboard showing live data from the Rust SecurityEngine.
    All panels are driven by system.security_api and the audit log file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecurityDashboard")
        self.setStyleSheet(theme.FILE_EXPLORER_STYLE)

        self._setup_ui()
        self._refresh_data()

        # Auto-refresh every 10 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_data)
        self._timer.start(10_000)

    # ── UI Construction ──────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QLabel("🛡️  SECURITY DASHBOARD")
        header.setStyleSheet(
            f"color: {theme.ACCENT_CYAN}; font-size: 17px; font-weight: bold;"
            f"font-family: 'Consolas', monospace;"
        )
        root.addWidget(header)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(10)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        self._core_panel = self._build_core_panel()
        self._session_panel = self._build_session_panel()
        self._vault_panel = self._build_vault_panel()
        self._audit_panel = self._build_audit_panel()

        self._content_layout.addWidget(self._core_panel)
        self._content_layout.addWidget(self._session_panel)
        self._content_layout.addWidget(self._vault_panel)
        self._content_layout.addWidget(self._audit_panel)
        self._content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # Action bar
        bar = QHBoxLayout()
        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setObjectName("FEBtn")
        btn_refresh.clicked.connect(self._refresh_data)
        bar.addWidget(btn_refresh)
        bar.addStretch()
        root.addLayout(bar)

    def _make_panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        """Return a styled panel frame and its inner layout."""
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL};"
            f"border: 1px solid {theme.BORDER_DIM};"
            f"border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 10px;"
            f"font-family: 'Consolas', monospace; letter-spacing: 1px;"
        )
        layout.addWidget(lbl)
        return panel, layout

    def _row_label(self, layout: QVBoxLayout, key: str) -> QLabel:
        """Add a key-value row; returns the value label for later update."""
        row = QHBoxLayout()
        k = QLabel(key)
        k.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 12px;"
            f"font-family: 'Consolas', monospace;"
        )
        v = QLabel("—")
        v.setStyleSheet(
            f"color: {theme.ACCENT_CYAN}; font-size: 12px;"
            f"font-family: 'Consolas', monospace; font-weight: bold;"
        )
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        layout.addLayout(row)
        return v

    # ── Panel builders ───────────────────────────────────────

    def _build_core_panel(self) -> QFrame:
        panel, layout = self._make_panel("RUST SECURITY CORE")
        self._lbl_core_status = self._row_label(layout, "Engine")
        self._lbl_core_mode = self._row_label(layout, "Mode")
        self._lbl_core_enforce = self._row_label(layout, "Enforcement")
        self._lbl_core_root = self._row_label(layout, "Data Root")
        return panel

    def _build_session_panel(self) -> QFrame:
        panel, layout = self._make_panel("ACTIVE SESSION")
        self._lbl_sess_user = self._row_label(layout, "User")
        self._lbl_sess_type = self._row_label(layout, "Session Type")
        self._lbl_sess_token = self._row_label(layout, "Token")
        return panel

    def _build_vault_panel(self) -> QFrame:
        panel, layout = self._make_panel("VAULT STATUS")
        self._lbl_vault_secrets = self._row_label(layout, "Stored Secrets")
        self._lbl_vault_enc = self._row_label(layout, "Encryption")
        return panel

    def _build_audit_panel(self) -> QFrame:
        panel, layout = self._make_panel("AUDIT LOG  (last 50 events)")

        self._audit_table = QTableWidget(0, 3)
        self._audit_table.setHorizontalHeaderLabels(["Timestamp", "Event", "Detail"])
        self._audit_table.setShowGrid(False)
        self._audit_table.setAlternatingRowColors(False)
        self._audit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._audit_table.setStyleSheet(
            f"QTableWidget {{ background: transparent; color: {theme.TEXT_PRIMARY};"
            f"font-size: 11px; font-family: 'Consolas', monospace; border: none; }}"
            f"QHeaderView::section {{ background: {theme.BG_PANEL};"
            f"color: {theme.TEXT_DIM}; border: none; font-size: 10px; "
            f"font-family: 'Consolas', monospace; padding: 4px; }}"
            f"QTableWidget::item {{ padding: 2px 6px; }}"
        )
        self._audit_table.horizontalHeader().setStretchLastSection(True)
        self._audit_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self._audit_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._audit_table.setMinimumHeight(200)
        self._audit_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self._audit_table)
        return panel

    # ── Data refresh ─────────────────────────────────────────

    def _refresh_data(self):
        self._update_core_panel()
        self._update_session_panel()
        self._update_vault_panel()
        self._update_audit_panel()

    def _update_core_panel(self):
        try:
            from system.security_api import get_security_api

            api = get_security_api()
            status = api.get_status()

            engine_ok = status.get("rust_available", False)
            self._lbl_core_status.setText("ONLINE" if engine_ok else "OFFLINE")
            self._lbl_core_status.setStyleSheet(
                f"color: {theme.ACCENT_GREEN if engine_ok else theme.ACCENT_RED};"
                f"font-size: 12px; font-family: 'Consolas', monospace; font-weight: bold;"
            )

            self._lbl_core_mode.setText(status.get("mode", "N/A"))
            self._lbl_core_enforce.setText(
                "ACTIVE" if status.get("enforcement") else "DISABLED"
            )

            # Show root dir (where Rust stores audit log + vault data)
            root = str(Path.home() / ".qvault")
            self._lbl_core_root.setText(root)

        except Exception as exc:
            logger.debug("security_dashboard core panel: %s", exc)
            self._lbl_core_status.setText("UNAVAILABLE")
            self._lbl_core_status.setStyleSheet(
                f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
            )

    def _update_session_panel(self):
        try:
            from core.system_state import STATE

            user = STATE.current_user
            stype = getattr(STATE, "session_type", None)

            self._lbl_sess_user.setText(user if user else "No active session")
            self._lbl_sess_user.setStyleSheet(
                f"color: {theme.ACCENT_GREEN if user else theme.TEXT_DIM};"
                f"font-size: 12px; font-family: 'Consolas', monospace; font-weight: bold;"
            )

            self._lbl_sess_type.setText(stype if stype else "N/A")

            # Show truncated token hint (first 8 chars only)
            from system.security_api import get_security_api

            token = get_security_api()._token
            if token:
                self._lbl_sess_token.setText(f"{token[:8]}…  (opaque UUID)")
            else:
                self._lbl_sess_token.setText("None")

        except Exception as exc:
            logger.debug("security_dashboard session panel: %s", exc)

    def _update_vault_panel(self):
        try:
            from system.security_api import get_security_api

            secrets = get_security_api().list_secrets()
            count = len(secrets) if secrets else 0
            self._lbl_vault_secrets.setText(str(count))
            self._lbl_vault_enc.setText("AES-256-GCM  (Argon2 key derivation)")

        except Exception as exc:
            logger.debug("security_dashboard vault panel: %s", exc)
            self._lbl_vault_secrets.setText("N/A")

    def _update_audit_panel(self):
        """
        Read the HMAC-signed audit.log written by the Rust core.
        Format per line: [iso8601] [EVENT_TYPE] USER:name - detail | HMAC:b64
        """
        log_path = Path.home() / ".qvault" / "audit.log"
        self._audit_table.setRowCount(0)

        if not log_path.exists():
            # No events yet — show a single informational row
            self._audit_table.insertRow(0)
            self._audit_table.setItem(0, 0, QTableWidgetItem("—"))
            self._audit_table.setItem(0, 1, QTableWidgetItem("NO LOG"))
            self._audit_table.setItem(
                0, 2, QTableWidgetItem("Audit log not yet created")
            )
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Show most recent lines first
            lines = [l.strip() for l in lines if l.strip()][-_MAX_AUDIT_LINES:]
            lines.reverse()

            for line in lines:
                # Strip HMAC portion for display (security boundary — not shown in UI)
                display = line.split(" | HMAC:")[0] if " | HMAC:" in line else line

                # Parse: [timestamp] [EVENT] USER:user - detail
                ts, event, detail = "—", "—", display
                try:
                    if display.startswith("["):
                        ts_end = display.index("]") + 1
                        ts_raw = display[1 : ts_end - 1]
                        # Shorten ISO timestamp for display
                        ts = ts_raw[:19].replace("T", " ")
                        rest = display[ts_end:].strip()

                        if rest.startswith("["):
                            ev_end = rest.index("]") + 1
                            event = rest[1 : ev_end - 1]
                            detail = rest[ev_end:].strip()
                except (ValueError, IndexError):
                    pass

                row = self._audit_table.rowCount()
                self._audit_table.insertRow(row)
                self._audit_table.setItem(row, 0, QTableWidgetItem(ts))
                self._audit_table.setItem(row, 1, QTableWidgetItem(event))
                self._audit_table.setItem(row, 2, QTableWidgetItem(detail))

                # Color-code by event severity
                color = theme.TEXT_PRIMARY
                if any(x in event for x in ("FAIL", "ERROR", "DENIED", "TAMPER")):
                    color = theme.ACCENT_RED
                elif any(x in event for x in ("WARN", "BLOCK", "SWEEP")):
                    color = theme.ACCENT_AMBER
                elif any(x in event for x in ("BOOT", "SUCCESS", "STORED", "CREATED")):
                    color = theme.ACCENT_GREEN

                for col in range(3):
                    item = self._audit_table.item(row, col)
                    if item:
                        item.setForeground(
                            __import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(color)
                        )

        except Exception as exc:
            logger.warning("security_dashboard audit panel read error: %s", exc)
            self._audit_table.insertRow(0)
            self._audit_table.setItem(0, 0, QTableWidgetItem("—"))
            self._audit_table.setItem(0, 1, QTableWidgetItem("READ ERROR"))
            self._audit_table.setItem(0, 2, QTableWidgetItem(str(exc)[:80]))
