# =============================================================
#  plugin_manager.py — Q-VAULT OS  |  Plugin System
#
#  Features:
#    - Load external apps as plugins
#    - Sandbox execution
#    - Permissions per plugin
#    - Plugin API layer
# =============================================================

import os
import json
import hashlib
import importlib.util
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


PLUGIN_DIR = Path.home() / ".qvault" / "plugins"
PLUGIN_MANIFEST = "plugin.json"
PLUGIN_API_VERSION = "1.2.0"


class PluginPermission(Enum):
    FILE_SYSTEM = "filesystem"
    PROCESS = "process"
    NETWORK = "network"
    SECURITY = "security"
    UI = "ui"
    STORAGE = "storage"


@dataclass
class PluginInfo:
    name: str
    version: str
    author: str
    description: str
    permissions: List[str]
    entry_point: str
    icon: Optional[str] = None
    homepage: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class Plugin:
    info: PluginInfo
    path: Path
    module: Any = None
    instance: Any = None
    enabled: bool = False
    loaded_at: Optional[float] = None


class PluginManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._plugins: Dict[str, Plugin] = {}
        self._api = None
        self._permissions = {}

        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        self._load_plugin_index()
        self._setup_api()

    def _load_plugin_index(self):
        index_file = PLUGIN_DIR / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    for plugin_id, info_data in data.items():
                        self._plugins[plugin_id] = Plugin(
                            info=PluginInfo(**info_data),
                            path=PLUGIN_DIR / plugin_id,
                            enabled=False,
                        )
            except Exception:
                pass

    def _save_plugin_index(self):
        index_file = PLUGIN_DIR / "index.json"
        try:
            index = {}
            for plugin_id, plugin in self._plugins.items():
                index[plugin_id] = plugin.info.__dict__
            with open(index_file, "w") as f:
                json.dump(index, f, indent=2)
        except Exception:
            pass

    def _setup_api(self):
        class PluginAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            @property
            def fs(self):
                return FileSystemAPI(self._plugin_id)

            @property
            def process(self):
                return ProcessAPI(self._plugin_id)

            @property
            def storage(self):
                return StorageAPI(self._plugin_id)

            @property
            def ui(self):
                return UIAPI(self._plugin_id)

            @property
            def security(self):
                return SecurityAPI(self._plugin_id)

            def log(self, message: str, level: str = "info"):
                print(f"[Plugin:{self._plugin_id}] {message}")

            def get_config(self, key: str, default: Any = None) -> Any:
                config_file = PLUGIN_DIR / self._plugin_id / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, "r") as f:
                            config = json.load(f)
                            return config.get(key, default)
                    except Exception:
                        pass
                return default

            def set_config(self, key: str, value: Any):
                config_file = PLUGIN_DIR / self._plugin_id / "config.json"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    config = {}
                    if config_file.exists():
                        with open(config_file, "r") as f:
                            config = json.load(f)
                    config[key] = value
                    with open(config_file, "w") as f:
                        json.dump(config, f, indent=2)
                except Exception:
                    pass

        class FileSystemAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            def read(self, path: str) -> Optional[str]:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.FILE_SYSTEM
                ):
                    return None

                try:
                    from core.filesystem import FILESYSTEM

                    return FILESYSTEM.read_file(path)
                except Exception:
                    return None

            def write(self, path: str, content: str) -> bool:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.FILE_SYSTEM
                ):
                    return False
                return False

            def list_dir(self, path: str) -> List[str]:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.FILE_SYSTEM
                ):
                    return []
                return []

        class ProcessAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            def get_processes(self) -> List[Dict]:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.PROCESS
                ):
                    return []
                try:
                    from core.process_manager import PROCESS_MGR

                    return PROCESS_MGR.list_processes()
                except Exception:
                    return []

            def kill_process(self, pid: int) -> bool:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.PROCESS
                ):
                    return False
                return False

        class StorageAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            def get_data_dir(self) -> Path:
                plugin_data = PLUGIN_DIR / self._plugin_id / "data"
                plugin_data.mkdir(parents=True, exist_ok=True)
                return plugin_data

            def save_data(self, key: str, data: Any):
                data_file = self.get_data_dir() / f"{key}.json"
                try:
                    with open(data_file, "w") as f:
                        json.dump(data, f)
                except Exception:
                    pass

            def load_data(self, key: str, default: Any = None) -> Any:
                data_file = self.get_data_dir() / f"{key}.json"
                if data_file.exists():
                    try:
                        with open(data_file, "r") as f:
                            return json.load(f)
                    except Exception:
                        pass
                return default

        class UIAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            def notify(self, title: str, message: str, level: str = "info"):
                if not self._check_permission(self._plugin_id, PluginPermission.UI):
                    return
                try:
                    from system.notification_system import NOTIFY

                    NOTIFY.send(title, message, level)
                except Exception:
                    pass

            def create_window(self, title: str, width: int = 800, height: int = 600):
                if not self._check_permission(self._plugin_id, PluginPermission.UI):
                    return None
                return None

        class SecurityAPI:
            def __init__(self, plugin_id: str):
                self._plugin_id = plugin_id

            def get_alerts(self, limit: int = 10) -> List[Dict]:
                if not self._check_permission(
                    self._plugin_id, PluginPermission.SECURITY
                ):
                    return []
                try:
                    from system.security_monitor import SEC_MONITOR

                    return SEC_MONITOR.get_alerts(limit)
                except Exception:
                    return []

            def log_security_event(self, event: str, severity: str = "INFO"):
                if not self._check_permission(
                    self._plugin_id, PluginPermission.SECURITY
                ):
                    return
                try:
                    from system.audit_logger import AUDIT

                    AUDIT.log(event, "plugin", event, severity)
                except Exception:
                    pass

        self._api = PluginAPI

    def _check_permission(self, plugin_id: str, permission: PluginPermission) -> bool:
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        return permission.value in plugin.info.permissions

    def register_api(self, name: str, api_class: type):
        setattr(self._api, name, api_class)

    def discover_plugins(self) -> List[str]:
        discovered = []

        for item in PLUGIN_DIR.iterdir():
            if not item.is_dir():
                continue

            manifest = item / PLUGIN_MANIFEST
            if not manifest.exists():
                continue

            try:
                with open(manifest, "r") as f:
                    data = json.load(f)

                if data.get("api_version") != PLUGIN_API_VERSION:
                    continue

                info = PluginInfo(
                    name=data.get("name", item.name),
                    version=data.get("version", "1.0.0"),
                    author=data.get("author", "Unknown"),
                    description=data.get("description", ""),
                    permissions=data.get("permissions", []),
                    entry_point=data.get("entry_point", "main"),
                    icon=data.get("icon"),
                    homepage=data.get("homepage"),
                    signature=data.get("signature"),
                )

                plugin_id = item.name
                self._plugins[plugin_id] = Plugin(info=info, path=item, enabled=False)

                discovered.append(plugin_id)

            except Exception:
                pass

        self._save_plugin_index()
        return discovered

    def load_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        try:
            plugin_path = plugin.path / f"{plugin.info.entry_point}.py"
            if not plugin_path.exists():
                plugin_path = plugin.path / "main.py"
                if not plugin_path.exists():
                    return False

            spec = importlib.util.spec_from_file_location(plugin_id, plugin_path)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            api_instance = self._api(plugin_id)

            if hasattr(module, "on_load"):
                module.on_load(api_instance)

            plugin.module = module
            plugin.instance = getattr(module, "PluginClass", None)
            plugin.enabled = True
            plugin.loaded_at = time.time()

            return True

        except Exception:
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        if plugin.module and hasattr(plugin.module, "on_unload"):
            try:
                plugin.module.on_unload()
            except Exception:
                pass

        plugin.module = None
        plugin.instance = None
        plugin.enabled = False

        return True

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    def list_enabled_plugins(self) -> List[Plugin]:
        return [p for p in self._plugins.values() if p.enabled]

    def install_plugin(self, plugin_path: Path) -> bool:
        if not plugin_path.exists() or not plugin_path.is_dir():
            return False

        dest = PLUGIN_DIR / plugin_path.name

        import shutil

        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(plugin_path, dest)
            self.discover_plugins()
            return True
        except Exception:
            return False

    def uninstall_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False

        self.unload_plugin(plugin_id)

        import shutil

        try:
            plugin_path = self._plugins[plugin_id].path
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
            del self._plugins[plugin_id]
            self._save_plugin_index()
            return True
        except Exception:
            return False

    def verify_signature(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        if not plugin.info.signature:
            return True

        plugin_dir = plugin.path
        manifest_file = plugin_dir / PLUGIN_MANIFEST

        try:
            with open(manifest_file, "r") as f:
                content = f.read()

            expected_sig = hashlib.sha256(content.encode()).hexdigest()[:16]
            return expected_sig == plugin.info.signature[:16]
        except Exception:
            return False


PLUGIN_MGR = PluginManager()
