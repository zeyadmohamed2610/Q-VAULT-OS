"""
apps/system_monitor/app.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS │ Phase 8 - System Intelligence Dashboard

Live feed of the AppRuntimeManager, decoding App States and Trust Scores.
─────────────────────────────────────────────────────────────────────────────
"""

from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QBrush, QPolygonF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QDialog, QTextEdit
)
from system.sandbox.base_app import BaseApp
from system.sandbox.secure_api import SecureAPI

# Attack Engine for Phase 10.5
from assets import theme
from apps.system_monitor.attack_engine import AttackEngine

# ── Phase 13.6 COMPONENTS ──────────────────────────────────────────────────

class PressureTimelinePlot(QWidget):
    """Sleek neon curve showing historical system pressure."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.history = [] # List of {"time": t, "ratio": r}
        self.setStyleSheet(f"background: #000; border: 1px solid {THEME['surface_dark']}; border-radius: 4px;")

    def update_history(self, history):
        self.history = history
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw grid
        painter.setPen(QColor(40, 40, 40))
        for i in range(1, 4):
            y = int(self.height() * (i / 4))
            painter.drawLine(0, y, self.width(), y)
            
        if not self.history:
            return

        w, h = self.width(), self.height()
        max_samples = 120
        samples = self.history[-max_samples:]
        
        # Scaling math
        step = w / (max_samples - 1) if len(samples) > 1 else w
        points = []
        for i, s in enumerate(samples):
            x = i * step
            # Ratio 1.0 = 70% height
            ratio = s["ratio"]
            y = h - (ratio * (h * 0.6))
            points.append(QPointF(x, y))

        if len(points) < 2: return

        # Draw the curve
        path = QPolygonF(points)
        pen = QPen(QColor(theme.ACCENT_CYAN))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw neon glow under the line
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(0, 230, 255, 100))
        grad.setColorAt(1, QColor(0, 230, 255, 0))
        
        fill_points = points + [QPointF(points[-1].x(), h), QPointF(points[0].x(), h)]
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF(fill_points))
        
        painter.setPen(pen)
        # Using drawPolyline for smoother appearance than drawPolygon
        for i in range(len(points) - 1):
            painter.drawLine(points[i].toPoint(), points[i+1].toPoint())

class DecisionLogPanel(QWidget):
    """Real-time feed of governance decisions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"""
            QListWidget {{
                background: {theme.BG_DARK};
                border: 1px solid {theme.BORDER_DIM};
                border-radius: 4px;
                color: {theme.TEXT_BRIGHT};
                font-family: {theme.FONT_MONO};
                font-size: 10px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {THEME['bg_mid']};
            }}
        """)
        layout.addWidget(self.list)

    def update_decisions(self, decisions):
        # Only add new ones
        current_count = self.list.count()
        if len(decisions) <= current_count:
            return
            
        new_ones = decisions[current_count:]
        for d in new_ones:
            time_str = f"[{d['state_after']}]"
            item_text = f"{time_str} {d['reason']}"
            item = QListWidgetItem(item_text)
            
            color = theme.ACCENT_GREEN
            if d['state_after'] == "EMERGENCY": color = "#ff3333"
            elif d['state_after'] == "AGGRESSIVE": color = theme.ACCENT_ORANGE
            
            item.setForeground(QColor(color))
            self.list.insertItem(0, item) # Newest at top
            if self.list.count() > 50:
                self.list.takeItem(self.list.count() - 1)

