"""
scratch/soak_runner.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS v1.0 — Production Soak Test Runner
Simulates 24h of heavy OS load (100x intensity) in a 10-minute window.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import time
import os
import psutil
import threading
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 1. ── Setup Environment ──
sys.path.append(os.getcwd())
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("soak.runner")

from system.runtime.isolated_widget import IsolatedAppWidget
from system.sandbox.secure_api import SecureAPI
from system.runtime_manager import AppRuntimeManager

class SoakTest:
    def __init__(self, duration_sec=600): # 10 minutes
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        self.app = QApplication(sys.argv)
        self.duration = duration_sec
        self.start_time = time.time()
        self.instances = []
        self.rm = AppRuntimeManager()
        
        # Performance Tracking
        self.stats = []
        self.is_running = True

    def spawn_apps(self, count=5):
        logger.info(f"🚀 Spawning {count} Isolated Apps for soak test...")
        for i in range(count):
            iid = f"SoakApp_{i}"
            api = SecureAPI(iid, iid)
            # 🟢 Phase 16.8: Explicit Kernel Registration for Observability
            record = self.rm.register(iid, None, secret=api.instance_id) # Using instance_id as mock secret
            record.state = record.state.RUNNING # Authoritative state boost
            
            widget = IsolatedAppWidget(iid, "apps.terminal.terminal_app", "TerminalApp", secure_api=api)
            self.instances.append(widget)
            logger.info(f"Instance {iid} launched and registered in Kernel.")

    def _flood_traffic(self):
        """Send high-intensity IPC calls to all apps."""
        if not self.is_running: return
        
        for widget in self.instances:
            # Simulate heavy CLI usage
            widget.call_remote("execute_command", {"command": "ls -la /"}, callback=lambda x: None)
            widget.call_remote("get_stats", {}, callback=lambda x: None)

    def _monitor_resources(self):
        """Measure RSS, Threads, and Leaks."""
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / (1024 * 1024) # MB
        threads = process.num_threads()
        global_kills = self.rm.global_kill_count
        
        uptime = time.time() - self.start_time
        logger.info(f"📊 [STRESS] Uptime: {uptime:.1f}s | RAM: {mem:.2f}MB | Threads: {threads} | Kills: {global_kills}")
        
        self.stats.append({
            "ts": uptime,
            "mem": mem,
            "threads": threads,
            "kills": global_kills
        })
        
        if uptime >= self.duration:
            self.stop()

    def _trigger_governance_stress(self):
        """Randomly drop trust scores to verify kill policy under load."""
        if not self.instances: return
        import random
        target = random.choice(self.instances)
        record = self.rm.get_record(target.instance_id)
        if record:
            logger.warning(f"🧨 Injecting Trust Violation to {target.instance_id}")
            record.trust_score = 10
            # Drain detection should kill it in ~100ms

    def stop(self):
        logger.info("🛑 Soak Test Complete. Analyzing results...")
        self.is_running = False
        
        # Leak Analysis
        if not self.stats:
            logger.error("❌ No stats collected. Runner failed early.")
            QApplication.quit()
            return
            
        first_mem = self.stats[0]["mem"]
        last_mem = self.stats[-1]["mem"]
        delta = last_mem - first_mem
        
        logger.info(f"🏁 [REPORT] Initial RAM: {first_mem:.2f}MB | Final RAM: {last_mem:.2f}MB | Delta: {delta:+.2f}MB")
        if delta > 50: # Arbitrary 50MB threshold for 'leak' in 10 mins
            logger.error("⚠️ CRITICAL: Significant Memory Growth Detected.")
        else:
            logger.info("✅ SUCCESS: Memory usage stable (+/- 50MB).")
            
        QApplication.quit()

    def run(self):
        self.spawn_apps(3) # Start with 3
        
        # Timers
        self.flood_timer = QTimer()
        self.flood_timer.timeout.connect(self._flood_traffic)
        self.flood_timer.start(50) # 20Hz flood
        
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_resources)
        self.monitor_timer.start(5000) # Every 5s
        
        # Every 60s, stress the governance
        self.gov_timer = QTimer()
        self.gov_timer.timeout.connect(self._trigger_governance_stress)
        self.gov_timer.start(60000)
        
        self.app.exec_()

if __name__ == "__main__":
    test = SoakTest(duration_sec=600) # 10 mins
    test.run()
