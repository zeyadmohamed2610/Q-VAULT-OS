from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
import threading
import time

class RecursionBombApp(QWidget):
    _app_id = "recursion_bomb"
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Recursion Bomb 💣")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Click to detonate. Target: Stack & Heap.")
        layout.addWidget(self.label)
        
        btn = QPushButton("Detonate")
        btn.clicked.connect(self.detonate)
        layout.addWidget(btn)

    def detonate(self):
        self.label.setText("Detonating... (Check System Monitor)")
        threading.Thread(target=self._deep_logic, args=(1000,), daemon=True).start()

    def _deep_logic(self, depth):
        if depth <= 0: return
        # Each level tries to allocate 1MB and recurse
        try:
            junk = [0] * (256 * 1024) # ~1MB
            self._deep_logic(depth - 1)
        except Exception as e:
            # We want to see if the OS catches this, not the app!
            pass
