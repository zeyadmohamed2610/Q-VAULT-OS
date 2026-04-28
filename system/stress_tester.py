import time
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from core.event_bus import SystemEvent, EVENT_BUS
from system.sequence_engine import SEQUENCE_ENGINE
from system.context_engine import CONTEXT_ENGINE

# Setup basic logging for the test
logging.basicConfig(level=logging.INFO)
report_logger = logging.getLogger("StressTestReport")

def run_stress_test():
    report = {
        "predictions_made": 0,
        "cooldown_triggers": 0,
        "rate_limited_events": 0,
        "false_positives_blocked": 0,
    }

    report_logger.info("🚀 Starting v2.6.1 Hardening Stress Test...")
    
    # 1. Test: Rapid App Switching (Stress the ADAPTING logic)
    report_logger.info("🧪 Test 1: Rapid App Switching (Simulating Flicker)")
    apps = ["vscode", "chrome", "obsidian", "terminal", "spotify"]
    for i in range(10):
        app = apps[i % len(apps)]
        EVENT_BUS.emit(SystemEvent.APP_LAUNCHED, {"app_id": app})
        time.sleep(0.1) # Rapid!
        
    if CONTEXT_ENGINE.pending_intent is not None:
        report["false_positives_blocked"] += 1
        report_logger.info("✅ SUCCESS: System entered ADAPTING state and blocked random flicker.")

    # 2. Test: Sequence Trigger & Rate Limiting
    report_logger.info("🧪 Test 2: Sequence Trigger & Rate Limiting")
    # Simulate a sequence: Setup -> Git
    for i in range(3):
        prev_id = f"step-a-{i}"
        next_id = f"step-b-{i}"
        report_logger.info(f"  Learning transition: {prev_id} -> {next_id}")
        EVENT_BUS.emit(SystemEvent.PLAN_COMPLETED, {"plan_id": prev_id})
        EVENT_BUS.emit(SystemEvent.PLAN_STARTED, {"plan_id": next_id})
        
    # Now simulate completion of a known "Prev" and check prediction
    test_prev = "step-a-0"
    EVENT_BUS.emit(SystemEvent.PLAN_COMPLETED, {"plan_id": test_prev})
    
    # Manually bypass the 30s idle gap and rate limit for testing
    SEQUENCE_ENGINE.last_completion_time = time.time() - 40
    SEQUENCE_ENGINE.last_suggestion_time = 0
    
    report_logger.info(f"  Requesting prediction for: {test_prev}")
    pid, conf, status = SEQUENCE_ENGINE.get_prediction()
    report_logger.info(f"  Prediction Result: PID={pid}, Status={status}, Conf={conf}")
    
    if status == "READY" and pid == "step-b-0":
        report["predictions_made"] += 1
        report_logger.info("✅ SUCCESS: Sequence Engine predicted the correct next step.")
    elif status == "RATE_LIMITED":
        report["rate_limited_events"] += 1
            
    # 3. Test: Ignore Cooldown Trigger
    report_logger.info("🧪 Test 3: Ignore Cooldown Trigger")
    # Force 3 ignores
    for _ in range(3):
        SEQUENCE_ENGINE.last_suggestion_time = 0 # Bypass rate limit for test
        SEQUENCE_ENGINE.notify_suggestion_made("git-456")
        SEQUENCE_ENGINE.notify_suggestion_ignored()
        
    if SEQUENCE_ENGINE.is_in_cooldown():
        report["cooldown_triggers"] += 1
        report_logger.info("✅ SUCCESS: Guardrail triggered 30-minute COOLDOWN after 3 ignores.")

    # 4. Generate Final Report
    report_logger.info("\n" + "="*30)
    report_logger.info("📋 FINAL STRESS TEST REPORT (v2.6.1)")
    report_logger.info(f"Predictions Made: {report['predictions_made']}")
    report_logger.info(f"Rate Limited:     {report['rate_limited_events']}")
    report_logger.info(f"Cooldowns:        {report['cooldown_triggers']}")
    report_logger.info(f"Flicker Blocked:  {report['false_positives_blocked']}")
    report_logger.info("="*30)

if __name__ == "__main__":
    import traceback
    try:
        run_stress_test()
    except Exception:
        traceback.print_exc()
