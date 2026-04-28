# =============================================================
#  tools/system_audit.py — Q-Vault OS
#
#  Automated System Validation & Audit Tool.
#  Simulates user behavior and verifies event-driven correctness.
# =============================================================

import sys
import os
import time
import logging

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EVENT_BUS, SystemEvent
from sdk.api import QVaultAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AUDIT")

class SystemAudit:
    def __init__(self):
        # Initialize System Logic (Isolated)
        from system.ai.ai_controller import AIController
        from system.automation.workflow_engine import WORKFLOW_ENGINE
        
        self.ai = AIController()
        self.engine = WORKFLOW_ENGINE
        
        # Register default workflows for testing
        self.ai.translator.execute_action("notify", {"message": "Audit Mode Active"})
        
        self.api = QVaultAPI()
        self.decisions = []
        self.rejections = []
        self.notifications = []
        
        # ── Listeners ──
        EVENT_BUS.subscribe(SystemEvent.EVT_AI_DECISION, lambda p: self.decisions.append(p.data))
        EVENT_BUS.subscribe(SystemEvent.EVT_AI_REJECTED_ACTION, lambda p: self.rejections.append(p.data))
        EVENT_BUS.subscribe(SystemEvent.NOTIFICATION_SENT, lambda p: self.notifications.append(p.data))

    def run_suite(self):
        logger.info("🚀 Starting Full System Audit...")
        
        # ── Test 1: AI Intent (Single Step) ──
        logger.info("[TEST 1] AI Intent: 'open files'")
        self.api.emit(SystemEvent.REQ_USER_INPUT.value, {"text": "open files"})
        time.sleep(1)
        self._verify("AI Decision for Launch", any(d.get("action") == "launch" for d in self.decisions))

        # ── Test 2: AI Safety Gate ──
        logger.info("[TEST 2] AI Safety: 'open security'")
        self.api.emit(SystemEvent.REQ_USER_INPUT.value, {"text": "open security"})
        time.sleep(1)
        self._verify("AI Safety Rejection", any("restricted" in r.get("reasoning", "").lower() for r in self.rejections))

        # ── Test 3: Multi-step Workflow ──
        logger.info("[TEST 3] Multi-step: 'prepare workspace'")
        self.api.emit(SystemEvent.REQ_USER_INPUT.value, {"text": "prepare workspace"})
        time.sleep(2)
        # Should have at least 3 steps (Launch Files, Launch Terminal, Notify)
        self._verify("Workflow Chain Execution", len(self.decisions) >= 3)

        # ── Test 4: Automation Trigger ──
        logger.info("[TEST 4] Automation: Manual 'sys.welcome' trigger")
        self.api.emit("sys.welcome", {})
        time.sleep(1)
        self._verify("Welcome Workflow Notification", any("Welcome" in n.get("message", "") for n in self.notifications))

        logger.info("✅ Audit Complete.")

    def _verify(self, name, condition):
        if condition:
            logger.info(f"  PASS: {name}")
        else:
            logger.error(f"  FAIL: {name}")

if __name__ == "__main__":
    # We need a running EventBus instance. 
    # Since we can't easily attach to the running process without IPC,
    # we'll just run this script which starts its own EventBus instance
    # to verify the logic in isolation.
    
    # Wait for the system to settle if running in parallel
    audit = SystemAudit()
    audit.run_suite()
