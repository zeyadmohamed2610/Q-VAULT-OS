# =============================================================
#  sandbox_system.py — Q-Vault OS  |  Security Sandbox Layer
#
#  Sandboxes all file operations to ~/QVAULT_SANDBOX
#  Prevents accidental modification of system files
# =============================================================

import os
import pathlib
import shutil
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import QMessageBox, QWidget


SANDBOX_DIR = pathlib.Path.home() / "QVAULT_SANDBOX"
TRASH_DIR = pathlib.Path.home() / ".qvault_trash"

HOST_OS = "Windows" if os.name == "nt" else "Linux"

SYSTEM_PATHS_WINDOWS = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\System Volume Information",
]

SYSTEM_PATHS_LINUX = [
    "/bin",
    "/usr",
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/boot",
    "/root",
]


def ensure_sandbox_exists():
    """Create sandbox directory if it doesn't exist."""
    try:
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def ensure_trash_exists():
    """Create trash directory if it doesn't exist."""
    try:
        TRASH_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def is_safe_mode_enabled() -> bool:
    """Check if safe mode is enabled."""
    return getattr(ensure_sandbox_exists, "_safe_mode", True)


def set_safe_mode(enabled: bool):
    """Enable or disable safe mode."""
    ensure_sandbox_exists._safe_mode = enabled


class SandboxManager:
    """Manages sandbox and security operations."""

    def __init__(self, parent: QWidget = None):
        self._parent = parent
        self._safe_mode = True
        ensure_sandbox_exists()
        ensure_trash_exists()

    @property
    def safe_mode(self) -> bool:
        return self._safe_mode

    @safe_mode.setter
    def safe_mode(self, value: bool):
        self._safe_mode = value

    def is_path_safe(self, path: str) -> bool:
        """Check if path is within sandbox or system paths."""
        if not self._safe_mode:
            return True

        abs_path = os.path.abspath(path)

        if HOST_OS == "Windows":
            for sp in SYSTEM_PATHS_WINDOWS:
                if abs_path.lower().startswith(sp.lower()):
                    return False
        else:
            for sp in SYSTEM_PATHS_LINUX:
                if abs_path.startswith(sp):
                    return False

        if self.is_in_sandbox(abs_path):
            return True

        if self.is_in_user_home(abs_path):
            return True

        return False

    def is_in_sandbox(self, path: str) -> bool:
        """Check if path is inside sandbox directory."""
        try:
            return os.path.abspath(path).startswith(str(SANDBOX_DIR))
        except Exception:
            return False

    def is_in_user_home(self, path: str) -> bool:
        """Check if path is inside user home directory."""
        try:
            home = str(pathlib.Path.home())
            return os.path.abspath(path).startswith(home)
        except Exception:
            return False

    def check_access(self, path: str) -> tuple[bool, str]:
        """
        Check if path can be accessed.
        Returns: (is_safe, message)
        """
        if self._safe_mode:
            if self.is_path_safe(path):
                return True, "OK"
            else:
                return False, f"System path protected: {path}"
        return True, "OK"

    def confirm_access(self, path: str, operation: str = "access") -> bool:
        """
        Show confirmation dialog for accessing outside sandbox.
        Returns True if user confirms.
        """
        if not self._safe_mode:
            return True

        if self.is_in_sandbox(path) or self.is_in_user_home(path):
            return True

        msg = QMessageBox(self._parent)
        msg.setWindowTitle("Q-VAULT Security Warning")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"You are about to {operation} a file outside the sandbox.")
        msg.setInformativeText(f"Path: {path}\n\nThis is a REAL system file. Continue?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        return msg.exec() == QMessageBox.Yes

    def move_to_trash(self, path: str) -> bool:
        """
        Move file to trash instead of permanent deletion.
        Returns True if successful.
        """
        try:
            ensure_trash_exists()
            filename = os.path.basename(path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_name = f"{timestamp}_{filename}"
            dest = TRASH_DIR / trash_name

            if os.path.isdir(path):
                shutil.move(path, dest)
            else:
                shutil.move(path, dest)

            return True
        except Exception as e:
            print(f"Failed to move to trash: {e}")
            return False

    def restore_from_trash(self, trash_name: str) -> bool:
        """Restore file from trash to original location."""
        try:
            trash_path = TRASH_DIR / trash_name
            if not trash_path.exists():
                return False

            original_name = (
                trash_name.split("_", 1)[1] if "_" in trash_name else trash_name
            )
            dest = pathlib.Path.home() / original_name

            shutil.move(str(trash_path), str(dest))
            return True
        except Exception:
            return False

    def empty_trash(self) -> bool:
        """Empty the trash directory."""
        try:
            if TRASH_DIR.exists():
                shutil.rmtree(TRASH_DIR)
                TRASH_DIR.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def get_trash_contents(self) -> list:
        """Get list of files in trash."""
        try:
            if not TRASH_DIR.exists():
                return []
            return [f.name for f in TRASH_DIR.iterdir()]
        except Exception:
            return []

    def get_sandbox_path(self) -> str:
        """Get the sandbox directory path."""
        return str(SANDBOX_DIR)

    def sanitize_path(self, path: str) -> str:
        """
        If in safe mode and path is outside sandbox,
        redirect to sandbox directory.
        """
        if not self._safe_mode:
            return path

        if self.is_in_sandbox(path) or self.is_in_user_home(path):
            return path

        return str(SANDBOX_DIR)


SANDBOX = SandboxManager()
