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
        Instantiate app via REGISTRY and wrap in an OSWindow.
        If the app is already open, focus the existing window.
        Never imports the app class directly.
        """
        from system.window_manager import get_window_manager
        from components.os_window import OSWindow
        from core.app_registry import REGISTRY
        from assets.theme import THEME

        wm = get_window_manager()

        # Focus existing window if already open
        existing = wm.find_by_title(app_def.name)
        if existing:
            wm.focus_window(existing.window_id)
            return

        workspace = self._get_workspace()
        widget = REGISTRY.instantiate(app_def, parent=workspace)

        if widget is None:
            logger.warning(
                "AppLauncher: REGISTRY could not instantiate '%s'", app_def.name
            )
            self._build_menu()  # Rebuild to show quarantine state
            return

        win_id = str(uuid.uuid4())
        window = OSWindow(win_id, app_def.name, widget, parent=workspace)
        window.resize(700, 500)
        # WindowManager tracks windows in _windows (dict), not .windows
        count = len(wm._windows)
        window.move(80 + (count % 8) * 30, 80 + (count % 8) * 30)
        # Sync SecureAPI instance_id to the actual window_id so guards
        # can resolve penalties against the correct AppRecord.
        if hasattr(widget, "secure_api") and widget.secure_api is not None:
            widget.secure_api.instance_id = win_id
        wm.register_window(window)

        logger.info("AppLauncher: opened '%s'", app_def.name)

    # ── Helpers ──────────────────────────────────────────────

    def _get_workspace(self):
        """Walk up parent chain to find the desktop workspace widget."""
        p = self.parent()
        while p is not None:
            if hasattr(p, "workspace"):
                return p.workspace
            p = p.parent() if hasattr(p, "parent") else None
        return None
