from assets.theme import *
# =============================================================
#  components/command_palette.py — Q-Vault OS
#
#  Intelligent Command Interface.
#  The primary bridge between the user and the AI layer.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QFrame, QGraphicsDropShadowEffect, QPushButton, QLabel
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor
from core.event_bus import EVENT_BUS, SystemEvent

class CommandPalette(QFrame):
    """
    Intelligent Floating Command Palette.
    - Ctrl+Space to activate.
    - Fuzzy search for apps and commands.
    - Direct AI intent submission.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()
        return
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("Palette")
        self._drag_pos = None

        # ───── Close Button ─────
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.move(465, 10)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text_disabled']};
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ color: {THEME['accent_error']}; }}
        """)
        self.btn_close.clicked.connect(self._close_palette)
        
        EVENT_BUS.subscribe(SystemEvent.EVT_AI_UNKNOWN_INTENT, self._handle_unknown_intent)
        EVENT_BUS.subscribe(SystemEvent.EVT_WORKFLOW_LIST, self._show_workflow_list)
        
        self.setStyleSheet(f"""
            QFrame#Palette {{
                background: rgba(20, 20, 35, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }}
            QLineEdit {{
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                color: white;
                font-size: 16px;
                font-family: 'Segoe UI';
                padding: 10px;
                selection-background-color: {THEME['primary_glow']};
            }}
            QListWidget {{
                background: transparent;
                border: none;
                color: {THEME['text_muted']};
                font-family: 'Segoe UI';
                font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background: rgba(255, 255, 255, 0.05);
                color: {THEME['primary_glow']};
                border-left: 3px solid {THEME['primary_glow']};
            }}
        """)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ── Input Area ──
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search apps or ask AI (e.g. 'Open Files', 'Prepare workspace')...")
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.input)
        
        # ── Suggestions List ──
        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list)
        
        # Initial suggestions
        self._update_suggestions("")
        
    def _update_suggestions(self, text):
        import difflib
        self.list.clear()
        text = text.lower()
        
        # 1. App Suggestions
        apps = ["Files", "Terminal", "Browser", "Settings", "Monitor"]
        # Use fuzzy match for apps
        matches = difflib.get_close_matches(text, [a.lower() for a in apps], n=3, cutoff=0.3)
        for match in matches:
            real_name = next(a for a in apps if a.lower() == match)
            self._add_item(f"Launch {real_name}", "launch")
                
        # 2. Command Suggestions
        commands = {
            "prepare workspace": "intent",
            "system status": "intent",
            "restart shell": "sys",
            "toggle debug": "sys"
        }
        cmd_matches = difflib.get_close_matches(text, list(commands.keys()), n=3, cutoff=0.4)
        for cmd in cmd_matches:
            self._add_item(cmd.title(), commands[cmd])
                
        # Default: Ask AI
        if text:
            self._add_item(f"Ask AI: '{text}'", "ai")
            
        self.list.setCurrentRow(0)

    def _handle_unknown_intent(self, payload):
        self.input.setPlaceholderText("I didn't quite catch that. Try another command?")
        self.input.setEnabled(True)
        self.list.setEnabled(True)

    def _show_workflow_list(self, payload):
        """Switches UI to Workflow Discovery mode."""
        from components.desktop import Desktop
        # Ensure palette is visible
        EVENT_BUS.emit(SystemEvent.REQ_COMMAND_PALETTE_TOGGLE, {"force": "open"}, source="WorkflowPanel")
        
        self.list.clear()
        self.input.setPlaceholderText("Browse Automation Workflows...")
        workflows = payload.data.get("workflows", [])
        for wf in workflows:
            self._add_item(f"Run: {wf.replace('_', ' ').title()}", "workflow", data=wf)
        self.list.setCurrentRow(0)

    def _add_item(self, text, itype, data=None):
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, itype)
        if data: item.setData(Qt.UserRole + 1, data)
        self.list.addItem(item)

    def _on_text_changed(self, text):
        self._update_suggestions(text)

    def _on_submit(self):
        item = self.list.currentItem()
        if not item: return
        
        text = item.text()
        itype = item.data(Qt.UserRole)
        
        raw_input = self.input.text()
        
        if itype == "launch":
            app = text.replace("Launch ", "")
            EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"text": f"open {app}"}, source="CommandPalette")
            self._close_palette()
        elif itype == "intent":
            EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"text": text}, source="CommandPalette")
            self._set_thinking(True)
        elif itype == "sys":
             if "Restart" in text: EVENT_BUS.emit(SystemEvent.REQ_SYSTEM_RESTART)
             if "Debug" in text: EVENT_BUS.emit(SystemEvent.REQ_DEBUG_TOGGLE)
             self._close_palette()
        elif itype == "ai":
             EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"text": raw_input}, source="CommandPalette")
             self._set_thinking(True)
        elif itype == "workflow":
             wf_name = item.data(Qt.UserRole + 1)
             EVENT_BUS.emit(SystemEvent.REQ_WORKFLOW_EXECUTE, {"name": wf_name}, source="CommandPalette")
             self._close_palette()

    def _set_thinking(self, thinking: bool):
        self.input.setEnabled(not thinking)
        self.list.setEnabled(not thinking)
        if thinking:
            self.input.setPlaceholderText("AI is reasoning...")
            # Listen for completion to close
            EVENT_BUS.subscribe(SystemEvent.EVT_AI_THINKING_STOP, lambda _: self._close_palette())
        else:
            self.input.setPlaceholderText("Search apps or ask AI...")

    def _on_item_clicked(self, item):
        self._on_submit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._close_palette()
        elif event.key() == Qt.Key_Down:
            self.list.setCurrentRow((self.list.currentRow() + 1) % self.list.count())
        elif event.key() == Qt.Key_Up:
            self.list.setCurrentRow((self.list.currentRow() - 1) % self.list.count())
        else:
            super().keyPressEvent(event)

    # ───── DRAGGING LOGIC ─────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.pos() - self._drag_pos
            self.move(self.pos() + delta)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _close_palette(self):
        self.hide()
        EVENT_BUS.emit(SystemEvent.REQ_COMMAND_PALETTE_TOGGLE)

    def show_and_focus(self):
        if self.parent() and hasattr(self.parent(), 'rect'):
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() // 4
            self.move(x, y)
        self.show()
        self.raise_()
        self.input.setFocus()
        self.input.clear()

    def show_centered(self, parent_rect: QRect):
        self.show_and_focus()
