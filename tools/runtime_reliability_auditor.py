import sys
import gc
import time
import psutil
import os
import random
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer, QObject

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import WindowManager
from components.os_window import OSWindow
from system.taskbar_controller import TaskbarController
from system.runtime_manager import RUNTIME_MANAGER
from system.app_controller import AppController

class ReliabilityAuditor:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.process = psutil.Process(os.getpid())
        self.wm = WindowManager()
        
        self.start_mem = self.get_mem_mb()
        self.metrics = {
            "dangling_windows": 0,
            "dangling_timers": 0,
            "dangling_qobjects": 0,
            "memory_growth_mb": 0,
            "events_emitted": 0
        }
        
    def get_mem_mb(self):
        return self.process.memory_info().rss / (1024 * 1024)
        
    def count_qobjects(self):
        # Force Qt to process all deleteLater() calls
        from PyQt5.QtCore import QEvent
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        gc.collect()
        
        widgets = 0
        timers = 0
        objects = 0
        for obj in gc.get_objects():
            try:
                if isinstance(obj, QWidget): widgets += 1
                elif isinstance(obj, QTimer): timers += 1
                elif isinstance(obj, QObject): objects += 1
            except Exception:
                pass
        return widgets, timers, objects

    def simulate_user_session(self, hours: int):
        """Simulates `hours` of user activity."""
        print(f"\n[Audit] Starting {hours}h horizon simulation...")
        
        events_per_hour = 1000  # 6 hours = 6000 events
        total_events = hours * events_per_hour
        
        start_w, start_t, start_o = self.count_qobjects()
        
        # Simulating window spawn/close cycles
        wids = []
        for i in range(total_events):
            action = random.choice(["open", "focus", "minimize", "close", "event_spam"])
            
            if action == "open" and len(wids) < 15:
                wid = f"win_{i}"
                w = OSWindow(wid, "Test App", QWidget())
                self.wm.register_window(w)
                wids.append(wid)
                self.metrics["events_emitted"] += 1
                
            elif action == "focus" and wids:
                wid = random.choice(wids)
                self.wm.focus_window(wid)
                self.metrics["events_emitted"] += 1
                
            elif action == "minimize" and wids:
                wid = random.choice(wids)
                self.wm.minimize_window(wid)
                self.metrics["events_emitted"] += 1
                
            elif action == "close" and wids:
                wid = random.choice(wids)
                self.wm.close_window(wid)
                wids.remove(wid)
                self.metrics["events_emitted"] += 1
                
            elif action == "event_spam":
                EVENT_BUS.emit(SystemEvent.STATE_CHANGED, {"cpu": random.randint(0, 100)})
                self.metrics["events_emitted"] += 1
                
            if i % 1000 == 0:
                self.app.processEvents() # Process Qt event loop
                
        # Clean up remaining
        for wid in list(wids):
            self.wm.close_window(wid)
            
        # Pump Event Loop for 600ms to allow all Failsafe QTimers to expire
        import time
        start_wait = time.time()
        while time.time() - start_wait < 0.6:
            self.app.processEvents()
            time.sleep(0.01)
        
        end_w, end_t, end_o = self.count_qobjects()
        mem_growth = self.get_mem_mb() - self.start_mem
        
        self.metrics["dangling_windows"] = max(0, end_w - start_w)
        self.metrics["dangling_timers"] = max(0, end_t - start_t)
        self.metrics["dangling_qobjects"] = max(0, end_o - start_o)
        self.metrics["memory_growth_mb"] = mem_growth
        
        print(f"  [>] Events Fired: {self.metrics['events_emitted']}")
        print(f"  [>] Dangling QWidgets: {self.metrics['dangling_windows']}")
        print(f"  [>] Dangling QTimers: {self.metrics['dangling_timers']}")
        print(f"  [>] Memory Growth: +{self.metrics['memory_growth_mb']:.2f} MB")
        
        return self.metrics

if __name__ == "__main__":
    auditor = ReliabilityAuditor()
    # 6-hour simulation
    metrics = auditor.simulate_user_session(hours=6)
    
    # Save raw data for analysis
    import json
    with open("reports/raw_reliability_metrics.json", "w") as f:
        json.dump(metrics, f)
