# =============================================================
#  crash_handler.py — Q-Vault OS  |  Global Exception Handling
#
#  Catches all uncaught exceptions and logs them safely
# =============================================================

import sys
import os
import traceback
import logging
from pathlib import Path
from datetime import datetime
from threading import Lock


LOG_DIR = Path.home() / ".qvault" / "logs"
LOG_FILE = LOG_DIR / "crash.log"


def init_crash_handler():
    """Initialize the crash handler system."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True,
    )


def log_crash(exc_type, exc_value, exc_traceback):
    """Log a crash to the crash log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    crash_entry = f"""
================================================================================
CRASH REPORT - {timestamp}
================================================================================
Exception Type: {exc_type.__name__}
Exception Value: {exc_value}

TRACEBACK:
{tb_text}

================================================================================
"""

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(crash_entry)
    except Exception:
        pass

    logging.error(f"CRASH: {exc_type.__name__}: {exc_value}")


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """Hook for uncaught exceptions in the main thread."""
    log_crash(exc_type, exc_value, exc_traceback)

    print(f"\n[CRASH] {exc_type.__name__}: {exc_value}")
    print("Check ~/.qvault/logs/crash.log for details")


def threading_exception_hook(args):
    """Hook for uncaught exceptions in background threads."""
    log_crash(args.exc_type, args.exc_value, args.exc_traceback)


def install_handlers():
    """Install global exception handlers."""
    init_crash_handler()

    sys.excepthook = global_exception_hook

    try:
        import threading

        threading.excepthook = threading_exception_hook
    except AttributeError:
        pass


def get_last_crash() -> str | None:
    """Get the last crash from the log file."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split(
                "================================================================================"
            )
            if len(lines) > 2:
                return lines[-2].strip()
    except Exception:
        pass
    return None


def clear_crash_log():
    """Clear the crash log file."""
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
    except Exception:
        pass
