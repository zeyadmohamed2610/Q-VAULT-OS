# =============================================================
#  boot_screen.py - Q-Vault OS  |  Premium Boot Screen
# =============================================================

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from assets import theme


_BOOT_LINES = [
    ("dim", "[    0.000000] Q-VAULT OS initializing..."),
    ("dim", "[    0.015000] Loading kernel modules..."),
    ("ok", "[    0.040000] [ OK ] Kernel initialized"),
    ("dim", "[    0.055000] Mounting virtual file system..."),
    ("ok", "[    0.085000] [ OK ] File system mounted"),
    ("dim", "[    0.110000] Starting security services..."),
    ("ok", "[    0.170000] [ OK ] Security engine ready"),
    ("dim", "[    0.230000] Initializing network stack..."),
    ("ok", "[    0.310000] [ OK ] Network interfaces up"),
    ("dim", "[    0.380000] Loading system services..."),
    ("ok", "[    0.450000] [ OK ] System services running"),
    ("dim", "[    0.520000] Starting desktop environment..."),
    ("ok", "[    0.620000] [ OK ] Desktop ready"),
    ("", ""),
    ("logo", " ███████╗      ██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗"),
    ("logo", "██╔════██╗     ██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝"),
    ("logo", "██║   ██║█████╗██║   ██║███████║██║   ██║██║     ██║   "),
    ("logo", "██║▄▄ ██║╚════╝╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║   "),
    ("logo", "╚██████╔╝       ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║   "),
    ("logo", " ╚══▀▀═╝         ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝   "),
    ("", ""),
    ("cyan", "        Q - V A U L T   S E C U R E   S Y S T E M"),
    ("dim", "Press any key or wait to continue..."),
]

_LINE_DELAY_MS = 70


class BootScreen(QWidget):
    boot_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_idx = 0
        self._done = False
        self.setStyleSheet("background: #020617;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(60, 40, 60, 40)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(2)
        self._content_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        outer.addLayout(self._content_layout)
        outer.addStretch()

        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 10)

        self._prog_bar = QLabel()
        self._prog_bar.setStyleSheet(
            f"color:{theme.PRIMARY}; font-family:'Consolas',monospace; font-size:11px;"
        )
        prog_row.addWidget(self._prog_bar)
        outer.addLayout(prog_row)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_anim.setDuration(300)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in_anim.start()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_line)
        self._timer.start(_LINE_DELAY_MS)

    def keyPressEvent(self, event):
        self._finish()

    def mousePressEvent(self, event):
        self._finish()

    def _next_line(self):
        if self._line_idx >= len(_BOOT_LINES):
            self._finish()
            return

        kind, text = _BOOT_LINES[self._line_idx]
        self._line_idx += 1

        self._content_layout.addWidget(self._make_line(kind, text))

        pct = int(self._line_idx / len(_BOOT_LINES) * 100)
        bar_filled = int(pct / 2)
        bar = "█" * bar_filled + "░" * (50 - bar_filled)
        self._prog_bar.setText(f"[{bar}] {pct}%")

    def _make_line(self, kind: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.PlainText)

        if kind == "ok":
            color = theme.PRIMARY
        elif kind == "logo":
            color = theme.PRIMARY
        elif kind == "dim":
            color = theme.TEXT_DIM
        elif kind == "cyan":
            color = theme.PRIMARY
        elif kind == "brand":
            color = theme.PRIMARY
        else:
            color = theme.TEXT_DIM

        font_size = 12 if kind in ("brand", "logo") else 11
        font_weight = "bold" if kind in ("brand", "logo") else "normal"
        lbl.setStyleSheet(
            f"color:{color}; font-family:'Consolas','Courier New',monospace;"
            f"font-size:{font_size}px; font-weight:{font_weight}; background:transparent;"
        )
        return lbl

    def _finish(self):
        if self._done:
            return
        self._done = True
        self._timer.stop()

        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(200)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out_anim.finished.connect(self.boot_complete.emit)
        self._fade_out_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#020617"))
        grad.setColorAt(0.5, QColor("#0f172a"))
        grad.setColorAt(1.0, QColor("#020617"))
        painter.fillRect(self.rect(), grad)

        painter.setPen(QPen(QColor(34, 197, 94, 8), 1))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 40):
            painter.drawLine(0, y, self.width(), y)

        painter.setPen(QColor(34, 197, 94, 40))
        painter.drawText(60, self.height() - 26, "Q-VAULT // secure boot")
