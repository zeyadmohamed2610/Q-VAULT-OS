import os
import sys
import stat
from system.analytics import ANALYTICS

def simulate_disk_failure():
    print("[*] Starting Disk Failure Simulation")
    
    # 1. Identify log file
    log_file = ANALYTICS._event_log_file
    print(f"[*] Target Log: {log_file}")
    
    # 2. Force some events (Baseline)
    ANALYTICS.track_event("before_failure")
    
    # 3. REVOKE Permissions (Simulate failure)
    print("[!] REVOKING WRITE PERMISSIONS...")
    original_mode = os.stat(log_file).st_mode
    try:
        # On Windows, we might need to useicacls or similar, 
        # but os.chmod(S_IREAD) usually works for basic "Permission denied".
        os.chmod(log_file, stat.S_IREAD)
        
        # 4. Trigger event (Should fail silently in Kernel)
        print("[*] Triggering event under failure...")
        ANALYTICS.track_event("during_failure", {"critical": True})
        
        print("[✅] SUCCESS: System did not crash.")
        
    finally:
        # 5. RESTORE Permissions
        print("[*] Restoring permissions...")
        os.chmod(log_file, stat.S_IWRITE)
        os.chmod(log_file, original_mode)
        
    # 6. Verify one last event
    ANALYTICS.track_event("after_failure")
    print("[*] Simulation Completed.")

if __name__ == "__main__":
    os.environ["PYTHONPATH"] = "."
    simulate_disk_failure()
