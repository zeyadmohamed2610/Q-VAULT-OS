# =============================================================
#  core_app.py — Q-Vault OS  |  System Core Monitor
# =============================================================

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from assets import theme
from core.system_state import STATE


class QVaultCoreApp(QWidget):
    """
    System diagnostic dashboard - shows OS core status.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Q-Vault Core")
        self.setMinimumSize(400, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("SYSTEM CORE MONITOR")
        header.setStyleSheet(
            f"color:{theme.ACCENT_CYAN}; font-weight:bold; font-size:14px;"
        )
        layout.addWidget(header)

        self.panel = QFrame()
        self.panel.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-radius:8px; border:1px solid {theme.BORDER_DIM};"
        )
        p_layout = QVBoxLayout(self.panel)

        self.user_status = self._create_row(p_layout, "Current User")
        self.session_status = self._create_row(p_layout, "Session Type")
        self.risk_status = self._create_row(p_layout, "Security Risk")
        self.theme_status = self._create_row(p_layout, "Theme")

        layout.addWidget(self.panel)

        e_header = QLabel("SYSTEM STATUS")
        e_header.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px; font-weight:bold; margin-top:5px;"
        )
        layout.addWidget(e_header)

        self.event_box = QLabel("Q-Vault OS running normally...")
        self.event_box.setStyleSheet(
            f"background:#05080c; border:1px solid #1a2535; color:{theme.ACCENT_GREEN}; font-family:Consolas; padding:8px; border-radius:4px; font-size:11px;"
        )
        layout.addWidget(self.event_box)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(1000)

        STATE.subscribe(self._on_state_change)
        self._refresh()

    def closeEvent(self, event):
        STATE.unsubscribe(self._on_state_change)
        super().closeEvent(event)

    def _on_state_change(self, field: str, old, new):
        self._refresh()

    def _create_row(self, layout, label):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{theme.TEXT_DIM};")
        val = QLabel("---")
        val.setAlignment(Qt.AlignRight)
        row.addWidget(lbl)
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _refresh(self):
        user = STATE.username()
        session = STATE.session_type
        theme_mode = STATE.theme

        from system.security_system import SEC

        risk = SEC.risk_level

        def set_s(lbl, text, ok=True):
            lbl.setText(text)
            if ok:
                lbl.setStyleSheet(f"color:{theme.ACCENT_GREEN}; font-weight:bold;")
            else:
                lbl.setStyleSheet(f"color:{theme.TEXT_DIM};")

        set_s(self.user_status, user if user else "guest")
        set_s(self.session_status, session)

        if risk == "HIGH":
            set_s(self.risk_status, risk, False)
            self.risk_status.setStyleSheet(
                f"color:{theme.ACCENT_RED}; font-weight:bold;"
            )
        elif risk == "MEDIUM":
            set_s(self.risk_status, risk, False)
            self.risk_status.setStyleSheet(
                f"color:{theme.ACCENT_AMBER}; font-weight:bold;"
            )
        else:
            set_s(self.risk_status, risk)

        set_s(self.theme_status, theme_mode)


def get_factory():
    return QVaultCoreApp
