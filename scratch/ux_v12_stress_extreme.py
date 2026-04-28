import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QGridLayout
from PyQt5.QtCore import Qt

# Mocking parts of the system for standalone verification
os.environ["PYTHONPATH"] = "."

from system.runtime.isolated_widget import IsolatedAppWidget
from system.runtime.app_controller_isolated import RuntimeState

def extreme_verification_run():
    app = QApplication(sys.argv)
    
    main_win = QWidget()
    main_win.setWindowTitle("Q-Vault v1.2 Extreme Stress Test")
    layout = QGridLayout(main_win)
    
    # Mock SecureAPI
    class MockAPI:
        def __init__(self, iid):
            self.instance_id = iid
            class MockFS:
                def list_dir(self, path): return [".", ".."]
            self.fs = MockFS()

    apps = []
    print("[*] Launching 9 Isolated Apps simultaneously...")
    for i in range(9):
        api = MockAPI(f"stress_instance_{i}")
        widget = IsolatedAppWidget(f"App_{i}", "apps.terminal.terminal_app", "TerminalApp", secure_api=api)
        layout.addWidget(widget, i // 3, i % 3)
        apps.append(widget)

    main_win.show()
    main_win.resize(1200, 800)
    
    def run_scenarios():
        time.sleep(3) # Let them all boot
        
        # 1. State Mapping Sync Check
        print("[*] Simulating Mixed Load Across Apps...")
        apps[0].controller.state_changed.emit(RuntimeState.CONGESTED) # Should say "Optimizing Load"
        apps[1].controller.metrics_updated.emit(200.0, 2, 100) # Should say "Hyper-Fast"
        apps[2].controller.metrics_updated.emit(10.0, 30, 100) # Should say "Heavy Load"
        
        time.sleep(3)
        
        # 2. Crash & Restart Scenario
        print("[*] Crashing App_4 and App_5...")
        apps[4].controller._handle_shutdown("SIMULATED_FAILURE")
        apps[5].controller._handle_shutdown("SIMULATED_RESTART_TEST")
        
        time.sleep(3)
        
        # 3. Focus Toggle Check
        print("[*] Toggling Focus simulation (App_0)...")
        # In a real GUI, focus would be sent by the OS, but we'll print confirmation
        print("Note: In manual testing, click on an app to see 'Focus Mode' (badge fade).")
        
        time.sleep(3)
        print("[*] Closing Stress Test.")
        app.quit()

    threading.Thread(target=run_scenarios, daemon=True).start()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    extreme_verification_run()
