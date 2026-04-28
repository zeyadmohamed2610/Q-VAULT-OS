# =============================================================
#  system/config.py — Q-Vault OS
#
#  Global Configuration & Environment Setup.
#  Handles production flags and system paths.
# =============================================================

import os
import logging
from pathlib import Path

# ── System Modes ──
PRODUCTION = os.getenv("QVAULT_ENV") == "production"

# ── Paths ──
def get_qvault_home() -> str:
    """Returns the absolute path to the Q-Vault home directory in the user's home."""
    home = Path.home() / ".qvault"
    if not home.exists():
        home.mkdir(parents=True, exist_ok=True)
    return str(home)

def init_environment():
    """Ensures all required system directories exist."""
    home = Path(get_qvault_home())
    
    # Required subdirectories
    dirs = ["logs", "memory", "plugins", "themes", "apps"]
    for d in dirs:
        (home / d).mkdir(exist_ok=True)
        
    # Setup Logging
    log_file = home / "logs" / "system.log"
    logging.basicConfig(
        level=logging.INFO if PRODUCTION else logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"[CONFIG] System Environment Initialized at {home}")
    logging.info(f"[CONFIG] Mode: {'PRODUCTION' if PRODUCTION else 'DEVELOPMENT'}")

def is_production() -> bool:
    return PRODUCTION

def is_first_run() -> bool:
    """Checks if this is the first time the OS is running."""
    flag_path = Path(get_qvault_home()) / ".first_run"
    return not flag_path.exists()

def mark_first_run_complete():
    """Marks onboarding as complete."""
    flag_path = Path(get_qvault_home()) / ".first_run"
    flag_path.touch()
