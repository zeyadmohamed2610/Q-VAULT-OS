import logging
import os
import pathlib
import time
from collections import deque
from typing import Union, Iterator, List
from .permissions import PM_GUARD, ENFORCEMENT_LEVEL
from system.runtime_manager import RUNTIME_MANAGER
from system.config import mask_path

logger = logging.getLogger("sandbox.fs_guard")


class FileSystemGuard:
    """
    Virtual Chroot — Controlled Enforcement.

    Safe Alternatives provided for every blocked operation:
      open()        -> self.open()       returns empty string on jail-escape
      scandir()     -> self.scandir()    returns [] on jail-escape
      listdir()     -> self.listdir()    returns [] on jail-escape
      path check    -> self.is_safe()    pure bool
    """

    def __init__(self, app_id: str, api=None):
        self.app_id = app_id
        self.api = api # Reference to SecureAPI for lock checks and policy
        # The sandbox root is now AUTHORITATIVE from RuntimeManager.
        # It is set during app registration in the Kernel.
        if self.api and hasattr(self.api, "instance_id"):
            record = RUNTIME_MANAGER.get_record(self.api.instance_id) if RUNTIME_MANAGER else None
            
            if record:
                self.jail_root = pathlib.Path(record.sandbox_root).resolve()
            else:
                # 🟢 Normal fallback for sandboxes where RM is None
                self.jail_root = pathlib.Path(".").resolve() / "users" / self.app_id
        else:
            self.jail_root = pathlib.Path(".").resolve() / "users" / self.app_id
        
        self.jail_root.mkdir(parents=True, exist_ok=True)
        self._call_window = deque() # Sliding window for rate limiting

    # ── Core check ────────────────────────────────────────────────────────────

    def _resolve(self, path: Union[str, pathlib.Path]) -> pathlib.Path:
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = self.jail_root / p
        return p.resolve(strict=False)

    def is_safe(self, path: Union[str, pathlib.Path]) -> bool:
        """
        Pure Resolution Boundary Check (Phase 14.3.2).
        
        Removes string-based heuristics (is_absolute, colon checks) in favor
        of OS-level canonical path resolution.
        """
        # Resolve path AND follow symlinks to find the REAL target
        try:
            target = self._resolve(path)
        except Exception:
            # If resolution fails (e.g. invalid path characters), block it
            return False
        
        # Security Boundary: MUST be inside jail_root.
        # This handles absolute paths, drive letters, and '..' automatically
        # because resolve() eliminates them.
        in_jail = target.is_relative_to(self.jail_root)
        
        if not in_jail:
            logger.warning(
                "[FS VIOLATION] App='%s' attempted access outside AUTHORIZED jail: %s",
                self.app_id, mask_path(target),
            )
        return in_jail

    def _enforce_rate_limit(self):
        """Pass-through to Kernel-level backpressure (Phase 14.3.2)."""
        # We no longer need local rate-limiting because RuntimeManager 
        # enforces it during acquire_worker() calls.
        pass

    # ── Safe Alternatives ─────────────────────────────────────────────────────

    def open(
        self,
        path: Union[str, pathlib.Path],
        mode: str = "r",
        *args,
        **kwargs,
    ):
        """
        Controlled drop-in for built-in open().
        """
        if self.api:
            # 14.3.2: Kernel now validates rate + pending calls here
            self.api.check_api_lock("fs")

        PM_GUARD.check(self.app_id, "file_access", str(path))

        # 14.3.2: Pure Resolve enforcement
        resolved_path = self._resolve(path)
        if not self.is_safe(resolved_path):
            if ENFORCEMENT_LEVEL == "strict":
                raise PermissionError(f"[Sandbox] AUTHORIZATION FAILED: {path} is outside your workspace.")
            return open(os.devnull, mode)

        # 14.3.2: Directory-based Protection
        # Protect system-level folders if the jail was somehow misconfigured
        if any(sys_dir in str(resolved_path) for sys_dir in ["/system/", "/core/", "/qvault-core/"]):
            raise PermissionError("[Sandbox] System core folders are READ-ONLY or HIDDEN.")

        return open(resolved_path, mode, *args, **kwargs)

    def scandir(self, path: Union[str, pathlib.Path]) -> List:
        """
        Controlled drop-in for os.scandir().
        """
        if self.api:
            self.api.check_api_lock("fs")
        PM_GUARD.check(self.app_id, "file_access", str(path))

        target = self._resolve(path)
        if not self.is_safe(target):
            logger.warning("[FS] Out-of-bounds scandir: %s", target)
            return []

        try:
            return sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name))
        except Exception:
            return []

    def listdir(self, path: Union[str, pathlib.Path]) -> List[str]:
        """Controlled drop-in for os.listdir()."""
        if self.api:
            self.api.check_api_lock("fs")
        PM_GUARD.check(self.app_id, "file_access", str(path))

        target = self._resolve(path)
        if not self.is_safe(target):
            return []

        try:
            return os.listdir(target)
        except Exception:
            return []

    def list_dir(self, path: Union[str, pathlib.Path] = ".") -> List[str]:
        """Convenience alias for listdir()."""
        return self.listdir(path)

    def read_file(self, path: Union[str, pathlib.Path], binary: bool = False) -> Union[str, bytes]:
        """
        Sovereign Read: Performs on-the-fly decryption if the file is encrypted.
        """
        if self.api:
            self.api.check_api_lock("fs")
        PM_GUARD.check(self.app_id, "file_access", str(path))

        target = self._resolve(path)
        if not self.is_safe(target):
            return b"" if binary else ""

        try:
            with open(target, "rb") as f:
                raw_data = f.read()

            # Check for Q-Vault Encryption Header
            MAGIC = b"QV-ENC\x00"
            if raw_data.startswith(MAGIC):
                from core.runtime_bridge import SECURITY_ENGINE
                if SECURITY_ENGINE and self.api:
                    # Decrypt via Rust bridge
                    decrypted = SECURITY_ENGINE.decrypt_file(self.api.instance_id, raw_data[len(MAGIC):])
                    if binary:
                        return decrypted
                    return decrypted.decode("utf-8", errors="replace")
            
            # Not encrypted or engine missing — fallback to plain
            if binary:
                return raw_data
            return raw_data.decode("utf-8", errors="replace")
            
        except Exception as e:
            logger.error("[FS] Read failed for %s: %s", target, e)
            return b"" if binary else ""

    def write_file(self, path: Union[str, pathlib.Path], data: Union[str, bytes], encrypt: bool = True) -> bool:
        """
        Sovereign Write: Transparently encrypts data via Rust before persisting to disk.
        """
        if self.api:
            self.api.check_api_lock("fs")
        PM_GUARD.check(self.app_id, "file_access", str(path))

        target = self._resolve(path)
        if not self.is_safe(target):
            return False

        try:
            payload = data if isinstance(data, bytes) else data.encode("utf-8")
            
            if encrypt:
                from core.runtime_bridge import SECURITY_ENGINE
                if SECURITY_ENGINE and self.api:
                    # Encrypt via Rust bridge
                    ciphertext = SECURITY_ENGINE.encrypt_file(self.api.instance_id, payload)
                    # Prepend magic header
                    payload = b"QV-ENC\x00" + ciphertext

            with open(target, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error("[FS] Write failed for %s: %s", target, e)
            return False
