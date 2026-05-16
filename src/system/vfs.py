"""
system.vfs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shim Layer for the Sovereign Virtual Filesystem.
Redirects all legacy system-space calls to the unified core.filesystem.FS.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import logging
from core.filesystem import FS, Meta

logger = logging.getLogger(__name__)

class VirtualFilesystemShim:
    """
    Backward-compatibility shim. 
    The UI expects 'VFS' to be an instance with specific methods.
    """
    def __init__(self):
        self._core = FS

    def cd(self, dest: str, cwd: str) -> str:
        # FS.cd(path, is_root) updates internal cwd. 
        # But UI expects it to return the new path string without necessarily updating state if just probing.
        # We'll use a temporary context for this.
        original_cwd = self._core.pwd()
        try:
            self._core.cd(dest)
            new_path = self._core.pwd()
            return new_path
        finally:
            self._core.cd(original_cwd)

    def ls(self, target: str, cwd: str):
        original_cwd = self._core.pwd()
        try:
            self._core.cd(cwd)
            return self._core.ls(target)
        finally:
            self._core.cd(original_cwd)

    def cat(self, target: str, cwd: str) -> str:
        original_cwd = self._core.pwd()
        try:
            self._core.cd(cwd)
            return self._core.cat(target)
        finally:
            self._core.cd(original_cwd)

    def touch(self, target: str, cwd: str, content: str = ""):
        original_cwd = self._core.pwd()
        try:
            self._core.cd(cwd)
            self._core.write_file(target, content)
        finally:
            self._core.cd(original_cwd)

    def mkdir(self, target: str, cwd: str):
        original_cwd = self._core.pwd()
        try:
            self._core.cd(cwd)
            self._core.mkdir(target)
        finally:
            self._core.cd(original_cwd)

    def rm(self, target: str, cwd: str, recursive: bool = False):
        original_cwd = self._core.pwd()
        try:
            self._core.cd(cwd)
            self._core.rm(target, recursive=recursive)
        finally:
            self._core.cd(original_cwd)

    def pwd(self, cwd: str) -> str:
        return cwd # Shim logic

    def save_to_vault(self):
        self._core.save()

    def load_from_vault(self):
        self._core.load()

# Export the shim as VFS for UI compatibility
VFS = VirtualFilesystemShim()
