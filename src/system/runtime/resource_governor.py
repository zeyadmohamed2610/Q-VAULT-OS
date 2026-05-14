import logging
from dataclasses import dataclass
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger("system.runtime.resource_governor")

@dataclass
class ResourceQuota:
    cpu_limit: float = 20.0  # Max % per app
    ram_limit_mb: float = 512.0 # Max MB per app
    burst_allowance: float = 1.5 # 150% for short periods

class ResourceGovernor:
    """
    Sovereign Resource Governor (Phase 16.2).
    Enforces per-app quotas and penalizes resource-heavy instances.
    """
    def __init__(self):
        self._quotas = {} # app_id -> ResourceQuota
        self._violations = {} # instance_id -> count

    def check_compliance(self, instance_id: str, app_id: str, cpu: float, ram_mb: float) -> bool:
        """Verifies if an instance is staying within its assigned sovereign quota."""
        quota = self._quotas.get(app_id, ResourceQuota())
        
        is_compliant = True
        if cpu > (quota.cpu_limit * quota.burst_allowance):
            logger.warning(f"[Governor] CPU Violation: {instance_id} using {cpu}% (Limit: {quota.cpu_limit}%)")
            is_compliant = False
            
        if ram_mb > quota.ram_limit_mb:
            logger.warning(f"[Governor] RAM Violation: {instance_id} using {ram_mb}MB (Limit: {quota.ram_limit_mb}MB)")
            is_compliant = False

        if not is_compliant:
            self._violations[instance_id] = self._violations.get(instance_id, 0) + 1
            EVENT_BUS.emit(SystemEvent.EVENT_APP_CRASHED, {"instance_id": instance_id, "reason": "RESOURCE_QUOTA_EXCEEDED"})
            
        return is_compliant

    def set_quota(self, app_id: str, cpu: float, ram: float):
        self._quotas[app_id] = ResourceQuota(cpu_limit=cpu, ram_limit_mb=ram)

# Global Singleton
RESOURCE_GOVERNOR = ResourceGovernor()
