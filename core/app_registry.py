# =============================================================
#  core/app_registry.py — Q-VAULT OS  |  Application Registry
#
#  THE single source of truth for all application definitions.
#  No other module may import an app class directly; all
#  instantiation MUST pass through AppRegistry.instantiate().
#
#  Architecture:
#    AppDefinition  — immutable data describing an app
#    AppRegistry    — singleton registry + dynamic loader
#    REGISTRY       — the process-wide singleton instance
#
#  Plugin contract for every app:
#    - Module lives at  apps/<module>.py  (or apps/<module>/__init__.py)
#    - Contains exactly one class matching AppDefinition.class_name
#    - __init__ signature:  __init__(self, parent=None)
#    - On failure: app moves to QUARANTINE status, never crashes the OS
# =============================================================

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field, replace
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)


# ── App Status ────────────────────────────────────────────────

class AppStatus(Enum):
    AVAILABLE   = auto()   # Importable and instantiable
    QUARANTINE  = auto()   # Import failed — moved to experimental/
    UNVERIFIED  = auto()   # Not yet tested this session


# ── App Definition (immutable manifest entry) ─────────────────

@dataclass(frozen=True)
class AppDefinition:
    """
    Immutable descriptor for a registered application.

    Fields
    ------
    name        Display name shown in launcher and title bar
    emoji       Short icon glyph for compact views
    module      Python module name under apps/  (e.g. "terminal")
    class_name  Class inside that module to instantiate
    icon_asset  Optional SVG/PNG filename in assets/
    sessions    Which session types grant access: "real" | "fake"
    show_on_desktop  Whether to show on the icon grid
    """
    name:             str
    emoji:            str
    module:           str
    class_name:       str
    icon_asset:       Optional[str]          = None
    sessions:         frozenset[str]         = field(default_factory=lambda: frozenset({"real", "fake"}))
    show_on_desktop:  bool                   = True
    isolation_mode:   str                    = "process" # "direct" (thread) or "process" (isolated)


# ── App Definitions manifest ──────────────────────────────────

_MANIFEST: tuple[AppDefinition, ...] = (
    AppDefinition(
        name="Files",
        emoji="📁",
        module="components.app_proxies",
        class_name="FileExplorerProxy",
        icon_asset="icons/files.svg",
        isolation_mode="process",
    ),
    AppDefinition(
        name="Terminal",
        emoji="🐚",
        module="components.app_proxies",
        class_name="TerminalProxy",
        icon_asset="icons/terminal.svg",
        isolation_mode="process",
    ),
    AppDefinition(
        name="System Monitor",
        emoji="📊",
        module="components.app_proxies",
        class_name="TaskManagerProxy",
        icon_asset="icons/prediction.svg",
        sessions=frozenset({"real"}),
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Security",
        emoji="🛡️",
        module="components.security_ui",
        class_name="SecurityPanel",
        icon_asset="icons/trust.svg",
        sessions=frozenset({"real"}),
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Marketplace",
        emoji="💎",
        module="components.app_proxies",
        class_name="MarketplaceProxy",
        icon_asset="icons/intent.svg",
        sessions=frozenset({"real"}),
        isolation_mode="process",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Network",
        emoji="🌐",
        module="components.app_proxies",
        class_name="NetworkToolsProxy",
        icon_asset="icons/trust.svg",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Settings",
        emoji="⚙️",
        module="components.app_proxies",
        class_name="SettingsProxy",
        icon_asset="icons/settings.svg",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Google Chrome",
        emoji="🌐",
        module="components.app_proxies",
        class_name="ChromeProxy",
        icon_asset="icons/chrome.svg",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Mozilla Firefox",
        emoji="🦊",
        module="components.app_proxies",
        class_name="FirefoxProxy",
        icon_asset="icons/firefox.svg",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Chaos Tester",
        emoji="🔥",
        module="adversary.chaos_tester",
        class_name="ChaosTester",
        icon_asset="icons/intent.svg",
        sessions=frozenset({"real"}),
        isolation_mode="process",
        show_on_desktop=True,
    ),
)


# ── Registry ──────────────────────────────────────────────────

# Phase 15.4: Global Isolation Policy
DEFAULT_ISOLATION = "direct"
CRITICAL_APPS = {"Desktop", "Taskbar", "SystemUI", "Chaos Tester"} # Chaos Tester needs process mode too
SAFE_MODE = False # Emergency Kill Switch

