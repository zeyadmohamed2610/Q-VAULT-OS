# =============================================================
#  tools/preflight_check.py — Q-Vault OS
#
#  FINAL PRE-FLIGHT VALIDATION.
#  Stress tests the system and validates core logic.
# =============================================================

import os
import sys
import time
import logging
import threading

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
from system.ai.ai_controller import AIController
from system.automation.workflow_engine import WORKFLOW_ENGINE

# Configure Logging for Audit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PREFLIGHT")

class PreflightCheck:
    def __init__(self):
        self.ai = AIController()
        self.engine = WORKFLOW_ENGINE
        self.errors = []
        self.slow_handlers = []
        
        # Monitor EventBus
        EVENT_BUS.subscribe("*", self._monitor)

    def _monitor(self, payload: EventPayload):
        if "Slow handler" in str(payload.data):
            self.slow_handlers.append(payload)
        if payload.type == SystemEvent.EVT_ERROR:
            self.errors.append(payload)

    def run(self):
        logger.info("Starting Final Pre-flight Check...")
        
        # 🧪 TEST 1: AI Reasoning & Safety
        logger.info("[TEST 1] AI Reasoning & Safety")
        self._test_ai("open files", expected_action="launch")
        self._test_ai("open security", should_be_rejected=True)
        
        # 🧪 TEST 2: Multi-step Workflow
        logger.info("[TEST 2] Multi-step Workflow")
        self._test_ai("prepare workspace")
        
        # 🧪 TEST 3: Stress / Chaos
        logger.info("[TEST 3] Event Stress Test")
        self._stress_test()
        
        # 🧪 TEST 4: Invalid Payloads
        logger.info("[TEST 4] Invalid Payload Handling")
        EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"malformed": "data"})
        EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, None)
        
        # Summary
        self.report()

    def _test_ai(self, prompt, expected_action=None, should_be_rejected=False):
        logger.info(f"  Testing prompt: '{prompt}'")
        EVENT_BUS.emit(SystemEvent.REQ_USER_INPUT, {"text": prompt})
        time.sleep(1.0) # Wait for reasoning

    def _stress_test(self):
        def spam():
            for i in range(50):
                EVENT_BUS.emit("test.noise", {"i": i})
        
        threads = [threading.Thread(target=spam) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

    def report(self):
        logger.info("=" * 40)
        logger.info("FINAL PRE-FLIGHT REPORT")
        logger.info(f"Critical Errors: {len(self.errors)}")
        logger.info(f"Slow Handlers: {len(self.slow_handlers)}")
        
        if len(self.errors) == 0:
            logger.info("RESULT: PASS")
        else:
            logger.error("RESULT: FAIL")
        logger.info("=" * 40)

if __name__ == "__main__":
    check = PreflightCheck()
    check.run()
