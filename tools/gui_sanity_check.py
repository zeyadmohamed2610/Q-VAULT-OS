# =============================================================
#  tools/gui_sanity_check.py — Q-Vault OS
#
#  Catches initialization crashes that headless audits miss.
# =============================================================

import sys
import os
from PyQt5.QtWidgets import QApplication

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_sanity_check():
    print("Starting GUI Sanity Check...")
    
    # Initialize a dummy application
    app = QApplication(sys.argv)
    
    try:
        print("1. Testing TaskbarUI Initialization...")
        from components.taskbar_ui import TaskbarUI
        taskbar = TaskbarUI()
        print("   PASS: TaskbarUI initialized without crash.")
        
        print("2. Testing Desktop Initialization...")
        from components.desktop import Desktop
        desktop = Desktop()
        print("   PASS: Desktop initialized without crash.")
        
        print("3. Testing CommandPalette Initialization...")
        from components.command_palette import CommandPalette
        palette = CommandPalette(desktop)
        print("   PASS: CommandPalette initialized without crash.")
        
    except Exception as e:
        print(f"\n❌ FATAL INITIALIZATION ERROR:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✅ ALL GUI COMPONENTS PASSED INITIALIZATION CHECK.")
    sys.exit(0)

if __name__ == "__main__":
    run_sanity_check()
