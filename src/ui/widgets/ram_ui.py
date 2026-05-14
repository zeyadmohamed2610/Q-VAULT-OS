import logging
import psutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from resources import theme

logger = logging.getLogger(__name__)

class RAMWidget(QWidget):
    """Real-time RAM usage display with dynamic health colors."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._lbl = QLabel("MEMORY: Loading...")
        self._lbl.setStyleSheet(f"color: {theme.THEME['text_muted']}; font-size: 8px; font-weight: 900; letter-spacing: 0.5px;")
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setFixedHeight(5)
        self._bar.setTextVisible(False)
        self._set_bar_style(theme.THEME['primary_glow'])
        layout.addWidget(self._bar)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000) # Faster refresh for RAM
        self._refresh()

    def _set_bar_style(self, color):
        self._bar.setStyleSheet(f"""
            QProgressBar {{ 
                background: rgba(255, 255, 255, 0.04); 
                border-radius: 2px; 
                border: none; 
            }}
            QProgressBar::chunk {{ 
                background: {color}; 
                border-radius: 2px; 
            }}
        """)

    def _refresh(self):
        try:
            mem = psutil.virtual_memory()
            pct = int(mem.percent)
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            
            # Dynamic coloring
            color = theme.THEME['primary_glow']
            if pct > 85:
                color = theme.THEME['accent_error']
            elif pct > 60:
                color = theme.THEME['warning']
                
            self._lbl.setText(f"MEMORY: {used_gb:.1f}GB / {total_gb:.1f}GB ({pct}%)")
            self._lbl.setStyleSheet(self._lbl.styleSheet().replace(theme.THEME['text_muted'], color if pct > 60 else theme.THEME['text_muted']))
            self._set_bar_style(color)
            self._bar.setValue(pct)
        except Exception as e:
            logger.error(f"RAM refresh error: {e}")
            self._lbl.setText("MEMORY: Unavailable")
