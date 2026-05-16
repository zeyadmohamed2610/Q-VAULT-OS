import logging
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor

from resources.theme import THEME

logger = logging.getLogger(__name__)

class SnapPreviewOverlay(QWidget):
    """
    Floating semi-transparent ghost rectangle to preview snap results.
    Controlled by WindowManager logic via Desktop.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._target_rect = QRect()
        self._opacity = 0.0
        
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self.hide() # Ensure it's hidden by default until explicitly shown

    def show_preview(self, rect: QRect):
        if self._target_rect == rect and self.isVisible():
            return
            
        self._target_rect = rect
        self.setGeometry(rect)
        self.show()
        
        self.anim.stop()
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.4)
        self.anim.start()

    def hide_preview(self):
        if not self.isVisible() or self.anim.endValue() == 0.0: 
            return
        
        self.anim.stop()
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.0)
        
        # Disconnect previous finished signals to prevent multiple hides
        try: self.anim.finished.disconnect()
        except Exception as e:
            # Common in PyQt when a signal was not connected; logging as debug to avoid noise.
            logger.debug(f"SnapPreviewOverlay: Animation disconnect failed: {e}")
            
        self.anim.finished.connect(self.hide)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Premium Glow / Ghost effect
        color = QColor(THEME['primary_glow'])
        color.setAlpha(100)
        
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)
        
        # Subtle border
        color.setAlpha(200)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(color)
        painter.drawRoundedRect(self.rect().adjusted(2,2,-2,-2), 8, 8)
