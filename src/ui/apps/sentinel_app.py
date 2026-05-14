import psutil
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QScrollArea, QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

class SystemSentinelApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SYSTEM SENTINEL")
        self.setMinimumSize(700, 500)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # ── Header ──
        header = QLabel("SYSTEM SENTINEL — FORENSIC CORE")
        header.setStyleSheet("color: #00e6ff; font-weight: bold; font-size: 18px; letter-spacing: 2px;")
        self.layout.addWidget(header)

        # ── Stats Row ──
        stats_layout = QHBoxLayout()
        
        self.cpu_card = self._create_stat_card("CPU USAGE", "0%")
        self.ram_card = self._create_stat_card("RAM USAGE", "0%")
        self.trust_card = self._create_stat_card("TRUST INDEX", "100%")
        
        stats_layout.addWidget(self.cpu_card)
        stats_layout.addWidget(self.ram_card)
        stats_layout.addWidget(self.trust_card)
        
        self.layout.addLayout(stats_layout)

        # ── Audit Logs ──
        log_header = QLabel("REAL-TIME SECURITY AUDIT TRAIL")
        log_header.setStyleSheet("color: rgba(0, 230, 255, 0.6); font-size: 11px; font-weight: bold;")
        self.layout.addWidget(log_header)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(0, 230, 255, 0.1);
                border-radius: 8px;
                color: #00ffaa;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        self.layout.addWidget(self.log_viewer)

        # ── System Pulse ──
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_stats)
        self.pulse_timer.start(1000)

        self._add_log_entry("Sovereign Kernel connected. Sentinel Active.")

    def _create_stat_card(self, title, val):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(0, 230, 255, 0.1);
                border-radius: 12px;
                padding: 15px;
            }
        """)
        l = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        v = QLabel(val)
        v.setObjectName("ValueLabel")
        v.setStyleSheet("color: #fff; font-size: 24px; font-weight: 900;")
        l.addWidget(t)
        l.addWidget(v)
        return card

    def _update_stats(self):
        # Update CPU
        cpu = psutil.cpu_percent()
        self.cpu_card.findChild(QLabel, "ValueLabel").setText(f"{cpu}%")
        
        # Update RAM
        ram = psutil.virtual_memory().percent
        self.ram_card.findChild(QLabel, "ValueLabel").setText(f"{ram}%")
        
        # Simulated Trust Index (Can be linked to RuntimeManager later)
        self.trust_card.findChild(QLabel, "ValueLabel").setText("100.0")

    def _add_log_entry(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_viewer.append(f"[{ts}] {msg}")

    def on_start(self):
        self._add_log_entry("Sentinel Subsystem Init complete.")
