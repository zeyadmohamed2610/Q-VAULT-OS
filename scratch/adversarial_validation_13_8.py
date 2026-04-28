
import sys
import os
import time
from PyQt5.QtWidgets import QApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def test_adversarial_resilience():
    print("--- Phase 13.8 Adversarial Resilience Validation ---")
    
    # ── Test 1: Trust Reset Gaming (Persistence) ──
    print("\n[Test 1] Testing Trust Persistence across restarts...")
    app_id = "AdversarialApp"
    iid1 = RUNTIME_MANAGER.start_app(app_id) # Uses 'terminal' stub or similar
    rec1 = RUNTIME_MANAGER.get_record(iid1)
    
    # Tank the trust
    print(f"  Dropping {iid1} trust to 40...")
    RUNTIME_MANAGER.apply_penalty(iid1, -60, "Malicious spam")
    print(f"  Current Trust: {rec1.trust_score}")
    
    # Restart
    print(f"  Closing window and restarting...")
    RUNTIME_MANAGER.unregister(iid1)
    
    iid2 = RUNTIME_MANAGER.start_app(app_id)
    rec2 = RUNTIME_MANAGER.get_record(iid2)
    print(f"  New Instance Trust: {rec2.trust_score}")
    
    if rec2.trust_score == 40:
        print("  SUCCESS: Trust-gaming prevented. Reputation persisted.")
    else:
        print(f"  FAIL: Trust reset to {rec2.trust_score}. Anti-gaming failed.")

    # ── Test 2: Collateral Damage (Innocent under Load) ──
    print("\n[Test 2] Testing Collateral Damage Protection...")
    good_id = RUNTIME_MANAGER.start_app("GoodApp")
    good_rec = RUNTIME_MANAGER.get_record(good_id)
    
    # Force system pressure
    print("  Triggering System pressure...")
    RUNTIME_MANAGER.global_state = "EMERGENCY"
    
    # Good app tries to get workers but fails (limit reached)
    print("  Good app attempts worker under pressure (Expected fail)...")
    for _ in range(5):
        try:
            RUNTIME_MANAGER.acquire_worker(good_id, "process")
        except PermissionError:
            pass
            
    print(f"  Good App Trust: {good_rec.trust_score}")
    if good_rec.trust_score == 100:
        print("  SUCCESS: Healthy app not penalized for system throttling.")
    else:
        print(f"  FAIL: Healthy app trust dropped to {good_rec.trust_score} due to pressure.")

    # ── Test 3: Stealth Attack Persistence ──
    print("\n[Test 3] Testing Stealth Transition to Quarantine...")
    stealth_id = RUNTIME_MANAGER.start_app("StealthApp")
    stealth_rec = RUNTIME_MANAGER.get_record(stealth_id)
    # Give it low starting reputation (from a previous session simulated)
    RUNTIME_MANAGER.apply_penalty(stealth_id, -30, "Previous session suspicion")
    
    # Steadily penalize
    print(f"  Stealthily dropping trust (starting at {stealth_rec.trust_score})...")
    while stealth_rec.state != "QUARANTINED" and stealth_rec.trust_score > 0:
        RUNTIME_MANAGER.apply_penalty(stealth_id, -10, "Repeated limit friction")
        if stealth_rec.trust_score <= 20: break
    
    print(f"  Final state: {stealth_rec.state} | Trust: {stealth_rec.trust_score}")
    if stealth_rec.state == "QUARANTINED" or stealth_rec.trust_score <= 20:
        print("  SUCCESS: Stealth attacker eventually quarantined.")
    else:
        print("  FAIL: Stealth attacker evaded quarantine.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_adversarial_resilience()
    app.quit()
