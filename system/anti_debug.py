# =============================================================
#  anti_debug.py — Q-VAULT OS  |  Anti-Debugging System
#
#  Detect and respond to debugging attempts
# =============================================================

import os
import sys
import time
import threading
import subprocess
from typing import List, Dict, Optional
from enum import Enum

WINDOWS_DEBUGGERS = [
    "x64dbg",
    "x32dbg",
    "ollydbg",
    "ida",
    "ida64",
    "idag",
    "idag64",
    "windbg",
    " ImmunityDebugger",
    "debug",
    "radare2",
    "cutter",
    "ghidra",
    "xdbg",
]

WINDOWS_SNIFFERS = [
    "wireshark",
    "tshark",
    "fiddler",
    "charles",
    "netmon",
    "procmon",
    "procexp",
    "processhacker",
    "regshot",
]

DEBUG_CHECK_INTERVAL = 30


class DebugDetectionLevel(Enum):
    NONE = "none"
    DETECTED = "detected"
    CONFIRMED = "confirmed"


class AntiDebugger:
    """
    Detect debugging and analysis tools.
    Works on Windows and Linux.
    """

    _instance = None
    _detection_level = DebugDetectionLevel.NONE

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._detected_tools: List[str] = []
        self._detection_count = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background debugger detection."""
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            self._check_for_debuggers()
            time.sleep(DEBUG_CHECK_INTERVAL)

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False

    def _check_for_debuggers(self):
        """Check for running debugger/analyzer processes."""
        detected = []

        if sys.platform == "win32":
            detected = self._check_windows_processes()
        else:
            detected = self._check_linux_processes()

        with self._lock:
            if detected:
                self._detected_tools.extend(detected)
                self._detection_count += 1
                self._detection_level = DebugDetectionLevel.CONFIRMED
                self._trigger_defense()
            else:
                if self._detection_count == 0:
                    self._detection_level = DebugDetectionLevel.NONE

    def _check_windows_processes(self) -> List[str]:
        """Check Windows processes for debuggers."""
        detected = []
        all_tools = WINDOWS_DEBUGGERS + WINDOWS_SNIFFERS

        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                running = result.stdout.lower()
                for tool in all_tools:
                    if tool.lower() in running:
                        detected.append(tool)
        except Exception:
            pass

        return detected

    def _check_linux_processes(self) -> List[str]:
        """Check Linux processes for debuggers."""
        detected = []

        try:
            for proc_dir in os.listdir("/proc"):
                if not proc_dir.isdigit():
                    continue

                cmdline_path = f"/proc/{proc_dir}/cmdline"
                try:
                    with open(cmdline_path, "rb") as f:
                        cmdline = f.read().decode("utf-8", errors="ignore").lower()
                        for tool in WINDOWS_DEBUGGERS + WINDOWS_SNIFFERS:
                            if tool.lower() in cmdline:
                                detected.append(tool)
                except Exception:
                    continue
        except Exception:
            pass

        return detected

    def check_sys_trace(self) -> bool:
        """Check if Python is being traced."""
        return sys.gettrace() is not None

    def check_execution_speed(self) -> bool:
        """Detect abnormal slowdown indicating debugging."""
        start = time.perf_counter()
        _ = sum(range(10000))
        elapsed = time.perf_counter() - start

        return elapsed > 0.1

    def check_ptrace(self) -> bool:
        """Check if process is being traced (Linux)."""
        if sys.platform != "linux":
            return False

        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("TracerPid:"):
                        pid = line.split()[1]
                        return pid != "0"
        except Exception:
            pass

        return False

    def _trigger_defense(self):
        """Trigger defensive measures when debugger detected."""
        from system.security_system import SEC, EVT_INTRUSION
        from system.notification_system import NOTIFY

        tools = ", ".join(self._detected_tools[-5:])
        detail = f"Debug/analysis tool detected: {tools}"

        SEC.report(
            EVT_INTRUSION,
            source="anti_debug",
            detail=detail,
            escalate=True,
        )

        NOTIFY.send(
            "DEBUGGER DETECTED",
            f"Analysis tool detected. System features restricted. {detail}",
            level="danger",
        )

        self._restrict_features()

    def _restrict_features(self):
        """Restrict system features when debugger detected."""
        from system.secure_executor import SECURE_EXECUTOR

        SECURE_EXECUTOR._current_profile = SECURE_EXECUTOR.ExecutionProfile.SAFE

        from system.secure_storage import SECURE_STORAGE

        SECURE_STORAGE._lockdown_mode = True

    def get_detection_level(self) -> DebugDetectionLevel:
        """Get current detection level."""
        return self._detection_level

    def get_detected_tools(self) -> List[str]:
        """Get list of detected tools."""
        with self._lock:
            return list(set(self._detected_tools))

    def get_detection_count(self) -> int:
        """Get number of times debugger was detected."""
        return self._detection_count

    def is_compiled(self) -> bool:
        """Check if running as compiled executable."""
        return getattr(sys, "frozen", False)

    def get_stats(self) -> Dict:
        """Get anti-debugger statistics."""
        return {
            "detection_level": self._detection_level.value,
            "detected_tools": self.get_detected_tools(),
            "detection_count": self._detection_count,
            "is_traced": self.check_sys_trace(),
            "is_compiled": self.is_compiled(),
            "monitoring": self._monitoring,
        }


ANTI_DEBUGGER = AntiDebugger()
