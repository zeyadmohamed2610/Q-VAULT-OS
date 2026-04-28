import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# Mocking parts of the system for standalone verification
os.environ["PYTHONPATH"] = "."

from core.app_registry import REGISTRY
from system.runtime.app_controller_isolated import RuntimeState

def chaos_certification_run():
    app = QApplication(sys.argv)
    
    main_win = QWidget()
    main_win.setWindowTitle("Q-Vault v1.2.1 Chaos Certification")
    layout = QVBoxLayout(main_win)
    
    print("[*] Starting v1.2.1 Chaos Certification (Stability Audit)...")

    # 1. Cold Start Profiling
    def profile_cold_start():
        print("\n[A] Profiling Cold Start...")
        t0 = time.perf_counter()
        
        # Instantiate Terminal (should be proxi'd by AppRegistry now)
        widget = REGISTRY.instantiate_by_name("Terminal", parent=main_win)
        t_instantiated = time.perf_counter()
        
        if widget is None:
            print("[!] ERROR: Terminal instantiation failed.")
            return

        layout.addWidget(widget)
        print(f"    - Proxy Instantiation: {(t_instantiated - t0)*1000:.2f}ms")
        
        # The widget should show BOOTING immediately
        # We'll wait for it to reach RUNNING
        
        time.sleep(2) # Let it boot
        print(f"    - App Controller State: {widget.controller.state}")
        return widget

    def run_chaos_scenarios(widget):
        # 2. Zombie Cleanup Audit (os.kill)
        print("\n[B] Simulating External Process Kill (Zombie Audit)...")
        pid = widget.controller._proc.pid
        print(f"    - Killing PID {pid} externally...")
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"    - Kill failed: {e}")
            
        time.sleep(1) # Drain loop should detect death
        print(f"    - State after kill: {widget.controller.state}")
        if widget.controller.state == RuntimeState.TERMINATED:
            print("    - SUCCESS: Drain loop detected external death.")
        else:
            print("    - FAILURE: System still thinks app is running.")

        # 3. Functional Restart from Death
        print("\n[C] Verifying Recovery from Death...")
        widget.controller.restart()
        time.sleep(1)
        print(f"    - State after restart signal: {widget.controller.state}")
        
        # 4. Rapid Open/Close (Churn)
        print("\n[D] Testing Rapid Churn (Focusing on resource cleanup)...")
        for i in range(3):
            print(f"    - Churn Cycle {i+1}...")
            temp_widget = REGISTRY.instantiate_by_name("Terminal", parent=None)
            time.sleep(0.1)
            temp_widget.controller.stop()
            del temp_widget
        
        print("\n[E] Chaos Test Complete. Closing in 3s...")
        time.sleep(3)
        app.quit()

    widget = profile_cold_start()
    main_win.show()
    main_win.resize(600, 400)
    
    if widget:
        threading.Thread(target=run_chaos_scenarios, args=(widget,), daemon=True).start()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    chaos_certification_run()
