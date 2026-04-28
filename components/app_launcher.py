# =============================================================
#  components/app_launcher.py — Q-VAULT OS  |  App Launcher
#
#  Registry-driven launcher menu.
#  Zero hardcoded imports. Every app comes from REGISTRY.
#
#  Architecture:
#    - Reads the session-filtered app list from REGISTRY
#    - Delegates all instantiation to REGISTRY.instantiate()
#    - Delegates window management to system.window_manager
#    - Quarantined apps are shown as disabled (grayed out)
# =============================================================

import uuid
import logging

from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import Qt
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)


class AppLauncher(QMenu):
    """
    Right-click / taskbar app menu.
    Populated entirely from core.app_registry.REGISTRY.
    Never imports an app class directly.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QMenu {{
                background-color: {THEME['surface_mid']};
                color: {THEME['text_main']};
                border: 1px solid {THEME['surface_raised']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }}
            QMenu::item:selected {{ background-color: {THEME['surface_mid']}; }}
            QMenu::item:disabled {{ color: {THEME['text_disabled']}; }}
            QMenu::separator {{ height: 1px; background: {THEME['surface_raised']}; margin: 4px 8px; }}
        """)
        self._build_menu()

    # ── Menu construction ────────────────────────────────────

    def _build_menu(self):
        """Build the menu from registry. Called once at construction."""
        self.clear()

        from core.app_registry import REGISTRY
        from core.system_state import STATE
        from assets.theme import THEME

        session = getattr(STATE, "session_type", "real") or "real"
        available = REGISTRY.apps_for_session(session)
        quarantined = {app.name for app, _ in REGISTRY.quarantined_apps()}

        if not available and not quarantined:
            self.addAction("(No apps registered)").setEnabled(False)
            return

        for app_def in available:
            label = f"{app_def.emoji}  {app_def.name}"
            if app_def.name in quarantined:
                action = self.addAction(f"⚠  {app_def.name}  [unavailable]")
                action.setEnabled(False)
            else:
                action = self.addAction(label)
                # Capture app_def by value in closure
                action.triggered.connect(
                    lambda checked=False, d=app_def: self._launch(d)
                )

        # Separator + quarantined section (informational only)
        if quarantined:
            self.addSeparator()
            lbl = self.addAction("Unavailable (quarantined):")
            lbl.setEnabled(False)
            for name, reason in REGISTRY.quarantined_apps():
                a = self.addAction(f"  ⛔  {name.name}")
                a.setEnabled(False)
                a.setToolTip(reason)

    # ── Launch ───────────────────────────────────────────────

    def _launch(self, app_def) -> None:
        """
        Emits REQ_APP_LAUNCH. AppController handles the actual spawning.
        """
        EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": app_def.name}, source="AppLauncher")
        logger.info("AppLauncher: requested launch for '%s'", app_def.name)

    # ── Helpers ──────────────────────────────────────────────

    def _get_workspace(self):
        """Walk up parent chain to find the desktop workspace widget."""
        p = self.parent()
        while p is not None:
            if hasattr(p, "workspace"):
                return p.workspace
            p = p.parent() if hasattr(p, "parent") else None
        return None