class AppRegistry:
    """
    Singleton application registry and dynamic loader.

    Responsibilities
    ----------------
    - Maintain the canonical app manifest (MANIFEST)
    - Dynamically import and instantiate app widgets on demand
    - Quarantine apps that fail to import (never crash the OS)
    - Provide session-filtered app lists to the UI layer
    """

    def __init__(self):
        # Status cache: app name -> AppStatus
        self._status: dict[str, AppStatus] = {
            app.name: AppStatus.UNVERIFIED for app in _MANIFEST
        }
        # Failure reason cache: app name -> error string
        self._errors: dict[str, str] = {}
        # Dynamic app definitions injected at runtime (e.g. by the attack engine).
        # Kept separate from the frozen _MANIFEST so the static manifest is
        # never mutated, but attack-engine adversarial apps are still resolvable.
        self._definitions: dict[str, AppDefinition] = {}

    # ── Public query API ─────────────────────────────────────

    @property
    def all_apps(self) -> tuple[AppDefinition, ...]:
        """Return the full immutable manifest."""
        return _MANIFEST

    def apps_for_session(self, session_type: str) -> list[AppDefinition]:
        """
        Return apps available for the given session type.
        session_type: "real" (Rust-authenticated) | "fake" (demo).
        Quarantined apps are silently excluded.
        """
        active = "fake" if session_type == "fake" else "real"
        return [
            app for app in _MANIFEST
            if active in app.sessions
            and self._status.get(app.name) != AppStatus.QUARANTINE
        ]

    def get_by_name(self, name: str) -> Optional[AppDefinition]:
        """Look up an AppDefinition by display name.

        Checks dynamically-registered definitions (_definitions) first so that
        attack-engine adversarial apps are resolvable, then falls back to the
        frozen manifest.  Returns None if not found.
        """
        # Dynamic registry (attack engine, plugins) takes priority
        if name in self._definitions:
            return self._definitions[name]
        for app in _MANIFEST:
            if app.name.lower() == name.lower():
                return app
        return None

    def status(self, name: str) -> AppStatus:
        return self._status.get(name, AppStatus.UNVERIFIED)

    def quarantined_apps(self) -> list[tuple[AppDefinition, str]]:
        """Return list of (AppDefinition, error_reason) for quarantined apps."""
        return [
            (app, self._errors.get(app.name, "Unknown error"))
            for app in _MANIFEST
            if self._status.get(app.name) == AppStatus.QUARANTINE
        ]

    # ── Status Management ────────────────────────────────────

    def set_status(self, name: str, status: AppStatus) -> None:
        self._status[name] = status

    def quarantine(self, name: str, reason: str) -> None:
        """Move app to quarantined state due to failure."""
        self._status[name] = AppStatus.QUARANTINE
        self._errors[name] = reason
        logger.warning("AppRegistry: QUARANTINE '%s' — %s", name, reason)
        self.report_failure(name, reason)

    # ── Verification ─────────────────────────────────────────

    def verify_all(self) -> dict[str, str]:
        """
        Dry-run import of every registered app (no instantiation).
        Returns dict of {app_name: "OK" | "QUARANTINE: <reason>"}.
        """
        results: dict[str, str] = {}
        for app in _MANIFEST:
            try:
                mod = importlib.import_module(app.module)
                if not hasattr(mod, app.class_name):
                    reason = f"Class '{app.class_name}' not in module"
                    self.quarantine(app.name, reason)
                    results[app.name] = f"QUARANTINE: {reason}"
                else:
                    if self._status[app.name] == AppStatus.UNVERIFIED:
                        self._status[app.name] = AppStatus.AVAILABLE
                    results[app.name] = "OK"
            except Exception as exc:
                reason = f"Load error: {exc}"
                self.quarantine(app.name, reason)
                results[app.name] = f"QUARANTINE: {reason}"
        return results

    def instantiate(self, name: str, secure_api=None) -> Optional[QWidget]:
        """
        Dynamically loads and instantiates an application widget.
        
        This is the ONLY way to launch an app in Q-Vault OS.
        Returns the widget instance, or None if failed.
        """
        app = self.get_by_name(name)
        if not app:
            logger.error(f"[REGISTRY] App '{name}' not found in manifest.")
            return None
            
        try:
            # 1. Resolve module
            mod = importlib.import_module(app.module)
            # 2. Resolve class
            cls = getattr(mod, app.class_name)
            # 3. Instantiate with common signature
            widget = cls(secure_api=secure_api)
            return widget
        except Exception as e:
            logger.error(f"[REGISTRY] Failed to instantiate '{name}': {e}", exc_info=True)
            self.quarantine(name, str(e))
            return None

    # ── Internal ──────────────────────────────────────────────

    def report_failure(self, app_name: str, detail: str) -> None:
        """Report a registry/launch failure via EventBus."""
        try:
            from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
            EVENT_BUS.emit(
                SystemEvent.EVT_WARNING, 
                EventPayload("app_registry_error", {"source": "app_registry", "app": app_name, "detail": detail, "escalate": True})
            )
        except Exception:
            pass

    def _quarantine(self, name: str, reason: str) -> None:
        self._status[name] = AppStatus.QUARANTINE
        self._errors[name] = reason
        logger.warning("AppRegistry: QUARANTINE '%s' — %s", name, reason)


# ── Process-wide singleton ────────────────────────────────────

# ── REGISTRY SINGLETON ──────────────────────────────────────────

REGISTRY = AppRegistry()
