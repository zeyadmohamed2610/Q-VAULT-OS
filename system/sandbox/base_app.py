"""
system/sandbox/base_app.py
─────────────────────────────────────────────────────────────────────────────
The mandatory App Contract for every Q-Vault OS application.

Every app class MUST:
  1. Inherit BaseApp (alongside QWidget)
  2. Accept `secure_api` as the first argument after `parent`
  3. Call super().__init__(secure_api) before any other init logic
  4. Implement the lifecycle hooks (on_start, on_stop at minimum)
  5. Declare permissions in manifest.json (enforced at launch)

Violation of this contract causes AppRegistry to quarantine the app.

Template usage:
─────────────────────────────────────────────────────────────────────────────
from PyQt5.QtWidgets import QWidget
from system.sandbox.base_app import BaseApp

class MyApp(BaseApp, QWidget):
    APP_ID = "my_app"                          # Must match manifest + registry

    def __init__(self, secure_api=None, parent=None):
        BaseApp.__init__(self, secure_api)
        QWidget.__init__(self, parent)
        self._setup_ui()

    def on_start(self):
        pass   # called after window is shown

    def on_stop(self):
        pass   # called before window close — clean up timers, threads here

    def get_permissions(self):
        return ["file_access:virtual_only", "network_access:DENIED"]
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .secure_api import SecureAPI

logger = logging.getLogger("sandbox.base_app")


class BaseApp:
    """
    Abstract contract that every Q-Vault application must inherit.

    Attributes
    ----------
    api         -> SecureAPI     injected by AppRegistry; all system access goes through here
    _app_id     -> str           resolved from APP_ID class var or class name
    _started    -> bool          tracks lifecycle state

    Required overrides
    ------------------
    on_start()          called automatically after the window is visible
    on_stop()           called automatically before close — clean up here
    get_permissions()   declare what your app needs; validated against manifest
    """

    # Subclasses set this; AppRegistry reads it for audit trails
    APP_ID: str = ""

    def __init__(self, secure_api: "SecureAPI | None" = None):
        self.api = secure_api
        self._app_id: str = self.APP_ID or self.__class__.__name__
        self._started: bool = False
        logger.debug("[BaseApp] '%s' contract initialised.", self._app_id)

    # ── API alias ─────────────────────────────────────────────────────────────
    @property
    def secure_api(self):
        """Alias for self.api — both names are valid throughout Q-Vault OS."""
        return self.api

    @secure_api.setter
    def secure_api(self, value):
        """Allow AppRegistry / launchers to set via either name."""
        self.api = value

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def on_start(self) -> None:
        """Override: called once after the window becomes visible."""

    def on_stop(self) -> None:
        """
        Override: release all resources before the window is destroyed.
        Stop QTimers, quit QThreads, unsubscribe from event buses here.
        """

    # ── Permission declaration ────────────────────────────────────────────────

    def get_permissions(self) -> List[str]:
        """
        Override: declare what this app needs.

        Format: "<action>:<level>"
        Examples:
          "file_access:virtual_only"
          "network_access:local_only"
          "system_calls:DENIED"

        The Registry validates this against the app's manifest.json.
        A mismatch marks the app UNVERIFIED with a warning (controlled mode).
        """
        return []

    # ── Automatic close-event wiring ──────────────────────────────────────────

    def closeEvent(self, event):   # noqa: N802  (Qt naming)
        """Intercept QWidget.closeEvent to call on_stop automatically."""
        if self._started:
            try:
                self.on_stop()
            except Exception as exc:
                logger.error("[BaseApp] on_stop() raised in '%s': %s", self._app_id, exc)
            self._started = False

        # Call QWidget's closeEvent if present (MRO handles this in subclasses)
        super_close = getattr(super(), "closeEvent", None)
        if super_close:
            super_close(event)
        else:
            event.accept()

    # ── Internal lifecycle trigger (called by AppRegistry) ───────────────────

    def _trigger_start(self) -> None:
        """Called by AppRegistry/OSWindow after widget is shown. Do not override."""
        if not self._started:
            self._started = True
            try:
                self.on_start()
            except Exception as exc:
                logger.error("[BaseApp] on_start() raised in '%s': %s", self._app_id, exc)

    # ── Repr ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        status = "running" if self._started else "idle"
        return f"<{self.__class__.__name__} app_id='{self._app_id}' status={status}>"
