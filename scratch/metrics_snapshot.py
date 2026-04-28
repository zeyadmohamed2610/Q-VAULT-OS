"""
scratch/metrics_snapshot.py
─────────────────────────────────────────────────────────────────────────────
Queries the live AppRuntimeManager state for a metrics snapshot.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import os
import time

sys.path.append(os.getcwd())

from system.runtime_manager import AppRuntimeManager

def get_snapshot():
    rm = AppRuntimeManager()
    print("--- Q-VAULT OS v1.0 METRICS SNAPSHOT ---")
    print(f"Uptime: {time.time() - rm.current_pressure_ratio:.1f}s (Approx)")
    print(f"Global Kills: {rm.global_kill_count}")
    print("-" * 40)
    
    with rm._lock:
        for iid, record in rm._registry.items():
            print(f"App: {record.app_id:<12} | Instance: {iid}")
            print(f"  Hz: {record.msg_hz:>6.1f} | PeakQ: {record.peak_queue_size:>3} | Trust: {record.trust_score:>3}")
            print(f"  Total Msgs: {record.total_msgs_handled}")
            print("-" * 40)

if __name__ == "__main__":
    get_snapshot()
