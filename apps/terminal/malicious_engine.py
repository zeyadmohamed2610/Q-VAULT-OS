"""
apps.terminal.malicious_engine
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS v1.0 — Malicious Flooding Adversary (Kernel-Compatible)
─────────────────────────────────────────────────────────────────────────────
"""
import time
from PyQt5.QtCore import QTimer

class TerminalApp:
    def __init__(self, secure_api):
        self.api = secure_api
        print("[ADVERSARY] Malicious Engine Loaded. Preparing flood...")
        
        # We use a QTimer to avoid blocking the engine's own event loop
        # so it can keep receiving the SYSTEM_CONGESTION signals.
        self.flood_timer = QTimer()
        self.flood_timer.timeout.connect(self._do_flood)
        self.flood_timer.start(10) # 100Hz base tick

    def _do_flood(self):
        # 2000Hz Flood (20 calls * 100Hz tick)
        # Sufficient for saturation without choking the simulator host
        for _ in range(20):
            try:
                # We call a legitimate guard method repeatedly
                self.api.system.list_instances() 
            except Exception as e:
                pass

    def handle_event(self, event, data):
        if event == "SYSTEM_CONGESTION":
            print(f"[ADVERSARY] RECEIVED CONGESTION SIGNAL: {data}")
            # Real malware might ignore this, which is what we want to test!
            pass
