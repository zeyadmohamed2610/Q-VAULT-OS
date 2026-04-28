# =============================================================
#  components/security_ui.py — Q-Vault OS  |  Security UI
#
#  Pure View component. No direct system calls.
#  Communicates via EventBus.
# =============================================================

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

from core.event_bus import EVENT_BUS, SystemEvent
from assets import theme

logger = logging.getLogger(__name__)

class SecurityPanel(QWidget):
    """Modern Security Monitor UI component."""

    intrusion_detected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")
        self._displayed_risk = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_risk_gauge())
        
        self._log = QTextEdit()
        self._log.setObjectName("SecLog")
        self._log.setReadOnly(True)
        root.addWidget(self._log, stretch=1)
        
        root.addWidget(self._make_controls())

        # Subscribe to security events
        EVENT_BUS.subscribe(SystemEvent.SECURITY_ALERT, self._on_sec_event)

    def _make_header(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("AppToolbar")
        row = QHBoxLayout(bar); row.setContentsMargins(8, 6, 8, 6)
        row.addWidget(QLabel("🔐  Security Monitor"))
        row.addStretch()
        return bar

    def _make_risk_gauge(self) -> QWidget:
        frame = QFrame(); frame.setObjectName("AppToolbar")
        col = QVBoxLayout(frame); col.setContentsMargins(12, 10, 12, 10)
        
        row = QHBoxLayout(); row.setSpacing(16)
        self._level_widgets = {}
        for level in ("LOW", "MEDIUM", "HIGH"):
            lbl = QLabel(level); lbl.setObjectName("RiskLabel"); lbl.setAlignment(Qt.AlignCenter)
            self._level_widgets[level] = lbl
            row.addWidget(lbl)
        col.addLayout(row)
        
        self._risk_text = QLabel("Current Risk: LOW")
        self._risk_text.setObjectName("StatusLabel"); self._risk_text.setAlignment(Qt.AlignCenter)
        col.addWidget(self._risk_text)
        return frame

    def _make_controls(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("AppStatusbar")
        row = QHBoxLayout(bar); row.setContentsMargins(8, 6, 8, 6)
        
        btn_clear = QPushButton("✓  Clear Risk")
        btn_clear.setObjectName("ClearBtn")
        btn_clear.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "clear_risk"}, source="security_ui"))
        row.addWidget(btn_clear)
        
        row.addStretch()
        
        btn_test = QPushButton("🧪 Test Intrusion")
        btn_test.setObjectName("SecBtn")
        btn_test.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.SECURITY_ALERT, {"type": "INTRUSION", "source": "test", "detail": "Test intrusion"}, source="security_ui"))
        row.addWidget(btn_test)
        return bar

    def _on_sec_event(self, payload):
        self._log.append(f"<b>{payload.type.name}</b>: {payload.data.get('detail', '')}")
        if "risk" in payload.data:
            self._update_risk(payload.data["risk"])

    def _update_risk(self, level: str):
        if level == self._displayed_risk: return
        self._displayed_risk = level
        for lvl, widget in self._level_widgets.items():
            state = "active" if lvl == level else "inactive"
            widget.setProperty("risk_state", state)
            widget.style().unpolish(widget); widget.style().polish(widget); widget.update()
        self._risk_text.setText(f"Current Risk: {level}")
