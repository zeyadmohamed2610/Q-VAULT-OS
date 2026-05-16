# system/kernel/event_bus.py
# ── Sovereign Re-export Layer ────────────────────────────────────────
# The canonical EventBus lives in core/event_bus.py (108 events).
# This module is a thin re-export shim so kernel-layer code that imports
# from system.kernel.event_bus continues to work without duplication.
# DO NOT add logic here. All changes go to core/event_bus.py.
# ─────────────────────────────────────────────────────────────────────

from core.event_bus import (   # noqa: F401 — intentional re-export
    SystemEvent,
    EventPayload,
    EventBus,
    EVENT_BUS,
    _Subscriber,
)

__all__ = ["SystemEvent", "EventPayload", "EventBus", "EVENT_BUS", "_Subscriber"]
