import json
import logging
from pathlib import Path
from typing import Optional, List
from assets.wallpaper_data import WALLPAPERS, TRANSPARENCY

logger = logging.getLogger(__name__)

class WallpaperManager:
    """Manages system wallpapers and user preferences."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WallpaperManager, cls).__new__(cls)
            cls._instance._config_file = Path.home() / ".qvault" / "config.json"
            cls._instance._listeners = []
        return cls._instance

    def _load_config(self) -> dict:
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load wallpaper config: {e}")
        return {}

    def _save_config(self, config: dict):
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save wallpaper config: {e}")

    def get_current_wallpaper_name(self) -> str:
        config = self._load_config()
        return config.get("wallpaper", "Cyber Grid")

    def set_wallpaper(self, name: str) -> bool:
        wallpaper = next((w for w in WALLPAPERS if w.name == name), None)
        if not wallpaper:
            return False

        config = self._load_config()
        config["wallpaper"] = name
        self._save_config(config)
        
        self._notify_listeners(name)
        return True

    def get_wallpaper_path(self, name: str) -> Optional[str]:
        from core.resources import get_asset_path
        wp = next((w for w in WALLPAPERS if w.name == name), None)
        if not wp or not wp.file:
            return None
        
        # Now uses core.resources for path normalization
        return get_asset_path(f"wallpapers/{wp.file}")

    def list_wallpapers(self) -> List:
        return WALLPAPERS

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, name: str):
        for listener in self._listeners:
            try:
                listener(name)
            except Exception as e:
                logger.warning(f"Theme listener failed: {e}")

    def get_transparency(self, key: str) -> float:
        return TRANSPARENCY.get(key, 0.90)

# Global singleton
WALLPAPER_MANAGER = WallpaperManager()
