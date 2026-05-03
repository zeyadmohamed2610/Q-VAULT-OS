import time
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer

from core.event_bus import EVENT_BUS, SystemEvent
from assets import theme
from assets.theme import THEME

logger = logging.getLogger(__name__)

class AutomationBrainUI(QWidget):
    """Modern Automation Brain UI component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")
        self.setStyleSheet(f"background: {THEME['bg_black']};")

        self._setup_ui()
        
        # Subscribe to relevant events
        EVENT_BUS.subscribe(SystemEvent.PLAN_STARTED, self._on_event)
        EVENT_BUS.subscribe(SystemEvent.PLAN_COMPLETED, self._on_event)
        EVENT_BUS.subscribe(SystemEvent.DECISION_MADE, self._on_event)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # HUD
        self.hud = QFrame()
        self.hud.setFixedHeight(60)
        self.hud.setStyleSheet("background: rgba(30, 41, 59, 0.4); border-radius: 12px;")
        hl = QHBoxLayout(self.hud)
        hl.addWidget(QLabel("BRAIN STATUS: ACTIVE"))
        hl.addStretch()
        self.layout.addWidget(self.hud)

        # Proactive area
        self.layout.addWidget(QLabel("PROACTIVE ACTIONS", objectName="SectionHeader"))
        self.proactive_area = QWidget()
        self.proactive_layout = QHBoxLayout(self.proactive_area)
        self.layout.addWidget(self.proactive_area)

        # Logs
        log_layout = QHBoxLayout()
        self.reasoning_scroll = QScrollArea()
        self.reasoning_container = QWidget()
        self.reasoning_layout = QVBoxLayout(self.reasoning_container)
        self.reasoning_scroll.setWidget(self.reasoning_container)
        log_layout.addWidget(self.reasoning_scroll)
        self.layout.addLayout(log_layout)

    def _on_event(self, payload):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] {payload.type.name}: {payload.data}"
        
        entry = QLabel(msg)
        entry.setWordWrap(True)
        entry.setStyleSheet(f"color: {THEME['text_dim']}; font-family: Consolas; font-size: 11px;")
        self.reasoning_layout.insertWidget(0, entry)
        
        if self.reasoning_layout.count() > 20:
            self.reasoning_layout.itemAt(self.reasoning_layout.count()-1).widget().deleteLater()
