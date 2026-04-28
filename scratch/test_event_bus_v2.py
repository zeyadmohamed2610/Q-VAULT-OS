"""
EventBus v2.0 — Functional Verification Test
Tests: subscribe, emit, weakref cleanup, unsubscribe, unsubscribe_all, stats
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from system.event_bus import EventBus, SystemEvent, _Subscriber

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")

# ── Fresh bus for each test ──────────────────────────────────────

print("\n🧪 TEST 1: Basic subscribe + emit")
bus = EventBus()
received = []
def on_app_launch(payload):
    received.append(payload.data)
bus.subscribe(SystemEvent.APP_LAUNCHED, on_app_launch)
bus.emit(SystemEvent.APP_LAUNCHED, {"app": "terminal"}, source="Test")
check("Callback received payload", len(received) == 1 and received[0]["app"] == "terminal")
check("Stats: 1 emit", bus.stats["total_emits"] == 1)
check("Stats: 1 alive subscriber", bus.stats["alive_subscribers"] == 1)


print("\n🧪 TEST 2: unsubscribe (plain function)")
bus2 = EventBus()
log = []
def logger_fn(p): log.append(1)
bus2.subscribe(SystemEvent.APP_CRASHED, logger_fn)
bus2.emit(SystemEvent.APP_CRASHED, {})
check("Before unsub: received", len(log) == 1)
bus2.unsubscribe(SystemEvent.APP_CRASHED, logger_fn)
bus2.emit(SystemEvent.APP_CRASHED, {})
check("After unsub: no more callbacks", len(log) == 1)


print("\n🧪 TEST 3: WeakMethod auto-cleanup (bound methods)")
bus3 = EventBus()
weak_log = []

class FakeWidget:
    def on_event(self, payload):
        weak_log.append(payload.data)

widget = FakeWidget()
bus3.subscribe(SystemEvent.WINDOW_OPENED, widget.on_event)
bus3.emit(SystemEvent.WINDOW_OPENED, {"id": "win1"})
check("Bound method received", len(weak_log) == 1)

# Kill the widget
del widget
import gc; gc.collect()

bus3.emit(SystemEvent.WINDOW_OPENED, {"id": "win2"})
check("Dead widget auto-cleaned, no call", len(weak_log) == 1)
check("Stats: 0 alive after cleanup", bus3.stats["alive_subscribers"] == 0)


print("\n🧪 TEST 4: unsubscribe_all (object cleanup)")
bus4 = EventBus()
calls = {"a": 0, "b": 0}

class ServiceA:
    def handle_open(self, p): calls["a"] += 1
    def handle_close(self, p): calls["a"] += 1

class ServiceB:
    def handle_open(self, p): calls["b"] += 1

sa = ServiceA()
sb = ServiceB()
bus4.subscribe(SystemEvent.WINDOW_OPENED, sa.handle_open)
bus4.subscribe(SystemEvent.WINDOW_CLOSED, sa.handle_close)
bus4.subscribe(SystemEvent.WINDOW_OPENED, sb.handle_open)

bus4.emit(SystemEvent.WINDOW_OPENED, {})
check("Both services called", calls["a"] == 1 and calls["b"] == 1)

bus4.unsubscribe_all(sa)
bus4.emit(SystemEvent.WINDOW_OPENED, {})
bus4.emit(SystemEvent.WINDOW_CLOSED, {})
check("After unsubscribe_all(sa): sa=1 (unchanged), sb=2", calls["a"] == 1 and calls["b"] == 2)


print("\n🧪 TEST 5: Subscriber identity for bound methods")
sub_a = _Subscriber(sa.handle_open)  # sa is still alive from test 4
sub_b = _Subscriber(sb.handle_open)
check("Same object identity", sub_a.owned_by(sa))
check("Different object identity", not sub_a.owned_by(sb))
check("matches_callback works", sub_b.matches_callback(sb.handle_open))


print("\n🧪 TEST 6: Re-entrant subscribe during emit")
bus6 = EventBus()
reentrant_log = []
def reentrant_cb(p):
    reentrant_log.append("first")
    # Subscribe another callback during emission
    bus6.subscribe(SystemEvent.LOGIN_SUCCESS, lambda p: reentrant_log.append("dynamic"))
bus6.subscribe(SystemEvent.LOGIN_SUCCESS, reentrant_cb)
bus6.emit(SystemEvent.LOGIN_SUCCESS, {})
check("Re-entrant subscribe did not crash", len(reentrant_log) == 1)
bus6.emit(SystemEvent.LOGIN_SUCCESS, {})
check("Dynamic subscriber active on next emit", "dynamic" in reentrant_log)


print("\n🧪 TEST 7: History + get_recent_events")
bus7 = EventBus()
for i in range(60):
    bus7.emit(SystemEvent.SETTING_CHANGED, {"i": i})
recent = bus7.get_recent_events(5)
check("History capped at 50", bus7.stats["history_size"] == 50)
check("get_recent returns correct count", len(recent) == 5)
check("Most recent is last emitted", recent[-1].data["i"] == 59)


# ── Summary ──────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*50}")
sys.exit(1 if FAIL > 0 else 0)
