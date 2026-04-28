# =============================================================
#  tools/api_check.py — Q-Vault OS  |  SDK Diagnostic Tool
#
#  Verifies that the Public SDK can communicate with the OS.
#  Uses the Fact/Reaction model only.
# =============================================================

import sys
import time
from sdk.api import api
from sdk.events import STATE_CHANGED

def main():
    print("⬡ Q-Vault OS: SDK Diagnostic Tool")
    print("──────────────────────────────────")
    
    # 1. Check System State (Synchronous-style SDK call)
    print("[1/3] Fetching system state...")
    state = api.get_system_state()
    print(f"      Status: {state.get('status', 'offline')}")
    print(f"      User:   {state.get('user', 'guest')}")
    
    # 2. Test Notification (Request)
    print("[2/3] Sending diagnostic notification...")
    api.notify("SDK Check", "Diagnostic tool connected successfully.", "success")
    print("      Request emitted.")

    # 3. Test Subscription (Fact)
    print("[3/3] Listening for system facts (3s)...")
    def on_state(data):
        print(f"      RECVD: State update from system: {data}")
    
    api.subscribe(STATE_CHANGED, on_state)
    
    # Wait a bit for events
    time.sleep(3)
    print("──────────────────────────────────")
    print("Diagnostic Complete.")

if __name__ == "__main__":
    main()
