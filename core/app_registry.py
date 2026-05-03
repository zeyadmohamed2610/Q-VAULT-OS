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
        name="Terminal",
        emoji="🖥️",
        module="apps.terminal.terminal_app",
        class_name="TerminalApp",
        icon_asset="icons/terminal.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="File Manager",
        emoji="📁",
        module="apps.file_manager.file_manager_app",
        class_name="FileManagerApp",
        icon_asset="icons/files.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Trash",
        emoji="🗑️",
        module="apps.trash.trash_app",
        class_name="TrashApp",
        icon_asset="icons/trash.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    # Legacy entries kept for backward compat (not shown on desktop)
    AppDefinition(
        name="Files",
        emoji="📁",
        module="apps.file_manager.file_manager_app",
        class_name="FileManagerApp",
        icon_asset="icons/files.svg",
        isolation_mode="direct",
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Q-Vault Browser",
        emoji="🌐",
        module="apps.browser.browser_app",
        class_name="BrowserApp",
        icon_asset="icons/browser.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Q-Vault Security",
        emoji="🛡️",
        module="apps.qvault_security.qvault_security_app",
        class_name="QVaultSecurityApp",
        icon_asset="icons/icon-vault.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Kernel Monitor",
        emoji="🖥",
        module="kernel.app",
        class_name="KernelMonitorApp",
        icon_asset="icons/kernel_monitor.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
    AppDefinition(
        name="Notepad",
        emoji="📝",
        module="apps.notepad.notepad_app",
        class_name="NotepadApp",
        icon_asset="icons/file_text.svg",
        isolation_mode="direct",
        show_on_desktop=True,
    ),
)


# ── Registry ──────────────────────────────────────────────────

# Phase 15.4: Global Isolation Policy
DEFAULT_ISOLATION = "direct"
CRITICAL_APPS = {"Desktop", "Taskbar"}
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

    def instantiate(self, name: str, secure_api=None, parent=None):
        """
        Dynamically loads and instantiates an application widget via centralized factory.
        
        This is the ONLY way to launch an app in Q-Vault OS.
        Returns the widget instance, or None if failed.
        """
        from system.app_factory import create_app_by_name

        try:
            return create_app_by_name(name, parent=parent)
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
