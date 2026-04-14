# =============================================================
#  crash_reporter.py — Q-VAULT OS  |  Crash Reporting System
#
#  Features:
#    - Auto-send crash reports
#    - Stack trace capture
#    - OS version tracking
#    - Local crash history
# =============================================================

import os
import json
import sys
import time
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

CRASH_DIR = Path.home() / ".qvault" / "crashes"


@dataclass
class CrashReport:
    crash_id: str
    timestamp: str
    exception_type: str
    message: str
    stack_trace: str
    os_version: str
    app_version: str
    user_id: str
    last_actions: list
    handled: bool


class CrashReporter:
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

        CRASH_DIR.mkdir(parents=True, exist_ok=True)
        self._recent_actions: list = []
        self._max_actions = 20

    def add_action(self, action: str):
        self._recent_actions.append({"action": action, "timestamp": time.time()})

        if len(self._recent_actions) > self._max_actions:
            self._recent_actions = self._recent_actions[-self._max_actions :]

    def capture_exception(self, exc_type: str, exc_value: Exception, tb: str) -> str:
        crash_id = f"crash_{int(time.time())}_{os.getrandom(4).hex()}"

        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, tb))

        report = CrashReport(
            crash_id=crash_id,
            timestamp=datetime.now().isoformat(),
            exception_type=exc_type.__name__
            if hasattr(exc_type, "__name__")
            else str(exc_type),
            message=str(exc_value),
            stack_trace=stack_trace,
            os_version=self._get_os_version(),
            app_version="1.2.0",
            user_id=self._get_user_id(),
            last_actions=[a["action"] for a in self._recent_actions[-10:]],
            handled=False,
        )

        self._save_crash(report)
        self._send_crash_report(report)

        return crash_id

    def _get_os_version(self) -> str:
        try:
            import platform

            return f"{platform.system()} {platform.release()} {platform.version()}"
        except Exception:
            return "Unknown"

    def _get_user_id(self) -> str:
        try:
            from core.system_state import STATE

            return STATE.username()
        except Exception:
            return "unknown"

    def _save_crash(self, report: CrashReport):
        try:
            crash_file = CRASH_DIR / f"{report.crash_id}.json"
            with open(crash_file, "w") as f:
                json.dump(asdict(report), f, indent=2)

            index_file = CRASH_DIR / "index.json"
            try:
                index = []
                if index_file.exists():
                    with open(index_file, "r") as f:
                        index = json.load(f)
                index.append(
                    {
                        "crash_id": report.crash_id,
                        "timestamp": report.timestamp,
                        "exception_type": report.exception_type,
                        "handled": report.handled,
                    }
                )
                with open(index_file, "w") as f:
                    json.dump(index, f, indent=2)
            except Exception:
                pass

        except Exception:
            pass

    def _send_crash_report(self, report: CrashReport):
        if not SUPABASE_KEY:
            self._queue_crash(report)
            return

        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/crash_reports"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }

            data = asdict(report)

            requests.post(url, headers=headers, json=data, timeout=5)

        except Exception:
            self._queue_crash(report)

    def _queue_crash(self, report: CrashReport):
        queue_file = CRASH_DIR / "pending.json"
        try:
            pending = []
            if queue_file.exists():
                with open(queue_file, "r") as f:
                    pending = json.load(f)

            pending.append(asdict(report))

            with open(queue_file, "w") as f:
                json.dump(pending, f, indent=2)
        except Exception:
            pass

    def sync_pending_crashes(self):
        if not SUPABASE_KEY:
            return

        queue_file = CRASH_DIR / "pending.json"
        if not queue_file.exists():
            return

        try:
            with open(queue_file, "r") as f:
                pending = json.load(f)

            if not pending:
                return

            import requests

            url = f"{SUPABASE_URL}/rest/v1/crash_reports"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }

            for crash in pending:
                try:
                    requests.post(url, headers=headers, json=crash, timeout=5)
                except Exception:
                    pass

            queue_file.unlink()

        except Exception:
            pass

    def get_crash_history(self, limit: int = 10) -> list:
        index_file = CRASH_DIR / "index.json"
        if not index_file.exists():
            return []

        try:
            with open(index_file, "r") as f:
                index = json.load(f)

            return index[-limit:]

        except Exception:
            return []

    def mark_handled(self, crash_id: str):
        crash_file = CRASH_DIR / f"{crash_id}.json"
        if crash_file.exists():
            try:
                with open(crash_file, "r") as f:
                    report = json.load(f)
                report["handled"] = True
                with open(crash_file, "w") as f:
                    json.dump(report, f, indent=2)
            except Exception:
                pass


CRASH_REPORTER = CrashReporter()
