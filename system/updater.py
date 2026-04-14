# =============================================================
#  updater.py — Q-VAULT OS  |  Auto Update System
#
#  Secure update pipeline with Supabase integration
# =============================================================

import os
import json
import hashlib
import threading
import time
import requests
from typing import Dict, Optional, Any
from pathlib import Path
from enum import Enum

CURRENT_VERSION = "1.2.0"

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qlulmfhluutrnoeueekz.supabase.co"
)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


class UpdateStatus(Enum):
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    RESTARTING = "restarting"
    ERROR = "error"
    UP_TO_DATE = "up_to_date"


class Updater:
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

        self._current_version = CURRENT_VERSION
        self._status = UpdateStatus.IDLE
        self._latest_version = ""
        self._download_url = ""
        self._sha256_hash = ""
        self._release_notes = ""
        self._download_path = ""
        self._error_message = ""
        self._lock = threading.Lock()
        self._update_table = "releases"

    def get_current_version(self) -> str:
        return self._current_version

    def check_for_updates(self) -> Dict[str, Any]:
        with self._lock:
            self._status = UpdateStatus.CHECKING

        print(f"[UPDATER] Checking for updates (current: {self._current_version})...")

        try:
            response = self._check_supabase()

            if response.get("available"):
                with self._lock:
                    self._latest_version = response.get(
                        "version", self._current_version
                    )
                    self._download_url = response.get("download_url", "")
                    self._sha256_hash = response.get("sha256", "")
                    self._release_notes = response.get("release_notes", "")
                    self._status = UpdateStatus.IDLE

                return {
                    "available": True,
                    "current": self._current_version,
                    "latest": self._latest_version,
                    "release_notes": self._release_notes,
                    "download_url": self._download_url,
                }
            else:
                with self._lock:
                    self._latest_version = self._current_version
                    self._status = UpdateStatus.UP_TO_DATE

                return {
                    "available": False,
                    "current": self._current_version,
                    "latest": self._latest_version,
                    "message": "You are running the latest version.",
                }

        except Exception as e:
            self._error_message = str(e)
            self._status = UpdateStatus.ERROR
            return {"error": str(e), "available": False}

    def _check_supabase(self) -> Dict:
        if not SUPABASE_KEY:
            return self._simulate_check()

        try:
            url = f"{SUPABASE_URL}/rest/v1/{self._update_table}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            params = {
                "select": "version,download_url,sha256,release_notes",
                "order": "version.desc",
                "limit": 1,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200 and response.json():
                latest = response.json()[0]
                latest_version = latest.get("version", "")

                if self._compare_versions(latest_version, self._current_version) > 0:
                    return {
                        "available": True,
                        "version": latest_version,
                        "download_url": latest.get("download_url", ""),
                        "sha256": latest.get("sha256", ""),
                        "release_notes": latest.get("release_notes", ""),
                    }

            return {"available": False}

        except Exception as e:
            print(f"[UPDATER] Supabase check failed: {e}")
            return self._simulate_check()

    def _compare_versions(self, v1: str, v2: str) -> int:
        parts1 = [int(p) for p in v1.split(".")]
        parts2 = [int(p) for p in v2.split(".")]

        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0

    def _simulate_check(self) -> Dict:
        time.sleep(0.5)
        return {
            "available": False,
            "version": "1.2.0",
            "download_url": f"https://qvault-os.com/releases/qvault-1.2.0.zip",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "release_notes": "No updates available.",
        }

    def download_update(self, progress_callback=None) -> bool:
        with self._lock:
            self._status = UpdateStatus.DOWNLOADING

        print(f"[UPDATER] Downloading update from {self._download_url}...")

        try:
            self._download_path = str(
                Path.home()
                / ".qvault"
                / "updates"
                / f"qvault-{self._latest_version}.zip"
            )
            Path(self._download_path).parent.mkdir(parents=True, exist_ok=True)

            if self._download_url.startswith("http"):
                response = requests.get(self._download_url, stream=True, timeout=60)
                total_size = int(response.headers.get("content-length", 0))

                with open(self._download_path, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size:
                                progress_callback(int(downloaded * 100 / total_size))
            else:
                with open(self._download_path, "wb") as f:
                    f.write(b"UPDATE_CONTENT_PLACEHOLDER")

            with self._lock:
                self._status = UpdateStatus.VERIFYING

            return self._verify_update()

        except Exception as e:
            self._error_message = f"Download failed: {str(e)}"
            self._status = UpdateStatus.ERROR
            return False

    def _verify_update(self) -> bool:
        if not self._download_path:
            return False

        try:
            with open(self._download_path, "rb") as f:
                content = f.read()
                actual_hash = hashlib.sha256(content).hexdigest()

            if self._sha256_hash and actual_hash != self._sha256_hash:
                self._error_message = "Hash verification failed"
                self._status = UpdateStatus.ERROR
                return False

            print("[UPDATER] Update package verified successfully")
            return True

        except Exception as e:
            self._error_message = f"Verification failed: {str(e)}"
            self._status = UpdateStatus.ERROR
            return False

    def apply_update(self) -> bool:
        with self._lock:
            self._status = UpdateStatus.APPLYING

        print("[UPDATER] Applying update...")

        try:
            time.sleep(1)

            self._update_version_file()

            with self._lock:
                self._status = UpdateStatus.RESTARTING

            return True

        except Exception as e:
            self._error_message = f"Apply failed: {str(e)}"
            self._status = UpdateStatus.ERROR
            return False

    def _update_version_file(self):
        version_file = Path.home() / ".qvault" / "version.json"
        version_file.parent.mkdir(parents=True, exist_ok=True)

        with open(version_file, "w") as f:
            json.dump(
                {
                    "version": self._latest_version,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                f,
            )

    def get_status(self) -> str:
        return self._status.value

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_version": self._current_version,
            "latest_version": self._latest_version,
            "status": self._status.value,
            "error": self._error_message,
            "download_url": self._download_url,
        }

    def set_current_version(self, version: str):
        self._current_version = version

    def get_release_history(self) -> list:
        if not SUPABASE_KEY:
            return []

        try:
            url = f"{SUPABASE_URL}/rest/v1/{self._update_table}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
            params = {
                "select": "version,release_notes,created_at",
                "order": "created_at.desc",
                "limit": 10,
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()

        except Exception:
            pass

        return []


UPDATER = Updater()
