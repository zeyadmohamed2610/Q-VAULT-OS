# =============================================================
#  tests/sdk/test_api_contract.py — SDK Contract Test
# =============================================================

import unittest
import sys

class TestSDKContract(unittest.TestCase):
    def test_no_illegal_imports(self):
        """
        Verify that importing sdk.api does NOT pull in system or components.
        This enforces strict Level 1 isolation.
        """
        # Clear existing modules from cache to force a fresh import check
        illegal_prefixes = ['system', 'components', 'apps']
        for mod in list(sys.modules.keys()):
            if any(mod.startswith(p) for p in illegal_prefixes):
                del sys.modules[mod]

        # Import SDK
        from sdk.api import api
        from sdk.events import APP_LAUNCHED
        
        # Check if any illegal module was loaded as a side effect
        loaded = sys.modules.keys()
        for p in illegal_prefixes:
            self.assertFalse(any(m.startswith(p) for m in loaded), f"SDK leaked import from {p}")

    def test_api_singleton(self):
        """Verify that the SDK provides a stable singleton."""
        from sdk.api import api as api1
        from sdk.api import api as api2
        self.assertIs(api1, api2)

    def test_emit_passthrough(self):
        """Verify that SDK emit reaches the internal EventBus."""
        from sdk.api import api
        from core.event_bus import EVENT_BUS, SystemEvent
        
        hits = []
        EVENT_BUS.subscribe(SystemEvent.REQ_APP_LAUNCH, lambda p: hits.append(p))
        
        api.launch_app("test_app")
        
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].data["name"], "test_app")

if __name__ == "__main__":
    unittest.main()
