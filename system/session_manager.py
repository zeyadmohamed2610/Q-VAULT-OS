# =============================================================
#  session_manager.py — Q-Vault OS  |  Unified Session Manager
#
#  SINGLE SOURCE OF TRUTH for:
#    • Authentication (login, fake-mode, lockout)
#    • Current user identity (username, role, uid, gid)
#    • Session type ("real" | "fake" | "demo")
#    • Sudo elevation cache (5-minute timeout, like Linux)
#    • User CRUD (create, delete, change password)
#    • Group membership
#
#  All other modules import from here — never from
#  core/user_manager.py or system/user_system.py directly.
#
#  Usage:
#    from system.session_manager import SESSION
#    result = SESSION.authenticate("admin", "admin123")
#    SESSION.sudo_granted  →  bool
#    SESSION.current_user  →  SessionUser | None
# =============================================================

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

try:
    from system.sync_manager import SYNC_MANAGER

    HAS_SYNC = True
except Exception:
    HAS_SYNC = False

# ── Storage paths ─────────────────────────────────────────────
_DB_DIR = Path.home() / ".qvault" / "users"
_DB_FILE = _DB_DIR / "users.json"
_GRP_FILE = _DB_DIR / "groups.json"

_SUDO_CACHE_SECONDS = 300  # 5 minutes
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


# ── Password utilities ────────────────────────────────────────


