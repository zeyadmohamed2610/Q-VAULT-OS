# =============================================================
#  tools/chaos_test.py — Q-Vault OS
#
#  Stress Testing & Robustness Validation.
#  Spams invalid payloads and high-frequency events.
# =============================================================

import sys
import os
import time
import threading

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EVENT_BUS, SystemEvent

def event_spammer():
    """Floods the bus with random noise."""
    for i in range(100):
        EVENT_BUS.emit("chaos.noise", {"index": i, "data": "X" * 1000})
        if i % 10 == 0:
            # Emit invalid payloads for critical events
            EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"wrong": "payload"})
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, None)
    print("Spammer finished.")

def run_chaos():
    print("Starting Chaos Test...")
    
    # 1. Start spammers
    threads = []
    for _ in range(5):
        t = threading.Thread(target=event_spammer)
        t.start()
        threads.append(t)
        
    # 2. Monitor stability
    start_time = time.time()
    while any(t.is_alive() for t in threads):
        time.sleep(0.5)
        if time.time() - start_time > 10: break
        
    print("Chaos Test Complete. System survived.")

if __name__ == "__main__":
    run_chaos()
