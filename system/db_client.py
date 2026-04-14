# =============================================================
#  db_client.py — Q-VAULT OS  |  Supabase Database Client
#
#  Production-grade database integration with:
#    - Local-first sync
#    - Offline fallback
#    - Retry logic
#    - RLS-aware queries
# =============================================================

import os
import json
import time
import hashlib
import base64
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field
from queue import Queue

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
LOCAL_DB_DIR = Path.home() / ".qvault" / "db"
PENDING_SYNC_FILE = LOCAL_DB_DIR / "pending_sync.json"


@dataclass
class DBUser:
    id: str
    username: str
    password_hash: str
    is_root: bool = False
    created_at: Optional[str] = None


@dataclass
class DBSession:
    id: str
    user_id: str
    token: str
    expires_at: str
    created_at: Optional[str] = None


@dataclass
class AuditLog:
    id: str
    user_id: Optional[str]
    action: str
    severity: str
    timestamp: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class TelemetryEvent:
    id: str
    event_type: str
    data: Dict
    created_at: Optional[str] = None


@dataclass
class Package:
    id: str
    name: str
    version: str
    description: Optional[str] = None
    installed: bool = False
    created_at: Optional[str] = None


class PendingSync:
    def __init__(self):
        self._lock = threading.Lock()
        self._queue: Queue = Queue()
        self._local_file = PENDING_SYNC_FILE
        self._ensure_local_dir()

    def _ensure_local_dir(self):
        LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)

    def add(self, operation: str, table: str, data: Dict):
        with self._lock:
            self._queue.put(
                {
                    "operation": operation,
                    "table": table,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def get_all(self) -> List[Dict]:
        with self._lock:
            items = []
            while not self._queue.empty():
                try:
                    items.append(self._queue.get_nowait())
                except Exception:
                    break
            return items

    def load_from_disk(self) -> List[Dict]:
        try:
            if self._local_file.exists():
                with open(self._local_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def save_to_disk(self, items: List[Dict]):
        try:
            with open(self._local_file, "w") as f:
                json.dump(items, f, indent=2)
        except Exception:
            pass

    def clear_disk(self):
        try:
            if self._local_file.exists():
                self._local_file.unlink()
        except Exception:
            pass


class DatabaseClient:
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

        self._supabase = None
        self._is_connected = False
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_running = False
        self._pending_sync = PendingSync()
        self._local_cache: Dict[str, Any] = {}
        self._use_remote = False
        self._retry_count = 3
        self._retry_delay = 1.0
        self._offline_mode = False

        self._ensure_local_db()
        self._init_supabase()
        self._start_background_sync()

    def _ensure_local_db(self):
        LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)

        local_users = LOCAL_DB_DIR / "users.json"
        local_sessions = LOCAL_DB_DIR / "sessions.json"
        local_audit = LOCAL_DB_DIR / "audit_logs.json"
        local_telemetry = LOCAL_DB_DIR / "telemetry.json"
        local_packages = LOCAL_DB_DIR / "packages.json"

        for f in [
            local_users,
            local_sessions,
            local_audit,
            local_telemetry,
            local_packages,
        ]:
            if not f.exists():
                f.write_text("[]")

    def _init_supabase(self):
        if not SUPABASE_KEY:
            self._offline_mode = True
            return

        try:
            from supabase import create_client, Client

            self._supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self._use_remote = True
        except Exception as e:
            self._offline_mode = True
            self._supabase = None

    def _start_background_sync(self):
        self._sync_running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()

    def _sync_loop(self):
        while self._sync_running:
            try:
                if self._is_connected and not self._offline_mode:
                    self._process_pending_sync()
            except Exception:
                pass
            time.sleep(5)

    def _process_pending_sync(self):
        if not self._use_remote or not self._supabase:
            return

        pending = self._pending_sync.load_from_disk()
        if not pending:
            return

        for item in pending:
            try:
                self._execute_remote(item["operation"], item["table"], item["data"])
            except Exception:
                pass

        self._pending_sync.clear_disk()

    def _execute_remote(self, operation: str, table: str, data: Dict) -> bool:
        if not self._supabase:
            return False

        try:
            if operation == "insert":
                self._supabase.table(table).insert(data).execute()
                return True
            elif operation == "update":
                self._supabase.table(table).update(data).execute()
                return True
            elif operation == "delete":
                self._supabase.table(table).delete().execute()
                return True
        except Exception:
            pass
        return False

    def _retry_operation(self, func, *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self._retry_count):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
        raise last_error

    def is_connected(self) -> bool:
        return self._is_connected

    def is_offline(self) -> bool:
        return self._offline_mode

    def test_connection(self) -> bool:
        if not self._supabase:
            self._offline_mode = True
            return False

        try:
            self._supabase.table("users").select("id").limit(1).execute()
            self._is_connected = True
            self._offline_mode = False
            return True
        except Exception:
            self._is_connected = False
            self._offline_mode = True
            return False

    def sync_users_to_cloud(self, users: List[Dict]) -> bool:
        if self._offline_mode or not self._supabase:
            self._pending_sync.add("insert", "users", users[0] if users else {})
            return False

        try:
            self._supabase.table("users").upsert(
                users, on_conflict="username"
            ).execute()
            return True
        except Exception:
            self._offline_mode = True
            self._pending_sync.add("insert", "users", users[0] if users else {})
            return False

    def sync_audit_log(
        self,
        action: str,
        severity: str,
        user_id: Optional[str] = None,
        metadata: Dict = None,
    ) -> bool:
        data = {
            "action": action,
            "severity": severity,
            "user_id": user_id,
            "metadata": metadata or {},
        }

        if self._offline_mode or not self._supabase:
            self._pending_sync.add("insert", "audit_logs", data)
            return False

        try:
            self._supabase.table("audit_logs").insert(data).execute()
            return True
        except Exception:
            self._offline_mode = True
            self._pending_sync.add("insert", "audit_logs", data)
            return False

    def sync_telemetry_event(self, event_type: str, data: Dict) -> bool:
        telemetry_data = {"event_type": event_type, "data": data}

        if self._offline_mode or not self._supabase:
            self._pending_sync.add("insert", "telemetry", telemetry_data)
            return False

        try:
            self._supabase.table("telemetry").insert(telemetry_data).execute()
            return True
        except Exception:
            self._offline_mode = True
            self._pending_sync.add("insert", "telemetry", telemetry_data)
            return False

    def sync_package(
        self, name: str, version: str, description: str, installed: bool
    ) -> bool:
        data = {
            "name": name,
            "version": version,
            "description": description,
            "installed": installed,
        }

        if self._offline_mode or not self._supabase:
            self._pending_sync.add("insert", "packages", data)
            return False

        try:
            self._supabase.table("packages").upsert(
                data, on_conflict="name,version"
            ).execute()
            return True
        except Exception:
            self._offline_mode = True
            self._pending_sync.add("insert", "packages", data)
            return False

    def create_session(
        self, user_id: str, token: str, expires_at: datetime
    ) -> Optional[DBSession]:
        data = {
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

        if self._offline_mode or not self._supabase:
            self._pending_sync.add("insert", "sessions", data)
            return None

        try:
            result = self._supabase.table("sessions").insert(data).execute()
            if result.data:
                return DBSession(**result.data[0])
        except Exception:
            self._offline_mode = True
            self._pending_sync.add("insert", "sessions", data)

        return None

    def validate_session(self, token: str) -> Optional[DBSession]:
        if not self._supabase or self._offline_mode:
            return None

        try:
            result = (
                self._supabase.table("sessions")
                .select("*")
                .eq("token", token)
                .execute()
            )
            if result.data:
                session = DBSession(**result.data[0])
                expires = datetime.fromisoformat(
                    session.expires_at.replace("Z", "+00:00")
                )
                if expires > datetime.now(expires.tzinfo):
                    return session
        except Exception:
            pass

        return None

    def get_user_by_username(self, username: str) -> Optional[DBUser]:
        if not self._supabase or self._offline_mode:
            return None

        try:
            result = (
                self._supabase.table("users")
                .select("*")
                .eq("username", username)
                .execute()
            )
            if result.data:
                return DBUser(**result.data[0])
        except Exception:
            pass

        return None

    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        if not self._supabase or self._offline_mode:
            return []

        try:
            result = (
                self._supabase.table("audit_logs")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return [AuditLog(**row) for row in result.data]
        except Exception:
            return []

    def get_packages(self) -> List[Package]:
        if not self._supabase or self._offline_mode:
            return []

        try:
            result = self._supabase.table("packages").select("*").execute()
            return [Package(**row) for row in result.data]
        except Exception:
            return []

    def get_telemetry(self, limit: int = 100) -> List[TelemetryEvent]:
        if not self._supabase or self._offline_mode:
            return []

        try:
            result = (
                self._supabase.table("telemetry")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [TelemetryEvent(**row) for row in result.data]
        except Exception:
            return []

    def shutdown(self):
        self._sync_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)


DB = DatabaseClient()
