import logging
import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTextEdit,
    QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

# ── Theme constants (matching Q-Vault OS design tokens) ───────

_BG_PANEL    = "rgba(11, 22, 45, 0.95)"
_BG_CARD     = "rgba(15, 31, 56, 0.9)"
_BORDER      = "rgba(84, 177, 198, 0.2)"
_TEXT_PRI     = "#d4e8f0"
_TEXT_DIM     = "#4a6880"
_ACCENT_CYAN  = "#54b1c6"
_ACCENT_GREEN = "#2dd4a8"
_ACCENT_RED   = "#ef4444"
_ACCENT_AMBER = "#f59e0b"


def _status_dot(color: str) -> str:
    return (
        f"color: {color}; font-size: 16px; "
        f"font-family: 'Segoe UI'; font-weight: bold;"
    )


class QVaultSecurityApp(QWidget):
    """
    Q-Vault Security monitoring dashboard.

    Displays real-time status of the qvault-pc-mediator subsystem
    and provides launch/stop controls.
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setObjectName("QVaultSecurityApp")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._adapter = None

        self._setup_ui()
        self._connect_adapter()
        self._subscribe_events()

        # Auto-refresh every 2 seconds
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(2000)

        # Initial refresh and auto-launch
        QTimer.singleShot(200, self._refresh_status)
        QTimer.singleShot(400, self._auto_launch)

    def _auto_launch(self):
        """Automatically start the mediator when the dashboard opens."""
        if self._adapter and not self._adapter.is_running():
            self._on_launch()

    # ── UI Construction ──────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(
            f"QWidget#QVaultSecurityApp {{ background: {_BG_PANEL}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        hdr = QLabel("🔐  Q-VAULT SECURITY MEDIATOR")
        hdr.setStyleSheet(
            f"color: {_ACCENT_CYAN}; font-size: 16px; font-weight: bold; "
            f"font-family: 'Consolas', monospace; letter-spacing: 1px; "
            f"background: transparent;"
        )
        root.addWidget(hdr)

        # Subtitle
        sub = QLabel("Hardware-backed PQC security subsystem monitor")
        sub.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 10px; "
            f"font-family: 'Consolas', monospace; background: transparent;"
        )
        root.addWidget(sub)

        # Scroll area for panels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(10)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        # Build panels
        self._build_mediator_panel()
        self._build_token_panel()
        self._build_vault_panel()
        self._build_event_log_panel()

        self._content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # Action bar
        self._build_action_bar(root)

    def _make_card(self, title: str) -> tuple:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_BG_CARD}; "
            f"border: 1px solid {_BORDER}; border-radius: 8px; }}"
        )
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 9px; "
            f"font-family: 'Consolas', monospace; letter-spacing: 2px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(lbl)
        return card, layout

    def _make_row(self, layout, key: str) -> QLabel:
        row = QHBoxLayout()
        k = QLabel(key)
        k.setStyleSheet(
            f"color: {_TEXT_PRI}; font-size: 12px; "
            f"font-family: 'Consolas', monospace; "
            f"background: transparent; border: none;"
        )
        v = QLabel("—")
        v.setStyleSheet(
            f"color: {_ACCENT_CYAN}; font-size: 12px; "
            f"font-family: 'Consolas', monospace; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        layout.addLayout(row)
        return v

    # ── Panel Builders ────────────────────────────────────────

    def _build_mediator_panel(self):
        card, layout = self._make_card("MEDIATOR STATUS")
        self._lbl_process = self._make_row(layout, "Process")
        self._lbl_pid = self._make_row(layout, "PID")
        self._lbl_uptime = self._make_row(layout, "Uptime")
        self._lbl_exe = self._make_row(layout, "Executable")
        self._content_layout.addWidget(card)

    def _build_token_panel(self):
        card, layout = self._make_card("TOKEN STATUS")
        self._lbl_token = self._make_row(layout, "Connection")
        self._content_layout.addWidget(card)

    def _build_vault_panel(self):
        card, layout = self._make_card("VAULT STATUS")
        self._lbl_vault = self._make_row(layout, "Lock State")
        self._lbl_session = self._make_row(layout, "Session")
        self._content_layout.addWidget(card)

    def _build_event_log_panel(self):
        card, layout = self._make_card("INTEGRATION LOG")
        self._event_log = QTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.setMinimumHeight(120)
        self._event_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._event_log.setStyleSheet(
            f"QTextEdit {{ background: rgba(1, 2, 14, 0.85); "
            f"color: {_TEXT_PRI}; border: 1px solid {_BORDER}; "
            f"border-radius: 6px; font-size: 10px; padding: 6px; "
            f"font-family: 'Consolas', monospace; }}"
        )
        layout.addWidget(self._event_log)
        self._content_layout.addWidget(card)

    def _build_action_bar(self, root):
        bar = QHBoxLayout()

        self._btn_launch = QPushButton("▶  Launch Mediator")
        self._btn_launch.setStyleSheet(
            f"QPushButton {{ background: rgba(45, 212, 168, 0.15); "
            f"color: {_ACCENT_GREEN}; border: 1px solid rgba(45, 212, 168, 0.3); "
            f"border-radius: 6px; padding: 8px 18px; font-size: 11px; "
            f"font-family: 'Segoe UI', sans-serif; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(45, 212, 168, 0.25); }}"
        )
        self._btn_launch.clicked.connect(self._on_launch)
        bar.addWidget(self._btn_launch)

        self._btn_stop = QPushButton("⏹  Stop")
        self._btn_stop.setStyleSheet(
            f"QPushButton {{ background: rgba(239, 68, 68, 0.12); "
            f"color: {_ACCENT_RED}; border: 1px solid rgba(239, 68, 68, 0.3); "
            f"border-radius: 6px; padding: 8px 18px; font-size: 11px; "
            f"font-family: 'Segoe UI', sans-serif; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(239, 68, 68, 0.22); }}"
        )
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setEnabled(False)
        bar.addWidget(self._btn_stop)

        bar.addStretch()

        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background: rgba(84, 177, 198, 0.12); "
            f"color: {_ACCENT_CYAN}; border: 1px solid {_BORDER}; "
            f"border-radius: 6px; padding: 8px 14px; font-size: 11px; "
            f"font-family: 'Segoe UI', sans-serif; }}"
            f"QPushButton:hover {{ background: rgba(84, 177, 198, 0.22); }}"
        )
        btn_refresh.clicked.connect(self._refresh_status)
        bar.addWidget(btn_refresh)

        root.addLayout(bar)

    # ── Adapter Connection ────────────────────────────────────

    def _connect_adapter(self):
        try:
            from kernel.security.qvault_runtime_bridge import QVAULT_BRIDGE
            QVAULT_BRIDGE.start()
            self._adapter = QVAULT_BRIDGE.adapter
            if self._adapter:
                self._adapter.state_changed.connect(self._on_state_changed)
        except Exception as exc:
            logger.warning("[QVaultApp] Adapter connection failed: %s", exc)

    def _subscribe_events(self):
        for ev in (
            SystemEvent.EVENT_QVAULT_STARTED,
            SystemEvent.EVENT_QVAULT_STOPPED,
            SystemEvent.EVENT_QVAULT_CONNECTED,
            SystemEvent.EVENT_QVAULT_DISCONNECTED,
            SystemEvent.EVENT_QVAULT_LOCKED,
            SystemEvent.EVENT_QVAULT_UNLOCKED,
            SystemEvent.EVENT_QVAULT_ERROR,
        ):
            EVENT_BUS.subscribe(ev, self._on_qvault_event)

    # ── Actions ───────────────────────────────────────────────

    def _on_launch(self):
        if self._adapter:
            ok = self._adapter.launch()
            if not ok:
                self._append_log("⚠ Launch failed — check executable path")
        else:
            self._append_log("⚠ Adapter not available")

    def _on_stop(self):
        if self._adapter:
            self._adapter.shutdown()

    # ── Event Handlers ────────────────────────────────────────

    def _on_state_changed(self, state: dict):
        self._update_ui(state)

    def _on_qvault_event(self, payload):
        ev_name = payload.type.value if hasattr(payload.type, "value") else str(payload.type)
        self._append_log(f"[{ev_name}] {payload.data}")
        self._refresh_status()

    # ── Status Refresh ────────────────────────────────────────

    def _refresh_status(self):
        if not self._adapter:
            self._set_offline_state()
            return

        state = self._adapter.get_full_state()
        self._update_ui(state)

        # Update event log from adapter
        logs = self._adapter.get_event_log(limit=30)
        if logs and not self._event_log.toPlainText():
            for entry in logs[-10:]:
                self._event_log.append(entry)

    def _update_ui(self, state: dict):
        running = state.get("mediator_running", False)

        # Process status
        if running:
            self._lbl_process.setText("● RUNNING")
            self._lbl_process.setStyleSheet(
                _status_dot(_ACCENT_GREEN) + " background: transparent; border: none;"
            )
        else:
            self._lbl_process.setText("○ STOPPED")
            self._lbl_process.setStyleSheet(
                _status_dot(_ACCENT_RED) + " background: transparent; border: none;"
            )

        # PID
        pid = state.get("pid")
        self._lbl_pid.setText(str(pid) if pid else "—")

        # Uptime
        uptime = state.get("uptime")
        if uptime and running:
            m, s = divmod(int(uptime), 60)
            h, m = divmod(m, 60)
            self._lbl_uptime.setText(f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._lbl_uptime.setText("—")

        # Executable
        try:
            from integrations.qvault import find_mediator_exe
            exe = find_mediator_exe()
            self._lbl_exe.setText(exe.name if exe else "Not found")
        except Exception:
            self._lbl_exe.setText("—")

        # Token
        token = state.get("token_connected", False)
        if token:
            self._lbl_token.setText("● CONNECTED")
            self._lbl_token.setStyleSheet(
                _status_dot(_ACCENT_GREEN) + " background: transparent; border: none;"
            )
        else:
            self._lbl_token.setText("○ DISCONNECTED")
            self._lbl_token.setStyleSheet(
                _status_dot(_TEXT_DIM) + " background: transparent; border: none;"
            )

        # Vault
        locked = state.get("vault_locked", True)
        if locked:
            self._lbl_vault.setText("🔒 LOCKED")
            self._lbl_vault.setStyleSheet(
                _status_dot(_ACCENT_AMBER) + " background: transparent; border: none;"
            )
        else:
            self._lbl_vault.setText("🔓 UNLOCKED")
            self._lbl_vault.setStyleSheet(
                _status_dot(_ACCENT_GREEN) + " background: transparent; border: none;"
            )

        # Session
        session = state.get("session_active", False)
        self._lbl_session.setText("Active" if session else "Inactive")

        # Error
        err = state.get("last_error")
        if err:
            self._append_log(f"⚠ {err}")

        # Button states
        self._btn_launch.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    def _set_offline_state(self):
        self._lbl_process.setText("○ OFFLINE")
        self._lbl_process.setStyleSheet(
            _status_dot(_TEXT_DIM) + " background: transparent; border: none;"
        )
        self._lbl_pid.setText("—")
        self._lbl_uptime.setText("—")
        self._lbl_token.setText("—")
        self._lbl_vault.setText("—")
        self._lbl_session.setText("—")
        self._lbl_exe.setText("—")

    def _append_log(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._event_log.append(f"[{ts}] {msg}")