def _hash(password: str) -> str:
    """Fast SHA-256 hash — used for in-memory comparison only."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Data model ────────────────────────────────────────────────


@dataclass
class SessionUser:
    """Immutable-ish user record used at runtime."""

    username: str
    display_name: str
    role: str  # "admin" | "user"
    uid: int
    gid: int
    home: str
    # Runtime-only (not persisted)
    failed_attempts: int = field(default=0, repr=False)
    locked_until: float = field(default=0.0, repr=False)

    @property
    def is_root(self) -> bool:
        return self.role == "admin" or self.uid == 0

    def is_locked(self) -> bool:
        if self.locked_until and time.time() < self.locked_until:
            return True
        if self.locked_until and time.time() >= self.locked_until:
            self.failed_attempts = 0
            self.locked_until = 0.0
        return False

    def seconds_until_unlock(self) -> int:
        return max(0, int(self.locked_until - time.time()))


@dataclass
class AuthResult:
    success: bool
    user: Optional[SessionUser] = None
    session_type: str = "real"
    message: str = ""
    locked: bool = False


# ── Persistent user store ─────────────────────────────────────


class _UserStore:
    """Loads/saves user records from JSON.  Not exposed publicly."""

    _DEFAULTS = [
        {
            "username": "admin",
            "display_name": "Administrator",
            "role": "admin",
            "uid": 0,
            "gid": 0,
            "home": "/root",
            "password_hash": _hash("admin123"),
            "decoy_hash": _hash("decoy123"),
        },
        {
            "username": "user",
            "display_name": "Standard User",
            "role": "user",
            "uid": 1000,
            "gid": 1000,
            "home": "/home/user",
            "password_hash": _hash("user123"),
            "decoy_hash": _hash("fake123"),
        },
        {
            "username": "guest",
            "display_name": "Guest",
            "role": "user",
            "uid": 1001,
            "gid": 1001,
            "home": "/home/guest",
            "password_hash": _hash(""),
            "decoy_hash": "",
        },
    ]

    def __init__(self):
        self._records: dict[str, dict] = {}  # username → raw dict
        self._groups: dict[str, list[str]] = {}  # group   → [usernames]
        self._load()

    def _load(self):
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        if _DB_FILE.exists():
            try:
                data = json.loads(_DB_FILE.read_text("utf-8"))
                self._records = {d["username"]: d for d in data}
            except Exception:
                pass
        # Ensure defaults are always present
        for d in self._DEFAULTS:
            if d["username"] not in self._records:
                self._records[d["username"]] = dict(d)

        if _GRP_FILE.exists():
            try:
                self._groups = json.loads(_GRP_FILE.read_text("utf-8"))
            except Exception:
                pass
        if not self._groups:
            self._groups = {
                "admin": ["admin"],
                "users": ["user", "guest"],
                "root": ["admin"],
            }

    def save(self):
        try:
            _DB_DIR.mkdir(parents=True, exist_ok=True)
            _DB_FILE.write_text(
                json.dumps(list(self._records.values()), indent=2), "utf-8"
            )
            _GRP_FILE.write_text(json.dumps(self._groups, indent=2), "utf-8")
        except Exception:
            pass

    def get(self, username: str) -> Optional[dict]:
        return self._records.get(username.lower())

    def all(self) -> list[dict]:
        return list(self._records.values())

    def set(self, username: str, record: dict):
        self._records[username.lower()] = record
        self.save()

    def delete(self, username: str) -> bool:
        if username in ("admin",):
            return False  # can't delete admin
        removed = self._records.pop(username.lower(), None)
        if removed:
            self.save()
        return removed is not None

    def groups_for(self, username: str) -> list[str]:
        return [g for g, members in self._groups.items() if username in members]


# ── Session Manager ───────────────────────────────────────────


class SessionManager:
    """
    Singleton.  Owns ALL user/session state for the running OS session.

    Public API
    ──────────
    authenticate(username, password) → AuthResult
    current_user     → SessionUser | None
    session_type     → str ("real" | "fake" | "demo")
    logout()
    sudo_request(password) → bool   (True = elevated for 5 min)
    sudo_granted     → bool
    sudo_drop()
    get_user(username) → SessionUser | None
    all_users()      → list[SessionUser]
    create_user(username, password, role) → SessionUser | None
    delete_user(username) → bool
    change_password(username, new_password) → tuple[bool, str]
    groups_for(username) → list[str]
    subscribe(cb) / unsubscribe(cb)  — cb(event: str)
    """

    def __init__(self):
        self._store = _UserStore()
        self._current_user: Optional[SessionUser] = None
        self._session_type: str = "real"
        self._sudo_until: float = 0.0  # epoch time when sudo expires
        self._observers: list[Callable] = []
        # Runtime lockout tracker (kept in memory, not persisted)
        self._lockout: dict[str, SessionUser] = {}

    # ── Observers ─────────────────────────────────────────────

    def subscribe(self, cb: Callable):
        if cb not in self._observers:
            self._observers.append(cb)

    def unsubscribe(self, cb: Callable):
        self._observers = [o for o in self._observers if o is not cb]

    def _notify(self, event: str):
        for cb in self._observers:
            try:
                cb(event)
            except Exception:
                pass

    # ── Authentication ────────────────────────────────────────

    def authenticate(self, username: str, password: str) -> AuthResult:
        uname = username.strip().lower()
        record = self._store.get(uname)

        if record is None:
            return AuthResult(
                success=False,
                message=f"Unknown user '{uname}'.",
            )

        # Get or create runtime lockout tracker
        rt = self._lockout.get(uname)
        if rt is None:
            rt = self._to_session_user(record)
            self._lockout[uname] = rt

        if rt.is_locked():
            return AuthResult(
                success=False,
                message=f"Account locked. Retry in {rt.seconds_until_unlock()}s.",
                locked=True,
            )

        ph = _hash(password)

        # Real password
        if ph == record.get("password_hash", ""):
            rt.failed_attempts = 0
            rt.locked_until = 0.0
            user = self._to_session_user(record)
            self._current_user = user
            self._session_type = "real"
            self._sudo_until = 0.0
            self._notify("login")

            if HAS_SYNC:
                try:
                    SYNC_MANAGER.sync_audit_log(
                        "LOGIN",
                        "INFO",
                        user_id=record.get("id"),
                        metadata={"username": uname},
                    )
                except Exception:
                    pass

            return AuthResult(
                success=True,
                user=user,
                session_type="real",
                message=f"Welcome, {user.display_name}.",
            )

        # Decoy / fake-mode password
        dh = record.get("decoy_hash", "")
        if dh and ph == dh:
            rt.failed_attempts = 0
            user = self._to_session_user(record)
            self._current_user = user
            self._session_type = "fake"
            self._sudo_until = 0.0
            self._notify("login_fake")
            return AuthResult(
                success=True,
                user=user,
                session_type="fake",
                message=f"Welcome, {user.display_name}. [DECOY SESSION]",
            )

        # Wrong password
        rt.failed_attempts += 1
        remaining = MAX_ATTEMPTS - rt.failed_attempts
        if rt.failed_attempts >= MAX_ATTEMPTS:
            rt.locked_until = time.time() + LOCKOUT_SECONDS
            return AuthResult(
                success=False,
                message=f"Too many failures. Locked for {LOCKOUT_SECONDS}s.",
                locked=True,
            )
        return AuthResult(
            success=False,
            message=f"Incorrect password. {remaining} attempt(s) remaining.",
        )

    def logout(self):
        self._current_user = None
        self._session_type = "real"
        self._sudo_until = 0.0
        self._notify("logout")

    # ── Current session ───────────────────────────────────────

    @property
    def current_user(self) -> Optional[SessionUser]:
        return self._current_user

    @current_user.setter
    def current_user(self, v):
        """Allow direct assignment for demo-mode / compatibility."""
        if isinstance(v, str):
            # e.g. STATE.current_user = "demo"
            self._current_user = SessionUser(
                username=v,
                display_name=v.capitalize(),
                role="user",
                uid=1000,
                gid=1000,
                home=f"/home/{v}",
            )
        else:
            self._current_user = v
        self._notify("user_changed")

    @property
    def session_type(self) -> str:
        return self._session_type

    @session_type.setter
    def session_type(self, v: str):
        self._session_type = v

    def username(self) -> str:
        if self._current_user:
            return self._current_user.username
        return "guest"

    def is_root(self) -> bool:
        return self._current_user is not None and self._current_user.is_root

    # ── Sudo ──────────────────────────────────────────────────

    def sudo_request(self, password: str) -> bool:
        """
        Verify password and grant sudo for 5 minutes.
        Returns True if granted, False if denied.
        """
        if self._current_user is None:
            return False
        ph = _hash(password)
        record = self._store.get(self._current_user.username)
        if record and ph == record.get("password_hash", ""):
            self._sudo_until = time.time() + _SUDO_CACHE_SECONDS
            self._notify("sudo_granted")
            return True
        self._notify("sudo_denied")
        return False

    def sudo_drop(self):
        """Explicitly drop sudo elevation."""
        self._sudo_until = 0.0

    @property
    def sudo_granted(self) -> bool:
        """True if sudo is currently active (within 5-min cache window)."""
        return time.time() < self._sudo_until

    def sudo_remaining(self) -> int:
        """Seconds remaining on sudo cache, or 0."""
        return max(0, int(self._sudo_until - time.time()))

    # ── User management ───────────────────────────────────────

    def get_user(self, username: str) -> Optional[SessionUser]:
        record = self._store.get(username)
        return self._to_session_user(record) if record else None

    def all_users(self) -> list[SessionUser]:
        return [self._to_session_user(r) for r in self._store.all()]

    def create_user(
        self,
        username: str,
        password: str = "",
        role: str = "user",
        display_name: str = "",
    ) -> Optional[SessionUser]:
        uname = username.lower().strip()
        if self._store.get(uname):
            return None  # already exists

        # Find next available uid
        existing_uids = {r.get("uid", 0) for r in self._store.all()}
        uid = max(existing_uids) + 1 if existing_uids else 1002

        record = {
            "username": uname,
            "display_name": display_name or uname.capitalize(),
            "role": role,
            "uid": uid,
            "gid": uid,
            "home": f"/home/{uname}",
            "password_hash": _hash(password),
            "decoy_hash": "",
        }
        self._store.set(uname, record)
        return self._to_session_user(record)

    def delete_user(self, username: str) -> bool:
        return self._store.delete(username)

    def change_password(self, username: str, new_password: str) -> tuple[bool, str]:
        record = self._store.get(username)
        if not record:
            return False, f"User '{username}' not found."
        record["password_hash"] = _hash(new_password)
        self._store.set(username, record)
        return True, "Password changed."

    def verify_password(self, username: str, password: str) -> bool:
        record = self._store.get(username)
        if not record:
            return False
        return _hash(password) == record.get("password_hash", "")

    def groups_for(self, username: str) -> list[str]:
        return self._store.groups_for(username)

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _to_session_user(record: dict) -> SessionUser:
        return SessionUser(
            username=record.get("username", "unknown"),
            display_name=record.get("display_name", record.get("username", "unknown")),
            role=record.get("role", "user"),
            uid=record.get("uid", 1000),
            gid=record.get("gid", 1000),
            home=record.get("home", "/home/user"),
        )


# ── Module singleton ──────────────────────────────────────────
SESSION = SessionManager()

# ── Legacy compatibility shims ────────────────────────────────
# These allow old import paths to keep working without changes.


class _UMShim:
    """Wraps SESSION so that 'from core.user_manager import UM' still works."""

    class _AuthResult:
        def __init__(self, r: AuthResult):
            self.success = r.success
            self.user = r.user
            self.session_type = r.session_type
            self.message = r.message
            self.locked = r.locked

    def authenticate(self, username: str, password: str):
        return self._AuthResult(SESSION.authenticate(username, password))

    def get_user(self, username: str):
        return SESSION.get_user(username)

    def all_users(self):
        return SESSION.all_users()

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> tuple[bool, str]:
        if not SESSION.verify_password(username, old_password):
            return False, "Current password is incorrect."
        return SESSION.change_password(username, new_password)


UM_SHIM = _UMShim()
