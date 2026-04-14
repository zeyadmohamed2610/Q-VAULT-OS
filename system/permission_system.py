# =============================================================
#  permission_system.py — Q-Vault OS  |  Linux-like Permissions
#
#  Full rwx permission model with ownership
# =============================================================

import os
import json
from pathlib import Path
from typing import Optional


METADATA_DIR = Path.home() / ".qvault" / "metadata"


def _ensure_metadata_dir():
    """Ensure metadata directory exists."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_metadata_path(path: str) -> Path:
    """Get metadata file path for a file/directory."""
    abs_path = os.path.abspath(path)
    safe_name = abs_path.replace("/", "_").replace("\\", "_").replace(":", "")
    return METADATA_DIR / f"{safe_name}.json"


class FileMetadata:
    """Represents file metadata including permissions."""

    def __init__(
        self, path: str, owner: int = 1000, group: int = 1000, mode: str = "755"
    ):
        self.path = path
        self.owner = owner
        self.group = group
        self.mode = mode

    @property
    def owner_read(self) -> bool:
        return self.mode[0] == "r"

    @property
    def owner_write(self) -> bool:
        return self.mode[0] == "r" and self.mode[1] == "w"

    @property
    def owner_exec(self) -> bool:
        return len(self.mode) > 2 and self.mode[2] == "x"

    @property
    def group_read(self) -> bool:
        return len(self.mode) > 3 and self.mode[3] == "r"

    @property
    def group_write(self) -> bool:
        return len(self.mode) > 4 and self.mode[4] == "w"

    @property
    def group_exec(self) -> bool:
        return len(self.mode) > 5 and self.mode[5] == "x"

    @property
    def other_read(self) -> bool:
        return len(self.mode) > 6 and self.mode[6] == "r"

    @property
    def other_write(self) -> bool:
        return len(self.mode) > 7 and self.mode[7] == "w"

    @property
    def other_exec(self) -> bool:
        return len(self.mode) > 8 and self.mode[8] == "x"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "owner": self.owner,
            "group": self.group,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileMetadata":
        return cls(
            path=data.get("path", ""),
            owner=data.get("owner", 1000),
            group=data.get("group", 1000),
            mode=data.get("mode", "755"),
        )

    def save(self):
        """Save metadata to disk."""
        _ensure_metadata_dir()
        meta_path = _get_metadata_path(self.path)
        with open(meta_path, "w") as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path: str) -> Optional["FileMetadata"]:
        """Load metadata from disk."""
        meta_path = _get_metadata_path(path)
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
                return cls.from_dict(data)
        except Exception:
            return None


def get_permission_string(mode: str) -> str:
    """Convert numeric mode to rwx string."""
    result = ""

    # Owner
    result += "r" if mode[0] == "r" else "-"
    result += "w" if len(mode) > 1 and mode[1] == "w" else "-"
    result += "x" if len(mode) > 2 and mode[2] == "x" else "-"

    # Group
    result += "r" if len(mode) > 3 and mode[3] == "r" else "-"
    result += "w" if len(mode) > 4 and mode[4] == "w" else "-"
    result += "x" if len(mode) > 5 and mode[5] == "x" else "-"

    # Other
    result += "r" if len(mode) > 6 and mode[6] == "r" else "-"
    result += "w" if len(mode) > 7 and mode[7] == "w" else "-"
    result += "x" if len(mode) > 8 and mode[8] == "x" else "-"

    return result


def parse_mode(mode_str: str) -> str:
    """Parse numeric mode (755) or symbolic mode (u+rw)."""
    if mode_str.isdigit():
        # Pad to 3 digits
        while len(mode_str) < 3:
            mode_str = "0" + mode_str
        return mode_str[:3]

    # Handle symbolic mode (simplified)
    result = "000"
    if "r" in mode_str:
        result = result[:0] + "r" + result[1:]
    if "w" in mode_str:
        result = result[:1] + "w" + result[2:]
    if "x" in mode_str:
        result = result[:2] + "x" + result[3:]

    return result


class PermissionManager:
    """Manages file permissions."""

    def __init__(self):
        _ensure_metadata_dir()
        self._cache = {}

    def get_metadata(self, path: str) -> FileMetadata:
        """Get file metadata, creating default if needed."""
        path = os.path.abspath(path)

        if path in self._cache:
            return self._cache[path]

        meta = FileMetadata.load(path)
        if meta is None:
            # Create default metadata
            meta = FileMetadata(path=path, owner=1000, group=1000, mode="755")
            meta.save()

        self._cache[path] = meta
        return meta

    def set_owner(self, path: str, owner: int, group: int = None):
        """Set file owner."""
        meta = self.get_metadata(path)
        meta.owner = owner
        if group is not None:
            meta.group = group
        meta.save()
        self._cache[os.path.abspath(path)] = meta

    def set_mode(self, path: str, mode: str):
        """Set file mode."""
        meta = self.get_metadata(path)
        meta.mode = parse_mode(mode)
        meta.save()
        self._cache[os.path.abspath(path)] = meta

    def check_permission(
        self, path: str, user_uid: int, user_groups: list, permission: str
    ) -> bool:
        """
        Check if user has permission.

        permission: 'r', 'w', or 'x'
        """
        path = os.path.abspath(path)

        # Root bypasses all permissions
        if user_uid == 0:
            return True

        meta = self.get_metadata(path)

        # Determine user category
        is_owner = meta.owner == user_uid
        is_group = meta.group in user_groups

        if is_owner:
            if permission == "r":
                return meta.owner_read
            elif permission == "w":
                return meta.owner_write
            elif permission == "x":
                return meta.owner_exec
        elif is_group:
            if permission == "r":
                return meta.group_read
            elif permission == "w":
                return meta.group_write
            elif permission == "x":
                return meta.group_exec
        else:
            if permission == "r":
                return meta.other_read
            elif permission == "w":
                return meta.other_write
            elif permission == "x":
                return meta.other_exec

        return False

    def can_read(self, path: str, user_uid: int, user_groups: list) -> bool:
        """Check if user can read file."""
        return self.check_permission(path, user_uid, user_groups, "r")

    def can_write(self, path: str, user_uid: int, user_groups: list) -> bool:
        """Check if user can write file."""
        return self.check_permission(path, user_uid, user_groups, "w")

    def can_execute(self, path: str, user_uid: int, user_groups: list) -> bool:
        """Check if user can execute file."""
        return self.check_permission(path, user_uid, user_groups, "x")

    def get_ls_string(self, path: str) -> str:
        """Get ls -l style permission string."""
        meta = self.get_metadata(path)
        perms = get_permission_string(meta.mode)

        if os.path.isdir(path):
            return "d" + perms
        return "-" + perms

    def copy_metadata(self, src: str, dst: str):
        """Copy metadata from source to destination."""
        src_meta = self.get_metadata(src)
        dst_meta = FileMetadata(
            path=dst, owner=src_meta.owner, group=src_meta.group, mode=src_meta.mode
        )
        dst_meta.save()
        self._cache[os.path.abspath(dst)] = dst_meta


# Global permission manager
PERM_MGR = PermissionManager()
