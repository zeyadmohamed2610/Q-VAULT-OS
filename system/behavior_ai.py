# =============================================================
#  behavior_ai.py — Q-VAULT OS  |  AI Behavior Analysis System
#
#  User behavior profiling and anomaly detection
# =============================================================

import os
import time
import hashlib
import threading
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta

RISK_THRESHOLD_HIGH = 70
RISK_THRESHOLD_CRITICAL = 90
BASELINE_WINDOW_HOURS = 24
ANOMALY_SPIKE_FACTOR = 3.0


class CommandProfile:
    """Profile for a single command type."""

    def __init__(self, name: str):
        self.name = name
        self.total_uses = 0
        self.last_used = 0.0
        self.avg_frequency = 0.0
        self.use_times: deque = deque(maxlen=1000)

    def record_use(self, timestamp: float):
        self.total_uses += 1
        self.last_used = timestamp
        self.use_times.append(timestamp)
        self._update_frequency()

    def _update_frequency(self):
        if len(self.use_times) < 2:
            return
        times = list(self.use_times)
        window = times[-1] - times[0]
        if window > 0:
            self.avg_frequency = len(times) / window * 3600


class UserBehaviorProfile:
    """Complete behavior profile for a user."""

    def __init__(self, username: str):
        self.username = username
        self.command_profiles: Dict[str, CommandProfile] = {}
        self.file_access_patterns: set = set()
        self.active_hours: Dict[int, int] = {}
        self.session_count = 0
        self.total_commands = 0
        self.created_at = time.time()
        self.baseline_established = False

    def record_command(self, command: str, timestamp: float):
        self.total_commands += 1

        if command not in self.command_profiles:
            self.command_profiles[command] = CommandProfile(command)
        self.command_profiles[command].record_use(timestamp)

        hour = datetime.fromtimestamp(timestamp).hour
        self.active_hours[hour] = self.active_hours.get(hour, 0) + 1

    def record_file_access(self, path: str):
        self.file_access_patterns.add(path)

    def get_active_hours(self) -> List[int]:
        threshold = self.total_commands * 0.1
        return [h for h, c in self.active_hours.items() if c >= threshold]

    def is_active_time(self, timestamp: float) -> bool:
        if not self.baseline_established:
            return True
        hour = datetime.fromtimestamp(timestamp).hour
        active = self.get_active_hours()
        return hour in active if active else True


class AnomalyDetector:
    """Detect behavioral anomalies."""

    def __init__(self, profile: UserBehaviorProfile):
        self.profile = profile
        self.recent_commands: deque = deque(maxlen=50)
        self.anomaly_history: List[Dict] = []

    def check_frequency_spike(self, current_freq: float) -> Optional[Dict]:
        if not self.profile.baseline_established:
            return None

        avg_freq = sum(
            p.avg_frequency for p in self.profile.command_profiles.values()
        ) / max(len(self.profile.command_profiles), 1)

        if avg_freq > 0 and current_freq > avg_freq * ANOMALY_SPIKE_FACTOR:
            anomaly = {
                "type": "FREQUENCY_SPIKE",
                "current": current_freq,
                "baseline": avg_freq,
                "factor": current_freq / avg_freq,
                "timestamp": time.time(),
            }
            self.anomaly_history.append(anomaly)
            return anomaly
        return None

    def check_abnormal_sequence(self, commands: List[str]) -> Optional[Dict]:
        suspicious_patterns = [
            ["rm", "-rf", "/"],
            ["chmod", "777"],
            ["wget", "curl"],
            ["sudo", "su"],
            [">", "/dev/null"],
        ]

        cmd_str = " ".join(commands)
        for pattern in suspicious_patterns:
            if all(c in cmd_str for c in pattern):
                anomaly = {
                    "type": "SUSPICIOUS_SEQUENCE",
                    "pattern": pattern,
                    "timestamp": time.time(),
                }
                self.anomaly_history.append(anomaly)
                return anomaly
        return None

    def check_unknown_commands(self, command: str) -> bool:
        if not self.profile.command_profiles:
            return False
        return command not in self.profile.command_profiles