class ExplanationDialog(QDialog):
    """Deep diagnostic popup for explainable governance."""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diagnostic Engine: {data['app_id']}")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"background: {theme.BG_DARK}; color: {theme.TEXT_BRIGHT};")
        
        layout = QVBoxLayout(self)
        
        # Header
        title = QLabel(f"EXPLAINABILITY REPORT")
        title.setStyleSheet(f"color: {theme.ACCENT_CYAN}; font-weight: bold; font-family: {theme.FONT_MONO}; font-size: 16px;")
        layout.addWidget(title)
        
        # Body
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setStyleSheet(f"background: #000; border: 1px solid {THEME['border_muted']}; font-family: {theme.FONT_MONO};")
        
        html = f"""
        <style>
            .key {{ color: #00e6ff; font-weight: bold; }}
            .val {{ color: #ffffff; }}
            .reason {{ color: #ffaa00; margin-left: 20px; }}
            .msg {{ font-style: italic; color: #888; border-top: 1px solid #333; padding-top: 10px; }}
        </style>
        <p><span class="key">Target:</span> <span class="val">{data['app_id']}</span></p>
        <p><span class="key">Context:</span> <span class="val">{data['global_state']} (Load {data['pressure_ratio']}x)</span></p>
        <p><span class="key">Trust Score:</span> <span class="val">{data['trust_score']} / 100</span></p>
        <hr>
        <p><span class="key">Resource Allocation Log:</span></p>
        <p>Base Limit: {data['base_worker_limit']}</p>
        <p>Trust Weighting: {data['trust_adjustment']:+}</p>
        <p><b>Final Cap: {data['final_worker_limit']} Workers</b></p>
        <p><span class="key">Active Restrictions:</span></p>
        """
        for r in data['reasons']:
            html += f"<p class='reason'>• {r.replace('_', ' ').title()}</p>"
            
        html += f"<div class='msg'>{data['explanation']}</div>"
        
        self.body.setHtml(html)
        layout.addWidget(self.body)
        
        btn_close = QPushButton("CLOSE")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background: {THEME['border_muted']}; border: 1px solid {THEME['text_disabled']}; padding: 10px;")
        layout.addWidget(btn_close)

