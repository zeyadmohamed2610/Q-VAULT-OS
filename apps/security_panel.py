# =============================================================
#  security_panel.py — Q-Vault OS  |  Security Panel (Finalized)
#
#  Finalization fix:
#    ✓ _update_risk caches the last displayed level and returns
#      immediately if unchanged — eliminates 12 redundant
#      setStyleSheet calls that fired on every SEC event
# =============================================================

import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from system.security_system import (
    SEC, RISK_LOW, RISK_MEDIUM, RISK_HIGH,
    EVT_INTRUSION, EVT_BUTTON, EVT_PROCESS, EVT_CLEARED
)
from assets import theme


RISK_COLORS = {
    RISK_LOW:    theme.ACCENT_GREEN,
    RISK_MEDIUM: theme.ACCENT_AMBER,
    RISK_HIGH:   theme.ACCENT_RED,
}

STYLE = f"""
    QWidget#SecurityPanel {{ background: {theme.BG_WINDOW}; }}
    QLabel#SecTitle {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 12px; font-weight: bold;
        padding: 4px 8px;
    }}
    QLabel#RiskLabel {{
        font-family: 'Consolas', monospace;
        font-size: 22px; font-weight: bold;
        padding: 8px 20px; border-radius: 6px;
    }}
    QTextEdit#SecLog {{
        background: #080c10;
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        border: none; padding: 6px;
    }}
    QPushButton#SecBtn {{
        background: transparent;
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 4px;
        padding: 5px 14px;
        font-family: 'Consolas', monospace;
        font-size: 11px;
    }}
    QPushButton#SecBtn:hover {{
        background: {theme.BG_HOVER};
        color: {theme.TEXT_PRIMARY};
    }}
    QPushButton#ClearBtn {{
        background: {theme.ACCENT_GREEN};
        color: {theme.BG_DARK};
        border: none; border-radius: 4px;
        padding: 5px 16px;
        font-family: 'Consolas', monospace;
        font-size: 11px; font-weight: bold;
    }}
    QPushButton#ClearBtn:hover {{ background: #44ffaa; }}
"""


class SecurityPanel(QWidget):

    # Emitted when intrusion arrives — Desktop shows the SecurityAlert overlay
    intrusion_detected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecurityPanel")
        self.setStyleSheet(STYLE)

        # Cache: last risk level we actually rendered.
        # _update_risk returns immediately if unchanged → zero wasted repaints.
        self._displayed_risk: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_risk_gauge())
        root.addWidget(self._make_log(), stretch=1)
        root.addWidget(self._make_controls())

        SEC.subscribe(self._on_sec_event)
        self._load_existing_log()

    def closeEvent(self, event):
        SEC.unsubscribe(self._on_sec_event)
        super().closeEvent(event)

    # ── SEC observer ──────────────────────────────────────────

    def _on_sec_event(self, entry: dict):
        self._append_entry(entry)
        self._update_risk(entry["risk_after"])
        if entry["event_type"] == EVT_INTRUSION:
            self.intrusion_detected.emit(entry)

    # ── Header ────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-bottom:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        title = QLabel("🔐  Security Monitor")
        title.setObjectName("SecTitle")
        row.addWidget(title)
        row.addStretch()
        return bar

    # ── Risk gauge ────────────────────────────────────────────

    def _make_risk_gauge(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-bottom:1px solid {theme.BORDER_DIM};"
        )
        col = QVBoxLayout(frame)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(16)

        self._level_widgets: dict[str, QLabel] = {}
        for level in (RISK_LOW, RISK_MEDIUM, RISK_HIGH):
            lbl = QLabel(level)
            lbl.setObjectName("RiskLabel")
            lbl.setAlignment(Qt.AlignCenter)
            self._level_widgets[level] = lbl
            row.addWidget(lbl)

        col.addLayout(row)

        self._risk_text = QLabel(f"Current Risk: {SEC.risk_level}")
        self._risk_text.setAlignment(Qt.AlignCenter)
        self._risk_text.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:11px; font-family:'Consolas',monospace;"
        )
        col.addWidget(self._risk_text)

        # Apply initial state (forces a full render on first open)
        self._update_risk(SEC.risk_level)
        return frame

    def _update_risk(self, level: str):
        """
        Repaint the risk gauge for `level`.
        Returns immediately if the level hasn't changed — prevents
        12 redundant setStyleSheet calls on every SEC event.
        """
        if level == self._displayed_risk:
            return
        self._displayed_risk = level

        for lvl, widget in self._level_widgets.items():
            color = RISK_COLORS[lvl]
            if lvl == level:
                widget.setStyleSheet(
                    f"color:{theme.BG_DARK}; background:{color};"
                    f"font-family:'Consolas',monospace; font-size:22px;"
                    f"font-weight:bold; padding:8px 20px; border-radius:6px;"
                )
            else:
                widget.setStyleSheet(
                    f"color:{color}; background:transparent;"
                    f"font-family:'Consolas',monospace; font-size:22px;"
                    f"font-weight:bold; padding:8px 20px; border-radius:6px;"
                    f"border:1px solid {theme.BORDER_DIM};"
                )
        self._risk_text.setText(f"Current Risk: {level}")

    # ── Event log ─────────────────────────────────────────────

    def _make_log(self) -> QTextEdit:
        self._log = QTextEdit()
        self._log.setObjectName("SecLog")
        self._log.setReadOnly(True)
        return self._log

    def _load_existing_log(self):
        for entry in SEC.get_log():
            self._append_entry(entry)
        self._update_risk(SEC.risk_level)

    def _append_entry(self, entry: dict):
        evt  = entry["event_type"]
        src  = entry["source"]
        det  = entry["detail"]
        ts   = entry["timestamp"]
        risk = entry["risk_after"]

        icon_color = {
            EVT_INTRUSION: ("🚨", theme.ACCENT_RED),
            EVT_BUTTON:    ("🔘", theme.ACCENT_AMBER),
            EVT_PROCESS:   ("⚠",  theme.ACCENT_AMBER),
            EVT_CLEARED:   ("✓",  theme.ACCENT_GREEN),
            "SYSTEM_BOOT": ("⚙",  theme.TEXT_DIM),
        }.get(evt, ("·", theme.TEXT_DIM))
        icon, color = icon_color

        self._log.append(
            f'<span style="color:{theme.TEXT_DIM};">[{_e(ts)}]  </span>'
            f'<span style="color:{color};font-weight:bold;">{icon} {_e(evt)}</span>'
            f'<span style="color:{theme.TEXT_DIM};">  ← {_e(src)}</span><br>'
            f'<span style="color:{theme.TEXT_PRIMARY};">    {_e(det)}</span>'
            f'<span style="color:{RISK_COLORS[risk]};"> → {risk}</span>'
        )
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )

    # ── Controls ──────────────────────────────────────────────

    def _make_controls(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-top:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)

        btn_clear = QPushButton("✓  Clear Risk")
        btn_clear.setObjectName("ClearBtn")
        btn_clear.clicked.connect(SEC.clear_risk)
        row.addWidget(btn_clear)

        btn_log = QPushButton("Clear Log View")
        btn_log.setObjectName("SecBtn")
        btn_log.clicked.connect(self._log.clear)
        row.addWidget(btn_log)

        row.addStretch()

        btn_test = QPushButton("🧪 Test Intrusion")
        btn_test.setObjectName("SecBtn")
        btn_test.clicked.connect(lambda: SEC.report(
            EVT_INTRUSION, source="manual_test",
            detail="Test intrusion injected from Security panel.",
            escalate=True,
        ))
        row.addWidget(btn_test)

        return bar


