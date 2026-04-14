# =============================================================
#  os_window.py — Floating window
#  FIXES (v2): bad imports, close() signal stacking, _scale_anim crash,
#              minimize signal stacking, show() flicker on rapid open
# =============================================================

from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from assets import theme


class OSWindow(QWidget):
    """
    Borderless floating window — the base for every app in Q-Vault OS.
    Parent is always the Desktop widget so windows stay on the canvas.
    """

    TITLE_H = 32

    def __init__(self, title: str, emoji: str, content: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("OSWindow")
        self.setMinimumSize(340, 240)
        self.resize(580, 400)
        self.setStyleSheet(theme.WINDOW_STYLE)

        self._dragging = False
        self._drag_offset = QPoint()
        self._maximized = False
        self._pre_max_geometry = None
        self._closing = False  # guard against double-close

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = self._make_title_bar(emoji, title)
        root.addWidget(self._title_bar)

        content.setParent(self)
        root.addWidget(content, stretch=1)

        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip_row.addWidget(QSizeGrip(self))
        grip_row.setContentsMargins(0, 0, 2, 2)
        root.addLayout(grip_row)

        self.set_focused(False)

        # Opacity / fade animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(theme.ANIMATION_NORMAL_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

    # ── Internal helper: safely disconnect all finished slots ─
    def _disconnect_fade_finished(self):
        try:
            self._fade_anim.finished.disconnect()
        except TypeError:
            pass  # No connections — safe

    # ── Show with fade ────────────────────────────────────────
    def show(self):
        self._closing = False
        self._disconnect_fade_finished()
        if self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        super().show()
        self._opacity_effect.setOpacity(0.0)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    # ── Animate close (× button) ──────────────────────────────
    def _animate_close(self):
        if self._closing:
            return
        self._closing = True
        self._disconnect_fade_finished()
        if self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._do_close)
        self._fade_anim.start()

    def _do_close(self):
        self._disconnect_fade_finished()
        super().close()

    # ── Title bar ─────────────────────────────────────────────
    def _make_title_bar(self, emoji: str, title: str) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(self.TITLE_H)

        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 0, 8, 0)
        row.setSpacing(5)

        btn_close = QPushButton()
        btn_close.setObjectName("BtnClose")
        btn_close.setToolTip("Close")
        btn_close.clicked.connect(self._animate_close)

        btn_min = QPushButton()
        btn_min.setObjectName("BtnMinimize")
        btn_min.setToolTip("Minimize")
        btn_min.clicked.connect(self._minimize)

        btn_max = QPushButton()
        btn_max.setObjectName("BtnMaximize")
        btn_max.setToolTip("Maximize")
        btn_max.clicked.connect(self._toggle_maximize)

        lbl = QLabel(f"{emoji}  {title}")
        lbl.setObjectName("TitleLabel")

        row.addWidget(btn_close)
        row.addWidget(btn_min)
        row.addWidget(btn_max)
        row.addWidget(lbl)
        row.addStretch()

        return bar

    # ── Focus state ───────────────────────────────────────────
    def set_focused(self, focused: bool):
        v = "true" if focused else "false"
        self.setProperty("focused", v)
        self._title_bar.setProperty("focused", v)
        self.setStyleSheet(theme.WINDOW_STYLE)

    # ── Minimize with fade ────────────────────────────────────
    def _minimize(self):
        self._disconnect_fade_finished()
        if self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._finish_minimize)
        self._fade_anim.start()

    def _finish_minimize(self):
        self._disconnect_fade_finished()
        self.hide()
        self._opacity_effect.setOpacity(1.0)

    # ── Maximize / restore ────────────────────────────────────
    def _toggle_maximize(self):
        if self._maximized:
            self._restore()
        else:
            self._maximize()

    def _maximize(self):
        if not self.parent():
            return
        from components.taskbar import Taskbar

        self._pre_max_geometry = self.geometry()
        self._geometry_anim = QPropertyAnimation(self, b"geometry")
        self._geometry_anim.setDuration(150)
        self._geometry_anim.setStartValue(self.geometry())
        usable_h = self.parent().height() - Taskbar.TASKBAR_HEIGHT
        self._geometry_anim.setEndValue(
            QRect(0, 0, self.parent().width(), usable_h)
        )
        self._geometry_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._geometry_anim.start()
        self._maximized = True

    def _restore(self):
        if self._pre_max_geometry:
            self._geometry_anim = QPropertyAnimation(self, b"geometry")
            self._geometry_anim.setDuration(150)
            self._geometry_anim.setStartValue(self.geometry())
            self._geometry_anim.setEndValue(self._pre_max_geometry)
            self._geometry_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._geometry_anim.start()
        self._maximized = False

    # ── Mouse events ──────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.raise_()
            self._notify_focus()
            if event.pos().y() <= self.TITLE_H and not self._maximized:
                self._dragging = True
                self._drag_offset = event.globalPos() - self.pos()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= self.TITLE_H:
            self._toggle_maximize()
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            target = event.globalPos() - self._drag_offset
            self.move(self._clamp(target))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    # ── Clamp position to desktop bounds ──────────────────────
    def _clamp(self, global_pos: QPoint) -> QPoint:
        if not self.parent():
            return global_pos
        from components.taskbar import Taskbar

        dw = self.parent().width()
        dh = self.parent().height() - Taskbar.TASKBAR_HEIGHT
        local = self.parent().mapFromGlobal(global_pos)
        x = max(0, min(local.x(), dw - self.width()))
        y = max(0, min(local.y(), dh - self.height()))
        return self.parent().mapToGlobal(QPoint(x, y))

    # ── Notify Desktop of focus change ────────────────────────
    def _notify_focus(self):
        p = self.parent()
        if p and hasattr(p, "on_window_focused"):
            p.on_window_focused(self)
