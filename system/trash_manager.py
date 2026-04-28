# =============================================================
#  system/trash_manager.py — Q-VAULT OS  |  Trash Manager
#
#  Moves files to the sandbox trash directory.
#  Trash is rooted inside the secure qvault_home to prevent
#  path escapes to the host filesystem.
#
#  CRITICAL FIX: Path resolution is now lazy (inside functions).
#  Previously used `Path("qvault_home/.trash")` at module import
#  time — that hardcoded relative path would silently create trash
#  in the wrong location if CWD != project root (e.g. packaged).
# =============================================================

import os
import shutil
from pathlib import Path
from system.config import get_qvault_home


def _get_trash_dir() -> Path:
    """Returns the trash directory path, creating it if needed."""
    trash = Path(get_qvault_home()) / ".trash"
    trash.mkdir(parents=True, exist_ok=True)
    return trash


def move_to_trash(path: str) -> bool:
    """
    Move a file or directory to the sandbox trash.
    Returns True on success, False if source does not exist.
    Raises ValueError if path escapes the sandbox.
    """
    src = Path(path).resolve()
    base = Path(get_qvault_home()).resolve()

    # Sandbox enforcement — no host OS escapes
    if not str(src).startswith(str(base)):
        raise ValueError(f"Access denied: path outside sandbox: {path}")

    if not src.exists():
        return False

    trash_dir = _get_trash_dir()
    name = src.name
    dest = trash_dir / name

    # Avoid overwrite collision by appending counter
    if dest.exists():
        counter = 1
        while dest.exists():
            dest = trash_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1

    shutil.move(str(src), str(dest))
    return True


def restore_from_trash(name: str) -> bool:
    """
    Restore a named file from trash back to qvault_home root.
    Returns True on success, False if not found in trash.
    """
    trash_dir = _get_trash_dir()
    src = trash_dir / name
    if not src.exists():
        return False
    dest = Path(get_qvault_home()) / name
    shutil.move(str(src), str(dest))
    return True


def list_trash() -> list[str]:
    """Return a list of filenames currently in trash."""
    trash_dir = _get_trash_dir()
    return [item.name for item in trash_dir.iterdir()]
