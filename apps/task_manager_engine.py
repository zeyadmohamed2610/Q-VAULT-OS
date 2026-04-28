import time
from typing import List, Dict, Any

class TaskManagerEngine:
    """
    Subprocess-level logic for System Monitoring (Phase 15.4).
    Reads from SecureAPI and formats data for the UI Proxy.
    """
    def __init__(self, secure_api):
        self.api = secure_api

    def get_process_list(self) -> List[Dict[str, Dict[str, Any]]]:
        """Fetch real-time metrics via SecureAPI.System (Phase 16.8)."""
        try:
            # 🟢 Authorized hook into SystemGuard
            instances = self.api.system.list_instances()
            formatted = []
            for iid, data in instances.items():
                name = data.get("app_id", "Unknown")
                hz = data.get("msg_hz", 0)
                sat = data.get("peak_q", 0)
                trust = data.get("trust", 100)
                
                status = data.get("state", "RUNNING")
                if data.get("is_throttled"): status = "CONGESTED"
                
                # Professional telemetry string
                line = f"[{status}] {name:<12} | Hz: {hz:>5} | PeakQ: {sat:>3} | Trust: {trust:>3}"
                formatted.append({"raw": line, "iid": iid})
            return formatted
        except Exception as e:
            return [{"raw": f"ERROR: {str(e)}"}]

    def kill_process(self, pid: int) -> bool:
        """Attempt to kill a process via governed API."""
        try:
            # This call will be validated by Kernel ownership rules
            self.api.process.run(["kill", str(pid)])
            return True
        except Exception as e:
            return False
