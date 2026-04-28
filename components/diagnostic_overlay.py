from assets.theme import *
# =============================================================
#  components/diagnostic_overlay.py — Q-Vault OS
#
#  Extended Diagnostic & Stability Monitor.
#  Real-time Window Geometry & Z-Index Tracking.
# =============================================================

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from .debug_event_overlay import DebugEventOverlay
from system.window_manager import get_window_manager

class DiagnosticOverlay(DebugEventOverlay):
    """
    Advanced diagnostic layer that adds window tracking 
    to the base event observability.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(450, 600) # Taller to fit window list
        
        # ── Window Monitor Section ──
        # Add a separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.1);")
        self.layout().insertWidget(2, sep) # After metrics
        
        win_header = QLabel("🛡️ WINDOW GEOMETRY LOCK")
        win_header.setFont(QFont("Segoe UI", 9, QFont.Bold))
        win_header.setStyleSheet(f"color: {THEME['accent_purple']}; margin-top: 10px;")
        self.layout().insertWidget(3, win_header)
        
        self.win_list_container = QWidget()
        self.win_list_layout = QVBoxLayout(self.win_list_container)
        self.win_list_layout.setContentsMargins(0, 5, 0, 10)
        self.win_list_layout.setSpacing(2)
        
        self.win_scroll = QScrollArea()
        self.win_scroll.setWidgetResizable(True)
        self.win_scroll.setFixedHeight(200)
        self.win_scroll.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 4px;")
        self.win_scroll.setWidget(self.win_list_container)
        
        self.layout().insertWidget(4, self.win_scroll)
        
        # Update timer for window state
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_window_stats)
        self.refresh_timer.start(500) # 2Hz refresh for geometry

    def _refresh_window_stats(self):
        # Clear current list
        while self.win_list_layout.count():
            item = self.win_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            
        wm = get_window_manager()
        windows = wm._windows
        
        if not windows:
            none_label = QLabel("No active windows")
            none_label.setStyleSheet(f"color: {THEME['text_disabled']}; font-style: italic;")
            self.win_list_layout.addWidget(none_label)
            return
            
        # Sort by Z-index (Top to Bottom)
        sorted_ids = sorted(windows.keys(), key=lambda k: getattr(windows[k], 'z_index', 0), reverse=True)
        
        for wid in sorted_ids:
            win = windows[wid]
            title = getattr(win, 'lbl_title', None)
            title_text = title.text() if title else wid[:10]
            
            # Diagnostic String: ID | POS(X,Y) | SIZE(WxH) | Z
            stats = f"{wid[:6]} | {win.x()},{win.y()} | {win.width()}x{win.height()} | Z:{win.z_index}"
            
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)
            
            # ── VALIDATION ENGINE ──
            is_active = getattr(wm, '_active', None) == wid
            parent = win.parent()
            pw = parent.width() if parent else 1920
            ph = parent.height() if parent else 1080
            
            # Check Bounds (Red if violating)
            is_out = (win.x() < -win.width() + 100 or win.x() > pw - 100 or
                      win.y() < 0 or win.y() > ph - 40)
            
            # Check Size (Orange if at min)
            is_min = (win.width() <= 400 or win.height() <= 300)
            
            # Z-Index Check (Yellow if duplicate - rare)
            is_duplicate_z = list(w.z_index for w in windows.values()).count(win.z_index) > 1
            
            style = "background: rgba(255, 255, 255, 0.05); border-radius: 2px;"
            if is_out: style = "background: rgba(255, 0, 0, 0.2); border: 1px solid red;"
            elif is_duplicate_z: style = "background: rgba(255, 255, 0, 0.2); border: 1px solid yellow;"
            elif is_active: style = "background: rgba(0, 230, 255, 0.1); border-left: 3px solid #00e6ff;"
            
            row.setStyleSheet(style)
            
            lbl_name = QLabel(title_text)
            lbl_name.setFixedWidth(100)
            lbl_name.setStyleSheet(f"color: {'white' if not is_out else THEME['error_bright']}; font-weight: bold;")
            
            lbl_stats = QLabel(stats)
            stat_color = "#88ff88"
            if is_out: stat_color = "#ff4444"
            elif is_min: stat_color = "#ffaa00" # Orange for "at limit"
            
            lbl_stats.setStyleSheet(f"color: {stat_color}; font-size: 9px;")
            
            row_layout.addWidget(lbl_name)
            row_layout.addWidget(lbl_stats)
            row_layout.addStretch()
            
            self.win_list_layout.addWidget(row)
        
        self.win_list_layout.addStretch()
