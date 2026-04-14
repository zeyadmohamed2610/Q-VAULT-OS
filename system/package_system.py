# =============================================================
#  package_system.py — Q-Vault OS  |  APT-like Package Manager
#
#  Full package management system
# =============================================================

import os
import json
from pathlib import Path
from typing import Optional

try:
    from system.sync_manager import SYNC_MANAGER

    HAS_SYNC = True
except Exception:
    HAS_SYNC = False


PACKAGE_DB_FILE = Path.home() / ".qvault" / "packages.json"
INSTALLED_DB_FILE = Path.home() / ".qvault" / "installed.json"


PACKAGE_REPOSITORY = {
    "vim": {
        "name": "vim",
        "version": "9.0",
        "description": "Enhanced text editor",
        "commands": ["vim", "vi"],
        "size": "2MB",
        "depends": [],
    },
    "nano": {
        "name": "nano",
        "version": "7.2",
        "description": "Simple text editor",
        "commands": ["nano"],
        "size": "500KB",
        "depends": [],
    },
    "git": {
        "name": "git",
        "version": "2.43",
        "description": "Distributed version control",
        "commands": ["git"],
        "size": "15MB",
        "depends": [],
    },
    "curl": {
        "name": "curl",
        "version": "8.5",
        "description": "HTTP client",
        "commands": ["curl"],
        "size": "1MB",
        "depends": [],
    },
    "wget": {
        "name": "wget",
        "version": "1.21",
        "description": "Network downloader",
        "commands": ["wget"],
        "size": "800KB",
        "depends": [],
    },
    "htop": {
        "name": "htop",
        "version": "3.3",
        "description": "Process viewer",
        "commands": ["htop"],
        "size": "400KB",
        "depends": [],
    },
    "tree": {
        "name": "tree",
        "version": "2.1",
        "description": "Directory tree viewer",
        "commands": ["tree"],
        "size": "100KB",
        "depends": [],
    },
    "jq": {
        "name": "jq",
        "version": "1.7",
        "description": "JSON processor",
        "commands": ["jq"],
        "size": "300KB",
        "depends": [],
    },
    "python3": {
        "name": "python3",
        "version": "3.12",
        "description": "Python interpreter",
        "commands": ["python3", "python"],
        "size": "20MB",
        "depends": [],
    },
    "nodejs": {
        "name": "nodejs",
        "version": "21.6",
        "description": "JavaScript runtime",
        "commands": ["node", "npm"],
        "size": "30MB",
        "depends": [],
    },
    "openssh": {
        "name": "openssh",
        "version": "9.5",
        "description": "SSH client and server",
        "commands": ["ssh", "scp", "sftp"],
        "size": "2MB",
        "depends": [],
    },
    "docker": {
        "name": "docker",
        "version": "24.0",
        "description": "Container runtime",
        "commands": ["docker"],
        "size": "80MB",
        "depends": [],
    },
    "gcc": {
        "name": "gcc",
        "version": "13.2",
        "description": "C compiler",
        "commands": ["gcc", "g++"],
        "size": "100MB",
        "depends": [],
    },
    "make": {
        "name": "make",
        "version": "4.4",
        "description": "Build automation",
        "commands": ["make"],
        "size": "500KB",
        "depends": [],
    },
    "net-tools": {
        "name": "net-tools",
        "version": "2.10",
        "description": "Network utilities",
        "commands": ["ifconfig", "netstat", "route"],
        "size": "200KB",
        "depends": [],
    },
}


class Package:
    """Represents a package."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        commands: list,
        size: str,
        depends: list = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.commands = commands
        self.size = size
        self.depends = depends or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "commands": self.commands,
            "size": self.size,
            "depends": self.depends,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Package":
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            description=data.get("description", ""),
            commands=data.get("commands", []),
            size=data.get("size", ""),
            depends=data.get("depends", []),
        )


def _load_installed() -> dict:
    """Load installed packages database."""
    try:
        if INSTALLED_DB_FILE.exists():
            with open(INSTALLED_DB_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_installed(installed: dict):
    """Save installed packages database."""
    INSTALLED_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTALLED_DB_FILE, "w") as f:
        json.dump(installed, f, indent=2)


class PackageManager:
    """Manages system packages."""

    def __init__(self):
        self._installed = _load_installed()

    def get_package(self, name: str) -> Optional[Package]:
        """Get package from repository."""
        if name in PACKAGE_REPOSITORY:
            return Package.from_dict(PACKAGE_REPOSITORY[name])
        return None

    def get_installed(self, name: str) -> Optional[Package]:
        """Get installed package."""
        if name in self._installed:
            return Package.from_dict(self._installed[name])
        return None

    def is_installed(self, name: str) -> bool:
        """Check if package is installed."""
        return name in self._installed

    def install(self, name: str) -> bool:
        """Install a package."""
        if self.is_installed(name):
            return False  # Already installed

        pkg = self.get_package(name)
        if not pkg:
            return False  # Package not found

        # Check dependencies
        for dep in pkg.depends:
            if not self.is_installed(dep):
                # Install dependency first
                if not self.install(dep):
                    return False

        # Install package
        self._installed[name] = pkg.to_dict()
        _save_installed(self._installed)

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_package(name, pkg.version, pkg.description, True)
            except Exception:
                pass

        return True

    def remove(self, name: str) -> bool:
        """Remove a package."""
        if not self.is_installed(name):
            return False  # Not installed

        if name == "base":
            return False  # Cannot remove base

        del self._installed[name]
        _save_installed(self._installed)

        if HAS_SYNC:
            try:
                SYNC_MANAGER.sync_package(name, "unknown", "", False)
            except Exception:
                pass

        return True

    def search(self, query: str) -> list:
        """Search packages by name or description."""
        results = []
        query = query.lower()

        for name, pkg in PACKAGE_REPOSITORY.items():
            if query in name.lower() or query in pkg.get("description", "").lower():
                status = "installed" if self.is_installed(name) else "available"
                results.append(
                    {
                        "name": name,
                        "version": pkg.get("version"),
                        "description": pkg.get("description"),
                        "status": status,
                    }
                )

        return results

    def list_all(self) -> list:
        """List all available packages."""
        results = []
        for name, pkg in PACKAGE_REPOSITORY.items():
            status = "installed" if self.is_installed(name) else "available"
            results.append(
                {
                    "name": name,
                    "version": pkg.get("version"),
                    "description": pkg.get("description"),
                    "status": status,
                }
            )
        return results

    def list_installed(self) -> list:
        """List installed packages."""
        results = []
        for name, pkg in self._installed.items():
            results.append(
                {
                    "name": name,
                    "version": pkg.get("version"),
                    "description": pkg.get("description"),
                    "size": pkg.get("size"),
                }
            )
        return results

    def get_commands(self) -> dict:
        """Get all available commands from installed packages."""
        commands = {}
        for name, pkg in self._installed.items():
            for cmd in pkg.get("commands", []):
                commands[cmd] = name
        return commands

    def which_command(self, cmd: str) -> Optional[str]:
        """Find which package provides a command."""
        # Check installed packages first
        for name, pkg in self._installed.items():
            if cmd in pkg.get("commands", []):
                return name

        # Check repository
        for name, pkg in PACKAGE_REPOSITORY.items():
            if cmd in pkg.get("commands", []):
                return name

        return None


# Global package manager
PKG_MGR = PackageManager()
