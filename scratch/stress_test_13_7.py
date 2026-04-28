
import sys
import os
import time
import multiprocessing
from pathlib import Path
from PyQt5.QtWidgets import QApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def cpu_loader():
    """Generates real CPU load for hardening validation."""
    while True:
        _ = [i*i for i in range(1000)]

def test_hardened_governance():
    print("--- Phase 13.7 Hardened Governance Stress Test ---")
    
    # 1. Register Apps
    good_id = RUNTIME_MANAGER.start_app("Terminal") # Good app
    bad_id = RUNTIME_MANAGER.start_app("Terminal")  # Bad app (we will use it to attack)
    
    print(f"Good App: {good_id} | Bad App: {bad_id}")

    # 2. Start CPU Stress in background
    print("Spawning CPU stressor...")
    p = multiprocessing.Process(target=cpu_loader)
    p.start()

    try:
        # 3. Simulate UI Lag (Manually report lag to the engine)
        print("Reporting artificial UI Lag (300ms)...")
        # We need to simulate the passage of time for report_ui_pulse
        # Mocking it for the test
        RUNTIME_MANAGER._last_pulse_time = time.time() - 0.4 # 400ms delta (expected 100)
        RUNTIME_MANAGER.report_ui_pulse()
        print(f"Engine UI Lag Metric: {RUNTIME_MANAGER.ui_lag_ms}ms")

        # 4. Perform mixed workload
        print("\nStarting mixed API load...")
        for i in range(20):
            # Good app behaves reasonably (1 call/0.1s)
            RUNTIME_MANAGER.acquire_worker(good_id, "process")
            RUNTIME_MANAGER.release_worker(good_id, "process")
            
            # Bad app spams (5 calls/cycle)
            for _ in range(5):
                try:
                    RUNTIME_MANAGER.acquire_worker(bad_id, "process")
                except Exception:
                    pass # Expected when limit hit
            
            time.sleep(0.1)

        # 5. Check Governance State
        print(f"\nFinal Global State: {RUNTIME_MANAGER.global_state}")
        print(f"Final Pressure Ratio: {RUNTIME_MANAGER.current_pressure_ratio:.2f}")
        
        good_rec = RUNTIME_MANAGER.get_record(good_id)
        bad_rec = RUNTIME_MANAGER.get_record(bad_id)
        
        print(f"Good App State: {good_rec.state} | Trust: {good_rec.trust_score}")
        print(f"Bad App State: {bad_rec.state} | Trust: {bad_rec.trust_score}")

        # ── SUCCESS CRITERIA ──
        success = True
        if RUNTIME_MANAGER.global_state == "NORMAL":
            print("FAIL: System failed to enter pressure state under CPU/Lag load.")
            success = False
        
        if bad_rec.state != "QUARANTINED" and bad_rec.trust_score > 50:
             print("FAIL: Attack app was not effectively restricted/quarantined.")
             success = False
             
        if good_rec.state == "QUARANTINED":
             print("FAIL: Healthy app was collateral damage (False Positive).")
             success = False

        if success:
            print("\n✅ PASS: System remained stable, identified threat, and protected healthy apps.")

    finally:
        p.terminate()
        p.join()

if __name__ == "__main__":
    # We need a real QApplication for the unregister/close logic if it hits
    app = QApplication(sys.argv)
    test_hardened_governance()
    app.quit()
