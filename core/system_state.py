# =============================================================
#  system_state.py — Q-Vault OS  |  Global System State
#
#  Single source of truth for runtime state shared across all
#  modules.  Import STATE anywhere to read or write:
#
#    from core.system_state import STATE
#    STATE.current_user          → User object or None
#    STATE.emergency_mode        → bool
#    STATE.alerts_enabled        → bool
#    STATE.animations_enabled    → bool
#
#  Observer callbacks fire when any field changes:
#    STATE.subscribe(cb)   →  cb(field, old_value, new_value)
# =============================================================

from typing import Callable, Any


class SystemState:
    """
    Holds all runtime flags for the OS session.
    Every setter fires registered observers so widgets can
    react to state changes without polling.
    """

    def __init__(self):
        # ── Session ───────────────────────────────────────────
        self._current_user = None  # User object from UserManager
        self._session_type = "real"  # "real" | "fake"
        self._first_run = True  # First run flag for welcome screen

        # ── Security ──────────────────────────────────────────
        self._emergency_mode = False
        self._alerts_enabled = True

        # ── UI preferences ───────────────────────────────────
        self._animations_enabled = True
        self._theme = "dark"  # "dark" | "light"

        self._observers: list[Callable] = []

    # ── Observer API ──────────────────────────────────────────

    def subscribe(self, cb: Callable):
        if cb not in self._observers:
            self._observers.append(cb)

    def unsubscribe(self, cb: Callable):
        self._observers = [o for o in self._observers if o is not cb]

    def _fire(self, field: str, old: Any, new: Any):
        for cb in self._observers:
            try:
                cb(field, old, new)
            except Exception:
                pass

    # ── Properties ────────────────────────────────────────────

    @property
    def current_user(self):
        return self._current_user

    @current_user.setter
    def current_user(self, v):
        old, self._current_user = self._current_user, v
        self._fire("current_user", old, v)

    @property
    def session_type(self) -> str:
        return self._session_type

    @session_type.setter
    def session_type(self, v: str):
        old, self._session_type = self._session_type, v
        self._fire("session_type", old, v)

    @property
    def emergency_mode(self) -> bool:
        return self._emergency_mode

    @emergency_mode.setter
    def emergency_mode(self, v: bool):
        old, self._emergency_mode = self._emergency_mode, v
        self._fire("emergency_mode", old, v)

    @property
    def alerts_enabled(self) -> bool:
        return self._alerts_enabled

    @alerts_enabled.setter
    def alerts_enabled(self, v: bool):
        old, self._alerts_enabled = self._alerts_enabled, v
        self._fire("alerts_enabled", old, v)

    @property
    def animations_enabled(self) -> bool:
        return self._animations_enabled

    @animations_enabled.setter
    def animations_enabled(self, v: bool):
        old, self._animations_enabled = self._animations_enabled, v
        self._fire("animations_enabled", old, v)

    @property
    def theme(self) -> str:
        return self._theme

    @theme.setter
    def theme(self, v: str):
        old, self._theme = self._theme, v
        self._fire("theme", old, v)

    @property
    def first_run(self) -> bool:
        return self._first_run

    @first_run.setter
    def first_run(self, v: bool):
        old, self._first_run = self._first_run, v
        self._fire("first_run", old, v)

    # ── Convenience helpers ───────────────────────────────────

    def is_root(self) -> bool:
        return self._current_user is not None and self._current_user.role == "admin"

    def username(self) -> str:
        if self._current_user:
            if isinstance(self._current_user, str):
                return self._current_user
            return self._current_user.username
        return "guest"

    def summary(self) -> dict:
        return {
            "user": self.username(),
            "role": self._current_user.role if self._current_user else "—",
            "session": self._session_type,
            "emergency": self._emergency_mode,
            "alerts": self._alerts_enabled,
            "theme": self._theme,
            "animations": self._animations_enabled,
        }


# ── Module singleton ──────────────────────────────────────────
STATE = SystemState()
