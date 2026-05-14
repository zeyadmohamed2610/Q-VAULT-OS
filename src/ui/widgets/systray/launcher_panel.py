from __future__ import annotations
import subprocess
import sys
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QPointF
from PyQt5.QtGui import QFont, QPainter, QRadialGradient, QColor

logger = logging.getLogger(__name__)
from resources.theme import THEME

class LauncherPanel(QWidget):
    """
    System launcher popup — Premium Glassmorphic Design.
    """
    lock_requested   = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(260)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("launcher_card")
        self.card.setStyleSheet(f"""
            QFrame#launcher_card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(15, 20, 30, 250), 
                    stop:1 rgba(8, 10, 15, 255));
                border: 1px solid rgba(0, 240, 255, 0.15);
                border-radius: 24px;
            }}
        """)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(20, 24, 20, 24)
        lay.setSpacing(8)

        # ── Header: User Profile ─────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)
        
        avatar = QLabel("⚛")
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"""
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                stop:0 rgba(0, 240, 255, 0.1), stop:1 rgba(0, 240, 255, 0));
            color: {THEME['primary_glow']};
            border: 1.5px solid rgba(0, 240, 255, 0.3);
            border-radius: 24px;
            font-size: 24px;
        """)
        header.addWidget(avatar)

        from system.auth_manager import AuthManager
        self._auth = AuthManager()
        
        user_info = QVBoxLayout(); user_info.setSpacing(2)
        self.username_lbl = QLabel(self._auth.display_name)
        self.username_lbl.setStyleSheet(f"color: white; font-weight: 800; font-size: 14px; background: transparent; letter-spacing: 0.5px;")
        user_role = QLabel("SOVEREIGN ROOT")
        user_role.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 8px; font-weight: 900; letter-spacing: 2px; background: transparent; opacity: 0.8;")
        user_info.addWidget(self.username_lbl); user_info.addWidget(user_role)
        header.addLayout(user_info)
        header.addStretch()
        lay.addLayout(header)
        
        # Connect to profile updates
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.subscribe(SystemEvent.SESSION_LOCKED, self._on_profile_updated)
        
        lay.addSpacing(12)

        # ── Telemetry: System Dashboard ──────────────────────
        tele_box = QVBoxLayout(); tele_box.setSpacing(10)
        
        from ui.widgets.storage_ui import StorageWidget
        self.storage = StorageWidget()
        tele_box.addWidget(self.storage)
        
        from ui.widgets.ram_ui import RAMWidget
        self.ram = RAMWidget()
        tele_box.addWidget(self.ram)
        
        lay.addLayout(tele_box)
        lay.addSpacing(14)

        # ── Action Button Factory ────────────────────────────
        def create_btn(label, icon, color, is_critical=False):
            btn = QPushButton(f"{icon}   {label}")
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            bg = "rgba(255, 255, 255, 0.02)"
            border = "rgba(0, 240, 255, 0.05)"
            if is_critical:
                bg = "rgba(255, 59, 107, 0.05)"
                border = "rgba(255, 59, 107, 0.15)"

            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {THEME['text_main']};
                    border: 1px solid {border};
                    border-radius: 10px;
                    text-align: left;
                    padding-left: 16px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 {color}22, stop:1 rgba(255, 255, 255, 0.02));
                    border-color: {color};
                    color: white;
                }}
            """)
            return btn

        # ── Group 1: Session Actions ──────────────────────────
        lay.addWidget(self._make_section_header("SESSION"))
        
        btn_lock = create_btn("Lock System", "🔒", THEME['primary_glow'])
        btn_lock.clicked.connect(self._lock)
        lay.addWidget(btn_lock)

        btn_logout = create_btn("Logout", "󰗽", THEME['primary_soft'])
        btn_logout.clicked.connect(self._logout)
        lay.addWidget(btn_logout)

        btn_settings = create_btn("Account Settings", "⚙", THEME['primary_glow'])
        btn_settings.clicked.connect(self._open_settings)
        lay.addWidget(btn_settings)

        lay.addSpacing(6); lay.addWidget(self._make_separator()); lay.addSpacing(6)

        # ── Group 2: Power Actions ────────────────────────────
        lay.addWidget(self._make_section_header("SYSTEM POWER"))

        btn_restart = create_btn("Restart System", "󰜉", THEME['warning']) 
        btn_restart.clicked.connect(self._restart)
        lay.addWidget(btn_restart)
        
        off_btn = create_btn("Power Off", "󰐥", THEME['accent_error'], is_critical=True)
        off_btn.clicked.connect(self._shutdown)
        lay.addWidget(off_btn)

        outer.addWidget(self.card)

    def _make_section_header(self, title):
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 7px; font-weight: 900; letter-spacing: 1.5px; margin-bottom: 2px;")
        return lbl

    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: rgba(0, 240, 255, 0.05); border: none; height: 1px;")
        return line

    def _on_profile_updated(self, payload):
        """Refreshes the UI when the user's sovereign identity changes."""
        self.username_lbl.setText(self._auth.display_name)

    def _open_settings(self):
        self.hide()
        from ui.widgets.account_settings_dialog import AccountSettingsDialog
        dlg = AccountSettingsDialog()
        dlg.exec_()

    def _logout(self):
        self.hide()
        # In a real OS, this would clear session. Here we emit a signal.
        self.logout_requested.emit()

    def _lock(self): 
        self.hide()
        from system.system_helper import SystemControlHelper
        SystemControlHelper.power_action("sleep")
        self.lock_requested.emit()

    def _restart(self): 
        self.hide()
        from system.system_helper import SystemControlHelper
        SystemControlHelper.power_action("restart")

    def _shutdown(self): 
        self.hide()
        from system.system_helper import SystemControlHelper
        SystemControlHelper.power_action("shutdown")

    def popup_above(self, pos: QPoint):
        self.adjustSize()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() - 15)
        self.show()

    def paintEvent(self, event):
        # Card style handled by stylesheet
        super().paintEvent(event)
