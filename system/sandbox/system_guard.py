import logging
from typing import Dict, Any
from system.runtime_manager import RUNTIME_MANAGER

class SystemGuard:
    """
    Controlled access to global OS telemetry and health metrics.
    Used by authorized system-level apps (like Marketplace).
    """
    def __init__(self, app_id: str, api: Any):
        self.app_id = app_id
        self.api = api
        self.logger = logging.getLogger(f"guard.system.{app_id}")

    def list_instances(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a sanitized map of all running application instances.
        """
        rm = RUNTIME_MANAGER
        if not rm: return {}
        
        results = {}
        with rm._lock:
            for iid, record in rm._registry.items():
                results[iid] = {
                    "app_id": record.app_id,
                    "state": record.state.value,
                    "trust": record.trust_score,
                    "is_throttled": record.local_throttled or record.congested,
                    "congested": record.congested,
                    "main_pid": record.main_pid,
                    "msg_hz": round(record.msg_hz, 1),
                    "peak_q": record.peak_queue_size,
                    "total_msgs": record.total_msgs_handled
                }
        return results

    def get_health(self) -> Dict[str, Any]:
        """Returns global Kernel health metrics."""
        rm = RUNTIME_MANAGER
        if not rm: return {"status": "unauthorized"}
        
        return {
            "global_state": rm.global_state,
            "pressure": rm.current_pressure_ratio,
            "ui_lag": rm.ui_lag_ms
        }
