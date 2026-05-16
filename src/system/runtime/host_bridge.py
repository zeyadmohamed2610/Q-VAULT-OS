import os
import sys
import logging
import subprocess
import ctypes
from pathlib import Path
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class HostProcessHandle:
    """A cross-platform handle for a host process."""
    def __init__(self, process_obj: Any, is_elevated: bool = False):
        self._proc = process_obj
        self.is_elevated = is_elevated
        self.pid = getattr(process_obj, "pid", 0)

    def poll(self) -> Optional[int]:
        if hasattr(self._proc, "poll"):
            return self._proc.poll()
        return None # Simplified for now

    def wait(self, timeout: Optional[float] = None) -> int:
        if hasattr(self._proc, "wait"):
            return self._proc.wait(timeout=timeout)
        return 0

    def terminate(self):
        if hasattr(self._proc, "terminate"):
            self._proc.terminate()

    def kill(self):
        if hasattr(self._proc, "kill"):
            self._proc.kill()

class HostBridge:
    """
    Sovereign Host Bridge (SHB)
    Encapsulates all direct Host OS interactions to prevent leaks.
    """
    
    @staticmethod
    def launch_process(exe_path: Path, elevated: bool = False, hidden: bool = True, cwd: Optional[Path] = None) -> Optional[HostProcessHandle]:
        """Launches a host process with sovereign abstraction."""
        if not exe_path.exists():
            logger.error(f"SHB: Executable not found: {exe_path}")
            return None

        if elevated and sys.platform == "win32":
            return HostBridge._launch_elevated_windows(exe_path, hidden, cwd)
        
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW if hidden else 0
                creation_flags |= 0x00000008 # DETACHED_PROCESS
            
            proc = subprocess.Popen(
                [str(exe_path)],
                creationflags=creation_flags,
                cwd=str(cwd or exe_path.parent)
            )
            return HostProcessHandle(proc)
        except Exception as e:
            if getattr(e, "winerror", 0) == 740:
                logger.info(f"SHB: {exe_path.name} requires elevation. Retrying...")
                return HostBridge._launch_elevated_windows(exe_path, hidden)
            logger.error(f"SHB: Launch failed: {e}")
            return None

    @staticmethod
    def _launch_elevated_windows(exe_path: Path, hidden: bool, cwd: Optional[Path] = None) -> Optional[HostProcessHandle]:
        """Internal Windows-specific elevation logic (Hidden from UI)."""
        import ctypes.wintypes as wt
        
        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wt.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wt.HWND),
                ("lpVerb", wt.LPCWSTR), ("lpFile", wt.LPCWSTR), ("lpParameters", wt.LPCWSTR),
                ("lpDirectory", wt.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wt.HINSTANCE),
                ("lpIDList", wt.LPVOID), ("lpClass", wt.LPCWSTR), ("hkeyClass", wt.HKEY),
                ("dwHotKey", wt.DWORD), ("hIconOrMonitor", wt.HANDLE), ("hProcess", wt.HANDLE),
            ]

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SW_HIDE = 0 if hidden else 1

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(sei)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.lpVerb = "runas"
        sei.lpFile = str(exe_path)
        sei.lpDirectory = str(cwd or exe_path.parent)
        sei.nShow = SW_HIDE

        if ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
            hProcess = sei.hProcess
            pid = ctypes.windll.kernel32.GetProcessId(hProcess)
            
            # Wrap the Windows handle in a compatible object
            class WinHandleWrapper:
                def __init__(self, h, p):
                    self.h = h
                    self.pid = p
                    self.returncode = None
                def poll(self):
                    if self.returncode is not None: return self.returncode
                    exit_code = wt.DWORD()
                    if ctypes.windll.kernel32.GetExitCodeProcess(self.h, ctypes.byref(exit_code)):
                        if exit_code.value != 259: # STILL_ACTIVE
                            self.returncode = exit_code.value
                            return self.returncode
                    return None
                def terminate(self):
                    ctypes.windll.kernel32.TerminateProcess(self.h, 1)
                def kill(self): self.terminate()
                def wait(self, timeout=None):
                    ms = int(timeout * 1000) if timeout else 0xFFFFFFFF
                    ctypes.windll.kernel32.WaitForSingleObject(self.h, ms)
                    return self.poll()
                def __del__(self):
                    if self.h: ctypes.windll.kernel32.CloseHandle(self.h)

            return HostProcessHandle(WinHandleWrapper(hProcess, pid), is_elevated=True)
        return None
