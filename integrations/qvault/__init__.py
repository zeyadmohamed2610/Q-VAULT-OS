from pathlib import Path

# Project root (three levels up from integrations/qvault/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Path to the hardware mediator project
MEDIATOR_PROJECT_DIR = _PROJECT_ROOT / "subsystems" / "pqc-mediator"

# Candidate executable paths (searched in order)
MEDIATOR_EXE_CANDIDATES = [
    MEDIATOR_PROJECT_DIR / "PQC-Vault" / "bin" / "Release" / "net9.0-windows" / "PQC-Vault.exe",
    MEDIATOR_PROJECT_DIR / "PQC-Vault" / "bin" / "Debug" / "net9.0-windows" / "PQC-Vault.exe",
]

# Integration log directory
LOG_DIR = _PROJECT_ROOT / "logs" / "qvault"

# Process name for OS-level detection
PROCESS_NAME = "PQC-Vault"

def find_mediator_exe() -> Path | None:
    """Resolve the mediator executable from candidate paths."""
    for candidate in MEDIATOR_EXE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
