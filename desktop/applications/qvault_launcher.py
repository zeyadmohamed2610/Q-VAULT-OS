import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from integrations.qvault import find_mediator_exe

logger = logging.getLogger(__name__)

# Project root (three levels up from desktop/applications/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def launch_mediator() -> Optional[subprocess.Popen]:
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
        if sys.platform == "win32":
            creation_flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )

        process = subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

        logger.info(
            "[QVaultLauncher] Mediator launched (PID=%d)", process.pid
        )
        return process

    except FileNotFoundError:
        logger.error("[QVaultLauncher] Executable not found at: %s", exe_path)
    except PermissionError:
        logger.error("[QVaultLauncher] Permission denied: %s", exe_path)
    except OSError as exc:
        logger.error("[QVaultLauncher] OS error launching mediator: %s", exc)
    except Exception as exc:
        logger.error("[QVaultLauncher] Unexpected error: %s", exc)

    return None


def terminate_mediator(process: subprocess.Popen) -> bool:
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
