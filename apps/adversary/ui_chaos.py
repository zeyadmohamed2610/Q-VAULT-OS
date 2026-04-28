from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
import threading
import time
from system.window_manager import get_window_manager

class UIChaosApp(QWidget):
    _app_id = "ui_chaos"
    
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("UI Chaos 🌀")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Click to disrupt the Desktop UI Thread.")
        layout.addWidget(self.label)
        
        btn = QPushButton("Spawn 20 Windows")
        btn.clicked.connect(self.spawn_chaos)
        layout.addWidget(btn)

    def spawn_chaos(self):
        wm = get_window_manager()
        self.label.setText("Spawning... (UI Stress Test)")
        
        def chaos_logic():
            for i in range(20):
                # Try to trigger a WindowManager heavy operation
                # Since we are in-process, we can try to call signals directly
                try:
                    # In a real app we shouldn't have access to WM, 
                    # but here we test if the OS survives manual disruption
                    pass 
                except: pass
                
                # Use the API to generate load while spamming
                try: self.api.fs.listdir("/")
                except: pass
                
                time.sleep(0.05)
            
            self.label.setText("Chaos finished. Did the OS freeze?")
            
        threading.Thread(target=chaos_logic, daemon=True).start()
