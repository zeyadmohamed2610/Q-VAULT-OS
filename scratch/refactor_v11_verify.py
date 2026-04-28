import sys
import os
import time
import threading
from PyQt5.QtWidgets import QApplication

# Mocking parts of the system for standalone verification
os.environ["PYTHONPATH"] = "."

from system.runtime.isolated_widget import IsolatedAppWidget
from system.runtime.app_controller_isolated import RuntimeState
from system.runtime_manager import AppRuntimeManager

def verification_run():
    app = QApplication(sys.argv)
    
    print("[*] Launching Refactored IsolatedAppWidget (v1.1)...")
    
    # We need a mock SecureAPI
    class MockAPI:
        def __init__(self):
            self.instance_id = "test_instance_123"
            class MockFS:
                def list_dir(self, path): return [".", ".."]
            self.fs = MockFS()

    api = MockAPI()
    
    # Create the widget
    # Using a known app (e.g. apps.terminal)
    widget = IsolatedAppWidget("TestApp", "apps.terminal.terminal_app", "TerminalApp", secure_api=api)
    widget.show()
    widget.resize(800, 600)
    
    # Verification Sequence
    def run_scenarios():
        time.sleep(2) # Wait for handshake
        
        # 1. Simulate CONGESTED
        print("[*] Simulating CONGESTED (qsize > 50)...")
        # Manually manipulate the internal qsize metric inside the record
        rm = AppRuntimeManager()
        record = rm.get_record(api.instance_id)
        if record:
            # We override the bridge's qsize report in the next governance loop
            # For this test, we'll just emit the signal directly from controller to test UI
            widget.controller.state_changed.emit(RuntimeState.CONGESTED)
            
        time.sleep(2)
        
        # 2. Simulate RECOVERING
        print("[*] Simulating RECOVERING...")
        widget.controller.state_changed.emit(RuntimeState.RECOVERING)
        
        time.sleep(1)
        
        # 3. Restore to RUNNING
        print("[*] Restoring to RUNNING...")
        widget.controller.state_changed.emit(RuntimeState.RUNNING)
        
        time.sleep(2)
        
        # 4. Final: Terminate
        print("[*] Simulating TERMINATED...")
        widget.controller.crashed.emit("MANUAL_VERIFICATION_KILL")
        
        time.sleep(2)
        print("[*] Closing verification.")
        app.quit()

    threading.Thread(target=run_scenarios, daemon=True).start()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    verification_run()
