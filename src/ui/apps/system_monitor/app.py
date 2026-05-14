"""
apps/system_monitor/app.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS │ Phase 8 - System Intelligence Dashboard

Live feed of the AppRuntimeManager, decoding App States and Trust Scores.
─────────────────────────────────────────────────────────────────────────────
"""

import logging
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QLinearGradient, QBrush, QPolygonF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QDialog, QTextEdit
)
from system.sandbox.base_app import BaseApp
from system.sandbox.secure_api import SecureAPI

from resources.theme import THEME

logger = logging.getLogger("ui.apps.system_monitor")

# ── Theme alias shim ──
class theme:
    ACCENT_CYAN   = THEME["primary_glow"]
    BG_DARK       = THEME["bg_dark"]
    BG_MID        = THEME["bg_mid"]
    BG_PANEL      = THEME["surface_dark"]
    BORDER_DIM    = THEME["border_subtle"]
    TEXT_BRIGHT   = THEME["text_main"]
    TEXT_DIM      = THEME["text_dim"]
    ACCENT_GREEN  = THEME["success"]
    ACCENT_ORANGE = THEME["warning"]
    DANGER        = THEME["accent_error"]
    FONT_MONO     = THEME.get("font_mono", "JetBrains Mono") # Fallback if token missing

class PressureTimelinePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.history = []
        self.setStyleSheet(f"background: {THEME['bg_black']}; border: 1px solid {THEME['border_subtle']}; border-radius: 6px;")

    def update_history(self, history):
        self.history = history
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(THEME['border_subtle']))
        for i in range(1, 4):
            y = int(self.height() * (i / 4))
            painter.drawLine(0, y, self.width(), y)
        if not self.history: return
        w, h = self.width(), self.height()
        max_samples = 120
        samples = self.history[-max_samples:]
        step = w / (max_samples - 1) if len(samples) > 1 else w
        points = []
        for i, s in enumerate(samples):
            x = i * step
            ratio = s["ratio"]
            y = h - (ratio * (h * 0.6))
            points.append(QPointF(x, y))
        if len(points) < 2: return
        path = QPolygonF(points)
        pen = QPen(QColor(theme.ACCENT_CYAN))
        pen.setWidth(2)
        painter.setPen(pen)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(0, 230, 255, 100))
        grad.setColorAt(1, QColor(0, 230, 255, 0))
        fill_points = points + [QPointF(points[-1].x(), h), QPointF(points[0].x(), h)]
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF(fill_points))
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i].toPoint(), points[i+1].toPoint())

class DecisionLogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setStyleSheet(f"background: {theme.BG_DARK}; border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; color: {theme.TEXT_BRIGHT}; font-family: {theme.FONT_MONO}; font-size: 10px;")
        layout.addWidget(self.list)

    def update_decisions(self, decisions):
        current_count = self.list.count()
        if len(decisions) <= current_count: return
        new_ones = decisions[current_count:]
        for d in new_ones:
            item_text = f"[{d['state_after']}] {d['reason']}"
            item = QListWidgetItem(item_text)
            color = theme.ACCENT_GREEN
            if d['state_after'] == "EMERGENCY": color = THEME['accent_error']
            elif d['state_after'] == "AGGRESSIVE": color = theme.ACCENT_ORANGE
            item.setForeground(QColor(color))
            self.list.insertItem(0, item)
            if self.list.count() > 50: self.list.takeItem(self.list.count() - 1)

class ExplanationDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diagnostic Engine: {data['app_id']}")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"background: {theme.BG_DARK}; color: {theme.TEXT_BRIGHT};")
        layout = QVBoxLayout(self)
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setStyleSheet(f"background: {THEME['bg_black']}; border: 1px solid {THEME['border_subtle']}; font-family: {theme.FONT_MONO};")
        html = f"""<p><b style='color:#00e6ff'>Target:</b> {data['app_id']}</p>
                   <p><b style='color:#00e6ff'>Trust:</b> {data['trust_score']}/100</p><hr>
                   <p><b>Final Cap: {data['final_worker_limit']} Workers</b></p>
                   <p style='color:#888'><i>{data['explanation']}</i></p>"""
        self.body.setHtml(html)
        layout.addWidget(self.body)
        btn = QPushButton("CLOSE")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class SystemMonitorWidget(BaseApp, QWidget):
    APP_ID = "system_monitor" 

    def __init__(self, secure_api: SecureAPI = None, parent=None):
        BaseApp.__init__(self, secure_api)
        QWidget.__init__(self, parent)
        self._card_cache = {}
        self.setStyleSheet(f"background: {theme.BG_DARK};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)

        # Header
        self._header = QWidget(); self._header.setFixedHeight(50)
        h_lo = QHBoxLayout(self._header)
        self._pressure_lbl = QLabel("SYSTEM LOAD: 0.00x")
        self._status_chip = QLabel("NORMAL")
        h_lo.addWidget(QLabel("⬡ A.I. COMMAND & CONTROL"))
        h_lo.addStretch()
        h_lo.addWidget(self._pressure_lbl)
        h_lo.addWidget(self._status_chip)
        root.addWidget(self._header)

        # Diag Row
        diag_row = QWidget(); diag_row.setFixedHeight(120)
        d_lo = QHBoxLayout(diag_row)
        self.pressure_plot = PressureTimelinePlot()
        self.decision_log = DecisionLogPanel()
        d_lo.addWidget(self.pressure_plot, stretch=2)
        d_lo.addWidget(self.decision_log, stretch=1)
        root.addWidget(diag_row)

        # Body
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

        self._lbl_totals = QLabel("Total Instances: 0")
        root.addWidget(self._lbl_totals)

    def on_start(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_telemetry)
        self._timer.start(1000)

    def _refresh_telemetry(self):
        try:
            from system.runtime_manager import RUNTIME_MANAGER
            data = RUNTIME_MANAGER.list_running()
            apps = data.get("apps", [])
            active_ids = {app["id"] for app in apps}

            for app_data in apps:
                iid = app_data["id"]
                if iid in self._card_cache:
                    self._update_app_card(self._card_cache[iid], app_data)
                else:
                    card = self._build_app_card(app_data)
                    self._card_cache[iid] = card
                    self.list_layout.insertWidget(self.list_layout.count()-1, card)
            
            for cid in list(self._card_cache.keys()):
                if cid not in active_ids:
                    card = self._card_cache.pop(cid)
                    card.setParent(None)
                    card.deleteLater()

            # Enhanced Header
            cpu = data.get('global_cpu', 0)
            mem = data.get('global_mem', 0)
            pressure = data.get('global_pressure', 0)
            
            self._pressure_lbl.setText(f"CPU: {cpu}%  |  MEM: {mem}%  |  LOAD: {pressure:.2f}x")
            self._status_chip.setText(data.get("global_state", "NORMAL"))
            
            # Color indicator for status
            state = data.get("global_state", "NORMAL")
            col = theme.ACCENT_GREEN
            if state == "EMERGENCY": col = THEME['accent_error']
            elif state == "AGGRESSIVE": col = theme.ACCENT_ORANGE
            self._status_chip.setStyleSheet(f"color: {col}; font-weight: bold; border: 1px solid {col}; border-radius: 4px; padding: 2px 8px;")

            self.pressure_plot.update_history(data.get("pressure_history", []))
            self.decision_log.update_decisions(data.get("decision_history", []))
            self._lbl_totals.setText(f"TOTAL INSTANCES: {data.get('total_instances', 0)}")
        except Exception as e:
            logger.error(f"Telemetry error: {e}")

    def _update_app_card(self, card, data):
        card.lbl_trust.setText(f"TRUST: {data['trust_score']}")
        card.lbl_mem.setText(f"{data['memory_delta_mb']:+.1f} MB")
        card.lbl_cpu.setText(f"CPU: {data.get('cpu_usage', 0.0):.1f}%")
        card.lbl_state.setText(data["state"])


    def _build_app_card(self, data):
        card = QFrame()
        card.setStyleSheet(f"background: {theme.BG_MID}; border: 1px solid {theme.BORDER_DIM}; border-radius: 4px;")
        lo = QHBoxLayout(card)
        
        card.lbl_id = QLabel(data["app_id"])
        card.lbl_trust = QLabel(f"TRUST: {data['trust_score']}")
        card.lbl_mem = QLabel(f"{data['memory_delta_mb']:+.1f} MB")
        card.lbl_cpu = QLabel(f"CPU: {data.get('cpu_usage', 0.0):.1f}%")
        card.lbl_state = QLabel(data["state"])
        
        lo.addWidget(card.lbl_id)
        lo.addStretch()
        lo.addWidget(card.lbl_mem)
        lo.addSpacing(10)
        lo.addWidget(card.lbl_cpu)
        lo.addSpacing(10)

        lo.addSpacing(20)
        lo.addWidget(card.lbl_trust)
        lo.addSpacing(20)
        lo.addWidget(card.lbl_state)
        
        btn_kill = QPushButton("KILL")
        btn_kill.setFixedWidth(50)
        btn_kill.setStyleSheet(f"QPushButton{{background: {THEME['accent_error']}; color: white; border-radius: 4px; font-weight: bold;}} QPushButton:hover{{background: #ff5252;}}")
        btn_kill.clicked.connect(lambda: self._kill_instance(data["id"]))
        lo.addWidget(btn_kill)

        btn_diag = QPushButton("🧠")
        btn_diag.setFixedSize(30, 30)
        btn_diag.clicked.connect(lambda: self._show_explanation(data["id"]))
        lo.addWidget(btn_diag)
        
        return card

    def _kill_instance(self, iid):
        from system.runtime_manager import RUNTIME_MANAGER
        RUNTIME_MANAGER.kill(iid)
        self._refresh_telemetry()


    def _show_explanation(self, iid):
        from system.runtime_manager import RUNTIME_MANAGER
        exp = RUNTIME_MANAGER.get_explanation(iid)
        ExplanationDialog(exp, self).exec_()