class LaunchControlPanel(QFrame):
    """v3.6.3 Mission Control for v4.0 Activation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setObjectName("LaunchControl")
        self.setStyleSheet(f"""
            QFrame#LaunchControl {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {THEME['bg_dark']}, stop:1 #000);
                border: 1px solid {THEME['surface_raised']}; border-radius: 8px; margin: 10px; padding: 15px;
            }}
            QLabel#KPIValue {{ color: {THEME['primary_glow']}; font-family: 'Consolas', monospace; font-size: 18px; font-weight: bold; }}
            QLabel#KPILabel {{ color: {THEME['text_disabled']}; font-size: 9px; text-transform: uppercase; letter-spacing: 1px; }}
            QPushButton#LaunchBtn {{
                background: {THEME['success']}; color: #000; font-weight: 800; border-radius: 6px; padding: 12px; font-size: 12px;
            }}
            QPushButton#LaunchBtn:disabled {{ background: {THEME['surface_raised']}; color: {THEME['text_disabled']}; }}
        """)
        
        lo = QVBoxLayout(self); stats = QHBoxLayout()
        
        self.acc_lbl = QLabel("98.2%"); self.acc_lbl.setObjectName("KPIValue")
        self.miss_lbl = QLabel("0"); self.miss_lbl.setObjectName("KPIValue")
        self.annoy_lbl = QLabel("0.12"); self.annoy_lbl.setObjectName("KPIValue")
        
        for val, name in [(self.acc_lbl, "Silent Accuracy"), (self.miss_lbl, "Missed Criticals"), (self.annoy_lbl, "Annoyance Score")]:
            col = QVBoxLayout(); col.addWidget(val, alignment=Qt.AlignCenter); col.addWidget(QLabel(name, objectName="KPILabel"), alignment=Qt.AlignCenter)
            stats.addLayout(col)
            
        lo.addLayout(stats)
        
        self.status_lbl = QLabel("STATUS: OBSERVING YOUR WORKFLOW SILENTLY")
        self.status_lbl.setObjectName("KPILabel")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet(f"color: {THEME['text_dim']}; font-style: italic;")
        lo.addWidget(self.status_lbl)
        
        self.launch_btn = QPushButton("ACTIVATE Q-VAULT v4.0 (PROMPT READINESS: 12%)")
        self.launch_btn.setObjectName("LaunchBtn")
        self.launch_btn.setEnabled(False)
        self.launch_btn.clicked.connect(self._activate_v4)
        lo.addWidget(self.launch_btn)

    def update_stats(self):
        from system.settings import SETTINGS
        elapsed = SETTINGS.get_shadow_elapsed_hours()
        ready_pct = int(min(1.0, elapsed / 48.0) * 100)
        
        self.launch_btn.setText(f"ACTIVATE Q-VAULT v4.0 (STABILITY: {ready_pct}%)")
        if SETTINGS.is_v4_ready():
            self.launch_btn.setEnabled(True)
            self.launch_btn.setText("ACTIVATE Q-VAULT v4.0 (EXIT SHADOW MODE)")

    def _activate_v4(self):
        """The Switch: Final transition to Production Mode."""
        from system.settings import SETTINGS
        from system.shadow_logger import SHADOW_LOGGER
        from system.notification_service import NOTIFICATION_SERVICE, NotificationLevel
        
        # 1. State Shift
        SETTINGS.set_shadow_mode(False)
        
        # 2. Hygiene: Archive Shadow phase
        SHADOW_LOGGER.archive_current_session()
        
        # 3. Notification
        NOTIFICATION_SERVICE.notify(
            title="Q-VAULT v4.0 ACTIVE",
            message="Professional Shadowing period complete. Active Engineering Partner online.",
            level=NotificationLevel.INFO
        )
        self.launch_btn.setText("Q-VAULT v4.0 PRODUCTION ACTIVE")
        self.launch_btn.setEnabled(False)
        self.status_lbl.setText("STATUS: PRODUCTION ACTIVE (SOVEREIGN MODE)")


class SystemMonitorWidget(BaseApp, QWidget):
    """
    Live Intelligence Dashboard reflecting the Q-Vault OS Runtime layer.
    """
    APP_ID = "system_monitor" 

    def __init__(self, secure_api: SecureAPI = None, parent=None):
        BaseApp.__init__(self, secure_api)
        QWidget.__init__(self, parent)

        self.setObjectName("AppContainer")
        self.setMinimumSize(600, 450)

        # Add the test runner
        self.attack_engine = AttackEngine()
        self.attack_engine.log_emitted.connect(self._on_attack_log)
        self.attack_engine.test_finished.connect(self._on_attack_finished)

        # ── Build UI ──
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        
        # ── Middle Diagnostic Row (Phase 13.6) ──
        diag_row = QWidget()
        diag_row.setFixedHeight(120)
        diag_row.setStyleSheet(f"background: {THEME['bg_black']}; border-bottom: 1px solid {theme.BORDER_DIM};")
        diag_layout = QHBoxLayout(diag_row)
        diag_layout.setContentsMargins(10, 5, 10, 5)
        
        self.pressure_plot = PressureTimelinePlot()
        self.decision_log = DecisionLogPanel()
        
        p_col = QVBoxLayout()
        p_lbl = QLabel("PRESSURE TIMELINE (2m)")
        p_lbl.setStyleSheet(f"color: {THEME['text_disabled']}; font-size: 9px; font-family: {theme.FONT_MONO};")
        p_col.addWidget(p_lbl)
        p_col.addWidget(self.pressure_plot)
        
        d_col = QVBoxLayout()
        d_lbl = QLabel("GOVERNANCE DECISION TRACE")
        d_lbl.setStyleSheet(f"color: {THEME['text_disabled']}; font-size: 9px; font-family: {theme.FONT_MONO};")
        d_col.addWidget(d_lbl)
        d_col.addWidget(self.decision_log)
        
        diag_layout.addLayout(p_col, stretch=2)
        diag_layout.addLayout(d_col, stretch=1)
        
        root.addWidget(diag_row)

        # v3.6.3 Launch Control (Top of main content)
        self.launch_control = LaunchControlPanel()
        root.addWidget(self.launch_control)

        main_h = QHBoxLayout()
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.addWidget(self._make_body(), stretch=2)
        main_h.addWidget(self._make_attack_logs_panel(), stretch=1)
        
        root.addLayout(main_h, stretch=1)
        root.addWidget(self._make_footer())

    def on_start(self) -> None:
        """Begin fetching telemetry."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_telemetry)
        self._timer.start(1000)

    def on_stop(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def get_permissions(self) -> list[str]:
        return ["file_access:virtual_only", "network_access:DENIED", "system_calls:DENIED"]

    # ── UI builders ───────────────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(54)
        header.setStyleSheet(f"background: {theme.BG_DARK}; border-bottom: 1px solid {theme.BORDER_DIM};")

        row = QHBoxLayout(header)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(15)

        title = QLabel("⬡ A.I. COMMAND & CONTROL")
        title.setStyleSheet(f"color: {theme.ACCENT_CYAN}; font-family: {theme.FONT_MONO}; font-size: 13px; font-weight: bold; letter-spacing: 2px;")
        
        # New Pressure Telemetry
        self._pressure_lbl = QLabel("PRESSURE: 0.00x")
        self._pressure_lbl.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 11px;")
        
        self._cooldown_lbl = QLabel("COOLDOWN: 0.0s")
        self._cooldown_lbl.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 11px;")
        self._cooldown_lbl.hide()

        self._status_chip = QLabel("NORMAL")
        self._status_chip.setStyleSheet(f"color: {theme.BG_DARK}; background: {theme.ACCENT_GREEN}; font-family: {theme.FONT_MONO}; font-weight: bold; padding: 2px 8px; border-radius: 4px;")

        row.addWidget(title)
        row.addStretch()
        row.addWidget(self._pressure_lbl)
        row.addWidget(self._cooldown_lbl)
        row.addWidget(self._status_chip)
        return header

    def _make_body(self) -> QWidget:
        body = QWidget()
        body.setStyleSheet(f"background: {theme.BG_MID};")
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(16, 16, 16, 16)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch() # Push items up
        
        self.scroll_area.setWidget(self.list_container)
        col.addWidget(self.scroll_area)
        
        return body

    from PyQt5.QtWidgets import QTextEdit
    def _make_attack_logs_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background: {theme.BG_DARK}; border-left: 1px solid {theme.BORDER_DIM};")
        col = QVBoxLayout(panel)
        col.setContentsMargins(8, 8, 8, 8)
        
        lbl = QLabel("ATTACK LOGS")
        lbl.setStyleSheet(f"color: {theme.DANGER}; font-weight: bold; font-family: {theme.FONT_MONO}; font-size: 11px;")
        col.addWidget(lbl)
        
        from PyQt5.QtWidgets import QTextEdit
        self.attack_logs_view = QTextEdit()
        self.attack_logs_view.setReadOnly(True)
        self.attack_logs_view.setStyleSheet(f"""
            QTextEdit {{
                background: #000;
                color: {THEME['success']};
                font-family: 'Consolas', monospace;
                font-size: 10px;
                border: 1px solid {THEME['border_muted']};
            }}
        """)
        col.addWidget(self.attack_logs_view)
        return panel

    def _make_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet(f"background: {theme.BG_DARK}; border-top: 1px solid {theme.BORDER_DIM};")
        row = QHBoxLayout(footer)
        row.setContentsMargins(12, 0, 12, 0)
        
        self._lbl_totals = QLabel("Total Processes: 0")
        self._lbl_totals.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 11px;")
        
        row.addWidget(self._lbl_totals)
        row.addStretch()

        self.btn_attack = QPushButton("🧪 Run Security Tests")
        self.btn_attack.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.DANGER};
                border: 1px solid {theme.DANGER};
                border-radius: 4px;
                padding: 4px 12px;
                font-family: {theme.FONT_MONO};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 58, 92, 0.1);
            }}
        """)
        self.btn_attack.clicked.connect(self._run_attack_tests)
        row.addWidget(self.btn_attack)

        return footer

    def _run_attack_tests(self):
        self.btn_attack.setEnabled(False)
        self.attack_logs_view.clear()
        self.attack_engine.run_tests_async()

    def _on_attack_log(self, severity: str, tag: str, message: str):
        colors = {
            "LOW": "#00ff00",
            "MEDIUM": "#ffaa00",
            "HIGH": "#ff3333",
            "CRITICAL": "#ff0000"
        }
        c = colors.get(severity, "#fff")
        self.attack_logs_view.append(f"<span style='color: #888;'>[ATTACK]</span><span style='color: {c};'>[{severity}][{tag}] {message}</span>")
        sb = self.attack_logs_view.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def _on_attack_finished(self, metrics: dict):
        self.btn_attack.setEnabled(True)
        self.attack_logs_view.append(f"<br><span style='color: #00ffff;'>=== REPORT ===</span>")
        self.attack_logs_view.append(f"<span style='color: #fff;'>Duration: {metrics['duration']:.2f}s</span>")
        self.attack_logs_view.append(f"<span style='color: #fff;'>Thread Delta: {metrics['thread_delta']}</span>")
        self.attack_logs_view.append(f"<span style='color: #fff;'>UI Lag Detect: {metrics['ui_lag']:.3f}s</span>")
        sb = self.attack_logs_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _refresh_telemetry(self) -> None:
        try:
            from system.runtime_manager import RUNTIME_MANAGER
            data = RUNTIME_MANAGER.list_running()
            
            # Clear old layout items
            for i in reversed(range(self.list_layout.count())):
                item = self.list_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
                elif item.spacerItem():
                    self.list_layout.removeItem(item)
                    
            apps = data.get("apps", [])
            for app_data in apps:
                card = self._build_app_card(app_data)
                self.list_layout.addWidget(card)
                
            self.list_layout.addStretch()
            self._lbl_totals.setText(f"Total Instances: {data['total_instances']}")
            
            # Update Global Headers
            pressure = data.get("global_pressure", 0.0)
            state = data.get("global_state", "NORMAL")
            cooldown = data.get("cooldown_remaining", 0.0)
            
            # Phase 13.6 Histories
            self.pressure_plot.update_history(data.get("pressure_history", []))
            self.decision_log.update_decisions(data.get("decision_history", []))
            
            self._pressure_lbl.setText(f"SYSTEM LOAD: {pressure:.2f}x")
            self._status_chip.setText(state)
            
            # State Color Logic
            state_colors = {
                "NORMAL": theme.ACCENT_GREEN,
                "SOFT": theme.ACCENT_CYAN,
                "AGGRESSIVE": theme.ACCENT_ORANGE,
                "EMERGENCY": "#ff3333"
            }
            bg = state_colors.get(state, theme.ACCENT_GREEN)
            self._status_chip.setStyleSheet(f"color: {theme.BG_DARK}; background: {bg}; font-family: {theme.FONT_MONO}; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            
            if cooldown > 0:
                self._cooldown_lbl.setText(f"COOLDOWN: {cooldown}s")
                self._cooldown_lbl.show()
                self._pressure_lbl.setStyleSheet(f"color: {theme.ACCENT_ORANGE}; font-family: {theme.FONT_MONO}; font-size: 11px;")
            else:
                self._cooldown_lbl.hide()
                self._pressure_lbl.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 11px;")
            
            # v3.6.3 UI Updates
            if hasattr(self, 'launch_control'):
                self.launch_control.update_stats()

        except Exception as e:
            self._status_chip.setText("TELEMETRY ERROR")
            self._status_chip.setStyleSheet(f"color: white; background: red; padding: 2px 8px; border-radius: 8px;")
            print("System Monitor Error:", e)

    def _build_app_card(self, data: dict) -> QFrame:
        card = QFrame()
        
        # Determine Card Color strictly by state and trust
        state = data["state"]
        score = data["trust_score"]
        
        border_col = theme.BORDER_DIM
        bg_col = theme.BG_PANEL
        
        if state == "QUARANTINED" or score < 20:
            border_col = "#ff3333"
            bg_col = "rgba(40, 10, 10, 0.4)"
        elif state == "CRASHED":
            border_col = theme.ACCENT_ORANGE
        elif state == "TERMINATED":
            border_col = "#555555"
        
        card.setStyleSheet(f"QFrame {{ background: {bg_col}; border: 1px solid {border_col}; border-radius: 6px; }}")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Info
        info_layout = QVBoxLayout()
        lbl_id = QLabel(data["app_id"])
        lbl_id.setStyleSheet(f"color: {theme.TEXT_BRIGHT}; font-weight: bold; font-size: 14px; border:none; background: transparent;")
        
        lbl_instance = QLabel(f"PID/Win: {data['id']}")
        lbl_instance.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 10px; border:none; background: transparent;")
        
        btn_explain = QPushButton("🧠 EXPLAIN")
        btn_explain.setFixedSize(80, 22)
        btn_explain.setCursor(Qt.PointingHandCursor)
        btn_explain.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 230, 255, 0.05);
                color: {theme.ACCENT_CYAN};
                border: 1px solid {theme.ACCENT_CYAN};
                border-radius: 3px;
                font-family: {theme.FONT_MONO};
                font-size: 9px;
            }}
            QPushButton:hover {{
                background: rgba(0, 230, 255, 0.15);
            }}
        """)
        btn_explain.clicked.connect(lambda: self._show_explanation(data["id"]))
        
        info_layout.addWidget(lbl_id)
        info_layout.addWidget(lbl_instance)
        info_layout.addWidget(btn_explain)
        
        # Trust Score Bar
        lbl_trust = QLabel(f"Trust: {score}")
        trust_color = theme.ACCENT_GREEN if score >= 80 else (theme.ACCENT_ORANGE if score >= 40 else "#ff3333")
        lbl_trust.setStyleSheet(f"color: {trust_color}; font-weight: bold; font-family: {theme.FONT_MONO}; font-size: 14px; border:none; background: transparent;")
        
        # State Badge
        lbl_state = QLabel(state)
        lbl_state.setStyleSheet(f"color: white; background: {border_col}; font-family: {theme.FONT_MONO}; font-size: 10px; font-weight: bold; padding: 4px; border-radius: 4px; border:none;")
        
        # Memory Telemetry
        mem_layout = QVBoxLayout()
        mem_val = f"{data['memory_delta_mb']:+.1f} MB"
        trend = data["mem_trend"]
        
        lbl_mem = QLabel(mem_val)
        trend_color = "#ff3333" if "SPIKE" in trend else (theme.ACCENT_ORANGE if "INCREASING" in trend else theme.TEXT_DIM)
        lbl_mem.setStyleSheet(f"color: {trend_color}; font-family: {theme.FONT_MONO}; font-size: 11px; border:none; background: transparent; font-weight: bold;")
        
        lbl_trend = QLabel(trend)
        lbl_trend.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 9px; border:none; background: transparent;")
        
        mem_layout.addWidget(lbl_mem, alignment=Qt.AlignRight)
        mem_layout.addWidget(lbl_trend, alignment=Qt.AlignRight)

        # Worker Telemetry
        worker_layout = QVBoxLayout()
        active_w = data["active_workers"]["total"]
        limit_w  = data["max_workers"]
        usage    = data["worker_usage"]
        
        lbl_workers = QLabel(f"Workers: {active_w} / {limit_w}")
        usage_color = theme.ACCENT_CYAN if usage < 0.5 else (theme.ACCENT_ORANGE if usage < 0.9 else "#ff3333")
        lbl_workers.setStyleSheet(f"color: {usage_color}; font-family: {theme.FONT_MONO}; font-size: 11px; border:none; background: transparent; font-weight: bold;")
        
        lbl_usage = QLabel(f"Load: {int(usage*100)}%")
        lbl_usage.setStyleSheet(f"color: {theme.TEXT_DIM}; font-family: {theme.FONT_MONO}; font-size: 9px; border:none; background: transparent;")
        
        worker_layout.addWidget(lbl_workers, alignment=Qt.AlignHCenter)
        worker_layout.addWidget(lbl_usage, alignment=Qt.AlignHCenter)

        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(worker_layout)
        layout.addStretch()
        layout.addLayout(mem_layout)
        layout.addSpacing(20)
        layout.addWidget(lbl_trust)
        layout.addSpacing(20)
        layout.addWidget(lbl_state)
        
        return card
    def _show_explanation(self, instance_id: str):
        try:
            from system.runtime_manager import RUNTIME_MANAGER
            from assets.theme import THEME
            explanation = RUNTIME_MANAGER.get_explanation(instance_id)
            dlg = ExplanationDialog(explanation, self)
            dlg.exec_()
        except Exception as e:
            print(f"Explanation Error: {e}")
