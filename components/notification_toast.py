from assets.theme import *
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import QTimer, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QCursor
from system.notification_service import NotificationData, NotificationLevel

class NotificationToast(QFrame):
    """
    v1.0 Notification Toast.
    Features hover-pause, dynamic content updates, and fluid entry/exit animations.
    """
    dismissed = pyqtSignal()
    
    def __init__(self, data: NotificationData, parent=None):
        super().__init__(parent)
        self.notif_id = data.id
        self._data = data
        self._remaining_ms = 0
        self._is_dismissing = False
        
        # Determine auto-dismiss duration based on priority
        if data.level == NotificationLevel.INFO:
            self._duration_ms = 3000
        elif data.level == NotificationLevel.WARNING:
            self._duration_ms = 4000
        else: # DANGER
            self._duration_ms = 6000
            
        # Hover pause timer logic
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.setInterval(100) # Check every 100ms
        
        self._setup_ui()
        self.update_content(data)
        
        self.start_timer()

    def _setup_ui(self):
        self.setFixedWidth(320)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # Base styling
        self.setStyleSheet("""
            NotificationToast {
                background-color: rgba(20, 20, 25, 0.85);
                border-radius: 16px;
            }
            QLabel { background: transparent; color: white; font-family: 'Segoe UI'; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)
        
        # Header (Icon + Title + Close)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0,0,0,0)
        
        self.lbl_icon = QLabel()
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 12))
        
        self.lbl_title = QLabel()
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text_muted']};
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        self.btn_close.clicked.connect(self.dismiss)
        
        header_layout.addWidget(self.lbl_icon)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        
        layout.addLayout(header_layout)
        
        # Message
        self.lbl_message = QLabel()
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setFont(QFont("Segoe UI", 10))
        self.lbl_message.setStyleSheet("color: #ccc;")
        layout.addWidget(self.lbl_message)

    def update_content(self, data: NotificationData):
        """Allows updating the toast without recreating it (e.g., grouped spam)."""
        self._data = data
        
        # Update text
        self.lbl_title.setText(data.title.upper())
        self.lbl_message.setText(data.message)
        
        # Update colors and icons
        if data.level == NotificationLevel.INFO:
            color = THEME["primary_soft"]
            icon = "🔔"
        elif data.level == NotificationLevel.WARNING:
            color = THEME["warning"]
            icon = "⚠️"
        else:
            color = THEME["error_bright"]
            icon = "🚨"
            
        self.lbl_icon.setText(icon)
        self.lbl_title.setStyleSheet(f"color: {color};")
        self.setStyleSheet(f"""
            NotificationToast {{
                background-color: rgba(20, 20, 25, 0.85);
                border: 1px solid {color}55;
                border-radius: 16px;
            }}
            QLabel {{ background: transparent; font-family: 'Segoe UI'; }}
        """)
        
        # Reset timer on update
        self.start_timer()
        self.adjustSize()

    # --- Timer & Hover Logic ---
    
    def start_timer(self):
        self._remaining_ms = self._duration_ms
        self._timer.start()
        
    def _on_timeout(self):
        self._remaining_ms -= 100
        if self._remaining_ms <= 0:
            self._timer.stop()
            self.dismiss()
            
    def enterEvent(self, event):
        """Pause timer on hover."""
        if not self._is_dismissing:
            self._timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Resume timer when hover ends."""
        if not self._is_dismissing:
            self._timer.start()
        super().leaveEvent(event)

    # --- Animations ---

    def animate_entry(self, target_x: int, target_y: int):
        if hasattr(self, 'anim_group') and self.anim_group.state() == QPropertyAnimation.Running:
            self.anim_group.stop()
            
        self.show()
        self.setWindowOpacity(0.0)
        
        start_x = target_x + 50
        self.move(start_x, target_y)
        
        self.anim_group = QParallelAnimationGroup(self)
        
        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(400)
        pos_anim.setStartValue(QPoint(start_x, target_y))
        pos_anim.setEndValue(QPoint(target_x, target_y))
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        op_anim = QPropertyAnimation(self, b"windowOpacity")
        op_anim.setDuration(300)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        
        self.anim_group.addAnimation(pos_anim)
        self.anim_group.addAnimation(op_anim)
        self.anim_group.start()

    def animate_shift(self, target_y: int):
        """Smoothly moves the toast vertically when others are dismissed."""
        if hasattr(self, 'shift_anim') and self.shift_anim.state() == QPropertyAnimation.Running:
            self.shift_anim.stop()
            
        self.shift_anim = QPropertyAnimation(self, b"pos")
        self.shift_anim.setDuration(300)
        self.shift_anim.setEndValue(QPoint(self.x(), target_y))
        self.shift_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.shift_anim.start()

    def dismiss(self):
        if self._is_dismissing: return
        self._is_dismissing = True
        self._timer.stop()
        
        if hasattr(self, 'shift_anim') and self.shift_anim.state() == QPropertyAnimation.Running:
            self.shift_anim.stop()
        if hasattr(self, 'anim_group') and self.anim_group.state() == QPropertyAnimation.Running:
            self.anim_group.stop()
            
        self.out_anim_group = QParallelAnimationGroup(self)
        
        pos_anim = QPropertyAnimation(self, b"pos")
        pos_anim.setDuration(300)
        pos_anim.setEndValue(QPoint(self.x() + 30, self.y()))
        pos_anim.setEasingCurve(QEasingCurve.InCubic)
        
        op_anim = QPropertyAnimation(self, b"windowOpacity")
        op_anim.setDuration(250)
        op_anim.setEndValue(0.0)
        
        self.out_anim_group.addAnimation(pos_anim)
        self.out_anim_group.addAnimation(op_anim)
        self.out_anim_group.finished.connect(self.dismissed.emit)
        self.out_anim_group.start()
