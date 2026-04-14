# =============================================================
#  process_isolation.py — Q-VAULT OS  |  Process Isolation
#
#  Per-process sandbox context and user isolation
# =============================================================

import os
import uuid
import pathlib
from typing import Optional, Set, Dict
from datetime import datetime

USER_HOME_BASE = pathlib.Path.home() / ".qvault" / "users"


class ProcessContext:
    """Represents a process's execution context."""

    def __init__(self, pid: int, user: str, home: str):
        self.pid = pid
        self.user = user
        self.home = home
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
        self.allowed_paths: Set[str] = set()
        self.restricted = True

        self._setup_allowed_paths()

    def _setup_allowed_paths(self):
        """Set up allowed paths for this context."""
        user_home = USER_HOME_BASE / self.user
        if user_home.exists():
            self.allowed_paths.add(str(user_home.resolve()))

        self.allowed_paths.add(str((USER_HOME_BASE / ".shared").resolve()))

    def can_access(self, path: str) -> bool:
        """Check if path is accessible in this context."""
        if not self.restricted:
            return True

        path_resolved = str(pathlib.Path(path).resolve())

        for allowed in self.allowed_paths:
            if path_resolved.startswith(allowed):
                return True

        return False

    def is_within_home(self, path: str) -> bool:
        """Check if path is within user's home directory."""
        user_home = USER_HOME_BASE / self.user
        path_resolved = pathlib.Path(path).resolve()
        home_resolved = user_home.resolve()

        try:
            path_resolved.relative_to(home_resolved)
            return True
        except ValueError:
            return False


class ProcessIsolation:
    """Manages process isolation and access control."""

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

        self._contexts: Dict[int, ProcessContext] = {}
        self._user_homes: Dict[str, str] = {}
        self._setup_user_homes()

    def _setup_user_homes(self):
        """Set up user home directories."""
        USER_HOME_BASE.mkdir(parents=True, exist_ok=True)

        for username in ["root", "user", "demo", "admin"]:
            user_home = USER_HOME_BASE / username
            user_home.mkdir(exist_ok=True)
            self._user_homes[username] = str(user_home)

    def create_context(self, pid: int, user: str) -> ProcessContext:
        """Create new process context."""
        home = self._user_homes.get(user, str(USER_HOME_BASE / user))

        context = ProcessContext(pid, user, home)
        self._contexts[pid] = context

        return context

    def get_context(self, pid: int) -> Optional[ProcessContext]:
        """Get process context."""
        return self._contexts.get(pid)

    def remove_context(self, pid: int):
        """Remove process context."""
        self._contexts.pop(pid, None)

    def check_access(self, pid: int, path: str) -> bool:
        """Check if process can access path."""
        context = self._contexts.get(pid)
        if not context:
            return False

        return context.can_access(path)

    def enforce_user_isolation(
        self, user: str, path: str, require_root: bool = False
    ) -> tuple[bool, str]:
        """
        Enforce user isolation - ensure user can only access their home directory.
        Returns (allowed, reason)
        """
        if require_root and user != "root":
            return False, "Root privileges required"

        user_home = self._user_homes.get(user)
        if not user_home:
            return False, f"User home not found: {user}"

        path_resolved = str(pathlib.Path(path).resolve())

        if path_resolved.startswith(user_home):
            return True, "OK"

        if user == "root":
            return True, "Root bypass"

        return False, f"Access denied: {path} is outside user home ({user})"

    def get_user_home(self, user: str) -> str:
        """Get user's home directory."""
        return self._user_homes.get(user, str(USER_HOME_BASE / user))

    def list_active_contexts(self) -> list:
        """List all active process contexts."""
        return [
            {
                "pid": ctx.pid,
                "user": ctx.user,
                "home": ctx.home,
                "session": ctx.session_id[:8] + "...",
                "created": ctx.created_at,
            }
            for ctx in self._contexts.values()
        ]

    def get_stats(self) -> Dict:
        """Get isolation statistics."""
        users = set(ctx.user for ctx in self._contexts.values())
        return {
            "active_contexts": len(self._contexts),
            "unique_users": len(users),
            "user_homes": len(self._user_homes),
        }


PROCESS_ISOLATION = ProcessIsolation()
