
import sys
import os
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def verify_fix():
    print("--- Verifying Critical Registry & Telemetry Fixes ---")
    
    # 1. Start an app
    instance_id = RUNTIME_MANAGER.start_app("Terminal")
    record = RUNTIME_MANAGER.get_record(instance_id)
    print(f"App Started: {instance_id}")
    
    # 2. Check Telemetry for new fields
    data = RUNTIME_MANAGER.list_running()
    app_data = next(a for a in data['apps'] if a['id'] == instance_id)
    
    print("\n[Telemetry Check]")
    fields = ["active_workers", "max_workers", "worker_usage"]
    all_present = True
    for f in fields:
        if f in app_data:
            print(f"  OK: Found {f} = {app_data[f]}")
        else:
            print(f"  FAIL: Missing {f}")
            all_present = False
            
    # 3. Test Penalty Debounce removal
    print("\n[Penalty Check] Spamming 5 penalties in 100ms...")
    initial_trust = record.trust_score
    for _ in range(5):
        RUNTIME_MANAGER.apply_penalty(instance_id, -5, "Verification Spam")
        # No sleep
    
    print(f"  Current Trust: {record.trust_score}")
    # Expected: 100 - (5 * 5) = 75
    if record.trust_score == initial_trust - 25:
        print("  SUCCESS: High-speed penalty debounce removed.")
    else:
        print(f"  FAIL: Trust is {record.trust_score}, expected {initial_trust - 25} (still debounced?)")

    # 4. Check Registry Leak Fix
    print("\n[Cleanup Check] Killing instance...")
    RUNTIME_MANAGER.kill(instance_id)
    print(f"  State after kill: {record.state}")
    
    # Explicit unregister (as called by OSWindow._final_close)
    print("  Calling unregister...")
    RUNTIME_MANAGER.unregister(instance_id)
    
    if instance_id not in RUNTIME_MANAGER._registry:
        print("  SUCCESS: Instance purged from registry (Memory Leak FIXED).")
    else:
        print("  FAIL: Instance still in registry after unregister.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    verify_fix()
    app.quit()
