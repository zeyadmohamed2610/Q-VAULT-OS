# =============================================================
#  sdk/events.py — Q-Vault OS  |  Stable Event Interface
#
#  Public event registry for developers.
#  GUARANTEE: These constants will never change, even if
#  internal system event strings are refactored.
# =============================================================

from core.event_bus import SystemEvent

# ── App Lifecycle ──
APP_LAUNCHED     = SystemEvent.APP_LAUNCHED.value
APP_CRASHED      = SystemEvent.APP_CRASHED.value
APP_TERMINATED   = SystemEvent.APP_TERMINATED.value

# ── Window Lifecycle ──
WINDOW_OPENED    = SystemEvent.WINDOW_OPENED.value
WINDOW_CLOSED    = SystemEvent.WINDOW_CLOSED.value
WINDOW_FOCUSED   = SystemEvent.WINDOW_FOCUSED.value
WINDOW_MINIMIZED = SystemEvent.WINDOW_MINIMIZED.value
WINDOW_RESTORED  = SystemEvent.WINDOW_RESTORED.value

# ── Auth & Session ──
LOGIN_SUCCESS    = SystemEvent.LOGIN_SUCCESS.value
LOGIN_FAILED     = SystemEvent.LOGIN_FAILED.value
SESSION_LOCKED   = SystemEvent.SESSION_LOCKED.value
SESSION_UNLOCKED = SystemEvent.SESSION_UNLOCKED.value

# ── System State ──
STATE_CHANGED    = SystemEvent.STATE_CHANGED.value
SETTING_CHANGED  = SystemEvent.SETTING_CHANGED.value

# ── Security ──
SECURITY_ALERT   = SystemEvent.SECURITY_ALERT.value

# ── Requests (Commands) ──
REQ_APP_LAUNCH      = SystemEvent.REQ_APP_LAUNCH.value
REQ_WINDOW_CLOSE    = SystemEvent.REQ_WINDOW_CLOSE.value
REQ_WINDOW_MINIMIZE = SystemEvent.REQ_WINDOW_MINIMIZE.value
REQ_WINDOW_FOCUS    = SystemEvent.REQ_WINDOW_FOCUS.value
REQ_NOTIFICATION    = SystemEvent.NOTIFICATION_SENT.value

# ── Physics & Drag (Phase 2) ──
REQ_WINDOW_DRAG_START  = SystemEvent.REQ_WINDOW_DRAG_START.value
REQ_WINDOW_DRAG_UPDATE = SystemEvent.REQ_WINDOW_DRAG_UPDATE.value
REQ_WINDOW_DRAG_END    = SystemEvent.REQ_WINDOW_DRAG_END.value
WINDOW_SNAPPED         = SystemEvent.EVT_WINDOW_SNAPPED.value

# ── Debug & Observability (Phase 3) ──
REQ_DEBUG_TOGGLE       = SystemEvent.REQ_DEBUG_TOGGLE.value
DEBUG_METRICS_UPDATED  = SystemEvent.DEBUG_METRICS_UPDATED.value
DEBUG_EVENT_EMITTED    = SystemEvent.DEBUG_EVENT_EMITTED.value

# ── Control & Health (Phase 3.5) ──
REQ_SYSTEM_CONTROL     = SystemEvent.REQ_SYSTEM_CONTROL.value
REQ_COMMAND_PALETTE_TOGGLE = SystemEvent.REQ_COMMAND_PALETTE_TOGGLE.value
REQ_SYSTEM_RESTART     = SystemEvent.REQ_SYSTEM_RESTART.value
REQ_USER_INPUT         = SystemEvent.REQ_USER_INPUT.value
EVT_ERROR              = SystemEvent.EVT_ERROR.value
EVT_WARNING            = SystemEvent.EVT_WARNING.value

# ── AI Intelligence (Phase 4.1) ──
EVT_AI_DECISION        = SystemEvent.EVT_AI_DECISION.value
EVT_AI_REJECTED_ACTION = SystemEvent.EVT_AI_REJECTED_ACTION.value
