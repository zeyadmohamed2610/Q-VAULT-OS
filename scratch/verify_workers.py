
import sys
import os
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER

def check_workers_reporting():
    print("--- Checking Worker Reporting and Lifecycle ---")
    
    # 1. Start an app
    instance_id = RUNTIME_MANAGER.start_app("Terminal")
    record = RUNTIME_MANAGER.get_record(instance_id)
    print(f"App: {record.app_id} | Instance: {instance_id}")
    
    # 2. Acquire a worker
    print("Acquiring worker...")
    RUNTIME_MANAGER.acquire_worker(instance_id, "network", "tk_123")
    print(f"Active Workers (Total): {record.active_workers['total']}")
    print(f"Active Workers (Network): {record.active_workers['network']}")
    
    # 3. Check list_running output
    data = RUNTIME_MANAGER.list_running()
    app_data = next(a for a in data['apps'] if a['id'] == instance_id)
    
    print("\nTelemetry Data for UI:")
    for k, v in app_data.items():
        print(f"  {k}: {v}")
    
    if "active_workers" not in app_data:
        print("\nCONFIRMED BUG: 'active_workers' is MISSING from telemetry list_running().")
        print("UI cannot display real worker truth.")

    # 4. Check unregister leak
    print("\nKilling app...")
    RUNTIME_MANAGER.kill(instance_id)
    print(f"Registry size after kill: {len(RUNTIME_MANAGER._registry)}")
    
    # We wait a bit in case there's async cleanup (there isn't)
    time.sleep(0.5)
    
    if instance_id in RUNTIME_MANAGER._registry:
        print("CONFIRMED BUG: Registry still contains instance after kill (Lifecycle Leak).")
    else:
        print("Instance was removed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_workers_reporting()
    sys.exit(0)
