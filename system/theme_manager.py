# =============================================================
#  system/theme_manager.py — Q-Vault OS  |  Theme Manager
#
#  Centralized authority for applying and managing UI themes.
#  Decouples the static asset layer from the dynamic UI engine.
# =============================================================

import logging
from PyQt5.QtWidgets import QApplication
from assets.theme import GLOBAL_STYLE

logger = logging.getLogger(__name__)

class ThemeManager:
    """Manages the application's look and feel."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
        return cls._instance

    def apply_global_theme(self, app: QApplication = None):
        """Applies the authoritative Cyber Neon stylesheet to the application."""
        if app is None:
            app = QApplication.instance()
        
        if app:
            app.setStyleSheet(GLOBAL_STYLE)
            logger.info("[ThemeManager] Global Cyber Neon theme enforced.")
        else:
            logger.error("[ThemeManager] Failed to apply theme: No QApplication instance found.")

# Global singleton
THEME_MANAGER = ThemeManager()
