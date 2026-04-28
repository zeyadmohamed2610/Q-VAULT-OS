"""
scratch/saturation_tester.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS v1.0 — 'Chaos Edge' Saturation & Leak Auditor (v1.0 Final)
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import time
import os
import psutil
import logging
import uuid
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QCoreApplication

# ── Environment ──
sys.path.append(os.getcwd())
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("chaos.edge")

from system.runtime.isolated_widget import IsolatedAppWidget
from system.sandbox.secure_api import SecureAPI
from system.runtime_manager import AppRuntimeManager

class SaturationTest:
    def __init__(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        self.app = QApplication(sys.argv)
        self.rm = AppRuntimeManager()
        self.instances = {}
        self.is_running = True
        self._step = 0
        self._lock = threading.Lock()

    def spawn(self, app_id, role="normal"):
        iid = f"{app_id}_{uuid.uuid4().hex[:4]}"
        api = SecureAPI(iid, app_id)
        
        # Explicit kernel registration
        record = self.rm.register(iid, None, secret=iid)
        record.state = record.state.RUNNING
        
        # 🟢 CORRECT: Use Engine modules (not Widget modules)
        if role == "spammer":
            module = "apps.terminal.malicious_engine"
            cls = "TerminalApp"
        else:
            module = "apps.terminal.terminal_engine"
            cls = "TerminalEngine"
        
        widget = IsolatedAppWidget(iid, module, cls, secure_api=api)
        with self._lock:
            self.instances[iid] = {"widget": widget, "role": role, "record": record}
        logger.info(f"🚀 Registered {role.upper()} app: {iid} ({module})")
        return iid

    def _flood_worker(self):
        """No internal loop needed - engine does it."""
        pass

    def _normal_traffic(self):
        """1Hz legitimate traffic."""
        with self._lock:
            for iid, data in self.instances.items():
                if data["role"] == "normal":
                    try:
                        data["widget"].call_remote("get_stats", {}, callback=lambda x: None)
                    except:
                        pass

    def _audit_loop(self):
        self._step += 1
        uptime = self._step * 2 # 2s ticks
        
        logger.info(f"--- Audit Step {self._step} (T+{uptime}s) ---")
        
        with self._lock:
            items = list(self.instances.items())
            for iid, data in items:
                rec = data["record"]
                widget = data["widget"]
                
                # Check if alive
                if not hasattr(widget, "_proc") or not widget._proc.is_alive():
                    # 🟢 GRACE PERIOD: Wait for kernel cleanup thread to identify death
                    logger.warning(f"💀 {iid} is DEAD natively. Waiting for Kernel cleanup...")
                    time.sleep(1) 
                    self._verify_cleanup(iid, widget)
                    del self.instances[iid]
                    continue

                status = "CONGESTED" if rec.congested else "NORMAL"
                logger.info(f"APP: {iid:<20} | Trust: {rec.trust_score:>3} | Hz: {rec.msg_hz:>6.1f} | Status: {status}")
                
        if not self.instances and self._step > 5:
            self.stop()

    def _verify_cleanup(self, iid, widget):
        """Deep-dive resource audit (Requirement 3)."""
        logger.info(f"🔍 [LEAK AUDIT] Verifying {iid} cleanup...")
        
        # 1. Pending Queue
        pending_count = len(widget._pending_calls)
        if pending_count == 0: logger.info("  ✅ Pending calls cleared.")
        else: logger.error(f"  ❌ LEAK: {pending_count} orphaned calls in map!")
        
        # 2. Bridge Thread
        if not widget.bridge._drain_thread.is_alive(): logger.info("  ✅ Bridge thread stopped.")
        else: logger.error("  ❌ LEAK: Bridge thread still running!")
        
        # 3. Connection Status
        try:
            widget.bridge.conn.send_bytes(b"ping")
            logger.error("  ❌ LEAK: IPC Pipe still open!")
        except:
            logger.info("  ✅ IPC Pipe closed.")

    def stop(self):
        logger.info("🏁 Chaos Edge Test Complete.")
        self.is_running = False
        QApplication.quit()

    def run(self):
        # 1. Spawn Mixed Load
        self.spawn("MaliciousSpammer", role="spammer")
        self.spawn("SystemTaskbar", role="normal")
        
        # Timers (Main Thread)
        self.normal_timer = QTimer()
        self.normal_timer.timeout.connect(self._normal_traffic)
        self.normal_timer.start(1000) # 1Hz
        
        self.audit_timer = QTimer()
        self.audit_timer.timeout.connect(self._audit_loop)
        self.audit_timer.start(2000) # 2s audit
        
        self.app.exec_()

if __name__ == "__main__":
    tester = SaturationTest()
    tester.run()
