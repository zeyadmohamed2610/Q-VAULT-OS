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

from resources.theme import THEME, FONT

# ── Theme constants (Centralized Sovereign Theme) ───────
_BG_PANEL    = THEME["bg_dark"]
_BG_CARD     = THEME["surface_dark"]
_BORDER      = THEME["border_subtle"]
_TEXT_PRI     = THEME["text_main"]
_TEXT_DIM     = THEME["text_dim"]
_ACCENT_CYAN  = THEME["primary_glow"]
_ACCENT_GREEN = THEME["success"]
_ACCENT_RED   = THEME["accent_error"]
_ACCENT_AMBER = THEME["warning"]


def _status_dot(color: str) -> str:
    return (
        f"color: {color}; font-size: 16px; "
        f"font-family: {FONT['mono']}; font-weight: bold;"
    )


class QVaultSecurityApp(QWidget):
    """
    Q-Vault Security monitoring dashboard.
    Upgraded for Sovereign Identity & Quantum Telemetry.
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
        hdr = QLabel("🛡️  Q-VAULT SOVEREIGN IDENTITY")
        hdr.setStyleSheet(
            f"color: {_ACCENT_CYAN}; font-size: 18px; font-weight: bold; "
            f"font-family: {FONT['mono']}; letter-spacing: 1px; "
            f"background: transparent;"
        )
        root.addWidget(hdr)

        # Subtitle
        sub = QLabel("Hardware-Anchored PQC Hybrid Runtime Monitor")
        sub.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 10px; text-transform: uppercase;"
            f"font-family: {FONT['mono']}; background: transparent;"
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
        self._build_quantum_panel()
        self._build_vault_panel()
        self._build_identity_panel()
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
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        lbl = QLabel(title)
        from resources.theme import FONT
        lbl.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 9px; font-weight: bold; "
            f"font-family: {FONT['mono']}; letter-spacing: 2px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(lbl)
        return card, layout

    def _make_row(self, layout, key: str) -> QLabel:
        from resources.theme import FONT
        row = QHBoxLayout()
        k = QLabel(key)
        k.setStyleSheet(
            f"color: {_TEXT_PRI}; font-size: 12px; "
            f"font-family: {FONT['mono']}; "
            f"background: transparent; border: none;"
        )
        v = QLabel("—")
        v.setStyleSheet(
            f"color: {_ACCENT_CYAN}; font-size: 12px; "
            f"font-family: {FONT['mono']}; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        layout.addLayout(row)
        return v

    # ── Panel Builders ────────────────────────────────────────

    def _build_mediator_panel(self):
        card, layout = self._make_card("KERNEL BRIDGE STATUS")
        self._lbl_process = self._make_row(layout, "Bridge Daemon")
        self._lbl_pid = self._make_row(layout, "System PID")
        self._lbl_uptime = self._make_row(layout, "Uptime")
        self._content_layout.addWidget(card)

    def _build_token_panel(self):
        card, layout = self._make_card("HARDWARE TOKEN (ESP32-S3)")
        self._lbl_token = self._make_row(layout, "Connection Status")
        self._lbl_hwid = self._make_row(layout, "Hardware ID")
        self._lbl_fw_ver = self._make_row(layout, "Firmware Rev")
        self._content_layout.addWidget(card)

    def _build_quantum_panel(self):
        card, layout = self._make_card("QUANTUM CORE METRICS")
        self._lbl_pqc_alg = self._make_row(layout, "Algorithm")
        self._lbl_handshake = self._make_row(layout, "Active Handshake")
        self._content_layout.addWidget(card)

    def _build_vault_panel(self):
        card, layout = self._make_card("DATA VAULT GOVERNANCE")
        self._lbl_vault = self._make_row(layout, "Encryption State")
        self._lbl_session = self._make_row(layout, "Sovereign Session")
        self._content_layout.addWidget(card)

    def _build_identity_panel(self):
        card, layout = self._make_card("SOVEREIGN IDENTITY MANAGEMENT")
        
        desc = QLabel("Provision new administrative identities to replace default credentials.")
        desc.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px; background: transparent; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        from resources.theme import FONT
        self._btn_provision = QPushButton("⊕  Provision New Identity")
        self._btn_provision.setStyleSheet(
            f"QPushButton {{ background: rgba(0, 230, 255, 0.1); "
            f"color: {_ACCENT_CYAN}; border: 1px solid rgba(0, 230, 255, 0.25); "
            f"border-radius: 6px; padding: 6px 12px; font-size: 11px; "
            f"font-family: {FONT['family']}; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(0, 230, 255, 0.2); }}"
        )
        self._btn_provision.clicked.connect(self._on_provision_identity)
        btn_layout.addWidget(self._btn_provision)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
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
            f"font-family: {FONT['mono']}; }}"
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
            f"font-family: {FONT['family']}; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(45, 212, 168, 0.25); }}"
        )
        self._btn_launch.clicked.connect(self._on_launch)
        bar.addWidget(self._btn_launch)

        self._btn_stop = QPushButton("⏹  Stop")
        self._btn_stop.setStyleSheet(
            f"QPushButton {{ background: rgba(239, 68, 68, 0.12); "
            f"color: {_ACCENT_RED}; border: 1px solid rgba(239, 68, 68, 0.3); "
            f"border-radius: 6px; padding: 8px 18px; font-size: 11px; "
            f"font-family: {FONT['family']}; font-weight: bold; }}"
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
            f"font-family: {FONT['family']}; }}"
            f"QPushButton:hover {{ background: rgba(84, 177, 198, 0.22); }}"
        )
        btn_refresh.clicked.connect(self._refresh_status)
        bar.addWidget(btn_refresh)

        root.addLayout(bar)

    # ── Adapter Connection ────────────────────────────────────

    def _connect_adapter(self):
        try:
            from system.kernel.security.qvault_runtime_bridge import QVAULT_BRIDGE
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

    def _on_provision_identity(self):
        from ui.widgets.provision_identity_dialog import ProvisionIdentityDialog
        dlg = ProvisionIdentityDialog(self)
        dlg.exec_()

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
            self._lbl_process.setText("● ACTIVE BRIDGE")
            self._lbl_process.setStyleSheet(
                _status_dot(_ACCENT_GREEN) + " background: transparent; border: none;"
            )
        else:
            self._lbl_process.setText("○ STANDBY")
            self._lbl_process.setStyleSheet(
                _status_dot(_ACCENT_RED) + " background: transparent; border: none;"
            )

        # PID & Uptime
        pid = state.get("pid")
        self._lbl_pid.setText(str(pid) if pid else "—")
        uptime = state.get("uptime")
        if uptime and running:
            m, s = divmod(int(uptime), 60)
            h, m = divmod(m, 60)
            self._lbl_uptime.setText(f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._lbl_uptime.setText("—")

        # Hardware Token (ESP32-S3)
        token = state.get("token_connected", False)
        if token:
            self._lbl_token.setText("● AUTHENTICATED")
            self._lbl_token.setStyleSheet(_status_dot(_ACCENT_GREEN) + " background: transparent; border: none;")
            self._lbl_hwid.setText(state.get("hwid", "ESP32-S3-Q8F4..."))
            self._lbl_fw_ver.setText(state.get("fw_ver", "v2.4.1-PQ"))
        else:
            self._lbl_token.setText("○ NOT DETECTED")
            self._lbl_token.setStyleSheet(_status_dot(_TEXT_DIM) + " background: transparent; border: none;")
            self._lbl_hwid.setText("—")
            self._lbl_fw_ver.setText("—")

        # Quantum Metrics
        self._lbl_pqc_alg.setText("ML-KEM-768 (Kyber)")
        self._lbl_handshake.setText("ACTIVE" if running and token else "IDLE")

        # Vault
        locked = state.get("vault_locked", True)
        if locked:
            self._lbl_vault.setText("🔒 AES-256-XTS LOCKED")
            self._lbl_vault.setStyleSheet(_status_dot(_ACCENT_AMBER) + " background: transparent; border: none;")
        else:
            self._lbl_vault.setText("🔓 SOVEREIGN DECRYPTED")
            self._lbl_vault.setStyleSheet(_status_dot(_ACCENT_GREEN) + " background: transparent; border: none;")

        self._lbl_session.setText("Active" if state.get("session_active") else "Inactive")

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
