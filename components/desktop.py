# =============================================================
#  desktop.py - Q-Vault OS  |  Desktop (v3 - Workspace + Sound)
# =============================================================

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from assets import theme
from components.desktop_icon import DesktopIcon
from components.os_window import OSWindow
from components.taskbar import Taskbar
from core.app_registry import AppDefinition, apps_for_session
from core.system_state import STATE


def _placeholder(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"color:{theme.TEXT_DIM}; font-size:13px;"
        f"font-family:'Consolas',monospace; background:transparent;"
        f"border:1px dashed {theme.BORDER_DIM}; border-radius:4px; margin:12px;"
    )
    return lbl


ICON_X = 16
ICON_Y = 20
ICON_STRIDE = 100  # matches CELL_H(84) + 16 gap


class Desktop(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Desktop")
        self.setFocusPolicy(Qt.StrongFocus)

        # Workspace system
        self._current_workspace = 0
        self._workspace_count = 2
        self._workspace_windows: dict[int, list[str]] = {0: [], 1: []}

        self._windows: dict[str, OSWindow] = {}
        self._creating: set[str] = set()  # guard rapid double-clicks
        self._focused: OSWindow | None = None
        self._open_n = 0
        self._apps: list[AppDefinition] = []
        self._app_index: dict[str, AppDefinition] = {}
        self._app_factories: dict[str, callable] = {}

        # Sound system (lightweight)
        self._init_sound()

        # Initialize clipboard
        self._clipboard_text = ""
        self._clipboard_files = []

        self._load_apps()

        self._taskbar = Taskbar(on_start_clicked=self._toggle_start_menu, parent=self)

        from components.start_menu import StartMenu

        self._start_menu = StartMenu(self._apps, on_launch=self._open_app, parent=self)
        self._start_menu.hide()

        self._build_icons()

        # Alt+Tab overlay
        self._alt_tab = AltTabOverlay(self)
        self._alt_tab.hide()

        from components.lock_screen import LockScreen

        self._lock_screen = LockScreen(on_unlock=self._on_unlock, parent=self)
        self._lock_screen.hide()

        self._emergency_banner = self._build_emergency_banner()
        self._emergency_banner.hide()

        from system.notification_system import NOTIFY

        NOTIFY.set_parent(self)
        NOTIFY.flush_queue()

        STATE.subscribe(self._on_state_change)
        from system.security_system import SEC

        SEC.subscribe(self._on_sec_notify)

    def _init_sound(self):
        """Initialize lightweight sound system"""
        try:
            from PyQt5.QtMultimedia import QSoundEffect

            self._sound_click = QSoundEffect()
            self._sound_notification = QSoundEffect()
            self._sound_enabled = True
        except ImportError:
            self._sound_enabled = False

    def _play_click(self):
        if not self._sound_enabled:
            return
        try:
            if hasattr(self, "_sound_click"):
                pass
        except Exception:
            pass

    def _play_notification(self):
        if not self._sound_enabled:
            return
        try:
            if hasattr(self, "_sound_notification"):
                pass
        except Exception:
            pass

    def closeEvent(self, event):
        from system.security_system import SEC

        STATE.unsubscribe(self._on_state_change)
        SEC.unsubscribe(self._on_sec_notify)
        super().closeEvent(event)

    def _wm_text(self) -> str:
        user = STATE.username()
        extra = "  [FAKE SESSION]" if STATE.session_type == "fake" else ""
        return f"{theme.BRAND_WORDMARK} // SECURE OS  |  {user}{extra}"

    def _load_apps(self):
        import importlib

        self._apps = apps_for_session(STATE.session_type)
        self._app_index = {app.name: app for app in self._apps}
        self._app_factories.clear()

        def _safe_factory(app_def: AppDefinition):
            try:
                module = importlib.import_module(f"apps.{app_def.module}")
                widget_class = getattr(module, app_def.class_name)
                return widget_class
            except Exception:
                return lambda: _placeholder(f"{app_def.class_name} (import error)")

        for app_def in self._apps:
            if app_def.name == "Security":

                def _security_factory(_app_def=app_def):
                    module = importlib.import_module(f"apps.{_app_def.module}")
                    panel = getattr(module, _app_def.class_name)()
                    panel.intrusion_detected.connect(self._show_security_alert)
                    return panel

                self._app_factories[app_def.name] = _security_factory
            else:
                self._app_factories[app_def.name] = _safe_factory(app_def)

    def _build_emergency_banner(self) -> QLabel:
        lbl = QLabel("WARNING  EMERGENCY MODE ACTIVE  DRIVE DISMOUNTED")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{theme.ACCENT_RED}; color:white; font-weight:bold;"
            f"font-family:'Consolas',monospace; font-size:12px; padding:6px;"
        )
        lbl.setParent(self)
        return lbl

    def _build_demo_banner(self) -> QLabel:
        lbl = QLabel("DEMO MODE ACTIVE - For demonstration purposes")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{theme.ACCENT_AMBER}; color:{theme.BG_DARK}; font-weight:bold;"
            f"font-family:'Consolas',monospace; font-size:11px; padding:4px;"
        )
        lbl.setParent(self)
        return lbl

    def show_demo_banner(self, show: bool = True):
        """Show or hide the demo mode banner."""
        if not hasattr(self, "_demo_banner"):
            self._demo_banner = self._build_demo_banner()

        if show:
            self._demo_banner.show()
            self._demo_banner.raise_()
        else:
            self._demo_banner.hide()

    def _on_state_change(self, field: str, old, new):
        if field == "emergency_mode" and new:
            self._emergency_banner.show()
            self._emergency_banner.raise_()

    def _on_sec_notify(self, entry: dict):
        from system.notification_system import NOTIFY

        if not STATE.alerts_enabled:
            return

        event_type = entry["event_type"]
        if event_type == "INTRUSION_DETECTED":
            NOTIFY.send("INTRUSION DETECTED", entry["detail"], level="danger")
        elif event_type == "SUSPICIOUS_PROCESS":
            NOTIFY.send("Suspicious Process", entry["detail"], level="warning")
        elif event_type == "RISK_CLEARED":
            NOTIFY.send(
                "Risk Cleared",
                "System risk level reset to LOW.",
                level="success",
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width, height = self.width(), self.height()
        taskbar_h = Taskbar.TASKBAR_HEIGHT

        self._taskbar.setGeometry(0, height - taskbar_h, width, taskbar_h)
        self._taskbar.raise_()
        self._alt_tab.reposition()
        self._start_menu.reposition()
        self._lock_screen.setGeometry(0, 0, width, height)
        self._emergency_banner.setGeometry(0, 0, width, 30)

        if hasattr(self, "_demo_banner"):
            self._demo_banner.setGeometry(0, 30, width, 26)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Base gradient
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(theme.DESKTOP_GRADIENT_START))
        grad.setColorAt(0.5, QColor(theme.DESKTOP_GRADIENT_MID))
        grad.setColorAt(1.0, QColor(theme.DESKTOP_GRADIENT_END))
        painter.fillRect(self.rect(), grad)

        # Subtle grid overlay (40px spacing)
        grid_color = QColor(34, 197, 94, 8)  # Green, very low opacity
        painter.setPen(grid_color)
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 40):
            painter.drawLine(0, y, self.width(), y)

        # Ambient radial glow in center
        from PyQt5.QtGui import QRadialGradient

        center_x = self.width() // 2
        center_y = self.height() // 2
        glow = QRadialGradient(center_x, center_y, int(self.width() * 0.5))
        glow.setColorAt(0.0, QColor(34, 197, 94, 12))
        glow.setColorAt(0.4, QColor(34, 197, 94, 6))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

        # Vignette effect
        vignette = QRadialGradient(
            self.width() // 2,
            self.height() // 2,
            int(self.width() * 0.7),
        )
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.6, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 180))
        painter.fillRect(self.rect(), vignette)

    def _build_icons(self):
        desktop_apps = [app for app in self._apps if app.show_on_desktop]
        for i, app_def in enumerate(desktop_apps):
            icon = DesktopIcon(
                app_def.name,
                app_def.emoji,
                app_def.icon_asset,
                parent=self,
            )
            icon.move(ICON_X, ICON_Y + i * ICON_STRIDE)
            icon.opened.connect(self._open_app)
            icon.show()
            print(
                f"[DESKTOP] Icon created: {app_def.name} at position ({ICON_X}, {ICON_Y + i * ICON_STRIDE})"
            )

    def _open_app(self, name: str):
        from core.process_manager import PM
        from system.process_scheduler import SCHEDULER
        from core.system_state import STATE

        try:
            # If already open, raise and focus
            if name in self._windows:
                win = self._windows[name]
                win.show()
                win.raise_()
                win.activateWindow()
                self.on_window_focused(win)
                self._start_menu.hide()
                return

            app_def = self._app_index.get(name)
            factory = self._app_factories.get(name)
            if app_def is None or factory is None:
                return

            # Rapid-click guard — prevent duplicate construction
            if name in self._creating:
                return
            self._creating.add(name)

            PM.spawn(argv=name, owner=STATE.username(), background=True)
            SCHEDULER.create_process(name, command=name, owner=STATE.username())

            offset = (self._open_n % 8) * 28
            self._open_n += 1

            content_widget = factory()
            win = OSWindow(name, app_def.emoji, content_widget, parent=self)
            win.move(110 + offset, 60 + offset)
            win.show()
            win.raise_()
            win.activateWindow()
            win.destroyed.connect(lambda _=None, n=name: self._on_closed(n))

            self._windows[name] = win
            self._creating.discard(name)

            if self._current_workspace not in self._workspace_windows:
                self._workspace_windows[self._current_workspace] = []
            self._workspace_windows[self._current_workspace].append(name)

            self._taskbar.add_window_button(
                window_id=name,
                title=f"{app_def.emoji} {name}",
                on_click=lambda _=False, n=name: self._taskbar_click(n),
            )
            self.on_window_focused(win)
            self._taskbar.raise_()
            self._start_menu.hide()

        except Exception as e:
            import logging
            import traceback
            self._creating.discard(name)
            logging.error(f"Failed to open app {name}: {e}")
            logging.error(traceback.format_exc())


    def app_emoji(self, name: str) -> str:
        app_def = self._app_index.get(name)
        return app_def.emoji if app_def else "[]"

    def on_window_focused(self, win: OSWindow):
        if self._focused and self._focused is not win:
            self._focused.set_focused(False)
        self._focused = win
        win.set_focused(True)
        win.raise_()
        self._taskbar.raise_()
        for name, candidate in self._windows.items():
            if candidate is win:
                self._taskbar.set_active(name)
                break

    def _taskbar_click(self, name: str):
        win = self._windows.get(name)
        if not win:
            return
        if win.isVisible():
            win.hide()
            self._taskbar.set_active(None)
            self._focused = None
        else:
            win.show()
            win.raise_()
            self.on_window_focused(win)

    def _on_closed(self, name: str):
        win = self._windows.pop(name, None)
        if win and win is self._focused:
            self._focused = None
        self._taskbar.remove_window_button(name)
        self._taskbar.set_active(None)

    def _show_security_alert(self, entry: dict):
        if not STATE.alerts_enabled:
            return
        from apps.security_panel import SecurityAlert

        alert = SecurityAlert(entry, parent=self)
        alert.show_on(self)
        self._notify_terminal(
            f"[SECURITY] {entry['event_type']} <- {entry['source']} | Risk: {entry['risk_after']}"
        )

    def _notify_terminal(self, message: str):
        win = self._windows.get("Terminal")
        if win:
            content = win.findChild(QWidget, "Terminal")
            if content and hasattr(content, "_sys"):
                content._sys(message)

    def lock(self):
        self._lock_screen.setGeometry(0, 0, self.width(), self.height())
        self._lock_screen.show()
        self._lock_screen.raise_()

    def _on_unlock(self):
        self._lock_screen.hide()
        self.setFocus()

    def _take_screenshot(self):
        import time as _time

        pixmap = self.grab()
        timestamp = _time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

        try:
            from core.filesystem import FS

            saved = FS.pwd()
            FS.cd("/home/user/Desktop")
            FS.touch(filename)
            node = FS._node_at(FS._cwd)
            if filename in node:
                node[filename].content = (
                    f"[PNG {pixmap.width()}x{pixmap.height()}px captured "
                    f"{_time.strftime('%Y-%m-%d %H:%M:%S')}]"
                )
            FS.cd(saved)
        except Exception:
            pass

        from system.notification_system import NOTIFY

        NOTIFY.send(
            "Screenshot captured",
            f"Saved -> Desktop/{filename}",
            level="success",
        )
        self._notify_terminal(
            f"[screenshot] Desktop/{filename} ({pixmap.width()}x{pixmap.height()}px)"
        )

    def _simulate_restart(self):
        from system.notification_system import NOTIFY

        NOTIFY.send("Restarting", "Returning to login in 1 second...", level="warning")
        self._notify_terminal("[kernel] Restart requested - logging out.")
        QTimer.singleShot(1200, self._do_logout)

    def _do_logout(self):
        parent = self.parent()
        if parent and hasattr(parent, "show_login"):
            parent.show_login()

    def show_login(self):
        self._do_logout()

    def _create_new_file(self):
        from core.filesystem import FS

        try:
            FS.touch("newfile.txt")
            self._open_app("Files")
        except Exception:
            pass

    def _create_new_folder(self):
        from core.filesystem import FS

        try:
            FS.mkdir("new_folder")
            self._open_app("Files")
        except Exception:
            pass

    def _refresh_desktop(self):
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(theme.CONTEXT_MENU_STYLE)

        # New File
        menu.addAction(QAction("New File", self, triggered=self._create_new_file))
        # New Folder
        menu.addAction(QAction("New Folder", self, triggered=self._create_new_folder))
        menu.addSeparator()
        # Open Terminal
        menu.addAction(
            QAction("Open Terminal", self, triggered=lambda: self._open_app("Terminal"))
        )
        # Refresh
        menu.addAction(QAction("Refresh", self, triggered=self._refresh_desktop))
        menu.addSeparator()
        # Screenshot
        menu.addAction(
            QAction("Screenshot  (PrtSc)", self, triggered=self._take_screenshot)
        )
        # Lock
        menu.addAction(QAction("Lock  (Ctrl+Alt+L)", self, triggered=self.lock))
        menu.addSeparator()
        # Settings
        menu.addAction(
            QAction("Settings", self, triggered=lambda: self._open_app("Settings"))
        )
        # Restart
        menu.addAction(
            QAction("Restart  (Ctrl+Alt+R)", self, triggered=self._simulate_restart)
        )
        menu.exec_(event.globalPos())

    def _toggle_start_menu(self):
        if self._start_menu.isVisible():
            self._start_menu.hide()
        else:
            self._start_menu.reposition()
            self._start_menu.show()
            self._start_menu.raise_()

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl_alt = Qt.ControlModifier | Qt.AltModifier

        if mods == ctrl_alt and key == Qt.Key_L:
            self.lock()
        elif mods == ctrl_alt and key == Qt.Key_Delete:
            self._open_app("Task Manager")
        elif mods == ctrl_alt and key == Qt.Key_T:
            self._open_app("Terminal")
        elif mods == ctrl_alt and key == Qt.Key_R:
            self._simulate_restart()
        elif mods == ctrl_alt and key == Qt.Key_Left:
            self._switch_workspace(-1)
        elif mods == ctrl_alt and key == Qt.Key_Right:
            self._switch_workspace(1)
        elif key == Qt.Key_Print:
            self._take_screenshot()
        elif mods == Qt.AltModifier and key == Qt.Key_Tab:
            if self._alt_tab.isVisible():
                self._alt_tab.advance()
            else:
                self._show_alt_tab()
        elif key in (Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R):
            self._toggle_start_menu()
        else:
            super().keyPressEvent(event)

    def _switch_workspace(self, direction: int):
        """Switch to next/previous workspace"""
        old_ws = self._current_workspace

        # Hide windows from current workspace
        for name in self._workspace_windows.get(old_ws, []):
            win = self._windows.get(name)
            if win and win.isVisible():
                win.hide()

        # Switch workspace
        self._current_workspace = (
            self._current_workspace + direction
        ) % self._workspace_count

        # Show windows from new workspace
        for name in self._workspace_windows.get(self._current_workspace, []):
            win = self._windows.get(name)
            if win:
                win.show()

        # Update taskbar indicator
        self._taskbar.set_workspace(self._current_workspace, self._workspace_count)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Alt and self._alt_tab.isVisible():
            self._alt_tab.hide()
            self._alt_tab.confirm(self._open_app)
        super().keyReleaseEvent(event)

    def _show_alt_tab(self):
        if not self._windows:
            return
        self._alt_tab.populate(list(self._windows.keys()))
        self._alt_tab.reposition()
        self._alt_tab.show()
        self._alt_tab.raise_()


class AltTabOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("AltTabOverlay")
        self.setStyleSheet(theme.ALT_TAB_STYLE)
        self._names: list[str] = []
        self._btns: list[QPushButton] = []
        self._sel = 0
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(16, 16, 16, 16)
        self._row.setSpacing(8)

    def populate(self, names: list[str]):
        while self._row.count():
            widget = self._row.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self._btns.clear()

        self._names = names
        self._sel = 0

        for i, name in enumerate(names):
            emoji = self.parent().app_emoji(name) if self.parent() else "[]"
            btn = QPushButton(f"{emoji}\n{name}")
            btn.setObjectName("AltTabItem")
            btn.setFixedSize(90, 80)
            btn.clicked.connect(lambda _=False, idx=i: self._click_select(idx))
            self._row.addWidget(btn)
            self._btns.append(btn)

        self._refresh_highlight()
        self.adjustSize()

    def advance(self):
        """Advance selection by one (called on each Alt+Tab press)."""
        if not self._names:
            return
        self._sel = (self._sel + 1) % len(self._names)
        self._refresh_highlight()

    def _refresh_highlight(self):
        for i, btn in enumerate(self._btns):
            selected = i == self._sel
            btn.setProperty("selected", "true" if selected else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _click_select(self, idx: int):
        self._sel = idx
        self.hide()
        p = self.parent()
        if p and hasattr(p, "_open_app"):
            self.confirm(p._open_app)

    def confirm(self, open_fn):
        if self._names and 0 <= self._sel < len(self._names):
            open_fn(self._names[self._sel])

    def reposition(self):
        if self.parent():
            self.adjustSize()
            x = (self.parent().width() - self.width()) // 2
            y = (self.parent().height() - self.height()) // 2
            self.move(x, y)
