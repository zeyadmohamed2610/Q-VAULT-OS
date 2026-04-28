from PyQt5.QtCore import QObject, QThread, pyqtSignal
from system.security_api import get_security_api


class LoginWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            api = get_security_api()
            result = api.login(self.username, self.password)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(
                {"success": False, "code": "UNKNOWN_ERROR", "message": str(e)}
            )


class SecurityController(QObject):
    _instance = None
    _initialized = False

    login_success = pyqtSignal(str, str)  # token, username
    login_failed = pyqtSignal(dict)
    session_expired = pyqtSignal()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SecurityController._initialized:
            return
        super().__init__()
        SecurityController._initialized = True
        self._thread = None
        self._worker = None
        self._last_username = None  # Race-safe: cached before worker runs

    def attempt_login(self, username, password):
        # Defensive check for deleted C++ objects (common in PyQt)
        try:
            if self._thread and self._thread.isRunning():
                return
        except RuntimeError:
            self._thread = None

        self._last_username = username  # Cache BEFORE any async work
        self._thread = QThread()
        self._worker = LoginWorker(username, password)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_login_finished)
        self._worker.finished.connect(self._thread.quit)
        
        # Defer worker deletion until the thread has fully finished
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda: setattr(self, "_thread", None))

        self._thread.start()

    def _on_login_finished(self, result: dict):
        if result.get("success"):
            token = result.get("token", "active_session_token")
            # Use cached username — never touch _worker here (may be deleted)
            username = result.get("username") or self._last_username
            self.login_success.emit(token, username)
        else:
            if result.get("code") == "SESSION_EXPIRED":
                self.session_expired.emit()
            else:
                self.login_failed.emit(result)

    def logout(self):
        try:
            api = get_security_api()
            api.logout()
        except BaseException:
            pass


def get_security_controller() -> SecurityController:
    return SecurityController()
