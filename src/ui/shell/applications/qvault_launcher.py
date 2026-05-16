import logging
import time
from pathlib import Path
from typing import Optional, Any

from system.integrations.qvault import find_mediator_exe
from system.runtime.host_bridge import HostBridge

logger = logging.getLogger(__name__)

def launch_mediator() -> Optional[Any]:
    """
    Launch qvault-pc-mediator via the Sovereign HostBridge.
    The UI layer is now fully decoupled from platform-specific APIs.
    """
    exe_path = find_mediator_exe()
    if exe_path is None:
        logger.debug("[QVaultLauncher] Cannot launch: executable not found")
        return None

    # Get project root to use as CWD for the mediator
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    # The HostBridge handles elevation, hidden windows, and platform checks internally.
    handle = HostBridge.launch_process(exe_path, elevated=False, hidden=True, cwd=project_root)
    
    if handle:
        logger.info("[QVaultLauncher] Mediator session established (PID=%d)", handle.pid)
        return handle
    
    # If standard launch fails (e.g. elevation required), HostBridge doesn't auto-elevate
    # unless requested. We can try elevated if standard fails.
    logger.warning("[QVaultLauncher] Standard launch failed, attempting elevated...")
    return HostBridge.launch_process(exe_path, elevated=True, hidden=True, cwd=project_root)

def terminate_mediator(handle: Any) -> bool:
    """
    Gracefully terminate a running mediator handle.
    """
    if handle is None:
        return False

    try:
        if handle.poll() is not None:
            return True  # Already exited

        handle.terminate()
        try:
            handle.wait(timeout=5)
            logger.info("[QVaultLauncher] Mediator handle terminated")
            return True
        except Exception:
            handle.kill()
            logger.warning("[QVaultLauncher] Mediator handle killed")
            return True

    except Exception as exc:
        logger.error("[QVaultLauncher] Error terminating mediator: %s", exc)
        return False
