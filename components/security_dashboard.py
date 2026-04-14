# =============================================================
#  security_dashboard.py — Q-VAULT OS  |  Security Dashboard
#
#  Real-time security monitoring UI
# =============================================================

import os
import pathlib
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from assets import theme


class SecurityDashboard(QWidget):
    """Security dashboard showing real-time security status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecurityDashboard")
        self.setStyleSheet(theme.FILE_EXPLORER_STYLE)

        self._setup_ui()
        self._start_monitoring()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel("🛡️ SECURITY DASHBOARD")
        header.setStyleSheet(
            f"color: {theme.ACCENT_CYAN}; font-size: 18px; font-weight: bold; font-family: 'Consolas', monospace;"
        )
        root.addWidget(header)

        root.addWidget(self._make_status_panel())
        root.addWidget(self._make_behavior_panel())
        root.addWidget(self._make_defense_panel())
        root.addWidget(self._make_threats_panel())
        root.addWidget(self._make_sync_panel())
        root.addWidget(self._make_actions_panel())

    def _make_status_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER_DIM}; border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)

        title = QLabel("SYSTEM STATUS")
        title.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        layout.addWidget(title)

        self._status_labels = {}

        status_items = [
            ("Command Injection", "SECURE"),
            ("Path Traversal", "SECURE"),
            ("Privilege Escalation", "SECURE"),
            ("Audit Logs", "INTEGRITY OK"),
            ("File Integrity", "MONITORING"),
            ("Encryption", "ACTIVE"),
        ]

        for label_text, status in status_items:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 12px; font-family: 'Consolas', monospace;"
            )
            row.addWidget(lbl)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(
                f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-family: 'Consolas', monospace; font-weight: bold;"
            )
            row.addWidget(status_lbl, 1, Qt.AlignRight)

            self._status_labels[label_text] = status_lbl
            layout.addLayout(row)

        return panel

    def _make_behavior_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER_DIM}; border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)

        title = QLabel("BEHAVIOR ANALYSIS")
        title.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        layout.addWidget(title)

        self._behavior_labels = {}

        behavior_items = [
            ("Threat Level", "NORMAL"),
            ("Risk Score", "0"),
            ("Blocked Commands", "0"),
            ("Suspicious Events", "0"),
        ]

        for label_text, status in behavior_items:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 12px; font-family: 'Consolas', monospace;"
            )
            row.addWidget(lbl)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(
                f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-family: 'Consolas', monospace; font-weight: bold;"
            )
            row.addWidget(status_lbl, 1, Qt.AlignRight)

            self._behavior_labels[label_text] = status_lbl
            layout.addLayout(row)

        return panel

    def _make_defense_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER_DIM}; border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)

        title = QLabel("DEFENSE SYSTEMS")
        title.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        layout.addWidget(title)

        self._defense_labels = {}

        defense_items = [
            ("Anti-Debugger", "PASSIVE"),
            ("Anti-Memory Dump", "ACTIVE"),
            ("Deception Layer", "INACTIVE"),
            ("Security Response", "READY"),
        ]

        for label_text, status in defense_items:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 12px; font-family: 'Consolas', monospace;"
            )
            row.addWidget(lbl)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(
                f"color: {theme.ACCENT_CYAN}; font-size: 12px; font-family: 'Consolas', monospace; font-weight: bold;"
            )
            row.addWidget(status_lbl, 1, Qt.AlignRight)

            self._defense_labels[label_text] = status_lbl
            layout.addLayout(row)

        return panel

    def _make_threats_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER_DIM}; border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)

        title = QLabel("RECENT SECURITY EVENTS")
        title.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        layout.addWidget(title)

        self._events_table = QTableWidget(0, 4)
        self._events_table.setHorizontalHeaderLabels(
            ["Time", "Type", "Source", "Detail"]
        )
        self._events_table.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-family: 'Consolas', monospace;"
        )
        self._events_table.horizontalHeader().setStretchLastSection(True)
        self._events_table.setMaximumHeight(150)
        layout.addWidget(self._events_table)

        return panel

    def _make_sync_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {theme.BG_PANEL}; border: 1px solid {theme.BORDER_DIM}; border-radius: 8px;"
        )
        layout = QVBoxLayout(panel)

        title = QLabel("SYNC STATUS")
        title.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 11px; font-family: Consolas, monospace;"
        )
        layout.addWidget(title)

        self._sync_labels = {}

        sync_items = [
            ("Connection", "OFFLINE"),
            ("Pending Sync", "0"),
            ("Last Sync", "NEVER"),
            ("Telemetry", "DISABLED"),
        ]

        for label_text, status in sync_items:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 12px; font-family: Consolas, monospace;"
            )
            row.addWidget(lbl)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet(
                f"color: {theme.ACCENT_CYAN}; font-size: 12px; font-family: Consolas, monospace; font-weight: bold;"
            )
            row.addWidget(status_lbl, 1, Qt.AlignRight)

            self._sync_labels[label_text] = status_lbl
            layout.addLayout(row)

        return panel

    def _make_actions_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn_refresh = QPushButton("🔄 Refresh")
        self._btn_refresh.setObjectName("FEBtn")
        self._btn_refresh.clicked.connect(self._refresh_data)
        layout.addWidget(self._btn_refresh)

        self._btn_clear = QPushButton("🗑️ Clear Alerts")
        self._btn_clear.setObjectName("FEBtn")
        self._btn_clear.clicked.connect(self._clear_alerts)
        layout.addWidget(self._btn_clear)

        layout.addStretch()

        return panel

    def _start_monitoring(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_data)
        self._refresh_timer.start(5000)

    def _refresh_data(self):
        try:
            self._update_security_monitor()
            self._update_behavior_monitor()
            self._update_defense_systems()
            self._update_events_table()
            self._update_sync_status()

        except Exception as e:
            pass

    def _update_security_monitor(self):
        try:
            from system.security_monitor import SEC_MONITOR

            alerts = SEC_MONITOR.get_alerts(10)
            blocked = len(alerts)
            if blocked > 0:
                self._status_labels["Command Injection"].setText(f"{blocked} ATTEMPTS")
                self._status_labels["Command Injection"].setStyleSheet(
                    f"color: {theme.ACCENT_AMBER}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._status_labels["Command Injection"].setText("SECURE")
                self._status_labels["Command Injection"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )

            from system.audit_logger_hardened import AUDIT_LOGGER

            integrity = AUDIT_LOGGER.get_stats()
            if integrity.get("integrity", False):
                self._status_labels["Audit Logs"].setText("INTEGRITY OK")
                self._status_labels["Audit Logs"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._status_labels["Audit Logs"].setText("TAMPERED!")
                self._status_labels["Audit Logs"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )

        except Exception as e:
            pass

    def _update_behavior_monitor(self):
        try:
            from system.behavior_monitor import BEHAVIOR_MONITOR

            threat_level = BEHAVIOR_MONITOR.get_threat_level()
            risk_score = BEHAVIOR_MONITOR.get_global_risk_score()

            self._behavior_labels["Threat Level"].setText(threat_level)
            if threat_level == "CRITICAL":
                self._behavior_labels["Threat Level"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )
            elif threat_level == "HIGH":
                self._behavior_labels["Threat Level"].setStyleSheet(
                    f"color: {theme.ACCENT_AMBER}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._behavior_labels["Threat Level"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )

            self._behavior_labels["Risk Score"].setText(str(risk_score))
            if risk_score >= 50:
                self._behavior_labels["Risk Score"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )
            elif risk_score >= 30:
                self._behavior_labels["Risk Score"].setStyleSheet(
                    f"color: {theme.ACCENT_AMBER}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._behavior_labels["Risk Score"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )

            from system.security_monitor import SEC_MONITOR

            stats = SEC_MONITOR.get_stats()
            self._behavior_labels["Blocked Commands"].setText(
                str(stats.get("total_alerts", 0))
            )
            self._behavior_labels["Suspicious Events"].setText(str(risk_score))

        except Exception as e:
            pass

    def _update_defense_systems(self):
        try:
            from system.anti_debug import ANTI_DEBUGGER

            debug_stats = ANTI_DEBUGGER.get_stats()
            detection_level = debug_stats.get("detection_level", "none")
            self._defense_labels["Anti-Debugger"].setText(
                detection_level.upper() if detection_level != "none" else "PASSIVE"
            )
            if detection_level != "none":
                self._defense_labels["Anti-Debugger"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )

            from system.anti_memory_dump import ANTI_MEMORY_DUMP

            memory_stats = ANTI_MEMORY_DUMP.get_stats()
            active_buffers = memory_stats.get("active_buffers", 0)
            suspicious_reads = memory_stats.get("suspicious_reads", 0)

            if suspicious_reads > 0:
                self._defense_labels["Anti-Memory Dump"].setText("ALERT!")
                self._defense_labels["Anti-Memory Dump"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._defense_labels["Anti-Memory Dump"].setText("ACTIVE")
                self._defense_labels["Anti-Memory Dump"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )

            from system.deception_layer import DECEPTION_LAYER

            deception_stats = DECEPTION_LAYER.get_stats()
            active = deception_stats.get("active", False)

            if active:
                self._defense_labels["Deception Layer"].setText("ACTIVE")
                self._defense_labels["Deception Layer"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._defense_labels["Deception Layer"].setText("INACTIVE")
                self._defense_labels["Deception Layer"].setStyleSheet(
                    f"color: {theme.TEXT_DIM}; font-size: 12px; font-weight: bold;"
                )

            from system.security_response import SECURITY_RESPONSE

            response_stats = SECURITY_RESPONSE.get_stats()
            threat_level = response_stats.get("threat_level", "LOW")

            self._defense_labels["Security Response"].setText(threat_level)
            if threat_level in ["HIGH", "CRITICAL"]:
                self._defense_labels["Security Response"].setStyleSheet(
                    f"color: {theme.ACCENT_RED}; font-size: 12px; font-weight: bold;"
                )
            else:
                self._defense_labels["Security Response"].setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; font-size: 12px; font-weight: bold;"
                )

        except Exception as e:
            pass

    def _update_events_table(self):
        events = []

        try:
            from system.security_monitor import SEC_MONITOR

            events = SEC_MONITOR.get_alerts(5)
        except Exception:
            pass

        self._events_table.setRowCount(0)

        for event in events:
            row = self._events_table.rowCount()
            self._events_table.insertRow(row)

            self._events_table.setItem(
                row, 0, QTableWidgetItem(event.get("type", "UNKNOWN"))
            )
            self._events_table.setItem(
                row, 1, QTableWidgetItem(event.get("detail", "")[:25])
            )
            self._events_table.setItem(row, 2, QTableWidgetItem("security"))
            self._events_table.setItem(
                row,
                3,
                QTableWidgetItem(
                    str(int(event.get("timestamp", 0)))
                    if isinstance(event.get("timestamp"), (int, float))
                    else event.get("timestamp", "")[:19]
                ),
            )

    def _clear_alerts(self):
        from system.security_monitor import SEC_MONITOR

        SEC_MONITOR.reset()
        self._refresh_data()

        from system.notification_system import NOTIFY

        NOTIFY.send("Alerts Cleared", "Security alerts have been cleared", level="info")


def create_security_dashboard(parent=None) -> QWidget:
    """Create and return security dashboard widget."""
    return SecurityDashboard(parent)

    def _update_sync_status(self):
        try:
            from system.sync_manager import SYNC_MANAGER
            status = SYNC_MANAGER.get_status()
            self._sync_labels['Connection'].setText('ONLINE' if status.is_online else 'OFFLINE')
            self._sync_labels['Pending Sync'].setText(str(status.pending_count))
            last_sync = status.last_sync if status.last_sync else 'NEVER'
            self._sync_labels['Last Sync'].setText(last_sync[:19] if len(last_sync) > 19 else last_sync)
            from system.telemetry import TELEMETRY
            telemetry_enabled = TELEMETRY.is_enabled()
            self._sync_labels['Telemetry'].setText('ENABLED' if telemetry_enabled else 'DISABLED')
        except Exception:
            self._sync_labels['Connection'].setText('N/A')
