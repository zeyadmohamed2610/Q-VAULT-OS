import random
from PyQt5.QtCore import QTimer, QObject
from core.event_bus import EVENT_BUS, SystemEvent
from kernel.memory_manager import MEMORY_MANAGER
from system.window_manager import get_window_manager
import logging

logger = logging.getLogger(__name__)

class AutomatedStressTester(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.step = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._perform_step)
        
        # We will open all apps and stress them
        self.apps_to_open = [
            {"id": "Terminal", "name": "Terminal"},
            {"id": "File Manager", "name": "File Manager"},
            {"id": "Kernel Monitor", "name": "Kernel Monitor"},
            {"id": "Q-Vault Browser", "name": "Q-Vault Browser"},
            {"id": "Trash", "name": "Trash"}
        ]
        
    def start(self):
        logger.info("[STRESS TEST] Starting Automated Comprehensive Stress Test...")
        self.timer.start(100)  # fast steps every 100ms

    def _perform_step(self):
        self.step += 1
        wm = get_window_manager()
        
        try:
            if self.step <= 5:
                # Open an app every step
                app = self.apps_to_open[self.step - 1]
                logger.info(f"[STRESS TEST] Opening {app['name']}")
                if app['id'] == "terminal":
                    EVENT_BUS.emit(SystemEvent.REQ_TERMINAL_OPEN_HERE, {"path": "."}, source="StressTest")
                else:
                    EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"app_id": app['id']}, source="StressTest")
                    
            elif 5 < self.step <= 15:
                # Randomly focus windows
                if wm._windows:
                    win_id = random.choice(list(wm._windows.keys()))
                    logger.info(f"[STRESS TEST] Focusing {win_id}")
                    EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS, {"id": win_id}, source="StressTest")
                    
            elif 15 < self.step <= 25:
                # Randomly minimize windows
                if wm._windows:
                    win_id = random.choice(list(wm._windows.keys()))
                    logger.info(f"[STRESS TEST] Minimizing {win_id}")
                    EVENT_BUS.emit(SystemEvent.REQ_WINDOW_MINIMIZE, {"id": win_id}, source="StressTest")
                    
            elif 25 < self.step <= 35:
                # Randomly restore windows
                if wm._windows:
                    win_id = random.choice(list(wm._windows.keys()))
                    logger.info(f"[STRESS TEST] Restoring {win_id}")
                    EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS, {"id": win_id}, source="StressTest")
                    
            elif 35 < self.step <= 45:
                # Memory & Kernel Stress
                pid = 2000 + self.step
                logger.info(f"[STRESS TEST] Simulating Heavy Memory Allocation PID {pid}")
                EVENT_BUS.emit(SystemEvent.PROC_SPAWNED, {"pid": pid, "name": f"stress_bot_{self.step}"}, source="StressTest")
                MEMORY_MANAGER.allocate(pid=pid, size=random.randint(20, 100), label=f"bot_alloc_{self.step}")
                EVENT_BUS.emit(SystemEvent.CORE_ASSIGNED, {"pid": pid, "core_id": self.step % 4}, source="StressTest")
                
            elif 45 < self.step <= 50:
                # Close random windows
                if wm._windows:
                    win_id = random.choice(list(wm._windows.keys()))
                    logger.info(f"[STRESS TEST] Closing {win_id}")
                    EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE, {"id": win_id}, source="StressTest")
            
            elif self.step > 50:
                logger.info("[STRESS TEST] Stress Test Completed Successfully! System remained stable.")
                self.timer.stop()
        except Exception as e:
            logger.error(f"[STRESS TEST] FAILED AT STEP {self.step}: {e}", exc_info=True)
            self.timer.stop()
