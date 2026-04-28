from assets.theme import *
import uuid
import os
import json
from pathlib import Path
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty, QTimer
from PyQt5.QtGui import QPainter, QColor, QPalette, QBrush, QPixmap, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QAction, QMenu, QMessageBox
from components.modern_launcher import ModernLauncher
from components.taskbar_ui import TaskbarUI
from system.taskbar_controller import TaskbarController
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager
import time
import logging

logger = logging.getLogger(__name__)

class _SystemOverlay(QWidget):
    """
    v1.4 High-Fidelity Snap Preview Engine.
    Rendered on top of all workspace elements with zero-lag path rendering.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.snap_info = None # (SlotType, Rect)
        self._alpha = 0
        from assets.theme import MOTION_SNAPPY
        self.anim = QPropertyAnimation(self, b"overlay_alpha")
        self.anim.setDuration(MOTION_SNAPPY)

    @pyqtProperty(int)
    def overlay_alpha(self): return self._alpha

    @overlay_alpha.setter
    def overlay_alpha(self, val):
        self._alpha = val
        self.update()

    def set_snap_guide(self, info):
        """info: (SlotType, Rect) or None"""
        if info == self.snap_info: return
        
        was_none = (self.snap_info is None)
        self.snap_info = info
        
        target = 100 if info else 0
        self.anim.stop()
        self.anim.setStartValue(self._alpha)
        self.anim.setEndValue(target)
        self.anim.start()

    def paintEvent(self, event):
        if self.snap_info and self._alpha > 0:
            slot_type, rect = self.snap_info
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Semantic Alpha Scaling
            o_border = int((self._alpha / 100.0) * 120)
            o_brush  = int((self._alpha / 100.0) * 40)
            
            from assets.theme import RADIUS_LG
            # Draw preview outline
            painter.setPen(QColor(0, 230, 255, o_border))
            painter.setBrush(QColor(0, 230, 255, o_brush))
            painter.drawRoundedRect(rect, RADIUS_LG, RADIUS_LG)

class Desktop(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icons = [] # FOUNDATIONAL: Must exist before ANY other init logic
        self.setObjectName("Desktop")
        self._launcher_active = False
        self._dim_alpha = 0
        
        # ── Runtime Governance: Setup Notification Parent ──
        try:
            from system.runtime_manager import RUNTIME_MANAGER
            RUNTIME_MANAGER.set_desktop_parent(self)
        except Exception:
            pass

        # Build Background Overlay (First Layer)
        self.overlay = QWidget(self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.selection_rect = None
        self.start_pos = None

        self.layout_layer = QVBoxLayout(self)
        self.layout_layer.setContentsMargins(0, 0, 0, 0)
        self.layout_layer.setSpacing(0)

        # ───── SYSTEM OVERLAY (Top Layer for effects) ─────
        self.sys_overlay = _SystemOverlay(self)

        # ───── UI COMPONENTS (Initialize early to avoid AttributeErrors) ─────
        from components.modern_launcher import ModernLauncher
        from components.command_palette import CommandPalette
        from components.ai_inspector import AIInspectorPanel
        from components.settings_hub import SettingsHub
        from components.marketplace import Marketplace
        from components.control_center import ControlCenter

        self.launcher = ModernLauncher(self)
        self.palette = CommandPalette(self)
        self.inspector = AIInspectorPanel(self)
        self.settings_hub = SettingsHub(self)
        self.marketplace = Marketplace(self)
        self.control_center = ControlCenter(self)
        
        # UI Policy: Hidden by default
        self.launcher.hide()
        self.palette.hide()
        self.inspector.hide()
        self.settings_hub.hide()
        self.marketplace.hide()
        self.control_center.hide()

        # ───── TASKBAR (V2.0 Decoupled Architecture) ─────
        self.taskbar_controller = TaskbarController()
        self.taskbar_ui = TaskbarUI(parent=self)
        self.taskbar_ui.setObjectName("Taskbar")
        
        # Connect BEFORE initializing state to catch the first tick (fixes 00:00 AM delay)
        self.taskbar_controller.state_updated.connect(self.taskbar_ui.update_state)
        
        # Wire UI -> Actions
        self.taskbar_ui.start_clicked.connect(self.launcher.toggle)
        self.taskbar_ui.app_clicked.connect(self.taskbar_controller.request_focus)
        self.taskbar_ui.shortcut_clicked.connect(self._on_shortcut_clicked)
        self.taskbar_ui.shortcut_clicked.connect(self.taskbar_controller.handle_shortcut)
        
        top_wrapper = QHBoxLayout()
        top_wrapper.setContentsMargins(15, 10, 15, 15) # Increased bottom margin for Taskbar
        top_wrapper.addWidget(self.taskbar_ui)
        self.layout_layer.addLayout(top_wrapper)

        # ───── MIDDLE LAYER (Sidebar + Workspace) ─────
        self.mid_layout = QHBoxLayout()
        self.mid_layout.setContentsMargins(0, 0, 0, 0)
        self.mid_layout.setSpacing(0)

        # Sidebar (System Navigation)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(60) 
        self.sidebar.setStyleSheet("background: transparent;")
        self.mid_layout.addWidget(self.sidebar)

        # DESKTOP SPACE (Workspace)
        self.workspace = QWidget()
        self.workspace.setObjectName("Workspace")
        self.workspace.setStyleSheet("background: transparent;")
        self.mid_layout.addWidget(self.workspace, stretch=1)
        
        self.layout_layer.addLayout(self.mid_layout, stretch=1)
        
        # ───── SYSTEM OVERLAY (Top Layer for effects) ─────
        self.sys_overlay = _SystemOverlay(self)

        # ───── BACKGROUND CACHE ─────
        from core.resources import get_asset_path
        from PyQt5.QtGui import QPixmap
        img_path = get_asset_path("qvault_vault.jpg")
        self._bg_pixmap = QPixmap(img_path)
        
        self.launcher.app_launched.connect(self.toggle_launcher)
        
        
        self.marketplace = Marketplace(self)
        self.marketplace.hide()


        # ───── STABILITY MONITOR (Diagnostic Layer) ─────
        from components.diagnostic_overlay import DiagnosticOverlay
        self.diagnostic = DiagnosticOverlay(self)
        self.diagnostic.hide() 
        
        # ───── SNAP PREVIEW ─────
        from components.snap_preview_overlay import SnapPreviewOverlay
        self.snap_preview = SnapPreviewOverlay(self.workspace)
        self.snap_preview.hide()

        # ── Event Reactor ──
        EVENT_BUS.subscribe(SystemEvent.SETTING_CHANGED, self._on_setting_changed)
        self._init_system_services()

    def _on_setting_changed(self, payload):
        setting = payload.data.get("setting")
        value = payload.data.get("value")
        
        if setting == "diagnostic":
            if value == "toggle":
                if self.diagnostic.isVisible():
                    self.diagnostic.hide()
                else:
                    self.diagnostic.show_in_corner(self.rect())

    def _init_system_services(self):
        # ───── EVENT SUBSCRIPTIONS ─────
        EVENT_BUS.subscribe(SystemEvent.REQ_COMMAND_PALETTE_TOGGLE, self._on_toggle_palette)
        EVENT_BUS.subscribe(SystemEvent.REQ_AI_INSPECTOR_TOGGLE, self._on_toggle_inspector)
        EVENT_BUS.subscribe(SystemEvent.REQ_SETTINGS_TOGGLE, self._on_toggle_settings)
        EVENT_BUS.subscribe(SystemEvent.REQ_MARKETPLACE_TOGGLE, self._on_toggle_marketplace)
        
        # ───── BETA: USER JOURNEY LOGGER ─────
        EVENT_BUS.subscribe("*", self._log_user_journey)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._desktop_menu)
        
        from system.window_manager import get_window_manager
        # Physics & Snap are now handled via EventBus reactions in _on_event_bus

        # ───── v2.0 IDLE MONITORING (via AuthManager) ─────
        # Timeout logic is owned by AuthManager.
        # Desktop only: (1) reports activity, (2) handles visual dimming via EventBus.
        EVENT_BUS.event_emitted.connect(self._on_event_bus)
        self._last_activity = time.time()
        self._is_dimming = False
        
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

        # ── v2.2 Metrics & Debug ──
        from system.metrics_collector import get_metrics_collector
        self._metrics = get_metrics_collector() 
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # ───── v1.5 QUICK PANEL ─────
        from components.quick_panel import QuickPanel
        self.quick_panel = QuickPanel(self)
        self.quick_panel.hide()
        
        from components.volume_osd import VolumeOSD
        self.volume_osd = VolumeOSD(self)
        self.quick_panel.volume_changed.connect(self.volume_osd.show_volume)

        # ───── v1.7 VERIFICATION OVERLAY ─────
        from components.debug_event_overlay import DebugEventOverlay
        self.debug_overlay = DebugEventOverlay(self)

        # ───── DESKTOP ICONS ─────
        self._create_icons()
        self.load_layout()

    def toggle_quick_panel(self):
        """Toggle the v2.7 Control Center overlay."""
        self.control_center.toggle()

    def init_notification_container(self):
        """Initialize the notification container. Called by system layer."""
        from components.notification_container import NotificationContainer
        if not hasattr(self, 'notification_container'):
            self.notification_container = NotificationContainer(self)
            self.notification_container.setup_position(self.rect())

    def _on_shortcut_clicked(self, name):
        """Handles taskbar shortcut clicks."""
        if name == "terminal":
            self.launch_app("Terminal")
        elif name == "files":
            self.launch_app("Files")
        elif name == "ai":
            self.toggle_inspector()
        elif name == "flows":
            self.palette.input.setText("workflow:")
            self.palette.show_centered()
        elif name == "control":
            self.quick_panel.toggle()
        elif name == "start":
            self.toggle_launcher()

    def toggle_inspector(self):
        if self.inspector.isVisible():
            self.inspector.hide()
        else:
            self.inspector.show_side(self.rect())
            self.inspector.raise_()

    def eventFilter(self, obj, event):
        """Global activity detector + v1.5 Hot Corners."""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.MouseMove:
            self._reset_idle()
            # Hot Corner: Top-Right (50px square)
            if event.globalPos().x() >= self.width() - 50 and event.globalPos().y() <= 50:
                if hasattr(self, "quick_panel") and not self.quick_panel.isVisible():
                    # Defensive: Ensure we don't spam show if it's already animating
                    if not getattr(self.quick_panel, "_is_visible", False):
                        self.toggle_quick_panel()

        elif event.type() in [QEvent.MouseButtonPress, QEvent.KeyPress]:
            self._reset_idle()
        return super().eventFilter(obj, event)

    def _reset_idle(self):
        self._last_activity = time.time()
        # Report activity to AuthManager (it owns the timeout)
        from system.auth_manager import get_auth_manager
        get_auth_manager().report_activity()
        if self._is_dimming:
            self._stop_dimming()

    def _start_dimming(self):
        """Begin idle dim animation."""
        self._is_dimming = True

    def _stop_dimming(self):
        """End idle dim animation."""
        self._is_dimming = False
        self._dim_alpha = 0
        self.update()

    def _on_event_bus(self, payload):
        """Handle USER_IDLE events from AuthManager for visual dimming."""
        if payload.type == SystemEvent.USER_IDLE:
            progress = payload.data.get("dim_progress", 0)
            if not self._is_dimming:
                self._start_dimming()
            self._dim_alpha = int(progress * 150)
            self.update()
        
        elif payload.type == SystemEvent.STATE_CHANGED and payload.data.get("type") == "snap_preview":
            slot = payload.data.get("slot")
            # Calculate rect for preview
            rect = None
            if slot:
                w, h = self.width(), self.height()
                if slot == WindowSlot.MAXIMIZED: rect = self.rect()
                elif slot == WindowSlot.HALF_LEFT: rect = QRect(0, 0, w//2, h)
                elif slot == WindowSlot.HALF_RIGHT: rect = QRect(w//2, 0, w//2, h)
                elif slot == WindowSlot.QUARTER_TL: rect = QRect(0, 0, w//2, h//2)
                elif slot == WindowSlot.QUARTER_TR: rect = QRect(w//2, 0, w//2, h//2)
                elif slot == WindowSlot.QUARTER_BL: rect = QRect(0, h//2, w//2, h//2)
                elif slot == WindowSlot.QUARTER_BR: rect = QRect(w//2, h//2, w//2, h//2)
            
            self._on_snap_guide(rect)

    def _on_toggle_palette(self, payload=None):
        if self.command_palette.isVisible():
            self.command_palette.hide()
        else:
            self.command_palette.show_centered(self.rect())
            self.command_palette.raise_()

    def _on_toggle_inspector(self, payload=None):
        if self.ai_inspector.isVisible():
            self.ai_inspector.hide()
        else:
            self.ai_inspector.show_side(self.rect())
            self.ai_inspector.raise_()

    def _on_toggle_settings(self, payload=None):
        if self.settings_hub.isVisible():
            self.settings_hub.hide()
        else:
            self.settings_hub.show_centered(self.rect())
            self.settings_hub.raise_()

    def _on_toggle_marketplace(self, payload=None):
        if self.marketplace.isVisible():
            self.marketplace.hide()
        else:
            self.marketplace.show_centered(self.rect())
            self.marketplace.raise_()

    def _log_user_journey(self, payload):
        """Records critical user interactions for Beta analysis."""
        from system.config import get_qvault_home
        import os, time
        
        # Filter for user-centric events
        user_events = [
            SystemEvent.REQ_USER_INPUT, 
            SystemEvent.REQ_APP_LAUNCH,
            SystemEvent.REQ_WORKFLOW_EXECUTE,
            SystemEvent.ACTION_CLICKED
        ]
        
        if payload.type in user_events or payload.type.name.startswith("REQ_"):
            log_path = os.path.join(get_qvault_home(), "logs", "user_journey.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            with open(log_path, "a") as f:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {payload.type.name} | Data: {payload.data} | Source: {payload.source}\n")

    def toggle_launcher(self):
        """Toggle the Modern Launcher with dimming effect."""
        self._launcher_active = not self._launcher_active
        if self._launcher_active:
            self.launcher.toggle()
        else:
            self.launcher.hide()
        self.update() # Trigger dimming repaint

    def _on_taskbar_search(self, text):
        """Unified search bridge between Taskbar and Palette."""
        if not text:
            self.palette.hide()
            return
        
        # Position palette below taskbar search
        search_geom = self.taskbar.search_bar.geometry()
        global_pos = self.taskbar.mapToGlobal(search_geom.bottomLeft())
        local_pos = self.mapFromGlobal(global_pos)
        
        self.palette.move(local_pos.x(), local_pos.y() + 5)
        self.palette.input.setText(text)
        self.palette.input.hide() # USER: Hide duplicate search
        self.palette.btn_close.hide() # User handles it via taskbar clearing
        self.palette.show()
        self.palette.raise_()


    def _on_snap_guide(self, rect):
        self.sys_overlay.set_snap_guide(rect)

    def resizeEvent(self, event):
        """Handle background scaling and overlay size."""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())
        self.sys_overlay.setGeometry(self.rect())
        self.sys_overlay.raise_()
        
        if hasattr(self, "debug_overlay") and self.debug_overlay:
            self.debug_overlay.show_in_corner(self.rect())
            self.debug_overlay.raise_()
            
        if hasattr(self, "palette") and self.palette and self.palette.isVisible():
            self.palette.show_centered(self.rect())
            self.palette.raise_()
            
        if hasattr(self, "settings_hub") and self.settings_hub and self.settings_hub.isVisible():
            self.settings_hub.show_centered(self.rect())
            
        if hasattr(self, "inspector") and self.inspector and self.inspector.isVisible():
            self.inspector.show_side(self.rect())
            self.inspector.raise_()

        if hasattr(self, "marketplace") and self.marketplace and self.marketplace.isVisible():
            self.marketplace.show_centered(self.rect())

        if hasattr(self, "onboarding") and self.onboarding:
            self.onboarding.show_centered(self.rect())
            
        self._update_background()

    def _update_background(self):
        """Triggers a repaint for the high-fidelity center-cropped wallpaper."""
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F12:
            EVENT_BUS.emit(SystemEvent.REQ_DEBUG_TOGGLE, source="Desktop_Hotkey")
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier and event.modifiers() & Qt.AltModifier:
            EVENT_BUS.emit(SystemEvent.REQ_SETTINGS_TOGGLE, source="Desktop_Hotkey")
        elif event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            EVENT_BUS.emit(SystemEvent.REQ_COMMAND_PALETTE_TOGGLE, source="Desktop_Hotkey")
        elif event.key() == Qt.Key_F10:
            EVENT_BUS.emit(SystemEvent.REQ_AI_INSPECTOR_TOGGLE, source="Desktop_Hotkey")
        elif event.key() == Qt.Key_M and event.modifiers() & Qt.ControlModifier:
            EVENT_BUS.emit(SystemEvent.REQ_MARKETPLACE_TOGGLE, source="Desktop_Hotkey")
        super().keyPressEvent(event)

    def paintEvent(self, event):
        """Draws the wallpaper identically to login_screen (Center-Crop) for a seamless transition."""
        from PyQt5.QtGui import QPainter
        from PyQt5.QtCore import Qt

        painter = QPainter(self)

        # ───── 1. Wallpaper Layer ─────
        if not self._bg_pixmap.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            # Center-crop math
            x = (scaled.width()  - self.width())  // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            # Fallback to black instead of white/default
            painter.fillRect(self.rect(), Qt.black)

        # ───── 1.5. Dashboard / Idle Dimmer (v1.5) ─────
        if self._launcher_active or self._dim_alpha > 0:
            alpha = 150 if self._launcher_active else self._dim_alpha
            painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))

        # ───── 2. Selection Overlay Layer ─────
        if self.selection_rect:
            painter.setBrush(QColor(200, 155, 60, 50)) # Gold tint
            painter.setPen(QColor(200, 155, 60))       # Solid Gold
            
            start, end = self.selection_rect
            rect = QRect(start, end).normalized()
            painter.drawRect(rect)

    def save_layout(self):
        from system.config import get_qvault_home
        import os, json
        config_dir = os.path.join(get_qvault_home(), ".config")
        os.makedirs(config_dir, exist_ok=True)
        state_path = os.path.join(config_dir, "desktop_state.json")
        data = {icon.name: {"x": icon.x(), "y": icon.y()} for icon in self.icons}
        with open(state_path, "w") as f:
            json.dump(data, f)

    def load_layout(self):
        from system.config import get_qvault_home
        import os, json
        state_path = os.path.join(get_qvault_home(), ".config", "desktop_state.json")
        if not os.path.exists(state_path):
            return
        try:
            with open(state_path, "r") as f:
                data = json.load(f)
            
            if not hasattr(self, "icons"): self.icons = []
            
            for icon in self.icons:
                if icon.name in data:
                    pos = data[icon.name]
                    icon.move(pos["x"], pos["y"])
        except Exception:
            pass

    def _create_icons(self):
        from components.desktop_icon import DesktopIcon
        from system.config import get_qvault_home
        from core.resources import get_asset_path
        from PyQt5.QtGui import QIcon
        home = get_qvault_home()

        from core.app_registry import REGISTRY
        items = []
        # Add system defaults (USER: Restore Home and Trash)
        items.append(("Home", home, "icons/files.svg"))
        items.append(("Trash", os.path.join(home, ".trash"), "icons/trash.svg"))
        
        # Add all registered apps (USER: system apps = neon, others = professional)
        for app in REGISTRY.all_apps:
            if app.show_on_desktop:
                items.append((app.name, app.module, app.icon_asset or "icons/prediction.svg"))

        # Grid Configuration (Horizontal First, shifted for sidebar)
        x, y = 80, 80 # Padding from edges (sidebar is 60px)
        col_width = 110
        row_height = 110
        max_cols = (self.width() - 150) // col_width
        
        for i, (name, path, icon_asset) in enumerate(items):
            icon = QIcon(get_asset_path(icon_asset))
            widget = DesktopIcon(name, icon, parent=self.workspace)
            widget.lower() # Keep icons behind windows
            
            # Grid Calculation (Fill rows first)
            col = i % max_cols
            row = i // max_cols
            
            widget.setFixedSize(100, 100) # Uniform size
            widget.move(x + (col * col_width), y + (row * row_height))
            widget.show()
            self.icons.append(widget)

    def set_user(self, username):
        """Sets the user and triggers onboarding if needed."""
        # v2.0: Taskbar/System Hubs handle user display via Controller
        logger.info(f"[Desktop] Session active for user: {username}")
        
        # Trigger Onboarding (v2.6) ONLY on first run
        from system.config import is_first_run, mark_first_run_complete
        if is_first_run():
            from components.onboarding_flow import OnboardingFlow
            self.onboarding = OnboardingFlow(self)
            self.onboarding.show_centered(self.rect())
            mark_first_run_complete()

    def contextMenuEvent(self, event):
        """Right-click menu for Desktop."""
        from PyQt5.QtWidgets import QMenu, QAction
        from PyQt5.QtGui import QCursor
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: rgba(10, 15, 25, 0.95);
                border: 1px solid rgba(0, 230, 255, 0.3);
                border-radius: 8px;
                padding: 5px;
                color: white;
            }}
            QMenu::item {{
                padding: 8px 25px 8px 10px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: rgba(0, 230, 255, 0.15);
                color: {THEME['primary_glow']};
            }}
        """)
        
        refresh_act = QAction("Refresh Desktop", self)
        refresh_act.triggered.connect(self._create_icons)
        
        wallpaper_act = QAction("Change Wallpaper", self)
        wallpaper_act.triggered.connect(lambda: self.launch_app("Settings"))
        
        monitor_act = QAction("System Monitor", self)
        monitor_act.triggered.connect(lambda: self.launch_app("System Monitor"))
        
        settings_act = QAction("Global Settings", self)
        settings_act.triggered.connect(lambda: self.launch_app("Settings"))
        
        menu.addAction(refresh_act)
        menu.addSeparator()
        menu.addAction(wallpaper_act)
        menu.addAction(monitor_act)
        menu.addAction(settings_act)
        
        menu.exec_(QCursor.pos())

    def launch_app(self, name: str):
        """Unified entry point for launching any registered application as a window."""
        from components.os_window import OSWindow
        from core.app_registry import REGISTRY
        from system.app_factory import create_app_by_name

        wm = get_window_manager()
        workspace = self.workspace

        # Check if already open (Singleton-ish behavior for core apps)
        existing = wm.find_by_title(name)
        if existing:
            wm.focus_window(existing.window_id)
            return

        # Instantiate from factory
        widget = create_app_by_name(name, parent=workspace)
        if widget is None:
            return

        # Create window frame
        win_id = str(uuid.uuid4())
        window = OSWindow(win_id, name, widget, parent=workspace)
        
        # ── Smart Sizing & Placement ──
        window.resize(720, 480) 
        
        # Staggered Placement: Prevent perfect stacking
        count = len(wm._windows)
        offset_x = 40 + (count % 6) * 40
        offset_y = 40 + (count % 6) * 40
        window.move(offset_x, offset_y)
        
        # Sync SecureAPI instance_id if available
        if hasattr(widget, "secure_api") and widget.secure_api is not None:
            widget.secure_api.instance_id = win_id

        wm.register_window(window)
        window.show() # Safe to show now that registration is complete
        return window

    def _open_file_manager(self):
        self.launch_app("Files")

    def _open_trash(self):
        from system.config import get_qvault_home
        trash_dir = os.path.join(get_qvault_home(), ".trash")
        os.makedirs(trash_dir, exist_ok=True)

        win = self.launch_app("Files")
        if win:
            win.setWindowTitle("Trash")
            # The widget inside is RealFileExplorer
            try:
                win.content_widget._navigate_to(trash_dir)
            except Exception:
                pass

    def _launch_terminal(self):
        from system.config import get_qvault_home
        self._launch_terminal_at(get_qvault_home())

    def _launch_terminal_at(self, path):
        win = self.launch_app("Terminal")
        if win:
            term = win.content_widget
            try:
                term.engine.cwd = Path(path).resolve()
                term.output.clear()
                term.output.insertPlainText("Q-Vault OS Terminal v1.0\nSecure Sandbox Enabled.\n")
                term._write_prompt()
            except Exception:
                pass

    def _on_taskbar_shortcut(self, name: str):
        """Handle quick-launch shortcuts from the taskbar."""
        if name == "terminal":
            self._launch_terminal()
        elif name == "files":
            self._open_file_manager()

    def _desktop_menu(self, pos):
        from PyQt5.QtWidgets import QMenu, QAction
        from PyQt5.QtGui import QIcon
        from system.config import get_qvault_home
        from core.resources import get_asset_path

        menu = QMenu(self)

        ac_refresh = QAction(QIcon(get_asset_path("icons/menu-refresh.svg")), "Refresh", self)
        menu.addAction(ac_refresh)
        menu.addSeparator()

        ac_folder = QAction(QIcon(get_asset_path("icons/menu-new-folder.svg")), "New Folder", self)
        ac_file = QAction(QIcon(get_asset_path("icons/menu-new-file.svg")), "New Document", self)
        menu.addAction(ac_folder)
        menu.addAction(ac_file)

        menu.addSeparator()
        ac_paste = QAction(QIcon(get_asset_path("icons/menu-paste.svg")), "Paste", self)
        menu.addAction(ac_paste)

        menu.addSeparator()
        ac_term = QAction(QIcon(get_asset_path("icons/menu-terminal.svg")), "Open Terminal Here", self)
        menu.addAction(ac_term)

        menu.addSeparator()
        ac_props = QAction(QIcon(get_asset_path("icons/menu-properties.svg")), "Properties", self)
        menu.addAction(ac_props)

        action = menu.exec_(self.mapToGlobal(pos))
        if not action:
            return

        base = os.path.join(get_qvault_home(), "Desktop")
        os.makedirs(base, exist_ok=True)

        if action == ac_folder:
            os.makedirs(os.path.join(base, "New Folder"), exist_ok=True)
            self.update()
        elif action == ac_file:
            open(os.path.join(base, "new_file.txt"), "w").close()
            self.update()
        elif action == ac_term:
            self._launch_terminal_at(base)
        elif action == ac_refresh:
            self.update()
        elif action == ac_paste:
            # Paste the system clipboard text as a .txt file on the Desktop.
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                import time as _t
                fname = f"pasted_{int(_t.time())}.txt"
                dest = os.path.join(base, fname)
                try:
                    with open(dest, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    self.update()
                except OSError as exc:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Desktop: paste failed — %s", exc
                    )
        elif action == ac_props:
            # Show a simple properties dialog for the Desktop folder.
            from PyQt5.QtWidgets import QMessageBox
            try:
                stat = os.stat(base)
                size_mb = sum(
                    os.path.getsize(os.path.join(r, f))
                    for r, _, files in os.walk(base)
                    for f in files
                ) / (1024 * 1024)
                msg = (
                    f"<b>Desktop</b><br>"
                    f"Path: <code>{base}</code><br>"
                    f"Size: {size_mb:.2f} MB<br>"
                    f"Items: {len(os.listdir(base))}"
                )
            except OSError:
                msg = f"<b>Desktop</b><br>Path: <code>{base}</code>"

            dlg = QMessageBox(self)
            dlg.setWindowTitle("Properties")
            dlg.setTextFormat(1)   # RichText
            dlg.setText(msg)
            dlg.exec_()


    # ───── MOUSE SELECTION BOX ─────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.selection_rect = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.selection_rect = (self.start_pos, event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.selection_rect:
            start, end = self.selection_rect
            rect = QRect(start, end).normalized()

            for icon in self.icons:
                icon_rect = icon.geometry()
                mapped_top_left = icon.parent().mapTo(self, icon_rect.topLeft())
                mapped_rect = QRect(mapped_top_left, icon_rect.size())
                
                if rect.intersects(mapped_rect):
                    icon.set_selected(True)
                else:
                    icon.set_selected(False)

        self.start_pos = None
        self.selection_rect = None
        self.update()



    # ───── GLOBAL KEY EVENTS ─────
    def keyPressEvent(self, event):
        # v1.3.2 Interaction Consistency: Launcher takes priority
        if self.launcher.isVisible():
            super().keyPressEvent(event)
            return

        from system.window_manager import get_window_manager
        wm = get_window_manager()

        if event.key() == Qt.Key_Tab and event.modifiers() & Qt.AltModifier:
            wm.cycle_windows()
            
        elif event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            self.toggle_launcher()

        elif event.key() == Qt.Key_1 and event.modifiers() & Qt.ControlModifier:
            wm.switch_workspace(0)

        elif event.key() == Qt.Key_2 and event.modifiers() & Qt.ControlModifier:
            wm.switch_workspace(1)
            
        super().keyPressEvent(event)
