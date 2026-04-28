
import sys
import os
import time
from pathlib import Path

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER
from system.sandbox.process_guard import ProcessGuard

def test_guard_penalty():
    print("--- Testing Guard Penalty Logic ---")
    
    app_id = "penalty_test_app"
    instance_id = "penalty_inst_123"
    
    # Manually register
    record = RUNTIME_MANAGER.register(instance_id, None)
    record.state = "RUNNING"
    
    # Create guard for this instance
    # Mocking a simple API with the right instance_id
    class MockAPI:
        def __init__(self, iid): self.instance_id = iid
        def check_api_lock(self, t): pass
    
    api = MockAPI(instance_id)
    guard = ProcessGuard(app_id, api=api)
    
    print(f"Initial Trust: {record.trust_score}")
    
    # Spam calls (more than 13)
    # The first 10 calls: count 0..9.
    # The 11th call: count 10, overflow 0.
    # The 12th call: count 11, overflow 1.
    # The 13th call: count 12, overflow 2.
    # The 14th call: count 13, overflow 3. -> PENALTY
    
    for i in range(20):
        try:
            guard._enforce_rate_limit()
        except Exception:
            pass
    
    print(f"Final Trust: {record.trust_score}")
    
    if record.trust_score < 100:
        print("SUCCESS: Penalty applied.")
    else:
        print("FAILED: No penalty applied.")

if __name__ == "__main__":
    test_guard_penalty()
