from assets.theme import *
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton
from PyQt5.QtCore import Qt

class SoundMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {THEME['surface_mid']};
                border: 1px solid {THEME['text_disabled']};
                border-radius: 8px;
                color: white;
            }}
            QSlider::groove:horizontal {{
                background: {THEME['text_disabled']};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['primary_glow']};
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -5px 0;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {THEME['text_muted']};
                padding: 4px;
            }}
            QPushButton:hover {{ color: white; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = QHBoxLayout()
        self.sound_icon = QLabel("🔊")
        self.volume_lbl = QLabel("50%")
        self.volume_lbl.setStyleSheet(f"color: {THEME['text_muted']};")
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.clicked.connect(self._toggle_mute)

        header.addWidget(self.sound_icon)
        header.addWidget(self.volume_lbl)
        header.addStretch()
        header.addWidget(self.mute_btn)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.setFixedWidth(200)
        self.slider.valueChanged.connect(self._on_volume_change)

        layout.addLayout(header)
        layout.addWidget(self.slider)

        self._muted = False
        self._pre_mute_val = 50

    def _on_volume_change(self, value):
        self.volume_lbl.setText(f"{value}%")
        if value == 0:
            self.sound_icon.setText("🔇")
        elif value < 50:
            self.sound_icon.setText("🔉")
        else:
            self.sound_icon.setText("🔊")

    def _toggle_mute(self):
        if self._muted:
            self.slider.setValue(self._pre_mute_val)
            self.mute_btn.setText("Mute")
            self._muted = False
        else:
            self._pre_mute_val = self.slider.value()
            self.slider.setValue(0)
            self.mute_btn.setText("Unmute")
            self._muted = True
