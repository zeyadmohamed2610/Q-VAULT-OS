from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from core.event_bus import EVENT_BUS, SystemEvent
from system.notification_service import NotificationData
from components.notification_toast import NotificationToast
import logging

logger = logging.getLogger(__name__)

class NotificationContainer(QWidget):
    """
    v1.0 Notification Director.
    Manages stacking, queueing, and lifecycle of NotificationToasts.
    """
    MAX_VISIBLE = 3
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Act as an overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Sizing and positioning: Top Right
        self.setFixedWidth(340)
        # We need a tall enough widget to hold toasts and slide them
        self.setFixedHeight(800)
        
        self._active_toasts = []  # List of NotificationToast
        self._queue = []          # List of NotificationData
        
        EVENT_BUS.subscribe(SystemEvent.NOTIFICATION_SENT, self._on_system_event)
        
        if parent:
            parent.installEventFilter(self)
            
    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.setup_position(obj.rect())
        return super().eventFilter(obj, event)
        
    def setup_position(self, screen_rect: QRect):
        """Aligns the container to the top right of the given screen/parent rect."""
        margin_right = 20
        margin_top = 40
        x = screen_rect.width() - self.width() - margin_right
        y = margin_top
        self.move(x, y)
        self.show()

    def _on_system_event(self, payload):
        data = payload.data.get("notification")
        if isinstance(data, NotificationData):
            self.show_notification(data)
                
    def show_notification(self, data: NotificationData):
        # 1. Check if we should update an existing toast
        for toast in self._active_toasts:
            if toast.notif_id == data.id:
                toast.update_content(data)
                return
                
        # 2. Check if we need to queue
        if len(self._active_toasts) >= self.MAX_VISIBLE:
            from system.notification_service import NotificationLevel
            if data.level == NotificationLevel.DANGER:
                # Priority override: dismiss oldest non-danger toast to make room
                for t in self._active_toasts:
                    if t._data.level != NotificationLevel.DANGER:
                        t.dismiss()
                        break
                # Force render immediately
                self._render_toast(data)
            else:
                self._queue.append(data)
            return
            
        # 3. Create and render
        self._render_toast(data)

    def _render_toast(self, data: NotificationData):
        toast = NotificationToast(data, parent=self)
        toast.dismissed.connect(lambda t=toast: self._on_toast_dismissed(t))
        
        # Calculate Y position based on current active toasts
        # Each toast is roughly 80-100px tall. We calculate dynamically.
        y_offset = 0
        for t in self._active_toasts:
            y_offset += t.height() + 10  # 10px spacing
            
        toast.move(self.width(), y_offset) # Start off-screen right
        toast.show()
        
        self._active_toasts.append(toast)
        
        # Animate entry
        target_x = self.width() - toast.width()
        toast.animate_entry(target_x, y_offset)

    def _on_toast_dismissed(self, toast: NotificationToast):
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
            toast.deleteLater()
            
        self._restack()
        
        # Pull from queue if available
        if self._queue and len(self._active_toasts) < self.MAX_VISIBLE:
            next_data = self._queue.pop(0)
            self._render_toast(next_data)

    def _restack(self):
        """Smoothly shifts remaining toasts upwards."""
        y_offset = 0
        for toast in self._active_toasts:
            toast.animate_shift(y_offset)
            y_offset += toast.height() + 10
