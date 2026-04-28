import time
import sys
import os
from system.analytics import ANALYTICS

def saturation_test(frequency=100, duration=10):
    print(f"[*] Starting Analytics Saturation: {frequency}Hz for {duration}s")
    
    total_events = frequency * duration
    interval = 1.0 / frequency
    
    latencies = []
    start_time = time.time()
    
    for i in range(total_events):
        t0 = time.perf_counter()
        ANALYTICS.track_event("stress_test_event", {"index": i, "load": "high"})
        dt = (time.perf_counter() - t0) * 1000 # convert to ms
        latencies.append(dt)
        
        # Sleep to maintain frequency
        elapsed = time.perf_counter() - t0
        if elapsed < interval:
            time.sleep(interval - elapsed)
            
    total_time = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    print("\n--- Saturation Results ---")
    print(f"Total Events: {len(latencies)}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Avg Latency: {avg_latency:.4f}ms")
    print(f"Max Latency: {max_latency:.4f}ms")
    
    if avg_latency <= 5.0:
        print("[SUCCESS] Latency check PASSED (<= 5ms)")
    else:
        print("[FAILURE] Latency check FAILED (> 5ms)")

if __name__ == "__main__":
    # Ensure qvault_home exists
    os.environ["PYTHONPATH"] = "."
    saturation_test()
