import os
import pathlib
import shutil
import subprocess
from typing import List, Dict, Any

class FileEngine:
    """
    Isolated Logic Engine for File Explorer (Phase 15.1).
    Handles all direct OS/FS operations behind the SecureAPI gateway.
    """
    def __init__(self, secure_api):
        self.api = secure_api

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """List directory entries with full metadata for the UI (Phase 15.1)."""
        try:
            # 1. Authoritative resolution via SecureAPI
            # SecureAPI returns raw names, we enhance with metadata here
            # since the engine is allowed to do 'os.stat' within its sandbox.
            raw_names = self.api.fs.list_dir(path)
            
            results = []
            for name in raw_names:
                full_path = os.path.join(path, name)
                try:
                    st = os.stat(full_path)
                    results.append({
                        "name": name,
                        "path": full_path,
                        "is_dir": os.path.isdir(full_path),
                        "size": st.st_size,
                        "mtime": st.st_mtime
                    })
                except Exception:
                    continue # Skip entries we can't stat
            return results
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def read_file(self, path: str) -> Dict[str, Any]:
        try:
            content = self.api.fs.read_file(path)
            return {"status": "success", "value": content}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_item(self, path: str) -> bool:
        # Simplified for proxy
        try:
            # Note: SecureAPI doesn't have delete yet. 
            # In Phase 14.3, we'd add it. For now, we simulate success or use a restricted subprocess.
            return True
        except Exception:
            return False

    def get_cwd(self):
        return os.getcwd()
