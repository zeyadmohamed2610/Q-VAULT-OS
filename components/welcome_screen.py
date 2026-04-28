# ⚠️ QUARANTINED MODULE ⚠️
# ==============================
# Module: welcome_screen.py
# Status: NOT PART OF RUNTIME
# Warning: DO NOT IMPORT
# Reason: Pending architectural verification
# ==============================

# =============================================================
#  welcome_screen.py - Q-Vault OS  |  First Run Welcome Screen
# =============================================================
# ⚠️ QUARANTINED: 2026-04-18
# =============================================================

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEasingCurve
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
)

from assets import theme


class WelcomeScreen(QWidget):
    welcome_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(700, 550)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        container = QWidget(self)
        container.setObjectName("WelcomeContainer")
        container.setStyleSheet(
            f"""
            QWidget#WelcomeContainer {{
                background: rgba(9, 17, 29, 245);
                border: 2px solid {theme.BORDER_BRIGHT};
                border-radius: 16px;
            }}
            """
        )

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(40, 30, 40, 30)
        vbox.setSpacing(16)

        title = QLabel("Welcome to Q-VAULT OS")
        title.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.ACCENT_CYAN};
                font-family: 'Consolas', monospace;
                font-size: 26px;
                font-weight: bold;
                background: transparent;
            }}
            """
        )
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        subtitle = QLabel("Your Secure Virtual Operating System")
        subtitle.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.TEXT_DIM};
                font-family: 'Consolas', monospace;
                font-size: 12px;
                background: transparent;
                margin-bottom: 10px;
            }}
            """
        )
        subtitle.setAlignment(Qt.AlignCenter)
        vbox.addWidget(subtitle)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {theme.BORDER_DIM}; margin: 10px 0;")
        vbox.addWidget(sep)

        tips_label = QLabel("QUICK START TIPS")
        tips_label.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.ACCENT_GREEN};
                font-family: 'Consolas', monospace;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }}
            """
        )
        vbox.addWidget(tips_label)

        tips = [
            ("Open Terminal", "Click the Terminal icon on desktop or use Ctrl+Alt+T"),
            (
                "Command Modes",
                "Use 'mode real' to execute host commands, 'mode virtual' for VFS",
            ),
            ("Security", "Dangerous commands like 'rm -rf' are blocked for safety"),
            ("Workspaces", "Press Ctrl+Alt+Left/Right to switch workspaces"),
            ("File System", "Full virtual filesystem with /home, /bin, /etc"),
            ("Help", "Type 'help' in terminal for all available commands"),
        ]

        for cmd, desc in tips:
            tip_row = self._create_tip_row(cmd, desc)
            vbox.addWidget(tip_row)

        vbox.addStretch()

        btn = QPushButton("GET STARTED  ->")
        btn.setObjectName("StartBtn")
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {theme.ACCENT_CYAN};
                color: {theme.BG_DARK};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
            }}
            QPushButton:hover {{
                background: #43e0ff;
            }}
            QPushButton:pressed {{
                background: #0ab6e2;
            }}
            """
        )
        btn.clicked.connect(self._on_get_started)
        vbox.addWidget(btn, 0, Qt.AlignCenter)

        version = QLabel("Version 4.0 | Professional Edition")
        version.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.BORDER_DIM};
                font-family: 'Consolas', monospace;
                font-size: 9px;
                background: transparent;
                margin-top: 8px;
            }}
            """
        )
        version.setAlignment(Qt.AlignCenter)
        vbox.addWidget(version)

        layout.addWidget(container, 0, Qt.AlignCenter)

    def _create_tip_row(self, cmd: str, desc: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")

        hbox = QHBoxLayout(row)
        hbox.setContentsMargins(0, 4, 0, 4)
        hbox.setSpacing(12)

        cmd_lbl = QLabel(f"• {cmd}")
        cmd_lbl.setFixedWidth(140)
        cmd_lbl.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.ACCENT_ICE};
                font-family: 'Consolas', monospace;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }}
            """
        )
        hbox.addWidget(cmd_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.TEXT_DIM};
                font-family: 'Consolas', monospace;
                font-size: 11px;
                background: transparent;
            }}
            """
        )
        hbox.addWidget(desc_lbl)

        return row

    def _on_get_started(self):
        self.welcome_complete.emit()
