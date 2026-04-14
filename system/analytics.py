# =============================================================
#  analytics.py — Q-VAULT OS  |  Analytics Engine
#
#  Features:
#    - Track daily active users
#    - Session duration tracking
#    - Feature usage analytics
#    - Smart insights
# =============================================================

import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

ANALYTICS_DIR = Path.home() / ".qvault" / "analytics"


@dataclass
class Event:
    name: str
    timestamp: float
    user_id: str
    session_id: str
    metadata: Dict


@dataclass
class Session:
    session_id: str
    user_id: str
    start_time: float
    end_time: Optional[float]
    duration: int
    events: List[str]
    app_usage: Dict[str, int]


@dataclass
class DailyStats:
    date: str
    active_users: int
    total_sessions: int
    avg_duration: int
    feature_usage: Dict[str, int]


class AnalyticsEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

        self._session_id = self._generate_session_id()
        self._user_id = "unknown"
        self._session_start = time.time()
        self._session_events: List[Event] = []
        self._app_usage: Dict[str, int] = defaultdict(int)

        self._current_session_file = ANALYTICS_DIR / "current_session.json"
        self._daily_stats_file = ANALYTICS_DIR / "daily_stats.json"
        self._event_log_file = ANALYTICS_DIR / "events.jsonl"

        self._load_session()

    def _generate_session_id(self) -> str:
        import hashlib

        return hashlib.sha256(f"{time.time()}-{os.getlogin()}".encode()).hexdigest()[
            :16
        ]

    def _load_session(self):
        if self._current_session_file.exists():
            try:
                with open(self._current_session_file, "r") as f:
                    data = json.load(f)
                    self._session_id = data.get("session_id", self._session_id)
                    self._user_id = data.get("user_id", "unknown")
                    self._session_start = data.get("start_time", time.time())
                    self._app_usage = defaultdict(int, data.get("app_usage", {}))
            except Exception:
                pass

    def _save_session(self):
        try:
            with open(self._current_session_file, "w") as f:
                json.dump(
                    {
                        "session_id": self._session_id,
                        "user_id": self._user_id,
                        "start_time": self._session_start,
                        "app_usage": dict(self._app_usage),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def set_user(self, user_id: str):
        self._user_id = user_id
        self._save_session()

    def start_session(self):
        self._session_id = self._generate_session_id()
        self._session_start = time.time()
        self._save_session()

    def end_session(self):
        if not self._session_start:
            return

        duration = int(time.time() - self._session_start)

        session_data = {
            "session_id": self._session_id,
            "user_id": self._user_id,
            "start_time": self._session_start,
            "end_time": time.time(),
            "duration": duration,
            "events_count": len(self._session_events),
            "app_usage": dict(self._app_usage),
        }

        sessions_file = ANALYTICS_DIR / "sessions.json"
        try:
            sessions = []
            if sessions_file.exists():
                with open(sessions_file, "r") as f:
                    sessions = json.load(f)

            sessions.append(session_data)

            sessions = sessions[-1000:]

            with open(sessions_file, "w") as f:
                json.dump(sessions, f, indent=2)
        except Exception:
            pass

        self._save_daily_stats()
        self._sync_to_cloud(session_data)

        self._session_start = 0

    def _save_daily_stats(self):
        today = datetime.now().strftime("%Y-%m-%d")

        sessions_file = ANALYTICS_DIR / "sessions.json"
        if not sessions_file.exists():
            return

        try:
            with open(sessions_file, "r") as f:
                sessions = json.load(f)

            today_sessions = [
                s
                for s in sessions
                if datetime.fromtimestamp(s["start_time"]).strftime("%Y-%m-%d") == today
            ]

            active_users = len(set(s["user_id"] for s in today_sessions))
            total_sessions = len(today_sessions)
            avg_duration = sum(s["duration"] for s in today_sessions) // max(
                1, total_sessions
            )

            feature_usage = defaultdict(int)
            for s in today_sessions:
                for app in s.get("app_usage", {}).keys():
                    feature_usage[app] += 1

            daily_stats = DailyStats(
                date=today,
                active_users=active_users,
                total_sessions=total_sessions,
                avg_duration=avg_duration,
                feature_usage=dict(feature_usage),
            )

            stats = {}
            if self._daily_stats_file.exists():
                with open(self._daily_stats_file, "r") as f:
                    stats = json.load(f)

            stats[today] = asdict(daily_stats)

            with open(self._daily_stats_file, "w") as f:
                json.dump(stats, f, indent=2)

        except Exception:
            pass

    def _sync_to_cloud(self, session_data: Dict):
        if not SUPABASE_KEY:
            return

        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/analytics"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }

            data = {
                "session_id": session_data["session_id"],
                "user_id": session_data["user_id"],
                "duration": session_data["duration"],
                "events_count": session_data["events_count"],
                "app_usage": session_data["app_usage"],
                "timestamp": datetime.now().isoformat(),
            }

            requests.post(url, headers=headers, json=data)

        except Exception:
            pass

    def track_event(self, event_name: str, metadata: Dict = None):
        event = Event(
            name=event_name,
            timestamp=time.time(),
            user_id=self._user_id,
            session_id=self._session_id,
            metadata=metadata or {},
        )

        self._session_events.append(event)

        try:
            with open(self._event_log_file, "a") as f:
                f.write(json.dumps(asdict(event)) + "\n")
        except Exception:
            pass

        if len(self._session_events) >= 10:
            self._flush_events()

    def _flush_events(self):
        if not SUPABASE_KEY:
            return

        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/analytics_events"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }

            events_data = [asdict(e) for e in self._session_events[:10]]
            requests.post(url, headers=headers, json=events_data)

            self._session_events = self._session_events[10:]

        except Exception:
            pass

    def track_app_usage(self, app_name: str, duration: int):
        self._app_usage[app_name] += duration
        self._save_session()

        self.track_event("app_usage", {"app": app_name, "duration": duration})

    def track_feature_usage(self, feature: str):
        self.track_event("feature_usage", {"feature": feature})

    def track_drop_off(self, stage: str):
        self.track_event("drop_off", {"stage": stage})

    def get_daily_stats(self, date: str = None) -> Dict:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        if self._daily_stats_file.exists():
            try:
                with open(self._daily_stats_file, "r") as f:
                    stats = json.load(f)
                    return stats.get(date, {})
            except Exception:
                pass

        return {}

    def get_weekly_stats(self) -> List[Dict]:
        stats = []

        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily = self.get_daily_stats(date)
            if daily:
                stats.append(daily)

        return stats

    def get_insights(self) -> Dict[str, Any]:
        weekly = self.get_weekly_stats()

        if not weekly:
            return {"unused_features": [], "friction_areas": [], "recommendations": []}

        all_app_usage = defaultdict(int)
        for day in weekly:
            usage = day.get("feature_usage", {})
            for app, count in usage.items():
                all_app_usage[app] += count

        sorted_usage = sorted(all_app_usage.items(), key=lambda x: x[1], reverse=True)
        most_used = [app for app, _ in sorted_usage[:5]]
        least_used = (
            [app for app, _ in sorted_usage[-5:]] if len(sorted_usage) > 5 else []
        )

        avg_sessions = sum(day.get("total_sessions", 0) for day in weekly) // max(
            1, len(weekly)
        )
        avg_duration = sum(day.get("avg_duration", 0) for day in weekly) // max(
            1, len(weekly)
        )

        recommendations = []
        if avg_duration < 60:
            recommendations.append(
                "Users have short sessions - consider more onboarding"
            )

        if least_used:
            recommendations.append(f"Features {least_used} may need better discovery")

        return {
            "most_used_apps": most_used,
            "unused_features": least_used,
            "avg_sessions_per_day": avg_sessions,
            "avg_session_duration": avg_duration,
            "recommendations": recommendations,
        }

    def get_user_journey(self, user_id: str) -> Dict:
        sessions_file = ANALYTICS_DIR / "sessions.json"
        if not sessions_file.exists():
            return {}

        try:
            with open(sessions_file, "r") as f:
                sessions = json.load(f)

            user_sessions = [s for s in sessions if s.get("user_id") == user_id]

            if not user_sessions:
                return {}

            first_session = user_sessions[0]
            last_session = user_sessions[-1]

            return {
                "first_seen": datetime.fromtimestamp(
                    first_session["start_time"]
                ).isoformat(),
                "last_seen": datetime.fromtimestamp(
                    last_session["start_time"]
                ).isoformat(),
                "total_sessions": len(user_sessions),
                "total_time": sum(s["duration"] for s in user_sessions),
                "drop_off_stage": self._analyze_journey(user_sessions),
            }

        except Exception:
            return {}

    def _analyze_journey(self, sessions: List[Dict]) -> Optional[str]:
        if len(sessions) < 3:
            return None

        recent_apps = set()
        for session in sessions[-3:]:
            recent_apps.update(session.get("app_usage", {}).keys())

        if len(recent_apps) <= 2:
            return "low_engagement"

        return None


ANALYTICS = AnalyticsEngine()
