import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from resources.theme import THEME, FONT

logger = logging.getLogger(__name__)

class ToastNotification(QFrame):
    finished = pyqtSignal(object)

    def __init__(self, title, message, level="info", parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.level = level
        
        # Color based on level
        accent = THEME['primary_glow']
        if level == "error": accent = THEME['accent_error']
        elif level == "warning": accent = THEME['accent_warning']
        elif level == "success": accent = THEME['success']

        self.setStyleSheet(f"""
            QFrame {{
                background: {THEME['bg_darker']};
                border: 1px solid {THEME['border_subtle']};
                border-left: 4px solid {accent};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)

        header = QHBoxLayout()
        icon_map = {"info": "ℹ️", "error": "⚠️", "warning": "🔸", "success": "✅"}
        icon = QLabel(icon_map.get(level, "ℹ️"))
        icon.setStyleSheet("background: transparent;")
        header.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(FONT['family'], 10, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont(FONT['family'], 9))
        msg_lbl.setStyleSheet(f"color: {THEME['text_main']}; background: transparent;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        # Shadow effect
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide_and_destroy)
        self.timer.start(5000)

        # Animation state
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.setWindowOpacity(0.0)

    def show_animated(self, start_pos: QPoint):
        self.move(start_pos)
        self.show()
        
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(400)
        self._anim.setStartValue(QPoint(start_pos.x() + 350, start_pos.y()))
        self._anim.setEndValue(start_pos)
        self._anim.start()

        self._opacity_anim.setDuration(300)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

    def hide_and_destroy(self):
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(300)
        self._anim.setEndValue(QPoint(self.x() + 350, self.y()))
        self._anim.finished.connect(lambda: self.finished.emit(self))
        self._anim.start()

        self._opacity_anim.setDuration(300)
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

class NotificationManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.toasts = []
        
        # Subscribe to global events
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.subscribe(SystemEvent.EVT_INFO, self._on_info)
        EVENT_BUS.subscribe(SystemEvent.EVT_WARNING, self._on_warning)
        EVENT_BUS.subscribe(SystemEvent.EVT_ERROR, self._on_error)

    def notify(self, title, message, level="info"):
        toast = ToastNotification(title, message, level, self.parent())
        toast.finished.connect(self._on_toast_finished)
        self.toasts.append(toast)
        self._reposition_toasts()
        
        # Calculate target position (bottom right)
        parent_rect = self.parent().rect()
        target_y = parent_rect.height() - 60 - (len(self.toasts) * 90)
        target_x = parent_rect.width() - 340
        toast.show_animated(QPoint(target_x, target_y))

    def _reposition_toasts(self):
        parent_rect = self.parent().rect()
        for i, toast in enumerate(reversed(self.toasts)):
            target_y = parent_rect.height() - 60 - ((i + 1) * 90)
            target_x = parent_rect.width() - 340
            # Slide them down smoothly
            anim = QPropertyAnimation(toast, b"pos")
            anim.setDuration(300)
            anim.setEndValue(QPoint(target_x, target_y))
            anim.start()

    def _on_toast_finished(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
        toast.deleteLater()
        self._reposition_toasts()

    def _on_info(self, payload):
        data = payload.data if hasattr(payload, 'data') else payload
        self.notify(data.get("title", "Info"), data.get("message", ""), "info")

    def _on_warning(self, payload):
        data = payload.data if hasattr(payload, 'data') else payload
        self.notify(data.get("title", "Warning"), data.get("message", ""), "warning")

    def _on_error(self, payload):
        data = payload.data if hasattr(payload, 'data') else payload
        self.notify(data.get("title", "Error"), data.get("message", ""), "error")
