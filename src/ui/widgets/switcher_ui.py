from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QColor, QFont, QPixmap
from resources.theme import THEME

class AltTabSwitcher(QWidget):
    """
    Sovereign Alt+Tab Overlay UI.
    Displays a glassmorphic list of active windows.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setFixedSize(600, 160)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.container = QFrame(self)
        self.container.setStyleSheet(f"""
            QFrame {{
                background: rgba(10, 15, 25, 220);
                border: 1px solid {THEME['primary_glow']}44;
                border-radius: 20px;
            }}
        """)
        self.container.setFixedSize(560, 120)
        
        self.inner_layout = QHBoxLayout(self.container)
        self.inner_layout.setContentsMargins(15, 0, 15, 0)
        self.inner_layout.setSpacing(10)
        self.inner_layout.setAlignment(Qt.AlignCenter)
        
        self._windows = []
        self._current_idx = 0
        self._items = []

    def show_switcher(self, windows, current_idx=0):
        # Clear existing
        for item in self._items:
            item.deleteLater()
        self._items = []
        
        self._windows = windows
        self._current_idx = current_idx % len(windows) if windows else 0
        
        for i, win in enumerate(windows):
            item = self._create_item(win, i == self._current_idx)
            self.inner_layout.addWidget(item)
            self._items.append(item)
            
        # Center on parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.center() - QPoint(self.width()//2, self.height()//2))
            
        self.show()
        self.raise_()

    def cycle(self):
        if not self._windows: return
        self._current_idx = (self._current_idx + 1) % len(self._windows)
        self._refresh_selection()
        return self._windows[self._current_idx]

    def _refresh_selection(self):
        for i, item in enumerate(self._items):
            is_sel = (i == self._current_idx)
            item.setProperty("selected", is_sel)
            item.style().unpolish(item)
            item.style().polish(item)
            
            # Subtle glow effect on selected
            item.setStyleSheet(self._get_item_style(is_sel))

    def _create_item(self, window, selected):
        frame = QFrame()
        frame.setFixedSize(80, 90)
        frame.setStyleSheet(self._get_item_style(selected))
        
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(5, 10, 5, 5)
        vl.setSpacing(5)
        vl.setAlignment(Qt.AlignCenter)
        
        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setScaledContents(True)
        # Try to get app icon from window metadata
        icon_path = getattr(window, "icon_path", "resources/icons/generic_app.svg")
        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtGui import QPainter
        pix = QPixmap(40, 40)
        pix.fill(Qt.transparent)
        renderer = QSvgRenderer(icon_path)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        icon_lbl.setPixmap(pix)
        vl.addWidget(icon_lbl, 0, Qt.AlignCenter)
        
        # Title (truncated)
        title = window.window_title if hasattr(window, "window_title") else "App"
        short_title = (title[:8] + '..') if len(title) > 10 else title
        lbl = QLabel(short_title)
        lbl.setStyleSheet("color: white; font-size: 9pt; background: transparent;")
        lbl.setAlignment(Qt.AlignCenter)
        vl.addWidget(lbl)
        
        return frame

    def _get_item_style(self, selected):
        bg = f"rgba(84, 177, 198, 0.25)" if selected else "transparent"
        border = f"1px solid {THEME['primary_glow']}" if selected else "none"
        return f"background: {bg}; border: {border}; border-radius: 12px;"

    def get_selected_window(self):
        if self._windows and 0 <= self._current_idx < len(self._windows):
            return self._windows[self._current_idx]
        return None
