"""
system/runtime/inspector.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS Phase 3 — Runtime Explainability Layer

Provides forensic-grade introspection tools to validate runtime integrity,
governance policies, and trust decisions.
─────────────────────────────────────────────────────────────────────────────
"""
import time
import json
from typing import Dict, Any, List
from system.runtime_manager import RUNTIME_MANAGER, AppState
from system.runtime.process_governor import PROCESS_GOVERNOR

class RuntimeInspector:
    """
    Forensic engine for Q-Vault Runtime introspection.
    """

    @staticmethod
    def get_full_audit_snapshot() -> Dict[str, Any]:
        """Generates a complete forensic snapshot of the current OS state."""
        rm_data = RUNTIME_MANAGER.list_running()
        
        snapshot = {
            "timestamp": time.time(),
            "kernel_identity": "Q-Vault-Governed-Runtime-v4.2",
            "global_governance": {
                "state": rm_data["global_state"],
                "pressure_ratio": rm_data["global_pressure"],
                "ui_lag_ms": rm_data["ui_lag_ms"],
                "cooldown": rm_data["cooldown_remaining"]
            },
            "active_instances": [],
            "quarantine_records": []
        }

        for app in rm_data["apps"]:
            if app["state"] == "QUARANTINED":
                snapshot["quarantine_records"].append(app)
            else:
                snapshot["active_instances"].append(app)

        return snapshot

    @staticmethod
    def explain_app_trust(instance_id: str) -> str:
        """Returns a human-readable (and professor-friendly) trust explanation."""
        explanation = RUNTIME_MANAGER.get_explanation(instance_id)
        if "error" in explanation:
            return f"❌ [ERROR] {explanation['error']}"

        lines = [
            f"🔍 EXPLAINABILITY REPORT: {explanation['app_id']} ({instance_id})",
            f"────────────────────────────────────────────────────────────────",
            f"Current Trust Score : {explanation['trust_score']}/100",
            f"Governance Decision : {explanation['explanation']}",
            f"System State       : {explanation['global_state']}",
            f"Pressure Ratio     : {explanation['pressure_ratio']}x",
            f"────────────────────────────────────────────────────────────────",
            f"Decision Factors    : {', '.join(explanation['reasons'])}",
            f"Base Worker Limit  : {explanation['base_worker_limit']}",
            f"Trust Adjustment   : {explanation['trust_adjustment']}",
            f"Final Allocation   : {explanation['final_worker_limit']} Slots",
            f"────────────────────────────────────────────────────────────────"
        ]
        return "\n".join(lines)

    @staticmethod
    def get_governance_decision_trace(limit: int = 10) -> str:
        """Traces the last N governance decisions made by the kernel."""
        rm_data = RUNTIME_MANAGER.list_running()
        decisions = rm_data.get("decision_history", [])[-limit:]
        
        if not decisions:
            return "No governance decisions recorded in current session buffer."

        output = ["📜 KERNEL GOVERNANCE DECISION TRACE", "────────────────────────────────────────────────────────────────"]
        for d in reversed(decisions):
            ts = time.strftime('%H:%M:%S', time.localtime(d['timestamp']))
            output.append(f"[{ts}] {d['state_before']} -> {d['state_after']}")
            output.append(f"      REASON: {d['reason']}")
            output.append(f"      PRESSURE: {d['pressure_ratio']}x | BURST: {d['burst_score']}")
            output.append(f"      AFFECTED: {len(d['affected_apps'])} instances")
            output.append("      ──")
        
        return "\n".join(output)

INSPECTOR = RuntimeInspector()
