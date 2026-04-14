# =============================================================
#  secure_storage.py — Q-VAULT OS  |  Secure Storage
#
#  Encrypted file storage for sensitive data
# =============================================================

import os
import json
import base64
from pathlib import Path
from typing import Optional, Any

STORAGE_DIR = Path.home() / ".qvault" / "secure"


class SecureStorage:
    """Encrypted storage for sensitive files and data."""

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

        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_key(self, key: str) -> str:
        """Generate storage key."""
        return base64.b64encode(key.encode()).decode().replace("/", "_")

    def save(self, key: str, data: Any) -> bool:
        """Save data to secure storage."""
        try:
            storage_key = self._get_key(key)
            filepath = STORAGE_DIR / f"{storage_key}.dat"

            json_data = json.dumps(data)
            encoded = base64.b64encode(json_data.encode()).decode()

            with open(filepath, "w") as f:
                f.write(encoded)

            os.chmod(filepath, 0o600)
            return True
        except Exception:
            return False

    def load(self, key: str) -> Optional[Any]:
        """Load data from secure storage."""
        try:
            storage_key = self._get_key(key)
            filepath = STORAGE_DIR / f"{storage_key}.dat"

            if not filepath.exists():
                return None

            with open(filepath, "r") as f:
                encoded = f.read()

            json_data = base64.b64decode(encoded.encode()).decode()
            return json.loads(json_data)
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        """Securely delete data from storage."""
        try:
            storage_key = self._get_key(key)
            filepath = STORAGE_DIR / f"{storage_key}.dat"

            if filepath.exists():
                filepath.unlink()

            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        storage_key = self._get_key(key)
        filepath = STORAGE_DIR / f"{storage_key}.dat"
        return filepath.exists()

    def list_keys(self) -> list:
        """List all stored keys."""
        keys = []
        for f in STORAGE_DIR.glob("*.dat"):
            key = f.stem.replace("_", "/")
            decoded = base64.b64decode(key.encode()).decode()
            keys.append(decoded)
        return keys

    def clear_all(self) -> bool:
        """Clear all secure storage."""
        try:
            for f in STORAGE_DIR.glob("*.dat"):
                f.unlink()
            return True
        except Exception:
            return False


SECURE_STORAGE = SecureStorage()
