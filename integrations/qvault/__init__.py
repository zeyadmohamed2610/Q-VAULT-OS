from pathlib import Path

# Project root (three levels up from integrations/qvault/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Path to the hardware mediator project
MEDIATOR_PROJECT_DIR = _PROJECT_ROOT / "subsystems" / "pqc-mediator"

# Candidate executable paths (searched in order)
MEDIATOR_EXE_CANDIDATES = [
    _PROJECT_ROOT / "binaries" / "PQC-Vault.exe",
    _PROJECT_ROOT / "binaries" / "PQC-Vault (1).exe",
    MEDIATOR_PROJECT_DIR / "PQC-Vault.exe",
    MEDIATOR_PROJECT_DIR / "PQC-Vault (1).exe",
    MEDIATOR_PROJECT_DIR / "PQC-Vault" / "bin" / "Release" / "net9.0-windows" / "PQC-Vault.exe",
    MEDIATOR_PROJECT_DIR / "PQC-Vault" / "bin" / "Debug" / "net9.0-windows" / "PQC-Vault.exe",
]

# Integration log directory
LOG_DIR = _PROJECT_ROOT / "logs" / "qvault"

# Process name for OS-level detection
PROCESS_NAME = "PQC-Vault"

def find_mediator_exe() -> Path | None:
    """Resolve the mediator executable from candidate paths."""
    searched = []
    for candidate in MEDIATOR_EXE_CANDIDATES:
        searched.append(str(candidate))
        if candidate.exists() and candidate.stat().st_size > 0:
            logger.info("[QVault] Resolved mediator at: %s", candidate)
            return candidate
    
    # If not found, log the searched paths to help the user debug
    try:
        from kernel.security.qvault_runtime_bridge import QVAULT_BRIDGE
        if QVAULT_BRIDGE and QVAULT_BRIDGE.adapter:
            QVAULT_BRIDGE.adapter._log_event("EXE_NOT_FOUND", f"Searched paths: {', '.join(searched)}")
    except Exception:
        pass
        
    return None
