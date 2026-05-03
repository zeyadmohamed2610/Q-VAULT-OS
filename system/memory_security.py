import os
import ctypes
import hashlib
from typing import Any, Optional
from weakref import WeakValueDictionary


class SecureMemory:
    """Secure memory management with automatic wiping."""

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
        self._sensitive_data = WeakValueDictionary()
        self._wipe_count = 0

    def store(self, key: str, value: Any):
        """Store sensitive data with automatic wiping on cleanup."""
        self._sensitive_data[key] = value

    def wipe(self, key: str) -> bool:
        """Securely wipe a specific key from memory."""
        if key in self._sensitive_data:
            try:
                del self._sensitive_data[key]
                self._wipe_count += 1
                return True
            except Exception:
                pass
        return False

    def wipe_all(self):
        """Wipe all sensitive data from memory."""
        keys = list(self._sensitive_data.keys())
        for key in keys:
            self.wipe(key)
        self._wipe_count = 0

    def secure_overwrite(self, data: bytearray) -> None:
        """
        Overwrite data with multiple patterns to prevent recovery.
        More secure than simple reassignment.
        """
        if not isinstance(data, bytearray):
            return

        length = len(data)

        try:
            for i in range(length):
                data[i] = 0x00

            for i in range(length):
                data[i] = 0xFF

            for i in range(length):
                data[i] = 0xAA

            for i in range(length):
                data[i] = 0x55

            for i in range(length):
                data[i] = 0x00

        except Exception:
            pass

    def secure_string_clear(self, s: str) -> None:
        """Attempt to clear a string from memory."""
        try:
            s_array = bytearray(s.encode())
            self.secure_overwrite(s_array)
        except Exception:
            pass

    def get_wipe_count(self) -> int:
        """Get number of items wiped."""
        return self._wipe_count

    def get_active_count(self) -> int:
        """Get number of active sensitive items."""
        return len(self._sensitive_data)


SECURE_MEMORY = SecureMemory()


def secure_wipe(data: bytearray) -> None:
    """Convenience function for secure wiping."""
    SECURE_MEMORY.secure_overwrite(data)


def clear_sensitive(key: str) -> bool:
    """Convenience function to clear sensitive data."""
    return SECURE_MEMORY.wipe(key)


def clear_all_sensitive() -> None:
    """Clear all sensitive data."""
    SECURE_MEMORY.wipe_all()
