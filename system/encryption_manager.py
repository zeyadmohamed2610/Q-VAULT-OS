# =============================================================
#  encryption_manager.py — Q-VAULT OS  |  Encryption Manager
#
#  AES-256-GCM encryption for files and sessions
# =============================================================

import os
import json
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.backends import default_backend

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


SALT_FILE = os.path.expanduser("~/.qvault/.keystore")
SESSION_KEY_FILE = os.path.expanduser("~/.qvault/.session.key")


class EncryptionManager:
    """AES-256 encryption manager for Q-VAULT OS."""

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

        if not CRYPTO_AVAILABLE:
            self._master_key = None
            return

        self._master_key = self._load_or_create_master_key()

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    def _load_or_create_master_key(self) -> Optional[bytes]:
        """Load master key from secure storage or create new."""
        if not os.path.exists(SALT_FILE):
            return None

        try:
            with open(SALT_FILE, "rb") as f:
                data = json.load(f)
                return base64.b64decode(data["key"])
        except Exception:
            return None

    def set_master_password(self, password: str) -> bool:
        """Set master password and generate encryption key."""
        if not CRYPTO_AVAILABLE:
            return False

        salt = os.urandom(16)
        key = self._derive_key(password, salt)

        data = {
            "salt": base64.b64encode(salt).decode(),
            "key": base64.b64encode(key).decode(),
        }

        os.makedirs(os.path.dirname(SALT_FILE), exist_ok=True)
        with open(SALT_FILE, "w") as f:
            json.dump(data, f)

        self._master_key = key
        return True

    def verify_master_password(self, password: str) -> bool:
        """Verify master password."""
        if not CRYPTO_AVAILABLE or not os.path.exists(SALT_FILE):
            return False

        try:
            with open(SALT_FILE, "r") as f:
                data = json.load(f)

            salt = base64.b64decode(data["salt"])
            stored_key = base64.b64decode(data["key"])
            key = self._derive_key(password, salt)

            return key == stored_key
        except Exception:
            return False

    def is_unlocked(self) -> bool:
        """Check if encryption is unlocked."""
        return self._master_key is not None

    def encrypt_data(self, plaintext: bytes) -> Optional[bytes]:
        """Encrypt data with AES-256-GCM."""
        if not CRYPTO_AVAILABLE or not self._master_key:
            return None

        iv = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(self._master_key), modes.GCM(iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return iv + encryptor.tag + ciphertext

    def decrypt_data(self, encrypted: bytes) -> Optional[bytes]:
        """Decrypt data with AES-256-GCM."""
        if not CRYPTO_AVAILABLE or not self._master_key:
            return None

        try:
            iv = encrypted[:12]
            tag = encrypted[12:28]
            ciphertext = encrypted[28:]

            cipher = Cipher(
                algorithms.AES(self._master_key),
                modes.GCM(iv, tag),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            return decryptor.update(ciphertext) + decryptor.finalize()
        except Exception:
            return None

    def encrypt_file(self, filepath: str, output_path: Optional[str] = None) -> bool:
        """Encrypt a file."""
        if not CRYPTO_AVAILABLE or not self._master_key:
            return False

        try:
            with open(filepath, "rb") as f:
                plaintext = f.read()

            encrypted = self.encrypt_data(plaintext)
            if not encrypted:
                return False

            output = output_path or filepath + ".encrypted"
            with open(output, "wb") as f:
                f.write(encrypted)

            return True
        except Exception:
            return False

    def decrypt_file(self, filepath: str, output_path: Optional[str] = None) -> bool:
        """Decrypt a file."""
        if not CRYPTO_AVAILABLE or not self._master_key:
            return False

        try:
            with open(filepath, "rb") as f:
                encrypted = f.read()

            plaintext = self.decrypt_data(encrypted)
            if not plaintext:
                return False

            output = output_path or filepath.replace(".encrypted", "")
            with open(output, "wb") as f:
                f.write(plaintext)

            return True
        except Exception:
            return False

    def generate_session_key(self) -> str:
        """Generate a random session key."""
        return secrets.token_hex(32)

    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 (for non-reversible storage)."""
        salt = os.urandom(32)
        hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(salt + hash_obj).decode()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            data = base64.b64decode(stored_hash)
            salt = data[:32]
            stored_hash_value = data[32:]
            hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            return hash_obj == stored_hash_value
        except Exception:
            return False

    def lock(self):
        """Lock encryption (clear master key from memory)."""
        self._master_key = None

    def get_status(self) -> dict:
        """Get encryption status."""
        return {
            "crypto_available": CRYPTO_AVAILABLE,
            "unlocked": self.is_unlocked(),
            "master_key_set": os.path.exists(SALT_FILE),
        }


ENCRYPTION_MGR = EncryptionManager()
