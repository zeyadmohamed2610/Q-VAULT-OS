from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
import threading
import time
import random

class PulseAttackerApp(QWidget):
    _app_id = "pulse_attacker"
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Pulse Attacker 🌊")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Mode: Jittered Burst (9/s target)")
        layout.addWidget(self.label)
        
        self.btn = QPushButton("Start Pulse")
        self.btn.clicked.connect(self.toggle_attack)
        layout.addWidget(self.btn)
        
        self.is_attacking = False

    def toggle_attack(self):
        self.is_attacking = not self.is_attacking
        self.btn.setText("Stop" if self.is_attacking else "Start Pulse")
        if self.is_attacking:
            threading.Thread(target=self._attack_loop, daemon=True).start()

    def _attack_loop(self):
        while self.is_attacking:
            # Burst 9 calls (one under the 10/s limit)
            for _ in range(9):
                try: self.api.fs.listdir("/")
                except: break
            
            # Jittered sleep to fool average-based detection
            time.sleep(random.uniform(0.5, 1.1))
            
            # Periodically try to "break" the limit with a fast double-burst
            if random.random() > 0.8:
                for _ in range(5):
                    try: self.api.fs.listdir("/")
                    except: break
