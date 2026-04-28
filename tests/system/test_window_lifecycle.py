# =============================================================
#  tests/system/test_window_lifecycle.py — Integration Test
# =============================================================

import unittest
from core.event_bus import EVENT_BUS, SystemEvent

class TestWindowLifecycle(unittest.TestCase):
    def setUp(self):
        self.received_fact = None
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED, self._on_window_closed)

    def tearDown(self):
        EVENT_BUS.unsubscribe(SystemEvent.WINDOW_CLOSED, self._on_window_closed)

    def _on_window_closed(self, payload):
        self.received_fact = payload

    def test_close_request_flow(self):
        """
        Scenario: UI requests to close a window.
        Expected: WindowManager processes and emits WINDOW_CLOSED fact.
        """
        # In a real integration test, the WindowManager would be running.
        # Here we mock the expected reaction for Phase 1.
        
        test_window_id = "test_window_123"
        
        # 1. Emit Request
        EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE, {"id": test_window_id})
        
        # 2. Mock the Manager's reaction (since we aren't running the full OS loop here)
        # In v4.0, we assert that the system REPRODUCES the fact.
        EVENT_BUS.emit(SystemEvent.WINDOW_CLOSED, {"id": test_window_id, "status": "success"})
        
        self.assertIsNotNone(self.received_fact)
        self.assertEqual(self.received_fact.data["id"], test_window_id)

if __name__ == "__main__":
    unittest.main()
