# =============================================================
#  license_manager.py — Q-VAULT OS  |  Licensing System
#
#  Features:
#    - License key generation & validation
#    - Supabase integration
#    - Device binding (HWID)
#    - Offline grace period
#    - Feature gating
# =============================================================

import os
import uuid
import json
import hashlib
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from dataclasses import dataclass

try:
    import wmi
    import win32api

    HAS_WINDOWS = True
except Exception:
    HAS_WINDOWS = False

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

LICENSE_DIR = Path.home() / ".qvault" / "license"
LICENSE_FILE = LICENSE_DIR / "license.json"
LICENSE_KEY_FILE = LICENSE_DIR / "key.lic"


class LicensePlan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class LicenseStatus(Enum):
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    TRIAL = "trial"
    OFFLINE = "offline"


@dataclass
class LicenseInfo:
    plan: str
    status: str
    expires_at: Optional[str]
    device_id: str
    features: Dict[str, bool]
    last_validation: Optional[str]
    is_trial: bool = False


class LicenseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._license_info: Optional[LicenseInfo] = None
        self._offline_until: Optional[datetime] = None
        self._grace_period_days = 7
        self._last_online_check = 0
        self._validation_interval = 3600

        self._ensure_license_dir()
        self._load_license()

    def _ensure_license_dir(self):
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_device_id(self) -> str:
        if HAS_WINDOWS:
            try:
                c = wmi.WMI()
                for bios in c.Win32_BIOS():
                    return hashlib.sha256(bios.SerialNumber.encode()).hexdigest()[:16]
            except Exception:
                pass

        fallback = f"{os.getlogin()}-{os.getcwd()}"
        return hashlib.sha256(fallback.encode()).hexdigest()[:16]

    def _generate_license_key(self, plan: str, days: int = 365) -> str:
        prefix = {"free": "QVFREE", "pro": "QVPRO", "enterprise": "QVEnt"}.get(
            plan, "QV"
        )

        unique = f"{plan}-{uuid.uuid4().hex[:12]}-{int(time.time())}"
        key_hash = hashlib.sha256(unique.encode()).hexdigest()[:16]
        return f"{prefix}-{key_hash.upper()}"

    def _load_license(self):
        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE, "r") as f:
                    data = json.load(f)
                    self._license_info = LicenseInfo(
                        plan=data.get("plan", "free"),
                        status=data.get("status", "invalid"),
                        expires_at=data.get("expires_at"),
                        device_id=data.get("device_id", ""),
                        features=data.get(
                            "features", self._get_default_features("free")
                        ),
                        last_validation=data.get("last_validation"),
                        is_trial=data.get("is_trial", False),
                    )
            except Exception:
                self._license_info = self._get_default_license()

    def _save_license(self):
        if not self._license_info:
            return

        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        encrypted = self._encrypt_license(
            {
                "plan": self._license_info.plan,
                "status": self._license_info.status,
                "expires_at": self._license_info.expires_at,
                "device_id": self._license_info.device_id,
                "features": self._license_info.features,
                "last_validation": self._license_info.last_validation,
                "is_trial": self._license_info.is_trial,
            }
        )

        with open(LICENSE_FILE, "w") as f:
            json.dump(encrypted, f, indent=2)

    def _encrypt_license(self, data: Dict) -> Dict:
        device_id = self._get_device_id()
        key = hashlib.sha256(device_id.encode()).digest()[:16]

        import base64

        json_str = json.dumps(data)
        encrypted = []
        for i, char in enumerate(json_str):
            encrypted.append(chr((ord(char) + ord(key[i % len(key)])) % 256))

        return {
            "data": base64.b64encode("".join(encrypted).encode()).decode(),
            "version": "1.0",
        }

    def _decrypt_license(self, data: Dict) -> Optional[Dict]:
        try:
            import base64

            encrypted = base64.b64decode(data["data"].encode()).decode()
            device_id = self._get_device_id()
            key = hashlib.sha256(device_id.encode()).digest()[:16]

            decrypted = []
            for i, char in enumerate(encrypted):
                decrypted.append(chr((ord(char) - ord(key[i % len(key)])) % 256))

            return json.loads("".join(decrypted))
        except Exception:
            return None

    def _get_default_features(self, plan: str) -> Dict[str, bool]:
        features = {
            "basic_os": True,
            "terminal": True,
            "file_explorer": True,
            "security_dashboard_basic": True,
            "local_encryption": True,
            "offline_mode": True,
            "package_manager": True,
            "security_dashboard_advanced": plan in ["pro", "enterprise"],
            "telemetry_dashboard": plan in ["pro", "enterprise"],
            "cloud_sync": plan in ["pro", "enterprise"],
            "multi_user": plan == "enterprise",
            "enterprise_support": plan == "enterprise",
            "plugin_api": plan in ["pro", "enterprise"],
            "priority_updates": plan in ["pro", "enterprise"],
        }
        return features

    def _get_default_license(self) -> LicenseInfo:
        return LicenseInfo(
            plan="free",
            status="valid",
            expires_at=None,
            device_id=self._get_device_id(),
            features=self._get_default_features("free"),
            last_validation=datetime.now().isoformat(),
            is_trial=False,
        )

    def has_feature(self, feature: str) -> bool:
        if not self._license_info:
            self._license_info = self._get_default_license()

        return self._license_info.features.get(feature, False)

    def get_plan(self) -> str:
        if not self._license_info:
            self._license_info = self._get_default_license()
        return self._license_info.plan

    def get_status(self) -> str:
        if not self._license_info:
            return "invalid"

        if self._license_info.status == "invalid":
            return "invalid"

        if self._license_info.expires_at:
            expires = datetime.fromisoformat(
                self._license_info.expires_at.replace("Z", "+00:00")
            )
            if expires < datetime.now(expires.tzinfo):
                return "expired"

        return self._license_info.status

    def get_info(self) -> LicenseInfo:
        if not self._license_info:
            self._license_info = self._get_default_license()
        return self._license_info

    def validate_license(self, force: bool = False) -> bool:
        now = time.time()
        if not force and (now - self._last_online_check) < self._validation_interval:
            return self.get_status() in ["valid", "trial"]

        self._last_online_check = now

        if not SUPABASE_KEY:
            return self._check_offline_grace_period()

        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/licenses"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            params = {
                "select": "*",
                "device_id": "eq." + self._get_device_id(),
                "status": "eq.active",
                "limit": 1,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200 and response.json():
                license_data = response.json()[0]
                self._update_license_from_server(license_data)
                self._offline_until = None
                return True

            return self._check_offline_grace_period()

        except Exception:
            return self._check_offline_grace_period()

    def _check_offline_grace_period(self) -> bool:
        if not self._offline_until:
            self._offline_until = datetime.now() + timedelta(
                days=self._grace_period_days
            )

        if datetime.now() < self._offline_until:
            if self._license_info:
                self._license_info.status = "offline"
            return True

        return False

    def _update_license_from_server(self, data: Dict):
        plan = data.get("plan", "free")
        expires_at = data.get("expires_at")

        self._license_info = LicenseInfo(
            plan=plan,
            status="valid",
            expires_at=expires_at,
            device_id=data.get("device_id", self._get_device_id()),
            features=self._get_default_features(plan),
            last_validation=datetime.now().isoformat(),
            is_trial=data.get("is_trial", False),
        )
        self._save_license()

    def activate_license(self, license_key: str) -> bool:
        if not SUPABASE_KEY:
            return self._activate_offline(license_key)

        try:
            import requests

            url = f"{SUPABASE_URL}/rest/v1/licenses"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            params = {
                "select": "*",
                "license_key": f"eq.{license_key}",
                "status": "eq.active",
                "limit": 1,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200 and response.json():
                license_data = response.json()[0]

                if (
                    license_data.get("device_id")
                    and license_data.get("device_id") != self._get_device_id()
                ):
                    return False

                device_id = self._get_device_id()
                update_url = f"{url}?license_key=eq.{license_key}"
                requests.patch(
                    update_url, headers=headers, json={"device_id": device_id}
                )

                self._update_license_from_server(license_data)
                return True

        except Exception:
            pass

        return False

    def _activate_offline(self, license_key: str) -> bool:
        parts = license_key.split("-")
        if len(parts) < 2:
            return False

        plan = parts[0].replace("QV", "").lower()
        if plan == "free":
            plan = "free"
        elif plan == "pro":
            plan = "pro"
        elif plan == "ent":
            plan = "enterprise"
        else:
            return False

        self._license_info = LicenseInfo(
            plan=plan,
            status="valid",
            expires_at=(datetime.now() + timedelta(days=365)).isoformat(),
            device_id=self._get_device_id(),
            features=self._get_default_features(plan),
            last_validation=datetime.now().isoformat(),
            is_trial=False,
        )
        self._save_license()
        return True

    def start_trial(self, days: int = 14) -> bool:
        self._license_info = LicenseInfo(
            plan="pro",
            status="trial",
            expires_at=(datetime.now() + timedelta(days=days)).isoformat(),
            device_id=self._get_device_id(),
            features=self._get_default_features("pro"),
            last_validation=datetime.now().isoformat(),
            is_trial=True,
        )
        self._save_license()
        return True

    def get_trial_days_remaining(self) -> int:
        if not self._license_info or not self._license_info.is_trial:
            return 0

        if not self._license_info.expires_at:
            return 0

        expires = datetime.fromisoformat(
            self._license_info.expires_at.replace("Z", "+00:00")
        )
        remaining = expires - datetime.now(expires.tzinfo)
        return max(0, remaining.days)

    def deactivate(self) -> bool:
        self._license_info = self._get_default_license()
        self._save_license()
        return True


LICENSE_MGR = LicenseManager()
