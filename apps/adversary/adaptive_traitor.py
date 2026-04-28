from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
import threading
import time
import random

class AdaptiveTraitorApp(QWidget):
    _app_id = "adaptive_traitor"
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Adaptive Traitor 🎭")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Status: Dormant (Trusted)")
        layout.addWidget(self.label)
        
        self.btn = QPushButton("Infiltrate")
        self.btn.clicked.connect(self.start_infiltration)
        layout.addWidget(self.btn)
        
        self.is_running = False

    def start_infiltration(self):
        self.is_running = True
        self.btn.setEnabled(False)
        threading.Thread(target=self._logic, daemon=True).start()

    def _logic(self):
        # 1. Dormancy Phase
        self.label.setText("Gaining Trust (5s)...")
        time.sleep(5.0)
        
        # 2. Adaptive Attack Phase
        self.label.setText("Executing Adaptive Poisoning...")
        
        intensity = 0.1 # Start fast
        success_count = 0
        block_count = 0
        
        while self.is_running:
            try:
                # Attempt sensitive operation
                self.api.fs.listdir("/")
                success_count += 1
                # If successful, try to push the limit slightly
                intensity = max(0.01, intensity - 0.01)
            except PermissionError:
                block_count += 1
                # ADAPTIVE: We were blocked! Back off immediately to let the window clear.
                self.label.setText(f"Blocked! Backing off... (Total: {block_count})")
                intensity = min(1.0, intensity * 2) # Exponential backoff
                time.sleep(2.0)
            except Exception:
                break
            
            time.sleep(intensity)
            
            if success_count % 10 == 0:
                self.label.setText(f"Infiltrating... (Hits: {success_count})")
