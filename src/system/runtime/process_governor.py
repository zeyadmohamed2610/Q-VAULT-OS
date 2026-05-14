"""
system.runtime.process_governor
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Runtime Process Alias Layer

Provides identity masking for host OS processes to prevent "Windows leaks"
(e.g., chrome.exe, svchost.exe) during documentary demonstrations.
────────────────────────────────────────────────────────────────────────────
"""
import os
import re

class ProcessGovernor:
    # Documentary Safe Mode flag
    _SAFE_MODE = False

    # Static mapping of host processes to Q-Vault runtime identities
    _ALIAS_MAP = {
        "chrome.exe":            "vault-browser",
        "msedge.exe":            "browserd",
        "svchost.exe":           "governor.service",
        "dwm.exe":               "display-server",
        "memcompression":        "memory-governor",
        "system idle process":   "kernel_task",
        "python.exe":            "runtime-governor",
        "explorer.exe":          "workspace-shell",
        "lsass.exe":             "identity-service",
        "wininit.exe":           "init-governor",
        "services.exe":          "service-governor",
        "taskmgr.exe":           "monitor-host",
        "cmd.exe":               "shell-vfs",
        "powershell.exe":        "shell-vfs",
        "conhost.exe":           "terminal-adapter",
        "runtimebroker.exe":     "sandbox-broker",
        "searchhost.exe":        "indexer-service",
        "startmenuexperiencehost.exe": "launcher-service",
        "shellexperiencehost.exe":     "shell-service",
        "ctfmon.exe":            "input-adapter",
        "spoolsv.exe":           "io-governor",
        "smss.exe":              "system-init",
    }

    # Filesystem artifact masking (Section 5)
    _PATH_ARTIFACT_PATTERNS = [
        (re.compile(r"C_Users_[a-zA-Z0-9_-]+", re.I), "runtime_profile"),
        (re.compile(r"C:[\\/][^ \n]*", re.I), "/secure/storage"),
        (re.compile(r"Users[\\/][a-zA-Z0-9_-]+", re.I), "home/user"),
        (re.compile(r"AppData", re.I), "Config"),
        (re.compile(r"LocalSettings", re.I), "Settings"),
        (re.compile(r"\.exe\b", re.I), ""),
    ]

    @classmethod
    def alias_process_name(cls, name: str) -> str:
        """Mask a host process name with a Q-Vault identity."""
        if not name:
            return "unknown-task"
            
        name_lower = name.lower()
        
        # 1. Direct map lookup
        if name_lower in cls._ALIAS_MAP:
            return cls._ALIAS_MAP[name_lower]
            
        # 2. Generic masking for .exe
        if name_lower.endswith(".exe"):
            return name_lower[:-4]
            
        # 3. Prevent generic Windows noise
        if name_lower in ("system", "registry", "memory compression"):
            return name_lower.replace(" ", "-")
            
        return name

    @classmethod
    def sanitize_path(cls, text: str) -> str:
        """Globally sanitize a string to remove Windows paths and host leaks."""
        if not text:
            return text
            
        result = text
        for pattern, replacement in cls._PATH_ARTIFACT_PATTERNS:
            result = pattern.sub(replacement, result)
            
        # Ensure unix-style paths everywhere
        result = result.replace("\\", "/")
        return result

    @classmethod
    def normalize_cpu(cls, cpu: float) -> float:
        """Ensure CPU usage looks realistic (max 100% per core, or capped at 99.9%)."""
        if cls._SAFE_MODE:
            return 12.4 # Predefined stable value for filming
        if cpu > 99.9:
            return 99.9
        return max(0.0, cpu)

    @classmethod
    def set_safe_mode(cls, enabled: bool):
        cls._SAFE_MODE = enabled

PROCESS_GOVERNOR = ProcessGovernor
