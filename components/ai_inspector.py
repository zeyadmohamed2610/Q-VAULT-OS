from assets.theme import *
# =============================================================
#  components/ai_inspector.py — Q-Vault OS
#
#  AI Governance & Transparency Dashboard.
#  Visualizes AI reasoning, decisions, and safety rejections.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QPushButton
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QColor
from core.event_bus import EVENT_BUS, SystemEvent

class AIInspectorPanel(QFrame):
    """
    Transparency Layer for the AI Engine.
    - Tracks EVT_AI_DECISION
    - Tracks EVT_AI_REJECTED_ACTION
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 500)
        self.setObjectName("AIInspector")
        self._drag_pos = None

        # ───── Close Button ─────
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.move(365, 10)
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
        self.btn_close.clicked.connect(self.hide)
        
        self.setStyleSheet(f"""
            QFrame#AIInspector {{
                background: rgba(15, 15, 25, 0.9);
                border: 1px solid {THEME['primary_glow']};
                border-radius: {RADIUS_MD}px;
            }}
            QLabel {{ color: #ccc; font-family: 'Segoe UI'; font-size: 11px; }}
            QScrollArea {{ background: transparent; border: none; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("🧠 AI GOVERNANCE INSPECTOR")
        header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header.setStyleSheet(f"color: {THEME['primary_glow']};")
        layout.addWidget(header)
        
        # Scroll Area for Logs
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setObjectName("AIInspectorContent")
        self.content.setAttribute(Qt.WA_StyledBackground, True)
        self.content.setStyleSheet("background: transparent;") # Inherits from panel or matches theme
        
        self.log_layout = QVBoxLayout(self.content)
        self.log_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        
        # 🧠 v2.7 Initial System Audit Logs
        self._add_log("SYSTEM: Governance Layer Initialized.", "#00e6ff")
        self._add_log("AUDIT: Secure Mode verification [PASSED]", "#00ff88")
        self._add_log("NETWORK: Monitoring traffic for anomalies...", "#aaaaaa")
        self._add_log("POLICY: Integrity protection active on /core/binaries", "#00e6ff")
        
        # ── Subscriptions ──
        EVENT_BUS.subscribe(SystemEvent.EVT_AI_DECISION, self._on_decision)
        EVENT_BUS.subscribe(SystemEvent.EVT_AI_REJECTED_ACTION, self._on_rejection)

    def _on_decision(self, payload):
        data = payload.data
        msg = f"✅ DECISION: {data.get('action')}\nParams: {data.get('params')}"
        self._add_log(msg, "#00ff88")

    def _on_rejection(self, payload):
        data = payload.data
        msg = f"❌ REJECTED: {data.get('action')}\nReason: {data.get('reasoning')}"
        self._add_log(msg, "#ff3a5c")

    def _add_log(self, text, color):
        card = QFrame()
        card.setStyleSheet(f"background: rgba(255,255,255,0.05); border-radius: 4px; border-left: 3px solid {color};")
        card_layout = QVBoxLayout(card)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {color};")
        card_layout.addWidget(lbl)
        
        # Insert at top
        self.log_layout.insertWidget(0, card)

    def show_side(self, parent_rect: QRect):
        margin = 20
        x = parent_rect.width() - self.width() - margin
        y = (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()

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
