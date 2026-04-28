# =============================================================
#  system/ai/context_builder.py — Q-Vault OS
#
#  Enhanced situational awareness for AI.
#  Tracks active state, history, and error telemetry.
# =============================================================

import time
from collections import deque
from core.event_bus import EVENT_BUS, SystemEvent

class ContextBuilder:
    """
    Situational awareness engine for AI.
    Tracks state transitions and maintains queryable buffers.
    """
    def __init__(self, max_history=50):
        # State Snapshots
        self.active_window_id = None
        self.last_user_action = None
        
        # Historical Buffers
        self._history = deque(maxlen=max_history)
        self._errors = deque(maxlen=5) # Last 5 errors
        
        # ── Subscriptions ──
        EVENT_BUS.subscribe(SystemEvent.WINDOW_FOCUSED, self._on_window_focused)
        EVENT_BUS.subscribe(SystemEvent.REQ_USER_INPUT, self._on_user_request)
        EVENT_BUS.subscribe(SystemEvent.EVT_ERROR, self._on_error)
        
        # General observation
        EVENT_BUS.subscribe(SystemEvent.APP_LAUNCHED, self._record)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED, self._record)

    def _on_window_focused(self, payload):
        self.active_window_id = payload.data.get("id")
        self._record(payload)

    def _on_user_request(self, payload):
        self.last_user_action = {
            "text": payload.data.get("text"),
            "time": payload.timestamp
        }
        self._record(payload)

    def _on_error(self, payload):
        self._errors.append({
            "type": payload.data.get("type"),
            "msg": payload.data.get("error") or payload.data.get("msg"),
            "time": payload.timestamp
        })
        self._record(payload)

    def _record(self, payload):
        entry = {
            "type": str(payload.type.value if hasattr(payload.type, 'value') else payload.type),
            "data": payload.data,
            "source": payload.source,
            "time": payload.timestamp
        }
        self._history.append(entry)

    # ── Query API ──

    def get_active_window(self):
        return self.active_window_id

    def get_last_error(self):
        return self._errors[-1] if self._errors else None

    def get_full_context(self):
        """Returns a structured snapshot for AI reasoning."""
        return {
            "active_window": self.active_window_id,
            "last_user_input": self.last_user_action.get("text") if self.last_user_action else None,
            "recent_errors": list(self._errors),
            "recent_events": list(self._history)[-10:]
        }

    def get_context_summary(self):
        ctx = self.get_full_context()
        summary = f"ACTIVE_WINDOW: {ctx['active_window']}\n"
        summary += f"LAST_INPUT: {ctx['last_user_input']}\n"
        summary += f"ERRORS: {len(ctx['recent_errors'])}\n"
        return summary
