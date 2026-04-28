# =============================================================
#  tests/core/test_resources.py — Q-Vault OS  |  Unit Test
# =============================================================

import unittest
import os
from core.resources import get_asset_path, get_theme_data

class TestResources(unittest.TestCase):
    def test_asset_resolution(self):
        """Verify that asset paths are resolved correctly."""
        path = get_asset_path("qvault_vault.jpg")
        self.assertTrue(path.endswith("assets\\qvault_vault.jpg") or path.endswith("assets/qvault_vault.jpg"))
        # We don't check for existence here as it depends on the env, 
        # but we check the path logic.

    def test_theme_bridge(self):
        """Verify that the theme bridge returns the static data."""
        theme = get_theme_data()
        self.assertTrue(hasattr(theme, "THEME"))
        self.assertIn("primary_glow", theme.THEME)

if __name__ == "__main__":
    unittest.main()
