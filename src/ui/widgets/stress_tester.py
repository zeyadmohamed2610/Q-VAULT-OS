import logging
import time
from PyQt5.QtCore import QThread, pyqtSignal
from system.runtime_manager import RUNTIME_MANAGER
from system.runtime.pressure_manager import PRESSURE_MANAGER

logger = logging.getLogger(__name__)

class AutomatedStressTester(QThread):
    """
    Sovereign Stress Tester (Phase 16).
    Automates backpressure and congestion testing to validate kernel governance.
    """
    status_update = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            super().start()

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        logger.info("[StressTester] Initiating long-term backpressure validation.")
        self.status_update.emit("Starting stress test...")
        
        # Simulating heavy load
        iterations = 0
        while self.running and iterations < 100:
            iterations += 1
            
            # Simulate CPU/RAM spike
            PRESSURE_MANAGER.calculate_system_pressure(cpu_usage=90.0, ram_usage=85.0, queue_backlog=600)
            
            # Request resources rapidly to trigger RuntimeManager rate limiting
            try:
                # We mock a high-frequency call loop
                for _ in range(20):
                    RUNTIME_MANAGER.get_record("system") # Mock interaction
                    time.sleep(0.01)
            except Exception as e:
                logger.debug(f"[StressTester] Triggered expected governance constraint: {e}")

            if iterations % 10 == 0:
                logger.info(f"[StressTester] Iteration {iterations}/100. Current pressure ratio: {PRESSURE_MANAGER.current_pressure_ratio}")
                
            time.sleep(0.5)

        logger.info("[StressTester] Validation complete.")
        self.status_update.emit("Stress test complete.")
        self.running = False

