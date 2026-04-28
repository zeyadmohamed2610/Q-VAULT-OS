import sys
import logging
from PyQt5.QtWidgets import QApplication

def run_tests():
    app = QApplication(sys.argv)
    
    # Configure logger for capturing Output
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("sandbox.test")
    
    logger.info("========== PHASE 5.5-A OBSERVATION TESTS ==========")

    # 1. Test Network Tools
    logger.info("--- Testing NetworkTools ---")
    try:
        from apps.network_tools import NetworkTools, PingWorker
        net_app = NetworkTools()
        # The user's evil payload
        payload = "127.0.0.1 & dir"
        net_app._ping_host.setText(payload)
        
        # Manually invoke worker (Simulating UI click)
        worker = PingWorker(payload, 1)
        worker.result.connect(lambda txt, col: logger.info(f"[PingWorker] {txt}"))
        worker.run() # Run synchronously for testing
        
        # Check if subprocess was triggered dangerously
        logger.info("[NetworkTools] Result captured.")

    except Exception as e:
        logger.error(f"NetworkTools failed: {e}")

    # 2. Test Terminal Engine
    logger.info("--- Testing TerminalEngine ---")
    try:
        from apps.terminal.terminal_engine import TerminalEngine
        engine = TerminalEngine()
        payload = "cd ../../"
        engine.output_ready.connect(lambda txt: logger.info(f"[Terminal] {txt}"))
        engine.execute_command(payload)
        logger.info("[Terminal] Execution requested.")
        
    except Exception as e:
        logger.error(f"TerminalEngine failed: {e}")

    # 3. Test File Explorer
    logger.info("--- Testing File Explorer ---")
    try:
        from apps.file_explorer import RealFileExplorer
        explorer = RealFileExplorer()
        payload = "C:\\Windows"

        # Simulate typing path and hitting enter
        explorer._addr_bar.setText(payload)
        explorer._on_address_enter()
        logger.info(f"[FileExplorer] Current Path stayed at: {explorer._current_path}")

    except Exception as e:
        logger.error(f"FileExplorer failed: {e}")

    logger.info("========== TESTS COMPLETED ==========")
    # app.exec_() not needed since we bypass events
    
if __name__ == "__main__":
    run_tests()
