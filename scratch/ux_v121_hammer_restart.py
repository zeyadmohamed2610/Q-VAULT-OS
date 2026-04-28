import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication

# Mocking parts of the system for standalone verification
os.environ["PYTHONPATH"] = "."

from system.runtime.isolated_widget import IsolatedAppWidget
from system.runtime.app_controller_isolated import RuntimeState

def hammer_verification_run():
    app = QApplication(sys.argv)
    
    print("[*] Starting v1.2.1 Hammer Restart Test...")
    
    # Mock SecureAPI
    class MockAPI:
        def __init__(self):
            self.instance_id = "hammer_instance"
            class MockFS:
                def list_dir(self, path): return []
            self.fs = MockFS()

    api = MockAPI()
    
    # Create the widget
    widget = IsolatedAppWidget("HammerApp", "apps.terminal.terminal_app", "TerminalApp", secure_api=api)
    widget.show()
    
    def hammer():
        time.sleep(2) # Wait for initial boot
        
        print("[!] Hammering RESTART button (5 times in 200ms)...")
        # Direct call to restart to simulate button clicks bypassing debounce logic 
        # or testing the lock/debounce inside the controller
        for i in range(5):
            print(f"    - Attempt {i+1}")
            widget.controller.restart()
            time.sleep(0.04) # 40ms interval

        print("[*] Monitoring PIDs (Should only have ONE active process link)...")
        time.sleep(5)
        
        # Verify that only the last one is running/booting
        print(f"[*] Final State: {widget.controller.state}")
        
        time.sleep(2)
        print("[*] Hammer Test Complete.")
        app.quit()

    threading.Thread(target=hammer, daemon=True).start()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    hammer_verification_run()
