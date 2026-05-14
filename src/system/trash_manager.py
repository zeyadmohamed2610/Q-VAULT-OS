import os
import shutil
import json
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

    # Avoid overwrite collision by appending uuid
    if dest.exists():
        import uuid
        dest = trash_dir / f"{src.stem}_{uuid.uuid4().hex[:6]}{src.suffix}"

    shutil.move(str(src), str(dest))
    
    # Save metadata
    meta_path = trash_dir / f"{dest.name}.meta"
    with open(meta_path, "w") as f:
        json.dump({"original_path": str(src)}, f)
        
    return True


def restore_from_trash(name: str) -> bool:
    """
    Restore a named file from trash back to its original path or qvault_home root.
    Returns True on success, False if not found in trash.
    """
    trash_dir = _get_trash_dir()
    src = trash_dir / name
    if not src.exists():
        return False
        
    meta_path = trash_dir / f"{name}.meta"
    dest_path = None
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            dest_path = Path(meta.get("original_path"))
        except Exception:
            pass
            
    if not dest_path:
        dest_path = Path(get_qvault_home()) / name
        
    # Prevent collision on restore
    if dest_path.exists():
        counter = 1
        while dest_path.exists():
            dest_path = dest_path.with_name(f"{dest_path.stem}_{counter}{dest_path.suffix}")
            counter += 1

    # Ensure parent dir exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(src), str(dest_path))
    
    if meta_path.exists():
        meta_path.unlink()
        
    return True


def list_trash() -> list[str]:
    """Return a list of filenames currently in trash (ignoring meta files)."""
    trash_dir = _get_trash_dir()
    return [item.name for item in trash_dir.iterdir() if not item.name.endswith(".meta")]
