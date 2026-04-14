# =============================================================
#  secure_temp.py — Q-VAULT OS  |  Secure Temp & Cache System
#
#  Encrypted temp files with auto-deletion
# =============================================================

import os
import pathlib
import tempfile
import shutil
import uuid
from typing import Optional
from datetime import datetime
from system.memory_security import secure_wipe

TEMP_ROOT = pathlib.Path.home() / ".qvault" / "tmp"
MAX_TEMP_SIZE_MB = 100


class SecureTempFile:
    """Secure temporary file with auto-cleanup."""

    def __init__(self, name: str = None, encrypted: bool = True):
        self._name = name or f"temp_{uuid.uuid4().hex}"
        self._path = None
        self._encrypted = encrypted
        self._created = datetime.now()
        self._secure = True

    def create(self) -> str:
        """Create secure temp file."""
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)

        self._path = TEMP_ROOT / self._name
        self._path.touch()

        os.chmod(self._path, 0o600)

        return str(self._path)

    def write(self, data: bytes) -> int:
        """Write data to temp file."""
        if not self._path:
            self.create()

        if self._encrypted:
            from system.encryption_manager import ENCRYPTION_MGR

            if ENCRYPTION_MGR.is_unlocked():
                encrypted = ENCRYPTION_MGR.encrypt_data(data)
                if encrypted:
                    data = encrypted

        with open(self._path, "wb") as f:
            return f.write(data)

    def read(self) -> Optional[bytes]:
        """Read data from temp file."""
        if not self._path or not self._path.exists():
            return None

        with open(self._path, "rb") as f:
            data = f.read()

        if self._encrypted:
            from system.encryption_manager import ENCRYPTION_MGR

            if ENCRYPTION_MGR.is_unlocked():
                decrypted = ENCRYPTION_MGR.decrypt_data(data)
                if decrypted:
                    return decrypted

        return data

    def secure_delete(self):
        """Securely delete temp file."""
        if not self._path or not self._path.exists():
            return

        try:
            with open(self._path, "r+b") as f:
                size = f.seek(0, 2)
                f.seek(0)
                f.write(b"\x00" * size)
                f.seek(0)
                f.write(b"\xff" * size)
                f.seek(0)
                f.write(b"\x55" * size)

            self._path.unlink()
        except Exception:
            pass

    @property
    def path(self) -> str:
        return str(self._path) if self._path else ""


class SecureTempManager:
    """Manages secure temporary files."""

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

        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self._active_files = {}

    def create_temp(self, name: str = None, encrypted: bool = True) -> SecureTempFile:
        """Create new secure temp file."""
        temp = SecureTempFile(name, encrypted)
        self._active_files[temp._name] = temp
        return temp

    def get_temp(self, name: str) -> Optional[SecureTempFile]:
        """Get existing temp file."""
        return self._active_files.get(name)

    def cleanup_all(self):
        """Securely delete all temp files."""
        for temp in list(self._active_files.values()):
            temp.secure_delete()

        self._active_files.clear()

        for f in TEMP_ROOT.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass

    def get_size(self) -> int:
        """Get total size of temp directory."""
        total = 0
        for f in TEMP_ROOT.glob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total

    def enforce_size_limit(self):
        """Enforce maximum temp size."""
        size_mb = self.get_size() / (1024 * 1024)
        if size_mb > MAX_TEMP_SIZE_MB:
            self.cleanup_all()

    def get_stats(self) -> dict:
        """Get temp manager stats."""
        return {
            "temp_dir": str(TEMP_ROOT),
            "active_files": len(self._active_files),
            "total_size_mb": self.get_size() / (1024 * 1024),
            "max_size_mb": MAX_TEMP_SIZE_MB,
        }


SECURE_TEMP = SecureTempManager()


def create_temp_file(name: str = None, encrypted: bool = True) -> SecureTempFile:
    """Create secure temp file."""
    return SECURE_TEMP.create_temp(name, encrypted)


def cleanup_all_temp():
    """Clean up all temp files."""
    SECURE_TEMP.cleanup_all()
