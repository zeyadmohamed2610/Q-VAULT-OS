from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint
from assets.theme import THEME

class DesktopIcon(QWidget):
    def __init__(self, name, icon, parent=None):
        super().__init__(parent)

        self.name = name
        self.setFixedSize(80, 90)

        self._dragging = False
        self._drag_pos = QPoint()
        self.selected = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(icon.pixmap(48, 48))
        self.icon_lbl.setAlignment(Qt.AlignCenter)

        self.text_lbl = QLabel(name)
        self.text_lbl.setAlignment(Qt.AlignCenter)
        self.text_lbl.setStyleSheet("color: white; font-weight: bold;")

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.text_lbl)

        self.setStyleSheet("""
            DesktopIcon { background: transparent; border-radius: 8px; }
            DesktopIcon:hover { background: rgba(0, 230, 255, 0.1); border: 1px solid rgba(0, 230, 255, 0.2); }
        """)

    def set_selected(self, state: bool):
        self.selected = state
        if state:
            self.setStyleSheet(f"background-color: rgba(0,170,255,0.3); border: 1px solid {THEME['primary_glow']}; border-radius: 6px;")
        else:
            self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = self.mapToParent(event.pos() - self._drag_pos)
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        
        # Grid Snap System
        grid_x = max(0, round(self.x() / 90) * 90)
        grid_y = max(0, round(self.y() / 90) * 90)
        
        # Collision Detection (USER: don't put icon on another icon)
        parent = self.parent()
        if parent:
            for other in parent.findChildren(DesktopIcon):
                if other != self and other.pos() == QPoint(grid_x, grid_y):
                    # Collision! Revert to original if we had it, or just shift slightly
                    # For now, revert to old grid pos
                    grid_x, grid_y = self._old_grid_pos if hasattr(self, "_old_grid_pos") else (self.x(), self.y())
                    break
        
        self._old_grid_pos = (grid_x, grid_y)
        self.move(grid_x, grid_y)

        # Notify persistence
        desktop = self.parent().parent() if hasattr(self.parent(), "parent") else None
        if desktop and hasattr(desktop, "save_layout"):
            desktop.save_layout()

    def mouseDoubleClickEvent(self, event):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DesktopIcon] Double-clicked: {self.name}")

        # Traverse up to find Desktop
        ptr = self.parent()
        desktop = None
        while ptr:
            if hasattr(ptr, "launch_app"):
                desktop = ptr
                break
            ptr = ptr.parent()
            
        if not desktop: 
            logger.warning("[DesktopIcon] Could not find Desktop parent for launching.")
            return

        # Launch Logic
        logger.debug(f"[DesktopIcon] Requesting launch for: {self.name}")
        if self.name in ["Home", "File System", "Files"]:
            desktop._open_file_manager()
        elif self.name == "Trash":
            desktop._open_trash()
        elif self.name == "Terminal":
            desktop._launch_terminal()
        else:
            # General app launch from registry
            desktop.launch_app(self.name)
        
        # Visual Feedback (Respond on the go)
        self._pulse_feedback()

    def _pulse_feedback(self):
        from PyQt5.QtCore import QPropertyAnimation, QRect
        from assets.theme import THEME
        orig_geom = self.geometry()
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(150)
        self.anim.setStartValue(orig_geom)
        self.anim.setEndValue(QRect(orig_geom.x()-5, orig_geom.y()-5, orig_geom.width()+10, orig_geom.height()+10))
        self.anim.setLoopCount(2)
        self.anim.start()
