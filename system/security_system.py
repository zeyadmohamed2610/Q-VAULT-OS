# =============================================================
#  security_system.py — Q-Vault OS  |  Security System
#
#  Central security event bus. All subsystems (Terminal, Task
#  Manager, etc.) talk through this singleton.
#
#  Risk levels:  LOW → MEDIUM → HIGH
#  Each intrusion event escalates the risk level and is logged
#  with a timestamp.
#
#  Observer pattern (same as ProcessManager):
#    SEC.subscribe(cb)   →  cb(event_dict) on every new event
#    SEC.unsubscribe(cb)
# =============================================================

import time
from typing import Callable


# ── Risk level constants ──────────────────────────────────────
RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"

_RISK_ORDER = [RISK_LOW, RISK_MEDIUM, RISK_HIGH]

# Color mapping for UI display
RISK_COLORS = {
    "LOW": "#00ff88",
    "MEDIUM": "#ffaa00",
    "HIGH": "#ff4444",
}

# ── Event type constants ──────────────────────────────────────
EVT_INTRUSION = "INTRUSION_DETECTED"
EVT_BUTTON = "BUTTON_PRESSED"
EVT_LOGIN = "LOGIN_ATTEMPT"
EVT_PROCESS = "SUSPICIOUS_PROCESS"
EVT_MANUAL = "MANUAL_ALERT"
EVT_CLEARED = "RISK_CLEARED"
EVT_CRITICAL = "CRITICAL_SYSTEM_EVENT"


def _ts() -> str:
    """Current timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


class SecuritySystem:
    """
    Singleton security event manager.

    Usage
    ─────
    from system.security_system import SEC
    SEC.report(EVT_INTRUSION, source="sensor", detail="Motion sensor")
    SEC.subscribe(my_callback)
    """

    def __init__(self):
        self._risk_level: str = RISK_LOW
        self._log: list[dict] = []
        self._observers: list[Callable] = []

        # Seed the log with a clean-boot entry
        self._append_log(
            event_type="SYSTEM_BOOT",
            source="kernel",
            detail="Q-Vault OS security subsystem initialized.",
            risk_after=RISK_LOW,
        )

    # ── Observer API ──────────────────────────────────────────

    def subscribe(self, cb: Callable):
        if cb not in self._observers:
            self._observers.append(cb)

    def unsubscribe(self, cb: Callable):
        self._observers = [o for o in self._observers if o is not cb]

    def _notify(self, entry: dict):
        for cb in self._observers:
            try:
                cb(entry)
            except Exception:
                pass

    # ── Reporting ─────────────────────────────────────────────

    def report(
        self,
        event_type: str,
        source: str = "system",
        detail: str = "",
        escalate: bool = True,
    ) -> dict:
        """
        Log a security event.

        event_type  one of the EVT_* constants
        source      originating subsystem ("sensor", "terminal", …)
        detail      human-readable description
        escalate    if True, bump the risk level (default True)
        Returns the log entry dict.
        """
        if escalate and event_type not in (EVT_BUTTON, EVT_CLEARED):
            self._escalate()

        entry = self._append_log(
            event_type=event_type,
            source=source,
            detail=detail,
            risk_after=self._risk_level,
        )
        self._notify(entry)
        return entry

    def clear_risk(self):
        """Manually reset risk level back to LOW."""
        self._risk_level = RISK_LOW
        entry = self._append_log(
            event_type=EVT_CLEARED,
            source="operator",
            detail="Risk level manually cleared to LOW.",
            risk_after=RISK_LOW,
        )
        self._notify(entry)

    # ── Risk level ────────────────────────────────────────────

    @property
    def risk_level(self) -> str:
        return self._risk_level

    def _escalate(self):
        idx = _RISK_ORDER.index(self._risk_level)
        if idx < len(_RISK_ORDER) - 1:
            self._risk_level = _RISK_ORDER[idx + 1]

    # ── Log ───────────────────────────────────────────────────

    def _append_log(
        self, event_type: str, source: str, detail: str, risk_after: str
    ) -> dict:
        entry = {
            "timestamp": _ts(),
            "event_type": event_type,
            "source": source,
            "detail": detail,
            "risk_after": risk_after,
        }
        self._log.append(entry)

        # Write to virtual disk log
        try:
            from core.filesystem import FS

            log_str = f'[{entry["timestamp"]}] {event_type} SOURCE={source} DETAIL="{detail}" RISK={risk_after}\n'
            if not FS.exists("/var/log"):
                FS.mkdir("/var", is_root=True)
                FS.mkdir("/var/log", is_root=True)

            fpath = "/var/log/security.log"
            content = (FS.read(fpath) if FS.exists(fpath) else "") + log_str
            FS.write(fpath, content, is_root=True)
        except Exception:
            pass

        return entry

    def get_log(self, limit: int = 200) -> list[dict]:
        """Return up to `limit` most recent log entries (newest last)."""
        return self._log[-limit:]

    def get_log_reversed(self, limit: int = 200) -> list[dict]:
        """Return most recent entries first."""
        return list(reversed(self._log[-limit:]))


# ── Module singleton ──────────────────────────────────────────
SEC = SecuritySystem()
