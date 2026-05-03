import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt, QTimer

from core.event_bus import EVENT_BUS, SystemEvent
from core.system_state import STATE
from assets import theme
from assets.theme import THEME

# ── Theme alias shim: map legacy attribute names to real tokens ──
theme.ACCENT_CYAN  = THEME["primary_glow"]   # #00e6ff
theme.BG_PANEL     = THEME["surface_dark"]   # #0a0f19
theme.BORDER_DIM   = THEME["border_subtle"]  # rgba(0,230,255,0.08)
theme.ACCENT_GREEN = THEME["success"]        # #00ff88

logger = logging.getLogger(__name__)

class CoreMonitorUI(QWidget):
    """System diagnostic dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")
        self.setMinimumSize(400, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("SYSTEM CORE MONITOR")
        header.setStyleSheet(f"color:{theme.ACCENT_CYAN}; font-weight:bold; font-size:14px;")
        layout.addWidget(header)

        self.panel = QFrame()
        self.panel.setStyleSheet(f"background:{theme.BG_PANEL}; border-radius:8px; border:1px solid {theme.BORDER_DIM};")
        p_layout = QVBoxLayout(self.panel)

        self.user_status = self._create_row(p_layout, "Current User")
        self.session_status = self._create_row(p_layout, "Session Type")
        self.risk_status = self._create_row(p_layout, "Security Risk")
        self.theme_status = self._create_row(p_layout, "Theme")
        layout.addWidget(self.panel)

        self.event_box = QLabel("Ready")
        self.event_box.setStyleSheet(f"background:{THEME['bg_black']}; border:1px solid {THEME['surface_raised']}; color:{theme.ACCENT_GREEN}; font-family:Consolas; padding:8px; border-radius:4px; font-size:11px;")
        layout.addWidget(self.event_box)

        # Refresh timer for live stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(1000)
        
        self._refresh()

    def _create_row(self, layout, label):
        row = QHBoxLayout()
        lbl = QLabel(label); lbl.setStyleSheet(f"color:{theme.TEXT_DIM};")
        val = QLabel("---"); val.setAlignment(Qt.AlignRight)
        row.addWidget(lbl); row.addWidget(val); layout.addLayout(row)
        return val

    def _refresh(self):
        self.user_status.setText(STATE.username() or "Guest")
        self.session_status.setText(STATE.session_type)
        self.theme_status.setText(STATE.theme)
        # Risk level should be requested or read from a state
        self.risk_status.setText("LOW")
        self.risk_status.setStyleSheet(f"color:{theme.ACCENT_GREEN}; font-weight:bold;")
