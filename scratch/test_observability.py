
import sys
import os
import time
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def test_observability():
    print("--- Testing Phase 13.6 Observability Engine ---")
    
    # Register an app to test explanation
    RUNTIME_MANAGER.register("test_app_1", None)
    
    # 1. Trigger many calls to force a pressure state change
    print("Simulating load spike...")
    for _ in range(50):
        RUNTIME_MANAGER.acquire_worker("test_app_1", "process")
    
    # 2. Check Decision History
    print(f"Decisions in history: {len(RUNTIME_MANAGER.decision_history)}")
    if RUNTIME_MANAGER.decision_history:
        last = RUNTIME_MANAGER.decision_history[-1]
        print(f"Latest Decision: {last['state_after']} | Reason: {last['reason']}")
        print(f"Affected Apps Captured: {len(last['affected_apps'])}")
        
    # 3. Check Pressure History
    print(f"Pressure History samples: {len(RUNTIME_MANAGER.pressure_history)}")
    
    # 4. Check NDJSON Persistence
    print("Forcing log flush...")
    RUNTIME_MANAGER._flush_governance_log(force=True)
    
    log_path = Path(".logs/governance.json")
    if log_path.exists():
        print(f"SUCCESS: governance.json exists ({log_path.stat().st_size} bytes)")
    else:
        print("FAIL: governance.json not found.")

    # 5. Check Explanation
    print("\n[Explain Test]")
    exp = RUNTIME_MANAGER.get_explanation("test_app_1")
    if "error" in exp:
        print(f"FAIL: {exp['error']}")
    else:
        print(f"Explain app_id: {exp['app_id']}")
        print(f"Final Worker Limit: {exp['final_worker_limit']}")
        print(f"Reasons: {exp['reasons']}")
        print(f"Human MSG: {exp['explanation']}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_observability()
    app.quit()
