from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtProperty, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen

class ToggleSwitch(QWidget):
    """
    Sovereign Animated Toggle Switch.
    Modern pill-shaped sliding switch with smooth animations.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, active_color="#00f0ff", bg_color="#243558"):
        super().__init__(parent)
        self.setFixedSize(44, 22)
        self.setCursor(Qt.PointingHandCursor)
        
        self._active = True
        self._active_color = QColor(active_color)
        self._bg_color = QColor(bg_color)
        self._circle_color = QColor("#ffffff")
        
        # Knob position (0.0 to 1.0)
        self._handle_pos = 1.0
        
        self._anim = QPropertyAnimation(self, b"handle_pos")
        self._anim.setDuration(200)

    @pyqtProperty(float)
    def handle_pos(self):
        return self._handle_pos

    @handle_pos.setter
    def handle_pos(self, pos):
        self._handle_pos = pos
        self.update()

    def is_checked(self):
        return self._active

    def set_checked(self, checked):
        if self._active == checked: return
        self._active = checked
        self._anim.stop()
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self.toggled.emit(checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_checked(not self._active)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Background Pill (padded to fit glow)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        p.setPen(Qt.NoPen)
        
        # Interpolate background color
        bg = self._active_color if self._active else self._bg_color
        p.setBrush(bg)
        p.drawRoundedRect(rect, rect.height()/2, rect.height()/2)
        
        # Glow (if active)
        if self._active:
            p.setBrush(QColor(self._active_color.red(), self._active_color.green(), self._active_color.blue(), 40))
            p.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), self.height()/2 + 2, self.height()/2 + 2)

        # Handle (Knob)
        margin = 4
        handle_size = self.height() - (margin * 2)
        # Calculate horizontal position
        x_start = margin
        x_end = self.width() - handle_size - margin
        current_x = x_start + (x_end - x_start) * self._handle_pos
        
        p.setBrush(self._circle_color)
        p.drawEllipse(QPointF(current_x + handle_size/2, self.height()/2), handle_size/2, handle_size/2)
        p.end()
