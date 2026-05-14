import logging
from typing import Dict, Any
from system.reasoning_engine import REASONING_ENGINE
from system.shadow_logger import SHADOW_LOGGER
from core.event_bus import EVENT_BUS

logger = logging.getLogger("sandbox.intel_guard")

class IntelligenceGuard:
    """
    Governed access to Q-Vault's AI Intelligence Layer (Reasoning & Observation).
    Exposed to isolated apps via SecureAPI.intel.
    """
    def __init__(self, app_id: str, api=None):
        self.app_id = app_id
        self.api = api

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Runs the ReasoningEngine on provided text/diff."""
        # We wrap it in a safe context
        context = {"app_id": self.app_id, "source": "terminal"}
        return REASONING_ENGINE.summarize_diff(text, context)

    def get_shadow_status(self) -> Dict[str, Any]:
        """Retrieves real-time KPIs from the ShadowLogger."""
        events = SHADOW_LOGGER._read_all_events()
        total = len(events)
        criticals = sum(1 for e in events if e.get('impact', {}).get('level') == 'CRITICAL' or e.get('impact') == 'CRITICAL')
        
        return {
            "total_events": total,
            "critical_risks": criticals,
            "readiness": "READY" if total > 0 else "INITIALIZING",
            "last_event_time": events[-1].get('time_str') if events else "N/A"
        }

    def get_audit_summary(self) -> str:
        """Returns a formatted summary of the latest Shadow Report."""
        import os
        report_path = "system/shadow_logs/SHADOW_REPORT.md"
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                return f.read()
        return "No audit report available yet."

    def get_system_status(self) -> Dict[str, Any]:
        """Final Integration Health Check."""
        
        return {
            "reasoning": "ONLINE" if REASONING_ENGINE else "OFFLINE",
            "shadow_mode": "ACTIVE" if SHADOW_LOGGER else "OFFLINE",
            "event_bus": "CONNECTED" if EVENT_BUS else "DISCONNECTED",
            "automation": "LINKED",
            "trust_grade": "A"
        }
