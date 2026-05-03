import logging
import subprocess
import sys
import time
import ctypes
from pathlib import Path
from typing import Optional, Any
from ctypes import wintypes as wt

from integrations.qvault import find_mediator_exe

logger = logging.getLogger(__name__)

# Project root (three levels up from desktop/applications/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ShellExecuteProcess:
    """
    Minimal wrapper around a Windows process handle to mimic subprocess.Popen.
    Used when launching with elevation (runas verb) via ShellExecuteEx.
    """
    def __init__(self, hProcess: int, pid: int):
        self.hProcess = hProcess
        self.pid = pid
        self.returncode = None
        
        if not hProcess or hProcess == -1: # INVALID_HANDLE_VALUE
             self.returncode = -1

    def poll(self) -> Optional[int]:
        if self.returncode is not None:
            return self.returncode
        
        if not self.hProcess or self.hProcess == -1:
            return -1

        # Check if process is still running
        exit_code = wt.DWORD()
        if ctypes.windll.kernel32.GetExitCodeProcess(self.hProcess, ctypes.byref(exit_code)):
            if exit_code.value != 259:  # STILL_ACTIVE
                self.returncode = exit_code.value
                return self.returncode
        else:
            # Handle is likely invalid or process is inaccessible
            self.returncode = -1
            return self.returncode

        return None

    def wait(self, timeout=None) -> int:
        if self.returncode is not None:
            return self.returncode
        
        if not self.hProcess or self.hProcess == -1:
            return -1

        # Wait for the process to terminate
        ms = int(timeout * 1000) if timeout is not None else 0xFFFFFFFF # INFINITE
        res = ctypes.windll.kernel32.WaitForSingleObject(self.hProcess, ms)
        
        if res == 0x00000102: # WAIT_TIMEOUT
            raise subprocess.TimeoutExpired(["elevated_process"], timeout)
            
        return self.poll()

    def terminate(self):
        if self.returncode is None and self.hProcess and self.hProcess != -1:
            ctypes.windll.kernel32.TerminateProcess(self.hProcess, 1)
            self.poll()

    def kill(self):
        """Alias for terminate on Windows handles."""
        self.terminate()

    def __del__(self):
        if hasattr(self, 'hProcess') and self.hProcess:
            ctypes.windll.kernel32.CloseHandle(self.hProcess)


def launch_mediator() -> Optional[Any]:
    """
    Launch qvault-pc-mediator as a detached subprocess.

    Returns the Popen handle on success, None on failure.
    The process is fully isolated — if it crashes, the OS continues.
    """
    exe_path = find_mediator_exe()
    if exe_path is None:
        logger.debug("[QVaultLauncher] Cannot launch: executable not found")
        return None

    try:
        # Launch detached so OS runtime is never blocked
        creation_flags = 0
        si = None
        if sys.platform == "win32":
            creation_flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Create mediator log file
        log_dir = Path.home() / ".qvault" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        mediator_log_path = log_dir / "mediator.log"
        
        # Open in append mode with unbuffered or line-buffered behavior
        log_file = open(mediator_log_path, "a", encoding="utf-8")
        log_file.write(f"\n--- LAUNCH AT {time.ctime()} ---\n")
        log_file.flush()

        process = subprocess.Popen(
            [str(exe_path)],
            startupinfo=si,
            creationflags=creation_flags,
            cwd=str(exe_path.parent),
            stdout=log_file,
            stderr=log_file,
        )
        
        # Close the file object in the parent; the child retains the handle
        log_file.close()
        
        logger.info(
            "[QVaultLauncher] Mediator launched (PID=%d). Logging to %s", 
            process.pid, mediator_log_path
        )
        return process

    except OSError as exc:
        # WinError 740: The requested operation requires elevation
        if sys.platform == "win32" and getattr(exc, "winerror", 0) == 740:
            logger.info("[QVaultLauncher] Elevation required. Requesting UAC...")
            return _launch_elevated_windows(exe_path)
        
        logger.error("[QVaultLauncher] OS error launching mediator: %s", exc)
    except FileNotFoundError:
        logger.error("[QVaultLauncher] Executable not found at: %s", exe_path)
    except PermissionError:
        logger.error("[QVaultLauncher] Permission denied: %s", exe_path)
    except Exception as exc:
        error_msg = f"OS Launch Error: {str(exc)}"
        logger.error("[QVaultLauncher] %s", error_msg)
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(SystemEvent.EVENT_QVAULT_ERROR, {"error": error_msg}, source="Launcher")
        except: pass
        return None

    return None


def terminate_mediator(process: Any) -> bool:
    """
    Gracefully terminate a running mediator process.

    Tries terminate() first, then kill() after timeout.
    Returns True if the process was stopped.
    """
    if process is None:
        return False

    try:
        if process.poll() is not None:
            return True  # Already exited

        process.terminate()
        try:
            process.wait(timeout=5)
            logger.info("[QVaultLauncher] Mediator terminated gracefully")
            return True
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            logger.warning("[QVaultLauncher] Mediator killed after timeout")
            return True

    except Exception as exc:
        logger.error("[QVaultLauncher] Error terminating mediator: %s", exc)
        return False


def _launch_elevated_windows(exe_path: Path) -> Optional[Any]:
    """
    Launch a process with Administrator privileges on Windows using ShellExecuteEx.
    This triggers the UAC prompt.
    """

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wt.HWND),
            ("lpVerb", wt.LPCWSTR),
            ("lpFile", wt.LPCWSTR),
            ("lpParameters", wt.LPCWSTR),
            ("lpDirectory", wt.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wt.HINSTANCE),
            ("lpIDList", wt.LPVOID),
            ("lpClass", wt.LPCWSTR),
            ("hkeyClass", wt.HKEY),
            ("dwHotKey", wt.DWORD),
            ("hIconOrMonitor", wt.HANDLE),
            ("hProcess", wt.HANDLE),
        ]

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SW_HIDE = 0

    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas"
    sei.lpFile = str(exe_path)
    sei.lpDirectory = str(exe_path.parent)
    sei.nShow = SW_HIDE

    if ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        hProcess = sei.hProcess
        pid = ctypes.windll.kernel32.GetProcessId(hProcess)
        logger.info("[QVaultLauncher] Elevated mediator launched (PID=%d)", pid)
        return ShellExecuteProcess(hProcess, pid)
    else:
        logger.error("[QVaultLauncher] UAC request failed or was denied")
        return None
