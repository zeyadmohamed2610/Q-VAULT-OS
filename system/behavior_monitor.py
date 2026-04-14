# =============================================================
#  behavior_monitor.py — Q-VAULT OS  |  Behavior Analysis Engine
#
#  Runtime behavior analysis and threat detection
# =============================================================

import time
import threading
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta

THREAT_THRESHOLD = 70
HIGH_RISK_THRESHOLD = 50
MEDIUM_RISK_THRESHOLD = 30


class BehaviorEvent:
    """Represents a behavior event."""

    def __init__(self, event_type: str, user: str, detail: str, risk_weight: int = 10):
        self.event_type = event_type
        self.user = user
        self.detail = detail
        self.risk_weight = risk_weight
        self.timestamp = time.time()


class BehaviorMonitor:
    """
    Monitor user behavior and detect suspicious activity.
    Tracks command frequency, access patterns, and risk scores.
    """

    _instance = None
    _threat_level = "NORMAL"
    _global_risk_score = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._event_queues: Dict[str, deque] = {}
        self._command_counts: Dict[str, int] = {}
        self._failed_access_counts: Dict[str, int] = {}
        self._user_risk_scores: Dict[str, int] = {}

        self._lock = threading.Lock()
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background behavior monitoring."""
        self._monitoring = True
        self._cleanup_timer = time.time()

    def record_event(
        self, event_type: str, user: str, detail: str, risk_weight: int = 10
    ):
        """Record a behavior event."""
        with self._lock:
            event = BehaviorEvent(event_type, user, detail, risk_weight)

            if user not in self._event_queues:
                self._event_queues[user] = deque(maxlen=100)

            self._event_queues[user].append(event)

            self._update_risk_score(user, risk_weight)

            if event_type in ["COMMAND_BLOCKED", "PATH_DENIED", "INTRUSION_ATTEMPT"]:
                self._increment_failed_access(user)

    def _update_risk_score(self, user: str, weight: int):
        """Update user's risk score."""
        if user not in self._user_risk_scores:
            self._user_risk_scores[user] = 0

        self._user_risk_scores[user] += weight

        self._global_risk_score += weight

        self._check_thresholds(user)

    def _increment_failed_access(self, user: str):
        """Track failed access attempts."""
        if user not in self._failed_access_counts:
            self._failed_access_counts[user] = 0

        self._failed_access_counts[user] += 1

    def _check_thresholds(self, user: str):
        """Check if risk thresholds exceeded."""
        user_score = self._user_risk_scores.get(user, 0)

        if (
            user_score >= THREAT_THRESHOLD
            or self._global_risk_score >= THREAT_THRESHOLD
        ):
            self._set_threat_level("CRITICAL")
            self._trigger_lockdown(user)
        elif user_score >= HIGH_RISK_THRESHOLD:
            self._set_threat_level("HIGH")
        elif user_score >= MEDIUM_RISK_THRESHOLD:
            self._set_threat_level("MEDIUM")

    def _set_threat_level(self, level: str):
        """Set system threat level."""
        if level == "CRITICAL":
            self._threat_level = "CRITICAL"
            self._trigger_security_alert()
        elif level == "HIGH" and self._threat_level != "CRITICAL":
            self._threat_level = "HIGH"
        elif level == "MEDIUM" and self._threat_level == "NORMAL":
            self._threat_level = "MEDIUM"

    def _trigger_security_alert(self):
        """Trigger security alert."""
        from system.notification_system import NOTIFY

        NOTIFY.send(
            "CRITICAL SECURITY ALERT",
            f"Threat level CRITICAL. Risk score: {self._global_risk_score}",
            level="danger",
        )

    def _trigger_lockdown(self, user: str):
        """Trigger system lockdown."""
        from system.secure_executor import SECURE_EXECUTOR

        SECURE_EXECUTOR._activate_fail_safe()

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "SYSTEM LOCKDOWN",
            f"User {user} triggered lockdown due to suspicious behavior",
            level="danger",
        )

    def check_command_frequency(self, user: str, window_seconds: int = 60) -> bool:
        """Check if command frequency is suspicious."""
        with self._lock:
            if user not in self._event_queues:
                return False

            cutoff = time.time() - window_seconds
            recent_events = [
                e
                for e in self._event_queues[user]
                if e.timestamp > cutoff and e.event_type == "COMMAND"
            ]

            if len(recent_events) > 10:
                self.record_event(
                    "HIGH_FREQUENCY",
                    user,
                    f"{len(recent_events)} commands in {window_seconds}s",
                    risk_weight=15,
                )
                return True

        return False

    def check_repeated_failure(self, user: str, threshold: int = 5) -> bool:
        """Check for repeated access failures."""
        failures = self._failed_access_counts.get(user, 0)

        if failures >= threshold:
            self.record_event(
                "REPEATED_FAILURE",
                user,
                f"{failures} failed access attempts",
                risk_weight=20,
            )
            return True

        return False

    def get_threat_level(self) -> str:
        """Get current threat level."""
        return self._threat_level

    def get_user_risk_score(self, user: str) -> int:
        """Get risk score for user."""
        return self._user_risk_scores.get(user, 0)

    def get_global_risk_score(self) -> int:
        """Get global risk score."""
        return self._global_risk_score

    def get_user_events(self, user: str, limit: int = 20) -> List[Dict]:
        """Get recent events for user."""
        if user not in self._event_queues:
            return []

        return [
            {
                "type": e.event_type,
                "detail": e.detail,
                "risk": e.risk_weight,
                "time": datetime.fromtimestamp(e.timestamp).isoformat(),
            }
            for e in list(self._event_queues[user])[-limit:]
        ]

    def reset_user_risk(self, user: str):
        """Reset user's risk score."""
        with self._lock:
            self._user_risk_scores[user] = 0
            self._failed_access_counts[user] = 0

    def get_stats(self) -> Dict:
        """Get behavior monitor statistics."""
        return {
            "threat_level": self._threat_level,
            "global_risk": self._global_risk_score,
            "tracked_users": len(self._event_queues),
            "failed_access_total": sum(self._failed_access_counts.values()),
        }


BEHAVIOR_MONITOR = BehaviorMonitor()
