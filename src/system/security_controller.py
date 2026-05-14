import threading
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


class UserProvisionWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, username, password, role="user"):
        super().__init__()
        self.username = username
        self.password = password
        self.role = role

    def run(self):
        try:
            api = get_security_api()
            result = api.create_user(self.username, self.password, self.role)
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
    provision_finished = pyqtSignal(dict)

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
        self._last_username = None 

    def attempt_login(self, username, password):
        try:
            if self._thread and self._thread.isRunning():
                return
        except RuntimeError:
            self._thread = None

        self._last_username = username
        self._thread = QThread()
        self._worker = LoginWorker(username, password)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_login_finished)
        self._worker.finished.connect(self._thread.quit)
        
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(lambda: setattr(self, "_thread", None))

        self._thread.start()

    def _on_login_finished(self, result: dict):
        if result.get("success"):
            token = result.get("token", "active_session_token")
            username = result.get("username") or self._last_username
            self.login_success.emit(token, username)
        else:
            if result.get("code") == "SESSION_EXPIRED":
                self.session_expired.emit()
            else:
                self.login_failed.emit(result)

    def provision_user(self, username, password, role="user"):
        """Asynchronously provision a new identity."""
        self._prov_thread = QThread()
        self._prov_worker = UserProvisionWorker(username, password, role)
        self._prov_worker.moveToThread(self._prov_thread)

        self._prov_thread.started.connect(self._prov_worker.run)
        self._prov_worker.finished.connect(self.provision_finished.emit)
        self._prov_worker.finished.connect(self._prov_thread.quit)
        
        self._prov_thread.finished.connect(self._prov_worker.deleteLater)
        self._prov_thread.finished.connect(self._prov_thread.deleteLater)
        self._prov_thread.start()

    def logout(self):
        try:
            api = get_security_api()
            api.logout()
        except BaseException:
            pass


_SECURITY_CONTROLLER_INSTANCE = None
_SECURITY_LOCK = threading.Lock()

def get_security_controller() -> SecurityController:
    global _SECURITY_CONTROLLER_INSTANCE
    if _SECURITY_CONTROLLER_INSTANCE is None:
        with _SECURITY_LOCK:
            if _SECURITY_CONTROLLER_INSTANCE is None:
                from PyQt5.QtWidgets import QApplication
                if not QApplication.instance():
                    return None
                _SECURITY_CONTROLLER_INSTANCE = SecurityController()
    return _SECURITY_CONTROLLER_INSTANCE
