# =============================================================
#  user_system.py — Q-VAULT OS  |  Multi-User Management
#
#  Full Linux-like user management system
# =============================================================

import os
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime


USER_DB_DIR = Path.home() / ".qvault" / "users"
USER_DB_FILE = USER_DB_DIR / "users.json"
GROUP_DB_FILE = USER_DB_DIR / "groups.json"


def _ensure_db_exists():
    """Ensure user database directory and files exist."""
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)

    if not USER_DB_FILE.exists():
        _create_default_users()

    if not GROUP_DB_FILE.exists():
        _create_default_groups()


def _hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 with salt."""
    salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return base64.b64encode(salt + hash_obj).decode()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        data = base64.b64decode(stored_hash)
        salt = data[:32]
        stored_hash_value = data[32:]
        hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hash_obj == stored_hash_value
    except Exception:
        return False


def _create_default_users():
    """Create default system users."""
    default_users = {
        "root": {
            "username": "root",
            "uid": 0,
            "gid": 0,
            "home": "/root",
            "password": _hash_password("root"),
            "shell": "/bin/bash",
            "full_name": "Super User",
            "created": datetime.now().isoformat(),
        },
        "user": {
            "username": "user",
            "uid": 1000,
            "gid": 1000,
            "home": "/home/user",
            "password": _hash_password("user"),
            "shell": "/bin/bash",
            "full_name": "Regular User",
            "created": datetime.now().isoformat(),
        },
        "guest": {
            "username": "guest",
            "uid": 1001,
            "gid": 1001,
            "home": "/home/guest",
            "password": _hash_password(""),
            "shell": "/bin/bash",
            "full_name": "Guest User",
            "created": datetime.now().isoformat(),
        },
    }

    with open(USER_DB_FILE, "w") as f:
        json.dump(default_users, f, indent=2)


def _create_default_groups():
    """Create default system groups."""
    default_groups = {
        "root": {"name": "root", "gid": 0, "members": ["root"]},
        "user": {"name": "user", "gid": 1000, "members": ["user"]},
        "guest": {"name": "guest", "gid": 1001, "members": ["guest"]},
        "admin": {"name": "admin", "gid": 100, "members": ["root"]},
    }

    with open(GROUP_DB_FILE, "w") as f:
        json.dump(default_groups, f, indent=2)


def load_users() -> dict:
    """Load all users from database."""
    _ensure_db_exists()
    try:
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict):
    """Save all users to database."""
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_groups() -> dict:
    """Load all groups from database."""
    _ensure_db_exists()
    try:
        with open(GROUP_DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_groups(groups: dict):
    """Save all groups to database."""
    USER_DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(GROUP_DB_FILE, "w") as f:
        json.dump(groups, f, indent=2)


class User:
    """Represents a system user."""

    def __init__(
        self,
        username: str,
        uid: int,
        gid: int,
        home: str,
        password_hash: str,
        shell: str,
        full_name: str = "",
        groups: list = None,
        created: str = None,
    ):
        self.username = username
        self.uid = uid
        self.gid = gid
        self.home = home
        self.password_hash = password_hash
        self.shell = shell
        self.full_name = full_name
        self.groups = groups or []
        self.created = created or datetime.now().isoformat()

    @property
    def is_root(self) -> bool:
        return self.uid == 0

    def verify_password(self, password: str) -> bool:
        return _verify_password(password, self.password_hash)

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "uid": self.uid,
            "gid": self.gid,
            "home": self.home,
            "password": self.password_hash,
            "shell": self.shell,
            "full_name": self.full_name,
            "groups": self.groups,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            username=data.get("username", ""),
            uid=data.get("uid", 1000),
            gid=data.get("gid", 1000),
            home=data.get("home", "/home/user"),
            password_hash=data.get("password", ""),
            shell=data.get("shell", "/bin/bash"),
            full_name=data.get("full_name", ""),
            groups=data.get("groups", []),
            created=data.get("created"),
        )


class UserManager:
    """Manages system users."""

    def __init__(self):
        _ensure_db_exists()
        self._users = load_users()
        self._groups = load_groups()

    def get_user(self, username: str) -> User | None:
        """Get user by username."""
        if username not in self._users:
            return None
        return User.from_dict(self._users[username])

    def get_user_by_uid(self, uid: int) -> User | None:
        """Get user by UID."""
        for u in self._users.values():
            if u.get("uid") == uid:
                return User.from_dict(u)
        return None

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user with password."""
        user = self.get_user(username)
        if not user:
            return False
        return user.verify_password(password)

    def user_exists(self, username: str) -> bool:
        """Check if user exists."""
        return username in self._users

    def create_user(
        self,
        username: str,
        password: str = "",
        uid: int = None,
        gid: int = None,
        home: str = None,
        shell: str = "/bin/bash",
        full_name: str = "",
    ) -> User | None:
        """Create a new user."""
        if self.user_exists(username):
            return None

        # Find available UID
        if uid is None:
            max_uid = 1000
            for u in self._users.values():
                max_uid = max(max_uid, u.get("uid", 0))
            uid = max_uid + 1

        # Find available GID
        if gid is None:
            max_gid = 1000
            for g in self._groups.values():
                max_gid = max(max_gid, g.get("gid", 0))
            gid = max_gid + 1

        # Default home directory
        if home is None:
            home = f"/home/{username}"

        user = User(
            username=username,
            uid=uid,
            gid=gid,
            home=home,
            password_hash=_hash_password(password),
            shell=shell,
            full_name=full_name,
        )

        self._users[username] = user.to_dict()
        save_users(self._users)

        # Create user group
        if str(gid) not in [g.get("gid") for g in self._groups.values()]:
            self._groups[username] = {
                "name": username,
                "gid": gid,
                "members": [username],
            }
            save_groups(self._groups)

        return user

    def delete_user(self, username: str) -> bool:
        """Delete a user."""
        if username not in self._users:
            return False

        if username == "root":
            return False  # Cannot delete root

        del self._users[username]
        save_users(self._users)

        # Remove from groups
        for g in self._groups.values():
            if username in g.get("members", []):
                g["members"].remove(username)
        save_groups(self._groups)

        return True

    def change_password(self, username: str, new_password: str) -> bool:
        """Change user password."""
        if username not in self._users:
            return False

        self._users[username]["password"] = _hash_password(new_password)
        save_users(self._users)
        return True

    def add_user_to_group(self, username: str, group: str) -> bool:
        """Add user to group."""
        if username not in self._users:
            return False
        if group not in self._groups:
            return False

        if username not in self._groups[group]["members"]:
            self._groups[group]["members"].append(username)
            save_groups(self._groups)

        if group not in self._users[username]["groups"]:
            self._users[username]["groups"].append(group)
            save_users(self._users)

        return True

    def remove_user_from_group(self, username: str, group: str) -> bool:
        """Remove user from group."""
        if username not in self._users:
            return False
        if group not in self._groups:
            return False

        if username in self._groups[group]["members"]:
            self._groups[group]["members"].remove(username)
            save_groups(self._groups)

        if group in self._users[username]["groups"]:
            self._users[username]["groups"].remove(group)
            save_users(self._users)

        return True

    def get_user_groups(self, username: str) -> list:
        """Get all groups user belongs to."""
        user = self.get_user(username)
        if not user:
            return []
        return user.groups

    def list_users(self) -> list:
        """List all users."""
        return [User.from_dict(u) for u in self._users.values()]


# Global user manager instance
USER_MGR = UserManager()
