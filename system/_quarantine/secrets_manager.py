# ⚠️ QUARANTINED MODULE ⚠️
# ==============================
# Module: secrets_manager.py
# Status: NOT PART OF RUNTIME
# Warning: DO NOT IMPORT
# Reason: Pending architectural verification
# ==============================

# =============================================================
#  secrets_manager.py — Q-Vault OS  |  Secure Key Store
#
#  Stores and retrieves API keys securely using PyNaCl SecretBox
# ⚠️ QUARANTINED: This module is not currently part of the runtime
# =============================================================

import os
from pathlib import Path
from logging import getLogger
from nacl.secret import SecretBox
from nacl.utils import random

logger = getLogger(__name__)

SECRETS_DIR = Path.home() / ".qvault" / "security"
ENV_FILE = SECRETS_DIR / "vault.enc"
KEY_FILE = SECRETS_DIR / "sys_key.bin"


class SecretsManager:
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
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_or_create_key()

    def _load_or_create_key(self):
        if not KEY_FILE.exists():
            key = random(SecretBox.KEY_SIZE)
            KEY_FILE.write_bytes(key)
        else:
            key = KEY_FILE.read_bytes()
        self._box = SecretBox(key)

    def set_secret(self, key: str, value: str):
        secrets = self._read_all()
        secrets[key] = value
        self._write_all(secrets)

    def get_secret(self, key: str, default: str = "") -> str:
        secrets = self._read_all()
        return secrets.get(key, default)

    def _read_all(self) -> dict:
        if not ENV_FILE.exists():
            return {}
        try:
            encrypted = ENV_FILE.read_bytes()
            decrypted = self._box.decrypt(encrypted).decode("utf-8")
            secrets = {}
            for line in decrypted.split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    secrets[k] = v
            return secrets
        except Exception as e:
            logger.error(f"Failed to decrypt secrets: {e}")
            return {}

    def _write_all(self, secrets: dict):
        lines = [f"{k}={v}" for k, v in secrets.items()]
        data = "\n".join(lines).encode("utf-8")
        encrypted = self._box.encrypt(data)
        ENV_FILE.write_bytes(encrypted)


SECRETS = SecretsManager()
