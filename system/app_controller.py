import logging
from core.event_bus import EVENT_BUS, SystemEvent
from system.auth_manager import get_auth_manager
from system.window_manager import get_window_manager
from PyQt5.QtWidgets import QStackedWidget

logger = logging.getLogger(__name__)

class AppController:
    """
    Singleton screen router.
    
    This controller is PASSIVE — it does NOT manage auth state.
    It subscribes to AuthManager.state_changed and switches screens.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self._stack: QStackedWidget = None
        self._screens = {}
        self.notification_manager = None
        self.cpu_service = None
        self.ai_controller = None

    def init_gui(self, stack: QStackedWidget, screens: dict):
        self._stack = stack
        self._screens = screens
        
        # Subscribe to AuthManager AFTER gui is ready
        am = get_auth_manager()
        am.state_changed.connect(self._on_auth_state_changed)
        # UI Action Requests (Decoupled Architecture)
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_FOCUS, self._on_window_request)
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_MINIMIZE, self._on_window_request)
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_CLOSE, self._on_window_request)
        EVENT_BUS.subscribe(SystemEvent.REQ_APP_LAUNCH, self._on_app_launch_request)
        
        EVENT_BUS.subscribe(SystemEvent.ACTION_CLICKED, self._on_ui_action_clicked)
        
        self._switch_to_boot()

    # ── Auth state reactor ───────────────────────────────────────

    def _on_auth_state_changed(self, new_state: str, old_state: str):
        """Single handler for ALL auth transitions."""
        logger.info(f"[AppController] Auth state: {old_state} -> {new_state}")

        if new_state == "logged_in":
            self._switch_to_desktop()
        elif new_state == "locked":
            self._switch_to_lock()
        elif new_state == "logged_out":
            self._stop_services()
            self._close_all_windows()
            
            # Prevent signal/memory leaks: destroy lock screen on full logout
            if "lock" in self._screens:
                lock_screen = self._screens.pop("lock")
                if self._stack:
                    self._stack.removeWidget(lock_screen)
                lock_screen.deleteLater()
                
            self._switch_to_login()


    # ── Screen switching (private) ───────────────────────────────

    def _switch_to_boot(self):
        if self._stack and "boot" in self._screens:
            boot_screen = self._screens["boot"]
            if hasattr(boot_screen, "boot_finished") and not getattr(boot_screen, "_connected", False):
                boot_screen.boot_finished.connect(self._switch_to_login)
                boot_screen._connected = True
            self._stack.setCurrentWidget(boot_screen)

    def switch_to_login(self):
        """Public entry point for login navigation."""
        self._switch_to_login()

    def _switch_to_login(self):
        self._stop_services()
        if self._stack and "login" in self._screens:
            self._stack.setCurrentWidget(self._screens["login"])

    def _switch_to_desktop(self):
        am = get_auth_manager()
        username = am.username

        if self._stack and "desktop" in self._screens:
            desktop_widget = self._screens["desktop"]
            desktop_widget.set_user(username)
            self._stack.setCurrentWidget(desktop_widget)
            
            # Start dynamic services
            self._start_services(desktop_widget)
            
            # Request desktop to initialize notification container
            if hasattr(desktop_widget, "init_notification_container"):
                desktop_widget.init_notification_container()

    def _switch_to_lock(self):
        am = get_auth_manager()

        # v1.6 Context Security: Wipe session brain
        from system.runtime.launcher_intelligence import BRAIN
        BRAIN.reset_session_context()

        if self._stack and "lock" not in self._screens and "lock_class" in self._screens:
            lock_cls = self._screens["lock_class"]
            lock = lock_cls(am.username, parent=self._stack)
            self._screens["lock"] = lock
            self._stack.addWidget(lock)
            
        if self._stack:
            self._stack.setCurrentWidget(self._screens["lock"])

    # ── Services ─────────────────────────────────────────────────

    def _start_services(self, desktop_widget):
        try:
            from system.services.cpu_service import CpuService
            self.cpu_service = CpuService()
        except Exception as e:
            logger.error(f"[AppController] Failed to start CpuService: {e}")
        
        # v2.2 AI Intelligence Layer
        from system.ai.ai_controller import AIController
        self.ai_controller = AIController()
        
        # v2.5 Automation & Workflows
        from system.automation.workflow_engine import WORKFLOW_ENGINE
        self._init_default_workflows(WORKFLOW_ENGINE)
        
        # v2.7 Ecosystem & Marketplace
        from system.marketplace.plugin_registry import PLUGIN_REGISTRY
        PLUGIN_REGISTRY.scan_plugins()
        # self.cpu_service.cpu_updated.connect(desktop_widget.top_panel.update_cpu)

    def _init_default_workflows(self, engine):
        """Registers the initial set of system automations."""
        # 1. Error Guardian Workflow
        engine.register_workflow({
            "name": "system_error_guardian",
            "trigger": SystemEvent.EVT_ERROR.value,
            "actions": [
                {"action": "notify", "params": {"title": "Guardian Alert", "message": "System anomaly detected.", "level": "error"}}
            ]
        })
        
        # 2. Welcome Workflow
        engine.register_workflow({
            "name": "welcome_sequence",
            "trigger": SystemEvent.EVT_WELCOME.value, # Manual trigger
            "actions": [
                {"action": "notify", "params": {"title": "Q-Vault OS", "message": "System ready. Welcome back."}},
                {"action": "launch", "params": {"app": "Files"}}
            ]
        })

    def _stop_services(self):
        if self.cpu_service:
            self.cpu_service.timer.stop()
            self.cpu_service.deleteLater()
            self.cpu_service = None

    def _close_all_windows(self):
        try:
            get_window_manager().close_all()
        except Exception:
            pass

    # ── UI Action Handlers ──────────────────────────────────────
    
    def _on_window_request(self, payload):
        """Unified command handler for window lifecycle requests."""
        wid = payload.data.get("id")
        if not wid: return
        
        wm = get_window_manager()
        
        event_type = payload.type
        logger.info(f"[AppController] Executing command: {event_type.name} for {wid}")
        
        if event_type == SystemEvent.REQ_WINDOW_FOCUS:
            # If the window is minimized, restore it (triggers WINDOW_RESTORED animation)
            window = wm._windows.get(wid)
            if window and getattr(window, "is_minimized", False):
                wm.restore_window(wid)
            else:
                wm.focus_window(wid)
        elif event_type == SystemEvent.REQ_WINDOW_MINIMIZE:
            wm.minimize_window(wid)
        elif event_type == SystemEvent.REQ_WINDOW_CLOSE:
            wm.close_window(wid)

    def _on_app_launch_request(self, payload):
        """Handle global requests to spawn applications."""
        name = payload.data.get("name")
        if not name: return
        
        # Dispatch to desktop if available
        if self._stack and "desktop" in self._screens:
            desktop = self._screens["desktop"]
            if hasattr(desktop, "launch_app"):
                desktop.launch_app(name)

    def launch_app(self, name: str):
        """Public API for launching apps from anywhere in the OS."""
        logger.info(f"[AppController] Requesting launch: {name}")
        if self._stack and "desktop" in self._screens:
            self._screens["desktop"].launch_app(name)

    def _on_ui_action_clicked(self, payload):
        """Handle global actions like @launcher toggle."""
        command = payload.data.get("command")
        if command == "@launcher":
            # Find the desktop widget and toggle launcher
            if self._stack and "desktop" in self._screens:
                desktop = self._screens["desktop"]
                if hasattr(desktop, "toggle_launcher"):
                    desktop.toggle_launcher()


def get_app_controller() -> AppController:
    return AppController()
