import logging
from pathlib import Path

logger = logging.getLogger("system.clipboard")

class FileClipboard:
    """
    Sovereign System Clipboard.
    Allows file Copy/Cut/Paste operations to persist across different 
    File Manager windows and the Desktop environment.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileClipboard, cls).__new__(cls)
            cls._instance.paths = []
            cls._instance.is_cut_mode = False
        return cls._instance

    def set_clipboard(self, paths: list[Path], cut_mode: bool = False):
        self.paths = [Path(p).resolve() for p in paths]
        self.is_cut_mode = cut_mode
        logger.info(f"[Clipboard] Stored {len(self.paths)} items (Cut: {cut_mode})")

    def get_clipboard(self):
        # Validate paths still exist
        valid_paths = [p for p in self.paths if p.exists()]
        return valid_paths, self.is_cut_mode

    def clear(self):
        self.paths = []
        self.is_cut_mode = False

CLIPBOARD = FileClipboard()
