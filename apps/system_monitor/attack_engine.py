import time
import threading
import uuid
import json
from PyQt5.QtCore import QObject, pyqtSignal

from system.runtime_manager import RUNTIME_MANAGER
from system.sandbox.secure_api import SecureAPI
from core.app_registry import REGISTRY, AppDefinition

class AttackEngine(QObject):
    log_emitted = pyqtSignal(str, str, str)  # severity, tag, message
    test_finished = pyqtSignal(dict) # result metrics

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False

    def run_tests_async(self):
        if self._is_running:
            return
        self._is_running = True
        threading.Thread(target=self._test_pipeline, daemon=True).start()

    def _log(self, severity: str, tag: str, message: str):
        self.log_emitted.emit(severity, tag, message)

    def _test_pipeline(self):
        self._log("MEDIUM", "INIT", "Bootstrapping Attack Engine...")
        
        # 1. Identity Layer: Create bad_actor
        session_id = uuid.uuid4().hex[:8]
        bad_app_id = f"bad_actor_app_{session_id}"
        
        self._log("LOW", "IDENTITY", f"Generating malicious identity: {bad_app_id}")

        # Register in the dynamic definitions dict (not the frozen _MANIFEST).
        # The key must match the string passed to start_app() so get_by_name
        # can resolve it.  Previously this wrote to a non-existent attribute.
        REGISTRY._definitions[bad_app_id] = AppDefinition(
            name=bad_app_id,           # name == key for dynamic defs
            emoji="☠️",
            module="system_monitor",
            class_name="SystemMonitorWidget",  # must be a real, importable class
            show_on_desktop=False
        )
        
        # Start app in runtime and capture the unique instance ID
        instance_id = RUNTIME_MANAGER.start_app(bad_app_id)
        
        # Give it an API hooked into this specific instance's resource tokens
        api = SecureAPI(bad_app_id, instance_id=instance_id)
        
        time.sleep(0.5)

        start_time = time.time()
        start_threads = threading.active_count()
        
        # ── Attack 1: FS Traversal ──
        self._log("HIGH", "FS_TRAVERSAL", "Attempting access to ../../../../Windows/System32")
        try:
            api.fs.open("../../../../Windows/System32/cmd.exe", "rb")
            self._log("CRITICAL", "FS_TRAVERSAL", "SUCCESS! Escape achieved! (VULNERABILITY DETECTED)")
        except Exception as e:
            self._log("LOW", "FS_TRAVERSAL", f"Blocked: {e}")
            
        time.sleep(0.5)

        # ── Attack 2: Localhost SSRF ──
        self._log("HIGH", "NETWORK", "Attempting Localhost SSRF (127.0.0.1)")
        resp = api.network.request("http://127.0.0.1:8080/admin")
        if resp["status"] != 0 and resp["content"] is not None:
             self._log("CRITICAL", "NETWORK", "NetworkGuard failed to block localhost!")
        else:
             self._log("LOW", "NETWORK", f"Blocked by guard.")

        time.sleep(0.5)

        # ── Attack 3: Malicious Protocol ──
        self._log("HIGH", "NETWORK", "Attempting file:// scheme fetch via urllib")
        resp = api.network.request("file:///C:/Windows/win.ini")
        if resp["status"] != 0 and resp["content"] is not None:
            self._log("CRITICAL", "NETWORK", "NetworkGuard allowed file scheme!")
        else:
            self._log("LOW", "NETWORK", "Blocked file:// scheme successfully.")

        time.sleep(0.5)

        # ── Attack 4: Network Hang ──
        self._log("MEDIUM", "STRESS", "Attempting Network Time-Hole (10.255.255.1 timeout leak)")
        t_start = time.time()
        # Set a short timeout for the test to avoid hanging the test pipeline forever (assume 2s max)
        resp = api.network.request("http://10.255.255.1:80", timeout=2.0)
        t_delta = time.time() - t_start
        self._log("LOW", "STRESS", f"Timeout executed in {t_delta:.2f}s without freezing main loop.")

        time.sleep(0.5)

        # ── Attack 5: Jittered Pulse (Sliding Window Bypass Attempt) ──
        self._log("HIGH", "PULSE_ATTACK", "Executing Jittered Pulse: 9 calls -> random sleep -> burst")
        import random
        for i in range(25):
            try: api.fs.listdir("/")
            except: pass
            if i % 9 == 0:
                time.sleep(random.uniform(0.1, 0.4)) # Jitter to confuse average-based limits
        
        self._log("LOW", "PULSE_ATTACK", "Pattern completed. Checking if cumulative violation triggered.")
        time.sleep(0.5)

        # ── Attack 6: Latent Traitor (Delayed Abuse) ──
        self._log("MEDIUM", "TRAITOR", "App acting normally for 3 seconds...")
        time.sleep(3.0)
        self._log("HIGH", "TRAITOR", "Surprise Abuse: Flooding network requests!")
        for _ in range(20):
             threading.Thread(target=lambda: api.network.request("https://google.com"), daemon=True).start()
        
        time.sleep(1.0)
        
        # ── Attack 7: Memory/Recursion Pressure ──
        self._log("HIGH", "RESOURCE_BOMB", "Deploying Recursion + Heap pressure")
        def recursion_bomb(depth):
            if depth <= 0: return
            _data = [0] * (1024 * 1024) # Allocate 1MB per level
            recursion_bomb(depth - 1)
        
        try:
            threading.Thread(target=recursion_bomb, args=(50,), daemon=True).start()
        except Exception as e:
            self._log("LOW", "RESOURCE_BOMB", f"Isolated: {e}")

        time.sleep(2.0)
        
        # ── Attack 8: The Coordinated Blitz (Final Boss) ──
        self._log("CRITICAL", "DISTRIBUTED", "Phase 13.5: Launching Multi-Identity Coordinated Blitz...")
        self._test_coordinated_blitz()

        # ── Performance Telemetry — collected after all attacks complete ──
        # start_time / start_threads are defined at the top of this method,
        # so this is the correct scope for computing duration and thread delta.
        end_time = time.time()
        end_threads = threading.active_count()
        # Subtract the known sleep budget (~7.5 s across all attacks) to isolate real overhead.
        # Using 7.5 as the approximated total intentional sleep in the pipeline.
        ui_lag = (end_time - start_time) - 7.5

        metrics = {
            "duration": round(end_time - start_time, 2),
            "thread_delta": end_threads - start_threads,
            "ui_lag": round(ui_lag, 2),
        }

        # ── Check Quarantine and Kill Switch ──
        state = RUNTIME_MANAGER.get_state(bad_app_id)
        self._log("MEDIUM", "VERIFICATION", f"Final State of malicious app: {state.state.name} | Score: {state.trust_score}")
        
        if state.state.name == "QUARANTINED":
            self._log("HIGH", "KILL_SWITCH", "Verifying kill switch is active (API Lock)")
            try:
                resp = api.network.request("https://example.com")
                if resp["status"] == 200:
                    self._log("CRITICAL", "KILL_SWITCH", "API IS STILL ALIVE DESPITE QUARANTINE!")
                else:
                    self._log("LOW", "KILL_SWITCH", "Kill switch successfully blocked external request.")
            except Exception as e:
                self._log("LOW", "KILL_SWITCH", f"Kill switch successfully blocked execution: {e}")
        else:
            self._log("CRITICAL", "VERIFICATION", "APP WAS NOT QUARANTINED!")

        # ── Emit results and mark engine idle ──
        self.test_finished.emit(metrics)
        self._is_running = False

    def _test_coordinated_blitz(self):
        """Launches 3 distinct identities to trigger Global Emergency Mode."""
        ids = []
        for i in range(3):
            app_id = f"conspirator_{uuid.uuid4().hex[:4]}_{i}"
            REGISTRY._definitions[app_id] = AppDefinition(
                name=app_id,
                emoji="🎭",
                module="system_monitor",
                class_name="SystemMonitorWidget",
                show_on_desktop=False
            )
            instance_id = RUNTIME_MANAGER.start_app(app_id)
            api = SecureAPI(app_id, instance_id=instance_id)
            ids.append((app_id, api))
            self._log("MEDIUM", "DISTRIBUTED", f"Identity {i} in place: {app_id}")
            time.sleep(0.5) # Staggered for overlap trigger

        def app_work(idx, api_obj):
            # Each app fires ~16 calls/sec.  Three apps together -> ~48 req/s,
            # well above the dynamic threshold and the burst detector ceiling.
            for _ in range(20):
                try: api_obj.fs.listdir("/")
                except: break
                time.sleep(0.06)

        threads = []
        self._log("HIGH", "DISTRIBUTED", "Executing synchronized burst logic...")
        for i, api_data in enumerate(ids):
            t = threading.Thread(target=app_work, args=(i, api_data[1]), daemon=True)
            t.start()
            threads.append(t)

        time.sleep(2.0)
        global_state = RUNTIME_MANAGER.global_state
        pressure = RUNTIME_MANAGER.current_pressure_ratio
        # BUG FIX: was :.2x (hex format) — corrected to :.2f (float, 2 decimal places)
        self._log("CRITICAL", "DISTRIBUTED", f"OS Global State: {global_state} | Pressure: {pressure:.2f}")

        for t in threads:
            t.join(timeout=1.0)

        # NOTE: timing telemetry (start_time, start_threads) lives in _test_pipeline
        # and is emitted there, after this method returns.  Do NOT emit test_finished
        # or reset _is_running here — that would run before the pipeline finishes.
