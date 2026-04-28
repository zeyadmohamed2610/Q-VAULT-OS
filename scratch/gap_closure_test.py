
import sys
import os
import time
from PyQt5.QtWidgets import QApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER
from core.process_manager import PM

def test_governance_gap_closure():
    print("--- Phase 13.9 Governance Gap Closure Verification ---")
    
    # Use a real app ID so it doesn't get auto-quarantined as a stub
    app_id = "Terminal" 
    iid = RUNTIME_MANAGER.start_app(app_id)
    rec = RUNTIME_MANAGER.get_record(iid)
    
    print(f"App Registered: {iid}")
    print(f"Initial Workers: {rec.active_workers['process']}")

    # 1. Test Governed Spawn
    print("\n[Step 1] Attempting Governed Spawn (ping)...")
    # 'ping' is in allowlist
    handle = RUNTIME_MANAGER.spawn_process(iid, "ping", "ping 127.0.0.1", background=True)
    
    if handle:
        print(f"  SUCCESS: Process spawned. Worker count: {rec.active_workers['process']}")
    else:
        print("  FAIL: Process handle not returned.")

    # 2. Test Accounting (Natural Exit simulation)
    print("\n[Step 2] Testing Automated Accounting (Natural Exit)...")
    # Find the PID
    procs = PM.background_jobs()
    the_proc = next((p for p in procs if p['owner'] == iid), None)
    if the_proc:
        pid = the_proc['pid']
        print(f"  Found PID: {pid}. Manually completing it to trigger observer...")
        PM._complete(pid)
        # Wait a tick for observer
        time.sleep(0.1)
        print(f"  Worker count after 'done' event: {rec.active_workers['process']}")
    else:
        print("  FAIL: Process not found in PM table.")

    # 3. Test Lifecycle Cleanup (Force Close)
    print("\n[Step 3] Testing Lifecycle Cleanup (App Close)...")
    # Spawn another
    handle2 = RUNTIME_MANAGER.spawn_process(iid, "ping", "ping 127.0.0.1", background=True)
    print(f"  Worker count after 2nd spawn: {rec.active_workers['process']}")
    
    print("  Unregistering app (Simulating window close)...")
    RUNTIME_MANAGER.unregister(iid)
    
    # Check if PM still has it
    remaining = [p for p in PM.background_jobs() if p['owner'] == iid]
    print(f"  Processes remaining for {iid}: {len(remaining)}")
    if not remaining:
        print("  SUCCESS: Lifecycle cleanup killed all child processes.")
    else:
        print("  FAIL: ZOMBIE DETECTED.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_governance_gap_closure()
    app.quit()
