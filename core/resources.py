import os
import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, works for development and PyInstaller.
    
    Args:
        relative_path: Path relative to the project root.
    Returns:
        The absolute path to the resource.
    """
    if relative_path is None:
        # Production Safety: Fallback to root or log error instead of crashing
        return str(Path(__file__).parent.parent)

    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = str(Path(__file__).parent.parent)

    return os.path.join(base_path, relative_path)

def get_binary_path() -> str:
    """Special helper to resolve the core/binaries directory."""
    return get_resource_path("core/binaries")

def get_asset_path(filename: str) -> str:
    """Special helper to resolve the assets directory."""
    if not filename:
        return "" # Safe fallback for UI icons
    return get_resource_path(os.path.join("assets", filename))

def get_theme_data():
    """Returns the static theme definition from assets."""
    from assets import theme
    return theme

def get_wallpaper_registry():
    """Returns the static wallpaper metadata from assets."""
    from assets import wallpaper_data
    return wallpaper_data
