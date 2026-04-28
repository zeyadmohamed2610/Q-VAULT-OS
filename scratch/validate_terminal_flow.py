
import sys
import os
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

# Add workspace to sys.path
sys.path.append(os.getcwd())

from system.runtime_manager import RUNTIME_MANAGER
from apps.terminal.terminal_engine import TerminalEngine
from system.sandbox.secure_api import SecureAPI

def test_terminal_flow():
    print("--- Starting Terminal Flow Validation ---")
    
    # 1. Setup Runtime and Engine
    app_id = "Terminal"
    instance_id = "term_test_123"
    api = SecureAPI(app_id, instance_id=instance_id)
    engine = TerminalEngine(secure_api=api)
    
    # Force start app in runtime
    RUNTIME_MANAGER.start_app(app_id) # This will create a real record for Terminal_xxxx
    # We want to use our specific instance_id
    record = RUNTIME_MANAGER.register(instance_id, engine)
    record.state = "RUNNING"
    print(f"Registered instance: {instance_id}")

    output_captured = []
    engine.output_ready.connect(lambda text: output_captured.append(text))

    # 2. Test Input -> Engine -> Filesystem (ls)
    print("\n[Test 1] Testing 'ls' command...")
    engine.execute_command("ls")
    QCoreApplication.processEvents()
    if output_captured:
        print(f"Output: {output_captured[-1].strip()}")
    else:
        print("FAILED: No output captured for 'ls'")

    # 3. Test Sandbox boundaries (cd escape)
    print("\n[Test 2] Testing sandbox escape (cd ..)...")
    engine.execute_command("cd ..")
    QCoreApplication.processEvents()
    print(f"Output: {output_captured[-1].strip()}")
    
    # 4. Test Guards (Rate Limit / Penalty)
    print("\n[Test 3] Testing ProcessGuard Rate Limiting...")
    # ProcessGuard.run or Popen triggers check
    # We'll use 'ping' which is in allowlist but we'll call it fast
    # Wait, TerminalEngine.execute_command runs ping in a thread. 
    # We can call it directly on the guard for faster testing without threads.
    
    initial_trust = record.trust_score
    print(f"Initial Trust: {initial_trust}")
    
    print("Spamming ping via execute_command (threaded)...")
    for _ in range(15):
        engine.execute_command("ping 127.0.0.1")
        # We need to wait a tiny bit because it starts threads
        time.sleep(0.01)
    
    # Wait for some threads to hit the guard
    time.sleep(1.0)
    QCoreApplication.processEvents()
    
    print(f"Final Trust: {record.trust_score}")
    if record.trust_score < initial_trust:
        print("SUCCESS: Penalty applied for rate limiting.")
    else:
        print("FAILED: No penalty applied for rate limiting.")

    # 5. Confirm broken unregister
    print("\n[Test 4] Testing Lifecycle Cleanup...")
    RUNTIME_MANAGER.kill(instance_id)
    print(f"State after kill: {record.state}")
    
    if instance_id in RUNTIME_MANAGER._registry:
        print("CONFIRMED BUG: Instance still in registry after kill (Memory Leak).")
    else:
        print("Unexpected: Instance was unregistered.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_terminal_flow()
    sys.exit(0)
