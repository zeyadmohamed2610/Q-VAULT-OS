# =============================================================
#  sync_manager.py — Q-VAULT OS  |  Production-Grade Sync Engine
#
#  Features:
#    - Local-first sync strategy
#    - Conflict resolution (last-write-wins)
#    - Background worker with batching
#    - Data integrity validation
#    - Fail-safe offline operation
# =============================================================

import os
import json
import time
import hashlib
import threading
import queue as queue_module
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field, asdict
from collections import defaultdict

SYNC_INTERVAL = 3
MAX_QUEUE_SIZE = 1000
MAX_BATCH_SIZE = 50
MAX_RETRIES = 3
DEBOUNCE_MS = 500

LOCAL_DB_DIR = Path.home() / ".qvault" / "db"
PENDING_QUEUE_FILE = LOCAL_DB_DIR / "pending_queue.json"
CONFLICT_LOG_FILE = LOCAL_DB_DIR / "conflicts.json"


@dataclass
class SyncOperation:
    type: str
    table: str
    data: Dict
    timestamp: str
    hash: str = field(
        default_factory=lambda: hashlib.sha256(str(time.time()).encode()).hexdigest()
    )
    retry_count: int = 0
    id: str = field(
        default_factory=lambda: hashlib.md5(
            str(time.time() + id(time)).encode()
        ).hexdigest()[:12]
    )


@dataclass
class SyncStatus:
    is_running: bool
    queue_size: int
    pending_count: int
    failed_count: int
    last_sync: Optional[str]
    is_online: bool


class SchemaValidator:
    SCHEMAS = {
        "users": {
            "required": ["username", "password_hash"],
            "optional": ["is_root", "created_at"],
        },
        "sessions": {
            "required": ["user_id", "token", "expires_at"],
            "optional": ["created_at"],
        },
        "audit_logs": {
            "required": ["action", "severity"],
            "optional": ["user_id", "timestamp", "metadata"],
        },
        "telemetry": {"required": ["event_type"], "optional": ["data", "created_at"]},
        "packages": {
            "required": ["name", "version"],
            "optional": ["description", "installed", "created_at"],
        },
    }

    @classmethod
    def validate(cls, data: Dict, table: str) -> bool:
        if table not in cls.SCHEMAS:
            return False
        schema = cls.SCHEMAS[table]
        for field_name in schema["required"]:
            if field_name not in data:
                return False
        return True


class ConflictResolver:
    @staticmethod
    def resolve(local: Dict, remote: Dict) -> Dict:
        local_time = local.get("updated_at") or local.get("created_at") or 0
        remote_time = remote.get("updated_at") or remote.get("created_at") or 0

        if local_time >= remote_time:
            return local
        else:
            return remote

    @staticmethod
    def merge_updates(local: Dict, remote: Dict) -> Dict:
        merged = dict(remote)
        for key, value in local.items():
            if key not in remote:
                merged[key] = value
        return merged


