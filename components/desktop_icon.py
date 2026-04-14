# =============================================================
#  desktop_icon.py - Premium Desktop Icons
# =============================================================

import os

from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QPainter, QTransform
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from assets import theme
from system.audit_logger import AUDIT, AuditEventType, AuditSeverity


class DesktopIcon(QWidget):
    """
    Premium desktop icon with smooth hover/click animations.
    """

    opened = pyqtSignal(str)

    CELL_W = 76
    CELL_H = 84

    def __init__(
        self,
        name: str,
        emoji: str,
        icon_asset: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.name = name
        self.setObjectName("DesktopIcon")
        self.setFixedSize(self.CELL_W, self.CELL_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._base_transform = QTransform()
        self._current_scale = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignCenter)

        icon_path = ""
        if icon_asset:
            base = os.path.dirname(os.path.dirname(__file__))
            icon_path = os.path.join(base, "assets", icon_asset)

        loaded = False
        if icon_path and os.path.exists(icon_path):
            if icon_path.lower().endswith(".svg"):
                try:
                    pix = QPixmap(icon_path)
                    if not pix.isNull():
                        pix = pix.scaled(
                            36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self._icon_lbl.setPixmap(pix)
                        loaded = True
                except Exception:
                    pass
            else:
                try:
                    pix = QPixmap(icon_path).scaled(
                        34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    if not pix.isNull():
                        self._icon_lbl.setPixmap(pix)
                        loaded = True
                except Exception:
                    pass

        if not loaded:
            self._icon_lbl.setText(emoji)
            self._icon_lbl.setObjectName("IconEmoji")

        self._text_lbl = QLabel(name)
        self._text_lbl.setObjectName("IconLabel")
        self._text_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl.setWordWrap(True)

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._text_lbl)

        self.setStyleSheet(theme.ICON_STYLE)
        self._setup_animations()

    def _setup_animations(self):
        self._scale_anim = QPropertyAnimation(self, b"geometry")
        self._scale_anim.setDuration(100)
        self._scale_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _animate_scale(self, target_scale: float):
        if self._scale_anim.state() == QPropertyAnimation.Running:
            self._scale_anim.stop()

        current_geom = self.geometry()
        w = int(self.CELL_W * target_scale)
        h = int(self.CELL_H * target_scale)
        x = current_geom.x() + (current_geom.width() - w) // 2
        y = current_geom.y() + (current_geom.height() - h) // 2

        self._scale_anim.setStartValue(current_geom)
        self._scale_anim.setEndValue(self._create_geometry(x, y, w, h))
        self._scale_anim.start()
        self._current_scale = target_scale

    def _create_geometry(self, x: int, y: int, w: int, h: int):
        from PyQt5.QtCore import QRect

        return QRect(x, y, w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_scale(0.95)
            self.setStyleSheet(theme.ICON_STYLE_PRESSED)
            from core.system_state import STATE

            AUDIT.log(
                AuditEventType.PROCESS_START,
                STATE.username(),
                f"desktop_icon:{self.name}",
                "press",
                "success",
                detail=f"User clicked on desktop icon: {self.name}",
            )
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._animate_scale(1.0)
            self.setStyleSheet(theme.ICON_STYLE)
            pos = event.pos()
            if self.rect().contains(pos):
                from core.system_state import STATE

                AUDIT.log(
                    AuditEventType.PROCESS_START,
                    STATE.username(),
                    f"desktop_icon:{self.name}",
                    "launch",
                    "success",
                    detail=f"User single-clicked on desktop icon: {self.name}",
                )
                self.opened.emit(self.name)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            from core.system_state import STATE

            AUDIT.log(
                AuditEventType.PROCESS_START,
                STATE.username(),
                f"desktop_icon:{self.name}",
                "launch",
                "success",
                detail=f"User double-clicked on desktop icon: {self.name}",
            )
            self.opened.emit(self.name)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(theme.ICON_STYLE_HOVER)
        self._animate_scale(1.05)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(theme.ICON_STYLE)
        self._animate_scale(1.0)
        super().leaveEvent(event)
