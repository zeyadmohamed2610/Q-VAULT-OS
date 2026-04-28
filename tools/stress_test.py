# =============================================================
#  tools/stress_test.py — Q-Vault OS
#
#  System Stability & Load Testing Tool.
#  Simulates high event traffic to verify EventBus resilience.
# =============================================================

import time
import random
import threading
from sdk.api import api
from sdk.events import REQ_APP_LAUNCH, REQ_WINDOW_DRAG_UPDATE

def simulate_load(duration_sec=10, events_per_sec=100):
    """
    Simulates high event load by flooding the EventBus with
    synthetic drag and app-launch requests.
    """
    print(f"🚀 Starting Stress Test: {events_per_sec} EPS for {duration_sec}s")
    start_time = time.time()
    count = 0
    
    # Target delay between events
    delay = 1.0 / events_per_sec
    
    while time.time() - start_time < duration_sec:
        # Simulate a Window Drag Update
        api.emit(REQ_WINDOW_DRAG_UPDATE, {
            "id": f"test_win_{random.randint(1, 5)}",
            "pos": {"x": random.randint(0, 1000), "y": random.randint(0, 1000)},
            "mouse_pos": {"x": 500, "y": 500}
        })
        
        # Occasionally launch apps
        if count % 50 == 0:
            api.emit(REQ_APP_LAUNCH, {"module": "Files"})
            
        count += 1
        time.sleep(delay)
        
    print(f"✅ Stress Test Complete. Total Events: {count}")

if __name__ == "__main__":
    # We run in a separate thread to not block if we were a plugin,
    # but as a tool we just run it directly.
    simulate_load()
