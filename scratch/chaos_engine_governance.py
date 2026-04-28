import sys
import os
import time
import json
import threading
import multiprocessing
import logging
from typing import Dict, List, Any

# Ensure we can import system modules
sys.path.append(os.getcwd())

# Force QApplication for QWidget support
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QCoreApplication
from system.runtime.ipc import AsyncIPCBridge, IPCProtocol
from system.runtime.isolated_widget import IsolatedAppWidget
from system.runtime_manager import AppRuntimeManager

# Redirect stderr to stdout 
sys.stderr = sys.stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stdout)
logger = logging.getLogger("chaos_engine")

def run_loop(duration: float):
    start = time.time()
    while time.time() - start < duration:
        QCoreApplication.processEvents()
        time.sleep(0.02)

def test_governance():
    print("\n--- TEST CASE: Governance & Kill Policy ---")
    rm = AppRuntimeManager()
    
    # 1. Non-critical (Terminal)
    logger.info("[KILL] Initializing Terminal instance...")
    mock_api = type('M', (), {'instance_id': 'chaos_u_01'})()
    term = IsolatedAppWidget("Terminal", "apps.terminal.terminal_app", "TerminalApp", secure_api=mock_api)
    
    # Authoritative Registration
    rec = rm.register(term.instance_id, term, "secret")
    rec.trust_score = 15 # Below 20 threshold
    
    logger.info(f"[KILL] Score set to {rec.trust_score}. Executing drain...")
    run_loop(1.0)
    
    if not term._proc.is_alive():
        print("Status: SUCCESS - Terminal killed authoritatively at trust 15.")
        term._proc.join(timeout=1.0)
        print("Status: SUCCESS - Process joined cleanly (No Zombies).")
    else:
        print(f"Status: FAILED - Terminal alive at score {rec.trust_score}")
        term._handle_crash("MANUAL_CLEANUP")

    # 2. Core Immunity (Desktop)
    logger.info("[IMMUNITY] Initializing Desktop instance...")
    mock_api2 = type('M', (), {'instance_id': 'chaos_u_02'})()
    desk = IsolatedAppWidget("Desktop", "apps.terminal.terminal_app", "TerminalApp", secure_api=mock_api2)
    
    rec2 = rm.register(desk.instance_id, desk, "secret")
    rec2.trust_score = 5 
    
    logger.info(f"[IMMUNITY] Core App score set to {rec2.trust_score}. Executing drain...")
    run_loop(1.0)
    
    if desk._proc.is_alive():
        print("Status: SUCCESS - Core App (Desktop) survived trust drop (Throttling enforced).")
    else:
        print("Status: FAILED - Core App was hard-killed.")
    
    desk._handle_crash("CLEANUP")

def run():
    qt_app = QApplication(sys.argv)
    test_governance()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
