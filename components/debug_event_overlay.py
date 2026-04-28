from assets.theme import *
# =============================================================
#  components/debug_event_overlay.py — Q-Vault OS
#
#  The Debug & Observability UI. Real-time Event Stream.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QPushButton, QLineEdit
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QFont, QColor
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload

class DebugEventOverlay(QFrame):
    """
    Real-time System Observability Layer.
    - Live Event Stream
    - Filter by Name/Type
    - Metrics Dashboard (EPS, Latency, Uptime)
    - Pause/Resume controls
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.SizeAllCursor)
        
        self.is_paused = False
        self.filter_text = ""
        self.max_rows = 15
        self._drag_pos = None
        
        self.setStyleSheet(f"""
            QFrame#Main {{
                background: rgba(10, 10, 20, 0.98);
                border: 1px solid {THEME['primary_glow']};
                border-radius: {RADIUS_MD}px;
            }}
            QLabel {{ color: #ccc; font-family: 'Consolas', 'Courier New'; font-size: 10px; }}
            QLineEdit {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: white;
                padding: 2px 5px;
                border-radius: 4px;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.1);
                border: none;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 0.2); }}
        """)
        self.setObjectName("Main")
        
        # ── Layout ──
        main_layout = QVBoxLayout(self)
        
        # Header + Metrics
        header_layout = QHBoxLayout()
        title = QLabel("📡 SYSTEM OBSERVABILITY")
        title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title.setStyleSheet(f"color: {THEME['primary_glow']};")
        header_layout.addWidget(title)
        
        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.clicked.connect(self._toggle_pause)
        header_layout.addWidget(self.btn_pause)
        main_layout.addLayout(header_layout)
        
        # Metrics Bar
        self.metrics_label = QLabel("EPS: 0.0 | UPTIME: 0s | ERR: 0")
        self.metrics_label.setStyleSheet(f"color: {THEME['success']}; font-weight: bold;")
        main_layout.addWidget(self.metrics_label)
        
        # Filter Input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter events (e.g. 'window', 'ui')...")
        self.filter_input.textChanged.connect(self._on_filter_changed)
        main_layout.addWidget(self.filter_input)
        
        # Event List (Scrollable)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.list_layout.addStretch()
        
        self.scroll.setWidget(self.list_container)
        main_layout.addWidget(self.scroll)
        
        # ── Subscriptions ──
        self._event_buffer = []
        EVENT_BUS.subscribe(SystemEvent.DEBUG_METRICS_UPDATED, self._on_metrics)
        EVENT_BUS.event_emitted.connect(self._buffer_event)
        
        # Periodic UI flush (USER: prevents freezing on high event volume)
        self.flush_timer = QTimer(self)
        self.flush_timer.setInterval(200) # 5Hz update
        self.flush_timer.timeout.connect(self._flush_buffer)
        self.flush_timer.start()

    def _buffer_event(self, payload):
        if self.is_paused: return
        self._event_buffer.append(payload)

    def _flush_buffer(self):
        if not self._event_buffer: return
        # Process only the last batch to keep UI responsive
        batch = self._event_buffer[-self.max_rows:]
        self._event_buffer.clear()
        for p in reversed(batch):
            self._on_event(p)

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.setText("RESUME" if self.is_paused else "PAUSE")
        color = THEME['error_bright'] if self.is_paused else 'white'
        self.btn_pause.setStyleSheet(f"color: {color};")

    def _on_filter_changed(self, text):
        self.filter_text = text.lower()
        # Clear current list and re-fill from history could be done here
        # For now, we just apply to incoming

    def _on_metrics(self, payload):
        data = payload.data
        txt = f"EPS: {data.get('events_per_sec', 0.0)} | UPTIME: {data.get('uptime_sec', 0)}s | ERR: {data.get('errors', 0)}"
        self.metrics_label.setText(txt)

    def _on_event(self, payload: EventPayload):
        if self.is_paused: return
        
        ename = str(payload.type.value if hasattr(payload.type, 'value') else payload.type).lower()
        if self.filter_text and self.filter_text not in ename and self.filter_text not in payload.source.lower():
            return
            
        self._add_row(payload)

    def _add_row(self, payload: EventPayload):
        row = QLabel()
        ename = str(payload.type.value if hasattr(payload.type, 'value') else payload.type).upper()
        
        is_req = "request" in ename.lower() or "req_" in ename.lower()
        prefix = "REQ" if is_req else "EVT"
        
        color = "#00e6ff" # Cyan for events
        if is_req: color = "#ffcc00" # Yellow for requests
        elif "dbg." in ename.lower(): color = "#888" # Grey for debug noise
        
        row.setText(f"[{prefix}] {ename} < {payload.source}")
        row.setStyleSheet(f"color: {color};")
        
        # Insert at top (index 0)
        self.list_layout.insertWidget(0, row)
        
        # Limit rows
        if self.list_layout.count() > self.max_rows:
            item = self.list_layout.takeAt(self.list_layout.count() - 2) # -2 because of stretch
            if item.widget():
                item.widget().deleteLater()

    # ── Draggable Logic ──
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def show_in_corner(self, parent_rect: QRect):
        margin = 15
        x = margin
        # Position at the very bottom left
        y = parent_rect.height() - self.height() - margin
        self.move(x, y)
        self.show()
        self.raise_()
