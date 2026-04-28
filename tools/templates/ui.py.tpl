# =============================================================
#  components/{{name}}_ui.py — Q-Vault OS  |  UI View
#
#  Generated via generate_plugin.py
#  Responsibilities: Pure UI rendering, no business logic.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from assets.theme import THEME

class {{className}}UI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("⬡ {{name}} View")
        self.label.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 18px;")
        self.layout.addWidget(self.label)
        
        self.desc = QLabel("Pure UI component decoupled from Logic Engine.")
        self.desc.setStyleSheet("color: rgba(255,255,255,0.7);")
        self.layout.addWidget(self.desc)