class BehaviorAI:
    """
    AI-powered behavior analysis system.
    Profiles user behavior and detects anomalies.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._user_profiles: Dict[str, UserBehaviorProfile] = {}
        self._current_user = None
        self._lock = threading.Lock()
        self._risk_score = 0
        self._anomaly_detector: Optional[AnomalyDetector] = None

        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring."""
        self._monitoring = True

    def set_current_user(self, username: str):
        """Set current user for monitoring."""
        with self._lock:
            self._current_user = username
            if username not in self._user_profiles:
                self._user_profiles[username] = UserBehaviorProfile(username)
            self._anomaly_detector = AnomalyDetector(self._user_profiles[username])

    def record_command(self, command: str):
        """Record command execution."""
        if not self._current_user:
            return

        with self._lock:
            profile = self._user_profiles.get(self._current_user)
            if not profile:
                return

            timestamp = time.time()
            profile.record_command(command, timestamp)
            self._update_risk_score(command, timestamp)

            if self._anomaly_detector:
                self._anomaly_detector.recent_commands.append(command)
                self._check_anomalies(command)

    def record_file_access(self, path: str):
        """Record file access."""
        if not self._current_user:
            return

        with self._lock:
            profile = self._user_profiles.get(self._current_user)
            if profile:
                profile.record_file_access(path)

    def _update_risk_score(self, command: str, timestamp: float):
        """Update risk score based on behavior."""
        risky_commands = [
            "rm -rf",
            "chmod 777",
            "wget",
            "curl",
            "sudo",
            "su",
            "chown",
            "dd",
            "mkfs",
            "fdisk",
        ]

        for rc in risky_commands:
            if rc in command:
                self._risk_score += 5
                break

        profile = self._user_profiles.get(self._current_user)
        if profile and profile.total_commands > 0:
            recent = sum(
                1
                for t in profile.command_profiles.values()
                for ut in t.use_times
                if time.time() - ut < 60
            )
            if recent > 20:
                self._risk_score += 2

        if self._risk_score > 100:
            self._risk_score = 100

    def _check_anomalies(self, command: str):
        """Check for anomalies."""
        if not self._anomaly_detector:
            return

        if self._anomaly_detector.check_unknown_commands(command):
            self._risk_score += 3

        if len(self._anomaly_detector.recent_commands) >= 3:
            seq = list(self._anomaly_detector.recent_commands)[-3:]
            anomaly = self._anomaly_detector.check_abnormal_sequence(seq)
            if anomaly:
                self._risk_score += 15

    def get_risk_score(self) -> int:
        """Get current risk score (0-100)."""
        return self._risk_score

    def get_risk_level(self) -> str:
        """Get risk level string."""
        if self._risk_score >= RISK_THRESHOLD_CRITICAL:
            return "CRITICAL"
        elif self._risk_score >= RISK_THRESHOLD_HIGH:
            return "HIGH"
        elif self._risk_score >= 30:
            return "MEDIUM"
        return "LOW"

    def establish_baseline(self, username: str):
        """Establish behavior baseline for user."""
        with self._lock:
            profile = self._user_profiles.get(username)
            if profile:
                profile.baseline_established = True

    def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics for current user."""
        if not self._current_user:
            return {}

        profile = self._user_profiles.get(self._current_user)
        if not profile:
            return {}

        return {
            "username": self._current_user,
            "total_commands": profile.total_commands,
            "unique_commands": len(profile.command_profiles),
            "risk_score": self._risk_score,
            "risk_level": self.get_risk_level(),
            "baseline_established": profile.baseline_established,
            "active_hours": profile.get_active_hours(),
        }

    def reset_risk(self):
        """Reset risk score."""
        self._risk_score = 0

    def get_anomaly_history(self) -> List[Dict]:
        """Get anomaly detection history."""
        if self._anomaly_detector:
            return list(self._anomaly_detector.anomaly_history)
        return []


BEHAVIOR_AI = BehaviorAI()
