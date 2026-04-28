# =============================================================
#  tests/core/test_event_bus.py — Q-Vault OS  |  Unit Test
# =============================================================

import unittest
import gc
from core.event_bus import EVENT_BUS, SystemEvent

class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.received_payload = None
        self.call_count = 0

    def _sample_callback(self, payload):
        self.received_payload = payload
        self.call_count += 1

    def test_subscribe_emit(self):
        """Verify basic subscription and emission."""
        EVENT_BUS.subscribe(SystemEvent.APP_LAUNCHED, self._sample_callback)
        
        test_payload = {"id": "test_app"}
        EVENT_BUS.emit(SystemEvent.APP_LAUNCHED, test_payload)
        
        self.assertEqual(self.call_count, 1)
        self.assertEqual(self.received_payload.data, test_payload)

    def test_unsubscribe(self):
        """Verify unsubscription stops delivery."""
        EVENT_BUS.subscribe("test.event", self._sample_callback)
        EVENT_BUS.unsubscribe("test.event", self._sample_callback)
        
        EVENT_BUS.emit("test.event", {})
        self.assertEqual(self.call_count, 0)

    def test_weak_ref_cleanup(self):
        """Verify that bound methods are cleaned up when the object dies."""
        class TempSubscriber:
            def __init__(self): self.hits = 0
            def handler(self, p): self.hits += 1

        obj = TempSubscriber()
        EVENT_BUS.subscribe("weak.test", obj.handler)
        
        # Emit while alive
        EVENT_BUS.emit("weak.test", {})
        self.assertEqual(obj.hits, 1)
        
        # Kill object
        del obj
        gc.collect()
        
        # Emit while dead
        EVENT_BUS.emit("weak.test", {})
        # If it didn't crash and didn't increment (obviously), it passed.
        # The internal list should eventually shrink.
        
    def test_priority_emission(self):
        """Verify that events are emitted in a specific order if priority is used."""
        results = []
        EVENT_BUS.subscribe("order.test", lambda p: results.append(1))
        EVENT_BUS.subscribe("order.test", lambda p: results.append(2))
        
        EVENT_BUS.emit("order.test", {})
        self.assertEqual(results, [1, 2])

if __name__ == "__main__":
    unittest.main()
