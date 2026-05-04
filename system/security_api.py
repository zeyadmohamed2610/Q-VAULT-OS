import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from system.ui_adapter import safe_call

logger = logging.getLogger(__name__)

# Try to load the trusted Rust core.
# We inject the local binary path to ensure it's picked up before any global site-packages.
import pathlib as _pathlib
_bin_dir = str(_pathlib.Path(__file__).resolve().parent.parent / "core" / "binaries")
if _bin_dir not in sys.path:
    sys.path.insert(0, _bin_dir)

try:
    import qvault_core
    logger.info(f"SecurityAPI: Successfully loaded Rust core from {_bin_dir}")
except ImportError as e:
    print(f"\nCRITICAL: Rust security core not available — system cannot start", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    sys.exit(1)


class SecurityAPI:
    """
    Singleton gateway defining a strict API boundary to Rust.
    """
    _instance = None
    _rust_engine = None
    _token = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._rust_engine is not None:
            return
            
        root_dir = str(Path.home() / ".qvault")
        try:
            self._rust_engine = qvault_core.SecurityEngine(root_dir)
            logger.info("SecurityAPI: Initialized strictly with Rust SecurityEngine.")
        except Exception as e:
            logger.critical(f"Failed to initialize Rust SecurityEngine: {e}")
            sys.exit(1)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Call Rust to authenticate; receive session UUID on success."""
        result = safe_call(self._rust_engine.login, username, password)
        if result["success"]:
            self._token = result["value"]
            # Sync to system state for purely UI logic to know the active session
            try:
                from core.system_state import STATE
                STATE.current_user = username
                STATE.session_type = "secure"
            except Exception:
                pass
            return {"success": True, "message": "Login accepted", "user": username}
        else:
            logger.warning(f"Login failed: {result.get('code')}")
            return result

    def verify_password(self, username: str, password: str) -> bool:
        """
        Verify credentials via Rust WITHOUT changing the current session token or state.
        Used for elevation (SUDO) prompts.
        """
        try:
            result = safe_call(self._rust_engine.login, username, password)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"SecurityAPI: verify_password error: {e}")
            return False

    def logout(self) -> None:
        """Call Rust to invalidate the session token."""
        if self._token:
            try:
                self._rust_engine.logout(self._token)
            except Exception:
                pass
            self._token = None
            
        try:
            from core.system_state import STATE
            STATE.current_user = None
            STATE.session_type = "none"
        except Exception:
            pass

    def create_user(self, username: str, password: str, role: str) -> Dict[str, Any]:
        """Delegate user creation to Rust (requires valid token & Admin rights)."""
        if not self._token:
            return {"success": False, "code": "NO_SESSION", "message": "No active session"}
            
        return safe_call(self._rust_engine.create_user, self._token, username, password, role)

    def store_secret(self, key: str, value: str) -> Dict[str, Any]:
        if not self._token:
            return {"success": False, "code": "NO_SESSION", "message": "No active session"}
            
        return safe_call(self._rust_engine.store_secret, self._token, key, value)

    def get_secret(self, key: str) -> Dict[str, Any]:
        if not self._token:
            return {"success": False, "code": "NO_SESSION", "message": "No active session", "value": None}
            
        res = safe_call(self._rust_engine.get_secret, self._token, key)
        if res.get("success") and res.get("value") is None:
            res["success"] = False
            res["code"] = "NOT_FOUND"
            res["message"] = "Secret not found"
        return res

    def list_secrets(self) -> list:
        if not self._token:
            return []
            
        res = safe_call(self._rust_engine.list_secrets, self._token)
        return res.get("value", []) if res.get("success") else []

    def hash_data(self, data: bytes) -> Dict[str, Any]:
        res = safe_call(self._rust_engine.hash_data, data)
        if res.get("success"):
            return {"success": True, "hash": bytes(res["value"]).hex()}
        return res

    def get_status(self) -> Dict[str, Any]:
        """Provides a simple static status since all checks are pushed to Rust."""
        return {
            "mode": "SECURE",
            "rust_available": True, 
            "enforcement": True,
        }

    # ── SECURITY EVENTS & RISK (Ported from legacy security_system) ──

    # Event constants
    EVT_INTRUSION = "INTRUSION_DETECTED"
    EVT_BUTTON    = "BUTTON_PRESSED"
    EVT_LOGIN     = "LOGIN_ATTEMPT"
    EVT_PROCESS   = "SUSPICIOUS_PROCESS"
    EVT_MANUAL    = "MANUAL_ALERT"
    EVT_CLEARED   = "RISK_CLEARED"
    EVT_CRITICAL  = "CRITICAL_SYSTEM_EVENT"

    # Risk level constants
    RISK_LOW    = "LOW"
    RISK_MEDIUM = "MEDIUM"
    RISK_HIGH   = "HIGH"
    
    _RISK_ORDER = [RISK_LOW, RISK_MEDIUM, RISK_HIGH]
    
    # UI Color mapping (cached for UI stability)
    RISK_COLORS = {
        "LOW":    "#00ff88",
        "MEDIUM": "#ffaa00",
        "HIGH":   "#ff4444",
    }

    def _init_security_state(self):
        self._risk_level = self.RISK_LOW
        self._observers = []
        self._log = []

    def subscribe(self, cb):
        """Observer pattern for security events."""
        if not hasattr(self, "_observers"): self._init_security_state()
        if cb not in self._observers:
            self._observers.append(cb)

    def unsubscribe(self, cb):
        if hasattr(self, "_observers"):
            self._observers = [o for o in self._observers if o is not cb]

    def _notify(self, entry: Dict[str, Any]):
        if hasattr(self, "_observers"):
            for cb in self._observers:
                try: cb(entry)
                except Exception: pass

    @property
    def risk_level(self) -> str:
        if not hasattr(self, "_risk_level"): self._init_security_state()
        return self._risk_level

    def report(self, event_type: str, source: str = "system", detail: str = "", escalate: bool = True) -> Dict[str, Any]:
        """
        Log a security event directly and escalate risk.
        In the future, this will initiate a Rust-side signed audit log.
        """
        if not hasattr(self, "_risk_level"): self._init_security_state()
        
        if escalate and event_type not in (self.EVT_BUTTON, self.EVT_CLEARED):
            self._escalate()

        import time
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "source": source,
            "detail": detail,
            "risk_after": self._risk_level,
        }
        self._log.append(entry)
        
        # Log to Rust core if initialized
        if self._rust_engine:
            try:
                # Internal rust logging doesn't have a direct python export for general events,
                # but we can trigger it through other secure ops in the future.
                # For now, we rely on the Python-side log for the UI components.
                pass
            except Exception:
                pass
                
        self._notify(entry)
        return entry

    def _escalate(self):
        idx = self._RISK_ORDER.index(self._risk_level)
        if idx < len(self._RISK_ORDER) - 1:
            self._risk_level = self._RISK_ORDER[idx + 1]

    def clear_risk(self):
        """Reset risk level to LOW."""
        if not hasattr(self, "_risk_level"): self._init_security_state()
        self._risk_level = self.RISK_LOW
        entry = self.report(self.EVT_CLEARED, source="operator", detail="Manual risk reset", escalate=False)
        return entry

    def get_log(self, limit: int = 100) -> list:
        if not hasattr(self, "_log"): self._init_security_state()
        return self._log[-limit:]

    # Shim functions for UI compatibility that no longer exist securely
    def is_secure_mode(self) -> bool:
        return True

    def is_lockdown(self) -> bool:
        return self.risk_level == self.RISK_HIGH

# Singleton
_api: Optional[SecurityAPI] = None

def get_security_api() -> SecurityAPI:
    global _api
    if _api is None:
        _api = SecurityAPI()
    return _api

# Public exports
def login(u: str, p: str): return get_security_api().login(u, p)
def logout(): return get_security_api().logout()
def create_user(u: str, p: str, r: str): return get_security_api().create_user(u, p, r)
def store_secret(k: str, v: str): return get_security_api().store_secret(k, v)
def get_secret(k: str): return get_security_api().get_secret(k)
def list_secrets(): return get_security_api().list_secrets()
def hash_data(d: bytes): return get_security_api().hash_data(d)
def get_status(): return get_security_api().get_status()
def init_security(): return get_security_api().get_status()
