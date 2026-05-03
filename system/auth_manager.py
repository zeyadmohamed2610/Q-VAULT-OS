import logging
import time
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
        self._session_token: str | None = None
        self._last_activity: float = time.time()

        # ── Session timeout config ───────────────────────────────
        self.IDLE_LIMIT = 300       # 5 minutes
        self.DIM_WARN   = 30        # start dimming 30s before lock
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(1000)
        self._idle_timer.timeout.connect(self._check_idle)

        # ── Wire to SecurityController ───────────────────────────
        self._sc = get_security_controller()
        self._sc.login_success.connect(self._on_login_success)
        self._sc.login_failed.connect(self._on_login_failed)
        self._sc.session_expired.connect(self._on_session_expired)

        logger.info("[AuthManager] Initialized. State: LOGGED_OUT")

    # ── Read-only properties ─────────────────────────────────────

    @property
    def state(self) -> AuthState:
        return self._state

    @property
    def username(self) -> str | None:
        return self._username

    @property
    def session_token(self) -> str | None:
        return self._session_token

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
        """Called by Desktop idle timer or user action."""
        if self._state != AuthState.LOGGED_IN:
            logger.warning(f"[AuthManager] Ignoring lock request — state is {self._state.value}.")
            return

        self._idle_timer.stop()
        self._set_state(AuthState.LOCKED)

    def request_logout(self) -> None:
        """Called by Taskbar logout. Full session teardown."""
        if self._state in (AuthState.LOGGED_OUT, AuthState.AUTHENTICATING):
            return

        self._idle_timer.stop()
        self._sc.logout()
        self._username = None
        self._session_token = None
        self._set_state(AuthState.LOGGED_OUT)

    def report_activity(self) -> None:
        """Called by Desktop on any user interaction to reset idle timer."""
        self._last_activity = time.time()

    # ── Internal callbacks from SecurityController ───────────────

    def _on_login_success(self, token: str, username: str):
        self._session_token = token
        self._username = username
        self._last_activity = time.time()
        self._set_state(AuthState.LOGGED_IN)
        self._idle_timer.start()
        
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
        self._idle_timer.stop()
        self._session_token = None
        self._username = None
        self._set_state(AuthState.LOGGED_OUT)
        logger.warning("[AuthManager] Session expired — forced logout.")

    # ── Session timeout (moved from desktop.py) ──────────────────

    def _check_idle(self):
        if self._state != AuthState.LOGGED_IN:
            return

        elapsed = time.time() - self._last_activity

        if elapsed >= self.IDLE_LIMIT:
            logger.info("[AuthManager] Idle timeout reached — locking session.")
            self.request_lock()
        elif elapsed >= (self.IDLE_LIMIT - self.DIM_WARN):
            progress = (elapsed - (self.IDLE_LIMIT - self.DIM_WARN)) / self.DIM_WARN
            EVENT_BUS.emit(SystemEvent.USER_IDLE, {
                "dim_progress": round(progress, 2),
                "seconds_remaining": int(self.IDLE_LIMIT - elapsed)
            }, source="AuthManager")

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


# ── Singleton accessor ───────────────────────────────────────────
def get_auth_manager() -> AuthManager:
    return AuthManager()
