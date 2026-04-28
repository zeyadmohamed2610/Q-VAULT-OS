# =============================================================
#  run.py — Q-Vault OS
#
#  Production Entry Point.
#  Environment Setup | Error Isolation | Bootstrapping.
# =============================================================

import sys
import os

# ── WINDOWS HYGIENE ──
# Force UTF-8 encoding for stdout/stderr to prevent crashes with Unicode characters (e.g., ✕)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import traceback
import logging

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from system.config import init_environment, is_production

def verify_rust_core():
    """Ensures the Rust security core is compiled and available."""
    bin_path = os.path.join(os.path.dirname(__file__), "core", "binaries", "qvault_core.pyd")
    if not os.path.exists(bin_path):
        print("[!] Rust Security Core missing. Attempting to build...")
        try:
            import subprocess
            rust_dir = os.path.join(os.path.dirname(__file__), "qvault-core")
            if os.path.exists(rust_dir):
                # Build and copy
                subprocess.check_call(["cargo", "build", "--release"], cwd=rust_dir)
                # Note: On Windows maturin/cargo builds qvault_core.dll/pyd in target/release
                # This part is simplified; usually a build script handles the move
                print("[+] Build successful. Please ensure qvault_core.pyd is in core/binaries")
            else:
                print("[ERROR] qvault-core source not found. Please restore the folder.")
        except Exception as e:
            print(f"[ERROR] Failed to build Rust core: {e}")

def start_qvault():
    """Bootstraps the OS and handles critical failures."""
    try:
        # 1. Init Environment (~/.qvault)
        init_environment()
        
        # 1.5 Verify Rust Core (USER: Is deleting target an error? No, but we check here)
        verify_rust_core()
        
        # 2. Launch main application
        from main import main
        main()
        
    except Exception as e:
        # Critical Crash Handler
        error_details = traceback.format_exc()
        logging.critical(f"[BOOT_ERROR] OS crashed during startup: {e}\n{error_details}")
        
        # If in dev, just print. If in production, show a friendly message.
        if not is_production():
            print(error_details)
        
        # Attempt to show a fallback error UI or just exit
        sys.exit(1)

if __name__ == "__main__":
    # Pre-boot check (Optional: verify assets, deps)
    # from _boot_pipeline import run_all_checks
    # if not run_all_checks(): sys.exit(1)
    
    start_qvault()
