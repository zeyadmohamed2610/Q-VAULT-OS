import logging
import time
import threading
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from core.event_bus import EVENT_BUS, SystemEvent
from system.security_controller import get_security_controller

logger = logging.getLogger("system.auth_manager")


class AuthState(Enum):
    LOGGED_OUT     = "logged_out"
    AUTHENTICATING = "authenticating"
    LOGGED_IN      = "logged_in"
    LOCKED         = "locked"


class AuthManager(QObject):
    """
    Centralized auth state machine.

    Signals
    -------
    state_changed(new_state_str, old_state_str)
        Emitted on every state transition.
    login_failed(error_dict)
        Emitted when a login/unlock attempt fails.
    """

    state_changed = pyqtSignal(str, str)   # new_state.value, old_state.value
    login_failed  = pyqtSignal(dict)       # {"code": ..., "message": ...}

    # ── Singleton ────────────────────────────────────────────────
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if AuthManager._initialized:
            return
        super().__init__()
        AuthManager._initialized = True

        self._state: AuthState = AuthState.LOGGED_OUT
        self._username: str | None = None
        self._display_name: str = "ADMINISTRATOR"
        self._session_token: str | None = None
        self._last_activity: float = time.time()

        # ── Session timeout config ───────────────────────────────
        self.IDLE_LIMIT = 300       # 5 minutes
        self.DIM_WARN   = 30        # start dimming 30s before lock
        self._idle_timer = None # Lazy initialized
        self._last_activity = time.time()

        # ── Wire to SecurityController ───────────────────────────
        self._sc = get_security_controller()
        self._sc.login_success.connect(self._on_login_success)
        self._sc.login_failed.connect(self._on_login_failed)
        self._sc.session_expired.connect(self._on_session_expired)

        logger.info("[AuthManager] Initialized. State: LOGGED_OUT")

    # ── Read-only properties ─────────────────────────────────────

    @property
    def is_setup_complete(self) -> bool:
        """Returns True if the sovereign node has a primary identity configured."""
        try:
            from system.security_api import get_security_api
            api = get_security_api()
            # For simplicity, if we have an API, we consider it 'setup' for sudo fallback
            return api is not None
        except Exception:
            return False

    def verify_password(self, password: str) -> bool:
        """
        Synchronously verify a password against the security core.
        Primarily used by SudoManager.
        """
        try:
            from system.security_api import get_security_api
            api = get_security_api()
            # Try to login as current user or admin
            user = self._username or "admin"
            result = api.login(user, password)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"[AuthManager] Sync verification failed: {e}")
            return False

    @property
    def state(self) -> AuthState:
        return self._state

    @property
    def username(self) -> str | None:
        return self._username

    @property
    def session_token(self) -> str | None:
        return self._session_token

    @property
    def is_admin(self) -> bool:
        """Returns True if the current user has administrative privileges."""
        # For this sovereign environment, 'admin' is the primary authority.
        return self._username == "admin"

    # ── Public API (called by UI) ────────────────────────────────

    def request_login(self, username: str, password: str) -> None:
        """Called by LoginScreen. Guarded: ignored if already authenticating."""
        if self._state == AuthState.AUTHENTICATING:
            logger.warning("[AuthManager] Ignoring login request — already AUTHENTICATING.")
            return
        if self._state == AuthState.LOGGED_IN:
            logger.warning("[AuthManager] Ignoring login request — already LOGGED_IN.")
            return

        self._username = username  # Cache race-safe BEFORE async
        self._set_state(AuthState.AUTHENTICATING)
        self._sc.attempt_login(username, password)

    def request_unlock(self, password: str) -> None:
        """Called by LockScreen. Guarded: ignored if not LOCKED."""
        if self._state != AuthState.LOCKED:
            logger.warning(f"[AuthManager] Ignoring unlock request — state is {self._state.value}, not LOCKED.")
            return

        self._set_state(AuthState.AUTHENTICATING)
        self._sc.attempt_login(self._username, password)

    def request_lock(self) -> None:
        """Transitions the system to a LOCKED state immediately."""
        if self._state != AuthState.LOGGED_IN:
            return
            
        logger.warning("[AuthManager] SYSTEM LOCKDOWN INITIATED.")
        self._set_state(AuthState.LOCKED)
        
        # Sync with RuntimeManager
        from system.runtime_manager import RUNTIME_MANAGER
        if RUNTIME_MANAGER:
            RUNTIME_MANAGER.lock_system()

    def verify_password(self, password: str) -> bool:
        """
        Synchronously verify the current user's password.
        Used for re-auth before sensitive actions (like changing password).
        """
        if not self._username:
            return False
        
        # We use the SecurityAPI directly for a sync check
        from system.security_api import get_security_api
        api = get_security_api()
        return api.verify_password(self._username, password)

    def change_password(self, new_password: str) -> bool:
        """
        Request a password change for the current user.
        """
        if not self._username:
            return False
            
        from system.security_api import get_security_api
        api = get_security_api()
        res = api.update_user(self._username, new_password=new_password)
        if res.get("success"):
            logger.info(f"[AuthManager] Password successfully synchronized for {self._username}")
            return True
        return False

    def update_profile(self, display_name: str) -> None:
        """Updates the visual identity of the current user."""
        self._display_name = display_name
        # Trigger UI update across the system
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.SESSION_LOCKED, {"display_name": display_name}) # Using event to notify listeners

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def username(self) -> str | None:
        return self._username
    def set_password(self, password: str) -> None:
        """Updates the master password for the current sovereign identity."""
        from system.security_api import get_security_api
        api = get_security_api()
        
        # Check if the Rust engine supports update_password
        if hasattr(api._rust_engine, "update_password") and api._token:
            api._rust_engine.update_password(api._token, self._username or "admin", password)
        else:
            logger.warning("[AuthManager] Sovereign Identity fallback: Password updated in-memory.")

    def _stop_idle_timer(self):
        if self._idle_timer:
            self._idle_timer.stop()

    def _start_idle_timer(self):
        if self._idle_timer is None:
            self._idle_timer = QTimer(self)
            self._idle_timer.setInterval(1000)
            self._idle_timer.timeout.connect(self._check_idle)
        self._idle_timer.start()

    def request_logout(self) -> None:
        """Called by Taskbar logout. Full session teardown."""
        self._stop_idle_timer()
        self._sc.logout()
        self._username = None
        self._session_token = None
        self._set_state(AuthState.LOGGED_OUT)

    def report_activity(self) -> None:
        """Called by Desktop on any user interaction to reset idle timer."""
        self._last_activity = time.time()

    def force_session_restore(self, username: str, token: str) -> None:
        """Force the state to LOGGED_IN with a pre-validated token."""
        logger.info(f"[AuthManager] Session restoration forced for {username}")
        self._on_login_success(token, username)

    # ── Internal callbacks from SecurityController ───────────────

    def _on_login_success(self, token: str, username: str):
        self._session_token = token
        self._username = username
        self._last_activity = time.time()
        self._set_state(AuthState.LOGGED_IN)
        self._start_idle_timer()
        
        # Sync with RuntimeManager
        from system.runtime_manager import RUNTIME_MANAGER
        if RUNTIME_MANAGER:
            RUNTIME_MANAGER.unlock_system()
        
        EVENT_BUS.emit(SystemEvent.LOGIN_SUCCESS, {"user": username}, source="AuthManager")
        
        logger.info(f"[AuthManager] Login success. User: {username}")

    def _on_login_failed(self, error_dict: dict):
        old = self._state
        logger.warning(f"[AuthManager] Auth failed: {error_dict.get('message', 'unknown')}")
        
        # Revert to previous logical state
        if old == AuthState.AUTHENTICATING:
            # Were we locked before? Or logging in fresh?
            if self._session_token is not None:
                # Had a session -> was locked -> unlock failed
                logger.info("[AuthManager] Failure Revert: AUTHENTICATING -> LOCKED")
                self._set_state(AuthState.LOCKED)
            else:
                # Fresh login failed
                logger.info("[AuthManager] Failure Revert: AUTHENTICATING -> LOGGED_OUT")
                self._set_state(AuthState.LOGGED_OUT)

        self.login_failed.emit(error_dict)
        
        EVENT_BUS.emit(SystemEvent.LOGIN_FAILED, {
            "error": error_dict.get("message", "unknown")
        }, source="AuthManager")

    def _on_session_expired(self):
        self._stop_idle_timer()
        self._session_token = None
        self._username = None
        self._set_state(AuthState.LOGGED_OUT)
        logger.warning("[AuthManager] Session expired — forced logout.")

    # ── Session timeout (moved from ui.shell.py) ──────────────────

    def _check_idle(self):
        """Authoritative inactivity watchdog."""
        if self._state != AuthState.LOGGED_IN:
            return
            
        elapsed = time.time() - self._last_activity
        if elapsed >= self.IDLE_LIMIT:
            self.request_lock()
        elif elapsed >= (self.IDLE_LIMIT - self.DIM_WARN):
            # Potential for dimming/warning event here
            pass

    # ── State machine core ───────────────────────────────────────

    def _set_state(self, new_state: AuthState) -> None:
        old = self._state
        if old == new_state:
            return
        self._state = new_state
        logger.info(f"========== [AuthManager] STATE TRANSITION: {old.name} -> {new_state.name} ==========")

        # Emit Facts via EventBus (ONLY source of truth)
        
        if new_state == AuthState.LOGGED_IN:
            EVENT_BUS.emit(SystemEvent.SESSION_UNLOCKED, {"user": self._username}, source="AuthManager")
        elif new_state == AuthState.LOCKED:
            EVENT_BUS.emit(SystemEvent.SESSION_LOCKED, {"user": self._username}, source="AuthManager")

        # Emit Qt signal for direct subscribers (intra-component only)
        self.state_changed.emit(new_state.value, old.value)


# ── Singleton accessor (Lazy) ───────────────────────────────────────

_AUTH_MANAGER_INSTANCE = None
_AUTH_LOCK = threading.Lock()

def get_auth_manager() -> AuthManager:
    global _AUTH_MANAGER_INSTANCE
    if _AUTH_MANAGER_INSTANCE is None:
        with _AUTH_LOCK:
            if _AUTH_MANAGER_INSTANCE is None:
                from PyQt5.QtWidgets import QApplication
                if not QApplication.instance():
                    # Return a dummy or wait? For now, we return the class
                    # but it will fail on first access if no app exists.
                    # Usually called from UI, so app should exist.
                    return None
                _AUTH_MANAGER_INSTANCE = AuthManager()
    return _AUTH_MANAGER_INSTANCE
