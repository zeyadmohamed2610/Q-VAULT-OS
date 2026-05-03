import logging
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QStackedWidget, QCheckBox, QComboBox, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer

from core.event_bus import EVENT_BUS, SystemEvent
from core.system_state import STATE
from assets import theme

logger = logging.getLogger(__name__)

def _divider() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setObjectName("Divider"); f.setFixedHeight(1)
    return f

def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper()); lbl.setObjectName("SectionLabel")
    return lbl

class SettingsUI(QWidget):
    """Modern Settings UI component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContainer")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(180)
        sb_col = QVBoxLayout(sidebar)
        
        title = QLabel("SETTINGS")
        title.setObjectName("SideTitle")
        sb_col.addWidget(title)
        sb_col.addWidget(_divider())

        self._side_btns = []
        self._stack = QStackedWidget()
        
        sections = [
            ("Appearance", self._make_appearance),
            ("Security", self._make_security),
            ("System", self._make_system),
        ]

        for i, (label, factory) in enumerate(sections):
            btn = QPushButton(label)
            btn.setObjectName("SidebarBtn")
            btn.clicked.connect(lambda _, idx=i: self._show_page(idx))
            self._side_btns.append(btn)
            sb_col.addWidget(btn)
            self._stack.addWidget(factory())

        sb_col.addStretch()
        root.addWidget(sidebar)
        root.addWidget(self._stack, stretch=1)
        self._show_page(0)

    def _show_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._side_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn); btn.style().polish(btn); btn.update()

    def _make_appearance(self) -> QWidget:
        page = QWidget(); col = QVBoxLayout(page)
        col.addWidget(_section("Appearance"))
        col.addWidget(QLabel("Theme: Dark Mode (Active)"))
        
        anim_chk = QCheckBox("Enable Animations")
        anim_chk.setChecked(STATE.animations_enabled)
        anim_chk.stateChanged.connect(lambda v: EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"key": "animations", "value": bool(v)}, source="settings_ui"))
        col.addWidget(anim_chk)
        
        col.addStretch()
        return page

    def _make_security(self) -> QWidget:
        page = QWidget(); col = QVBoxLayout(page)
        col.addWidget(_section("Security"))
        
        btn_clear = QPushButton("Clear Risk Level")
        btn_clear.setObjectName("ActionBtn")
        btn_clear.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "clear_risk"}, source="settings_ui"))
        col.addWidget(btn_clear)
        
        col.addStretch()
        return page

    def _make_system(self) -> QWidget:
        page = QWidget(); col = QVBoxLayout(page)
        col.addWidget(_section("System Actions"))
        
        for action in ["Logout", "Restart", "Shutdown"]:
            btn = QPushButton(action)
            btn.setObjectName("DangerBtn")
            btn.clicked.connect(lambda _, a=action: self._request_action(a))
            col.addWidget(btn)
            
        col.addStretch()
        return page

    def _request_action(self, action: str):
        # Notify system of the request
        EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
            "title": "System",
            "message": f"Requesting {action}...",
            "type": "warning"
        }, source="settings_ui")
        
        # Real action requested via EventBus
        if action == "Logout":
            EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "logout"}, source="settings_ui")
        elif action == "Restart":
            EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "restart"}, source="settings_ui")
        elif action == "Shutdown":
            EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"action": "shutdown"}, source="settings_ui")