def _e(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# =============================================================
#  SecurityAlert — dismissable banner shown on intrusion
# =============================================================

class SecurityAlert(QWidget):
    """
    Floating banner shown at the top-centre of the Desktop
    when INTRUSION_DETECTED fires.
    Auto-dismisses after 8 seconds.
    """

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        box = QWidget()
        box.setStyleSheet(f"""
            background: rgba(20, 5, 5, 235);
            border: 2px solid {theme.ACCENT_RED};
            border-radius: 8px;
        """)
        col = QVBoxLayout(box)
        col.setContentsMargins(20, 14, 20, 14)
        col.setSpacing(6)

        hdr = QHBoxLayout()
        icon_lbl = QLabel("🚨")
        icon_lbl.setStyleSheet("font-size:28px; background:transparent;")
        title_lbl = QLabel("INTRUSION DETECTED")
        title_lbl.setStyleSheet(
            f"color:{theme.ACCENT_RED}; font-size:18px; font-weight:bold;"
            f"font-family:'Consolas',monospace; background:transparent;"
        )
        dismiss_btn = QPushButton("✕  Dismiss")
        dismiss_btn.setStyleSheet(f"""
            background:{theme.ACCENT_RED}; color:white; border:none;
            border-radius:4px; padding:5px 16px;
            font-family:'Consolas',monospace; font-weight:bold;
        """)
        dismiss_btn.clicked.connect(self._dismiss)
        hdr.addWidget(icon_lbl)
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        hdr.addWidget(dismiss_btn)

        detail_lbl = QLabel(
            f"Source:  {entry.get('source', 'unknown')}\n"
            f"{entry.get('detail', '')}\n"
            f"Risk Level  →  {entry.get('risk_after', '?')}"
        )
        detail_lbl.setStyleSheet(
            f"color:{theme.TEXT_PRIMARY}; font-size:12px;"
            f"font-family:'Consolas',monospace; background:transparent;"
        )

        col.addLayout(hdr)
        col.addWidget(detail_lbl)
        root.addWidget(box)

        QTimer.singleShot(8000, self._dismiss)

    def _dismiss(self):
        self.hide()
        self.deleteLater()

    def show_on(self, desktop: QWidget):
        self.setParent(desktop)
        self.setWindowFlags(Qt.FramelessWindowHint)
        w = min(560, desktop.width() - 40)
        self.setFixedWidth(w)
        self.adjustSize()
        self.move((desktop.width() - w) // 2, 60)
        self.show()
        self.raise_()
