# =============================================================
#  notification_system.py — Q-Vault OS  |  Notifications
#
#  Toast-style notifications that appear in the bottom-right
#  corner of the desktop and auto-dismiss after a timeout.
#
#  Usage (from anywhere):
#    from system.notification_system import NOTIFY
#    NOTIFY.send("Title", "Message body", level="info")
#
#  Levels:  info | success | warning | danger
#  The Desktop must call NOTIFY.set_parent(desktop_widget)
#  once so the toasts know where to render.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

from assets import theme


_LEVEL_COLORS = {
    "info": (theme.ACCENT_CYAN, "ℹ"),
    "success": (theme.ACCENT_GREEN, "✓"),
    "warning": (theme.ACCENT_AMBER, "⚠"),
    "danger": (theme.ACCENT_RED, "🚨"),
}

_AUTO_DISMISS_MS = 5000  # 5 seconds
_TOAST_WIDTH = 320
_TOAST_SPACING = 8


class Toast(QWidget):
    """Single toast notification widget."""

    def __init__(self, title: str, body: str, level: str, on_close, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_TOAST_WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # type: ignore
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # type: ignore

        color, icon = _LEVEL_COLORS.get(level, _LEVEL_COLORS["info"])

        # ── Card ──────────────────────────────────────────────
        card = QWidget(self)
        card.setStyleSheet(f"""
            background: rgba(17, 24, 32, 230);
            border: 1px solid {color};
            border-radius: 6px;
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"color:{color}; font-size:14px; background:transparent;"
        )

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color:{color}; font-family:'Consolas',monospace;"
            f"font-size:12px; font-weight:bold; background:transparent;"
        )

        close_btn = QPushButton("×")
        close_btn.setStyleSheet(f"""
            background:transparent; color:{theme.TEXT_DIM};
            border:none; font-size:16px; padding:0 2px;
        """)
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self._dismiss)

        header.addWidget(icon_lbl)
        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # Body
        if body:
            body_lbl = QLabel(body)
            body_lbl.setWordWrap(True)
            body_lbl.setStyleSheet(
                f"color:{theme.TEXT_DIM}; font-family:'Consolas',monospace;"
                f"font-size:11px; background:transparent;"
            )
            card_layout.addWidget(body_lbl)

        # Fit card to content
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.adjustSize()

        self._on_close = on_close

        # Auto-dismiss timer
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)
        self._auto_timer.start(_AUTO_DISMISS_MS)

    def show_fade(self):
        self.show()

    def _dismiss(self):
        self._auto_timer.stop()
        self._cleanup()

    def _cleanup(self):
        if self._on_close:
            self._on_close(self)
        self.hide()
        self.deleteLater()


class NotificationManager:
    """
    Singleton notification manager.
    Call NOTIFY.set_parent(desktop) once at startup.
    Then call NOTIFY.send() from anywhere.
    """

    def __init__(self):
        self._parent: QWidget | None = None
        self._queue: list[dict] = []
        self._active: list[Toast] = []

    def set_parent(self, parent: QWidget):
        self._parent = parent

    def send(self, title: str, body: str = "", level: str = "info") -> None:
        """
        Show a toast. If no parent is set yet, queues it.
        level: "info" | "success" | "warning" | "danger"
        """
        if self._parent is None:
            self._queue.append({"title": title, "body": body, "level": level})
            return
        self._show(title, body, level)

    def flush_queue(self):
        """Call after set_parent() to display any queued notifications."""
        for item in self._queue:
            self._show(item["title"], item["body"], item["level"])
        self._queue.clear()

    def _show(self, title: str, body: str, level: str):
        if self._parent is None:
            return
        toast = Toast(
            title=title,
            body=body,
            level=level,
            on_close=self._on_toast_closed,
            parent=self._parent,
        )
        self._active.append(toast)
        self._reposition()
        toast.show_fade()

    def _on_toast_closed(self, toast: Toast):
        if toast in self._active:
            self._active.remove(toast)
        self._reposition()

    def _reposition(self):
        if not self._parent:
            return
        from components.taskbar import Taskbar

        right_margin = 16
        bottom_margin = Taskbar.TASKBAR_HEIGHT + 10
        pw = self._parent.width()
        ph = self._parent.height()

        y = ph - bottom_margin
        for toast in reversed(self._active):
            toast.adjustSize()
            x = pw - _TOAST_WIDTH - right_margin
            y -= toast.height() + _TOAST_SPACING
            toast.move(x, y)
            toast.raise_()


# ── Module singleton ──────────────────────────────────────────
NOTIFY = NotificationManager()
