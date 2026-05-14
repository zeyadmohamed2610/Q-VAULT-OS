from __future__ import annotations
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QFont

class TrayIconButton(QPushButton):
    """
    28×28 rounded icon button for the system tray zone.
    Loads a real SVG icon and renders it as QIcon.
    States: active (cyan dot), inactive (muted dot).
    """
    def __init__(self, icon_svg: str = "", tooltip: str = "", parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self._active   = True
        self._icon_svg = icon_svg

        # Load real SVG icon
        if icon_svg:
            from pathlib import Path
            from PyQt5.QtSvg import QSvgRenderer
            from PyQt5.QtGui import QPixmap, QPainter, QIcon
            from PyQt5.QtCore import QSize
            svg_path = Path(icon_svg)
            if not svg_path.is_absolute():
                # resolve relative to project root
                import os
                svg_path = Path(os.path.dirname(os.path.dirname(
                    os.path.dirname(__file__)))) / icon_svg
            if svg_path.exists():
                pix = QPixmap(20, 20)
                pix.fill(Qt.transparent)
                renderer = QSvgRenderer(str(svg_path))
                p = QPainter(pix)
                p.setRenderHint(QPainter.Antialiasing)
                renderer.render(p)
                p.end()
                self.setIcon(QIcon(pix))
                self.setIconSize(QSize(20, 20))

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                outline: none;
                border-radius: 6px;
            }
            QPushButton:hover  { background: rgba(84,177,198,0.12); }
            QPushButton:pressed{ background: rgba(84,177,198,0.22); }
            QPushButton:checked{ background: rgba(84,177,198,0.18); }
        """)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(84, 177, 198) if self._active else QColor(74, 104, 128)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(20, 20, 6, 6)
        painter.end()