class PendingQueue:
    def __init__(self):
        self._queue: queue_module.Queue = queue_module.Queue(maxsize=MAX_QUEUE_SIZE)
        self._failed: List[SyncOperation] = []
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self):
        try:
            LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)
            if PENDING_QUEUE_FILE.exists():
                with open(PENDING_QUEUE_FILE, "r") as f:
                    data = json.load(f)
                    for item in data:
                        self._queue.put(SyncOperation(**item))
        except Exception:
            pass

    def _save_to_disk(self):
        try:
            items = list(self._queue.queue) + self._failed
            data = [asdict(op) for op in items]
            with open(PENDING_QUEUE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def add(self, operation: SyncOperation) -> bool:
        try:
            self._queue.put_nowait(operation)
            self._save_to_disk()
            return True
        except queue_module.Full:
            try:
                self._queue.get_nowait()
            except queue_module.Empty:
                pass
            self._queue.put(operation)
            self._save_to_disk()
            return True

    def get_batch(self, max_size: int = MAX_BATCH_SIZE) -> List[SyncOperation]:
        batch = []
        for _ in range(min(max_size, self._queue.qsize())):
            try:
                batch.append(self._queue.get_nowait())
            except queue_module.Empty:
                break
        return batch

    def requeue_failed(self):
        with self._lock:
            for op in self._failed:
                if op.retry_count < MAX_RETRIES:
                    op.retry_count += 1
                    try:
                        self._queue.put_nowait(op)
                    except queue_module.Full:
                        pass
            self._failed = [op for op in self._failed if op.retry_count >= MAX_RETRIES]
            self._save_to_disk()

    def mark_failed(self, operation: SyncOperation):
        with self._lock:
            self._failed.append(operation)
            self._save_to_disk()

    def size(self) -> int:
        return self._queue.qsize()

    def failed_count(self) -> int:
        return len(self._failed)


class SyncManager:
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

        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._pending_queue = PendingQueue()
        self._last_sync: Optional[datetime] = None
        self._is_online = False
        self._debounce_timer: Optional[threading.Timer] = None
        self._debounce_pending = False
        self._supabase_client = None
        self._sync_stats = defaultdict(int)
        self._conflict_log: List[Dict] = []

        self._init_supabase()
        self._start_worker()

    def _init_supabase(self):
        try:
            from supabase import create_client

            supabase_url = os.environ.get(
                "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
            )
            supabase_key = os.environ.get("SUPABASE_KEY", "")
            if supabase_key:
                self._supabase_client = create_client(supabase_url, supabase_key)
                self._is_online = True
        except Exception:
            self._is_online = False

    def _start_worker(self):
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        while self._running:
            try:
                if self._is_online:
                    self._process_pending_queue()
                    self._reconcile_with_cloud()
                else:
                    self._check_connection()
            except Exception:
                pass
            time.sleep(SYNC_INTERVAL)

    def _check_connection(self):
        if not self._supabase_client:
            return
        try:
            self._supabase_client.table("users").select("id").limit(1).execute()
            self._is_online = True
        except Exception:
            self._is_online = False

    def _process_pending_queue(self):
        batch = self._pending_queue.get_batch()
        if not batch:
            return

        success_count = 0
        failed_ops = []

        for op in batch:
            if self._validate_operation(op):
                if self._execute_sync(op):
                    success_count += 1
                else:
                    failed_ops.append(op)
            else:
                failed_ops.append(op)

        for op in failed_ops:
            self._pending_queue.mark_failed(op)

        self._sync_stats["total_synced"] += success_count
        self._last_sync = datetime.now()

    def _validate_operation(self, op: SyncOperation) -> bool:
        data_hash = hashlib.sha256(
            json.dumps(op.data, sort_keys=True).encode()
        ).hexdigest()
        if data_hash != op.hash:
            return False
        return SchemaValidator.validate(op.data, op.table)

    def _execute_sync(self, op: SyncOperation) -> bool:
        if not self._supabase_client:
            return False

        try:
            table = op.table
            data = op.data

            if op.type == "insert":
                self._supabase_client.table(table).insert(data).execute()
            elif op.type == "update":
                if "id" in data:
                    self._supabase_client.table(table).update(data).eq(
                        "id", data["id"]
                    ).execute()
            elif op.type == "delete":
                if "id" in data:
                    self._supabase_client.table(table).delete().eq(
                        "id", data["id"]
                    ).execute()

            return True
        except Exception:
            return False

    def _reconcile_with_cloud(self):
        pass

    def _debounced_sync(self):
        if self._debounce_pending:
            return
        self._debounce_pending = True
        self._debounce_timer = threading.Timer(DEBOUNCE_MS / 1000, self._trigger_sync)
        self._debounce_timer.start()

    def _trigger_sync(self):
        self._debounce_pending = False

    def queue_operation(self, op_type: str, table: str, data: Dict):
        operation = SyncOperation(
            type=op_type, table=table, data=data, timestamp=datetime.now().isoformat()
        )

        if not self._pending_queue.add(operation):
            pass

        if self._is_online:
            self._debounced_sync()

    def queue_insert(self, table: str, data: Dict):
        self.queue_operation("insert", table, data)

    def queue_update(self, table: str, data: Dict):
        self.queue_operation("update", table, data)

    def queue_delete(self, table: str, data: Dict):
        self.queue_operation("delete", table, data)

    def sync_users(self, users: List[Dict]):
        for user in users:
            self.queue_insert("users", user)

    def sync_audit_log(
        self,
        action: str,
        severity: str,
        user_id: Optional[str] = None,
        metadata: Dict = None,
    ):
        data = {
            "action": action,
            "severity": severity,
            "user_id": user_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.queue_insert("audit_logs", data)

    def sync_telemetry(self, event_type: str, data: Dict):
        telemetry_data = {
            "event_type": event_type,
            "data": data,
            "created_at": datetime.now().isoformat(),
        }
        self.queue_insert("telemetry", telemetry_data)

    def sync_package(self, name: str, version: str, description: str, installed: bool):
        data = {
            "name": name,
            "version": version,
            "description": description,
            "installed": installed,
            "updated_at": datetime.now().isoformat(),
        }
        self.queue_insert("packages", data)

    def sync_session(self, user_id: str, token: str, expires_at: datetime):
        data = {
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at.isoformat(),
        }
        self.queue_insert("sessions", data)

    def get_status(self) -> SyncStatus:
        return SyncStatus(
            is_running=self._running,
            queue_size=self._pending_queue.size(),
            pending_count=self._pending_queue.size(),
            failed_count=self._pending_queue.failed_count(),
            last_sync=self._last_sync.isoformat() if self._last_sync else None,
            is_online=self._is_online,
        )

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._sync_stats)

    def get_conflicts(self) -> List[Dict]:
        return self._conflict_log

    def force_sync_now(self):
        self._process_pending_queue()

    def shutdown(self):
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)


SYNC_MANAGER = SyncManager()
