from assets.theme import *
# =============================================================
#  components/system_control_panel.py — Q-Vault OS
#
#  The System Control & Stabilization Interface.
#  Provides deep access to system health and control.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from core.event_bus import EVENT_BUS, SystemEvent

class SystemControlPanel(QFrame):
    """
    Stabilization & Control Layer UI.
    - Real-time Health Metrics
    - Performance Gauges
    - Critical Action Center
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(350, 450)
        self.setObjectName("ControlPanel")
        
        self.setStyleSheet(f"""
            QFrame#ControlPanel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {THEME['surface_mid']}, stop:1 {THEME['surface_raised']});
                border: 1px solid {THEME['primary_glow']};
                border-radius: {RADIUS_MD}px;
            }}
            QLabel {{ color: white; font-family: 'Segoe UI'; }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: white;
                padding: 8px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {THEME['primary_glow']}; color: black; }}
            QPushButton#Danger {{ color: {THEME['error_bright']}; }}
            QPushButton#Danger:hover {{ background: {THEME['error_bright']}; color: white; }}
            QProgressBar {{
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 4px;
                text-align: center;
                color: transparent;
                height: 10px;
            }}
            QProgressBar::chunk {{ background: {THEME['primary_glow']}; border-radius: 4px; }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # ── Header ──
        header = QLabel("⚙ SYSTEM CONTROL CENTER")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setStyleSheet(f"color: {THEME['primary_glow']};")
        self.layout.addWidget(header)
        
        self.layout.addSpacing(10)
        
        # ── Metrics Section ──
        self.metrics_container = QFrame()
        self.metrics_container.setStyleSheet("background: rgba(0, 0, 0, 0.2); border-radius: 10px; padding: 10px;")
        metrics_layout = QVBoxLayout(self.metrics_container)
        
        self.eps_label = self._create_metric_row(metrics_layout, "Events / Sec", "0.0")
        self.win_label = self._create_metric_row(metrics_layout, "Active Windows", "0")
        self.proc_label = self._create_metric_row(metrics_layout, "Active Procs", "0")
        
        self.layout.addWidget(self.metrics_container)
        
        # ── Health Gauge ──
        self.layout.addSpacing(15)
        self.layout.addWidget(QLabel("SYSTEM STABILITY"))
        self.health_bar = QProgressBar()
        self.health_bar.setValue(100)
        self.layout.addWidget(self.health_bar)
        
        self.layout.addStretch()
        
        # ── Action Center ──
        self.layout.addWidget(QLabel("ACTION CENTER"))
        
        btn_debug = QPushButton("Toggle Debug Overlay (F12)")
        btn_debug.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.REQ_DEBUG_TOGGLE))
        self.layout.addWidget(btn_debug)
        
        btn_restart = QPushButton("Restart Shell")
        btn_restart.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.REQ_SYSTEM_RESTART))
        self.layout.addWidget(btn_restart)
        
        btn_kill = QPushButton("Kill All Apps")
        btn_kill.setObjectName("Danger")
        btn_kill.clicked.connect(lambda: EVENT_BUS.emit(SystemEvent.REQ_PROCESS_KILL, {"all": True}))
        self.layout.addWidget(btn_kill)
        
        # ── Subscriptions ──
        EVENT_BUS.subscribe(SystemEvent.DEBUG_METRICS_UPDATED, self._update_metrics)
        EVENT_BUS.subscribe(SystemEvent.EVT_ERROR, self._on_system_error)

    def _create_metric_row(self, layout, name, value):
        row = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {THEME['text_muted']};")
        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Consolas", 10, QFont.Bold))
        row.addWidget(name_lbl)
        row.addStretch()
        row.addWidget(val_lbl)
        layout.addLayout(row)
        return val_lbl

    def _update_metrics(self, payload):
        data = payload.data
        self.eps_label.setText(str(data.get("events_per_sec", 0.0)))
        self.win_label.setText(str(data.get("active_windows", 0)))
        self.proc_label.setText(str(data.get("active_processes", 0)))
        
        # Calculate pseudo-health based on EPS and errors (placeholder logic)
        errors = data.get("errors", 0)
        health = max(0, 100 - (errors * 10))
        self.health_bar.setValue(health)
        
        if health < 50:
            self.health_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {THEME['error_bright']}; }}")
        else:
            self.health_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {THEME['primary_glow']}; }}")

    def _on_system_error(self, payload):
        # Flash health bar or show alert
        self.health_bar.setValue(self.health_bar.value() - 5)

    def show_centered(self, parent_rect):
        x = (parent_rect.width() - self.width()) // 2
        y = (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()
