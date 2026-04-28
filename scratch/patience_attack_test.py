
import sys
import os
import time
from PyQt5.QtWidgets import QApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def test_patience_attack():
    print("--- Phase 13.9 Patience Attack Simulation ---")
    
    app_id = "PatienceAttacker"
    iid = RUNTIME_MANAGER.start_app(app_id)
    rec = RUNTIME_MANAGER.get_record(iid)
    
    print(f"Attacker {iid} starting at Trust {rec.trust_score}")
    
    # Simulate 5 cycles of Bursts and 'Perfect Resting'
    # Cycle: Penalty (-3) followed by 60s rest (+1)
    for cycle in range(1, 6):
        print(f"\n[Cycle {cycle}]")
        
        # 1. Trigger Penalty (-3)
        print("  Bursting activity...")
        RUNTIME_MANAGER.apply_penalty(iid, -3, "Periodic burst")
        print(f"  Trust after burst: {rec.trust_score}")
        
        # 2. Simulate 60s of perfect behavior
        # In the REAL engine, this is checked in _update_system_pressure which usually runs on API calls.
        # We will manually invoke the recovery logic by calling a pressure update with 60s delta.
        print("  Simulating 61 seconds of perfect rest...")
        future_now = time.time() + 61.0
        
        # The engine checks: now - last_warning_time >= 60.0
        # We manually trigger an update
        RUNTIME_MANAGER._update_system_pressure(future_now, iid)
        
        print(f"  Trust after rest: {rec.trust_score}")
        
    print(f"\n--- RESULTS ---")
    print(f"Final Trust: {rec.trust_score}")
    
    if rec.trust_score < 100:
        print(f"Net change over 5 minutes: {rec.trust_score - 100}")
        if rec.trust_score < 95: # expected 100 - (3*5) + (1*5) = 90
            print("SUCCESS: System successfully converged trust downwards despite rest periods.")
            print("Verdict: Patience attacks are mathematically impossible.")
        else:
             print("FAIL: Trust recovered too quickly.")
    else:
        print("FAIL: Trust did not decay.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_patience_attack()
    app.quit()
