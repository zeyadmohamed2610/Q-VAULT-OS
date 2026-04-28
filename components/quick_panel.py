from assets.theme import *
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QPoint, QEasingCurve, QTimer, pyqtSignal
from tools.system_control_helper import SystemControlHelper

class QuickWidget(QFrame):
    def __init__(self, title: str, icon_text: str):
        super().__init__()
        self.setObjectName("QuickWidget")
        self.setStyleSheet(f"""
            #QuickWidget {{
                background: rgba(30, 35, 45, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
            QLabel {{ background: transparent; color: {THEME['text_dim']}; font-size: 11px; }}
            #WidgetIcon {{ font-size: 14px; color: {THEME['primary_glow']}; font-family: 'Segoe UI Symbol'; }}
        """)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        
        self.icon_lbl = QLabel(icon_text)
        self.icon_lbl.setObjectName("WidgetIcon")
        
        self.title_stack = QVBoxLayout()
        self.title_lbl = QLabel(title.upper())
        self.title_stack.addWidget(self.title_lbl)
        
        self.layout.addWidget(self.icon_lbl)
        self.layout.addLayout(self.title_stack, stretch=1)

class QuickPanel(QWidget):
    volume_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self._is_visible = False
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("QuickPanel")
        self.setStyleSheet(f"""
            QWidget#QuickPanel {{
                background: rgba(10, 12, 18, 0.98);
                border: 1px solid {THEME['primary_glow']}33;
                border-radius: 16px;
            }}
            QPushButton.PowerBtn {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                color: {THEME['text_dim']};
                font-size: 9px;
                font-weight: bold;
                padding: 10px 5px;
            }}
            QPushButton.PowerBtn:hover {{
                background: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid {THEME['primary_glow']}66;
            }}
            QSlider::groove:horizontal {{ background: rgba(255,255,255,0.05); height: 4px; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {THEME['primary_glow']}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # ───── POWER ACTIONS (With Icons) ─────
        power_row = QHBoxLayout()
        self.btn_shutdown = QPushButton("⏻\nSHUTDOWN")
        self.btn_sleep = QPushButton("⏾\nSLEEP")
        self.btn_restart = QPushButton("⟳\nRESTART")
        
        for btn in [self.btn_shutdown, self.btn_sleep, self.btn_restart]:
            btn.setProperty("class", "PowerBtn")
            btn.setCursor(Qt.PointingHandCursor)
            power_row.addWidget(btn)
            
        self.btn_shutdown.clicked.connect(lambda: SystemControlHelper.power_action("shutdown"))
        self.btn_restart.clicked.connect(lambda: SystemControlHelper.power_action("restart"))
        self.btn_sleep.clicked.connect(lambda: SystemControlHelper.power_action("sleep"))
        
        self.layout.addLayout(power_row)

        # ───── AIRPLANE MODE ─────
        self.airplane_mode = QFrame()
        self.airplane_mode.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);")
        am_layout = QHBoxLayout(self.airplane_mode)
        self.lbl_am = QLabel("✈  AIRPLANE MODE")
        self.lbl_am.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 10px; font-weight: bold;")
        am_layout.addWidget(self.lbl_am)
        self.am_toggle = QPushButton("OFF")
        self.am_toggle.setFixedSize(50, 24)
        self.am_toggle.setCheckable(True)
        self.am_toggle.setStyleSheet("QPushButton { background: #333; color: white; border-radius: 12px; font-size: 9px; font-weight: bold; } QPushButton:checked { background: orange; color: black; }")
        self.am_toggle.toggled.connect(self._on_airplane_toggle)
        am_layout.addWidget(self.am_toggle)
        self.layout.addWidget(self.airplane_mode)

        # ───── VOLUME (Debounced for performance) ─────
        vol_box = QuickWidget("Volume", "🔊")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self._on_vol_change)
        vol_box.title_stack.addWidget(self.vol_slider)
        self.layout.addWidget(vol_box)

        self.layout.addStretch()
        
        # Debounce Timer for Volume
        self.vol_timer = QTimer()
        self.vol_timer.setSingleShot(True)
        self.vol_timer.timeout.connect(self._apply_volume)
        self._pending_vol = 70

        # Footer
        footer = QLabel("Q-VAULT CONTROL HUB v2.1")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: {THEME['text_disabled']}; font-size: 9px; letter-spacing: 1px;")
        self.layout.addWidget(footer)

    def _on_vol_change(self, val):
        self._pending_vol = val
        if not self.vol_timer.isActive():
            self.vol_timer.start(50) # 50ms debounce

    def _apply_volume(self):
        SystemControlHelper.set_volume(self._pending_vol)
        self.volume_changed.emit(self._pending_vol)

    def _on_airplane_toggle(self, checked):
        self.am_toggle.setText("ON" if checked else "OFF")
        SystemControlHelper.set_airplane_mode(checked)

    def toggle(self):
        if self._is_visible: self.hide_panel()
        else: self.show_panel()

    def show_panel(self):
        self._is_visible = True
        self.raise_()
        self.show()
        parent_w = self.parent().width()
        target_y = 60
        panel_h = 320
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(QRect(parent_w, target_y, 280, panel_h))
        self.anim.setEndValue(QRect(parent_w - 295, target_y, 280, panel_h))
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def hide_panel(self):
        self._is_visible = False
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(self.parent().width(), self.y()))
        self.anim.setEasingCurve(QEasingCurve.InCubic)
        self.anim.finished.connect(self.hide)
        self.anim.start()
