# ═══════════════════════════════════════════════════════════════════
#  run.py — Q-Vault OS
#  Single-command bootstrap: python run.py
#
#  Works on: Windows 10/11, Ubuntu 20+, macOS 12+
#  Requires: Python 3.10+ (3.11 recommended for Rust ABI)
#
#  What this does:
#    1. Checks Python version
#    2. Installs missing packages automatically
#    3. Verifies assets and security core
#    4. Launches the OS
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
import io
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ── Windows: Force UTF-8 to prevent Unicode crashes ─────────────────
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# ANSI colors (work on Windows 10+ with VT processing enabled)
# ────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.system("")   # Enable ANSI escape processing on Windows

R  = "\x1b[38;2;248;81;73m"    # red    #f85149
G  = "\x1b[38;2;63;185;80m"    # green  #3fb950
Y  = "\x1b[38;2;210;153;34m"   # yellow #d29922
C  = "\x1b[38;2;84;177;198m"   # cyan   #54b1c6
D  = "\x1b[38;2;74;104;128m"   # dim    #4a6880
B  = "\x1b[1m"                  # bold
RS = "\x1b[0m"                  # reset


def _print(symbol: str, color: str, message: str) -> None:
    print(f"  {color}{symbol}{RS}  {message}")


def ok(msg: str)    -> None: _print("v", G, msg)
def warn(msg: str)  -> None: _print("!", Y, msg)
def fail(msg: str)  -> None: _print("x", R, msg)
def info(msg: str)  -> None: _print("->", C, msg)
def step(msg: str)  -> None: print(f"\n{C}{B}{'─'*52}{RS}\n  {B}{msg}{RS}")


# ════════════════════════════════════════════════════════════════════
# STEP 1 — PYTHON VERSION CHECK
# ════════════════════════════════════════════════════════════════════
def check_python() -> None:
    step("Step 1 — Checking Python version")
    major, minor = sys.version_info.major, sys.version_info.minor
    version_str  = f"{major}.{minor}.{sys.version_info.micro}"

    if major < 3 or (major == 3 and minor < 10):
        fail(f"Python {version_str} detected.")
        fail("Q-Vault OS requires Python 3.10 or newer.")
        fail("Download: https://python.org/downloads/")
        sys.exit(1)

    if minor < 11:
        warn(f"Python {version_str} (3.11+ recommended for Rust ABI stability)")
    else:
        ok(f"Python {version_str}")


# ════════════════════════════════════════════════════════════════════
# STEP 2 — INSTALL DEPENDENCIES
# ════════════════════════════════════════════════════════════════════
def install_dependencies() -> None:
    step("Step 2 — Installing / verifying dependencies")

    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        warn("requirements.txt not found — skipping dependency check")
        return

    # Check if pip is available
    try:
        import pip  # noqa: F401
    except ImportError:
        fail("pip is not available. Install pip first:")
        fail("  python -m ensurepip --upgrade")
        sys.exit(1)

    # Try to import key packages; install if missing
    critical = {
        "PyQt5":        "PyQt5==5.15.10",
        "argon2":       "argon2-cffi>=23.1.0",
        "cryptography": "cryptography>=42.0.0",
        "psutil":       "psutil>=5.9.8",
    }
    optional = {
        "PyQt5.QtWebEngineWidgets": "PyQtWebEngine>=5.15.0",
        "structlog":                "structlog>=24.0.0",
        "PIL":                      "Pillow>=10.0.0",
    }

    needs_install: list[str] = []

    for import_name, pkg_spec in critical.items():
        try:
            __import__(import_name)
            ok(f"{pkg_spec.split('>=')[0].split('==')[0]}")
        except ImportError:
            warn(f"Missing: {import_name} — will install")
            needs_install.append(pkg_spec)

    for import_name, pkg_spec in optional.items():
        try:
            __import__(import_name)
            ok(f"{pkg_spec.split('>=')[0].split('==')[0]} (optional)")
        except ImportError:
            warn(f"Optional missing: {import_name} — will install")
            needs_install.append(pkg_spec)

    if needs_install:
        info(f"Installing {len(needs_install)} package(s)...")
        for pkg in needs_install:
            try:
                pip_cmd = [sys.executable, "-m", "pip", "install", pkg,
                           "--quiet", "--disable-pip-version-check"]
                subprocess.check_call(
                    pip_cmd,
                    stdout=None if _VERBOSE else subprocess.DEVNULL,
                    stderr=None if _VERBOSE else subprocess.DEVNULL,
                )
                ok(f"Installed: {pkg}")
            except subprocess.CalledProcessError as e:
                warn(f"Could not install {pkg}: {e}")

    # Final verification of critical packages
    for import_name in critical:
        try:
            __import__(import_name)
        except ImportError:
            fail(f"Critical package missing after install attempt: {import_name}")
            fail("Run manually: pip install -r requirements.txt")
            sys.exit(1)


# ════════════════════════════════════════════════════════════════════
# STEP 3 — VERIFY RUST SECURITY CORE
# ════════════════════════════════════════════════════════════════════
def check_rust_core() -> None:
    step("Step 3 — Verifying Rust Security Core")

    # Platform-specific binary names
    binary_names = [
        "qvault_core.pyd",    # Windows (Python extension)
        "qvault_core.so",     # Linux / macOS
        "qvault_core.dll",    # Windows (alternative)
    ]
    bin_dir = ROOT / "core" / "binaries"

    found = False
    for name in binary_names:
        if (bin_dir / name).exists():
            ok(f"Rust core found: {name}")
            found = True
            break

    if not found:
        warn("Rust core binary not found in core/binaries/")
        rust_src = ROOT / "Cargo.toml"
        if rust_src.exists():
            info("Attempting to build Rust core with maturin...")
            try:
                # Ensure maturin is available
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "maturin", "--quiet"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.check_call(
                    [sys.executable, "-m", "maturin", "develop", "--release"],
                    cwd=ROOT,
                )
                ok("Rust core built successfully")
            except subprocess.CalledProcessError:
                warn("Could not auto-build Rust core.")
                warn("Manual build: maturin develop --release")
                warn("OS will launch with reduced security — Python fallback active")
        else:
            warn("Cargo.toml not found. Using Python security fallback.")


# ════════════════════════════════════════════════════════════════════
# STEP 4 — VERIFY ASSETS
# ════════════════════════════════════════════════════════════════════
def check_assets() -> None:
    step("Step 4 — Checking required assets")

    required = [
        "assets/qvault_vault.jpg",
        "assets/design_tokens.py",
        "assets/theme.py",
        "assets/icons/terminal.svg",
        "assets/icons/files.svg",
        "assets/icons/trash.svg",
        "assets/icons/browser.svg",
        "assets/icons/qvault_logo.svg",
    ]
    optional_icons = [
        "assets/icons/kernel_monitor.svg",
        "assets/icons/wifi.svg",
        "assets/icons/bluetooth.svg",
        "assets/icons/folder.svg",
        "assets/icons/file_text.svg",
        "assets/icons/file_generic.svg",
        "assets/icons/trash_full.svg",
    ]

    all_ok = True
    for rel in required:
        path = ROOT / rel
        if path.exists():
            ok(rel)
        else:
            fail(f"MISSING: {rel}")
            all_ok = False

    for rel in optional_icons:
        if not (ROOT / rel).exists():
            warn(f"Optional icon missing (non-critical): {rel}")

    if not all_ok:
        fail("One or more required assets are missing.")
        fail("Please restore the assets/ directory from the repository.")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════════
# STEP 5 — INIT ENVIRONMENT (~/.qvault)
# ════════════════════════════════════════════════════════════════════
def init_qvault_environment() -> None:
    step("Step 5 — Initializing Q-Vault environment")
    try:
        sys.path.insert(0, str(ROOT))
        from system.config import init_environment
        init_environment()
        ok("~/.qvault/ directories ready")
    except Exception as e:
        fail(f"Environment init failed: {e}")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════════
# STEP 6 — LAUNCH
# ════════════════════════════════════════════════════════════════════
def launch() -> None:
    step("Step 6 — Launching Q-Vault OS")
    print()
    print(f"  {C}{'='*48}{RS}")
    print(f"  {B}{C}  Q-Vault OS v1.0.0  --  Starting...{RS}")
    print(f"  {C}{'='*48}{RS}")
    print()

    try:
        from main import main
        main()
    except KeyboardInterrupt:
        print(f"\n  {Y}OS terminated by user.{RS}")
        sys.exit(0)
    except Exception:
        import traceback
        fail("Critical error during launch:")
        print(f"\n{R}{traceback.format_exc()}{RS}")
        fail("Please report this issue with the traceback above.")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════
_VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

def bootstrap() -> None:
    """Run the full boot sequence: checks, dependencies, assets, env."""
    print()
    print(f"  {C}{B}Q-Vault OS -- Boot Sequence{RS}")
    print(f"  {D}Platform: {sys.platform} | Python {sys.version.split()[0]}{RS}")

    t0 = time.time()

    check_python()
    install_dependencies()
    check_rust_core()
    check_assets()
    init_qvault_environment()

    elapsed = time.time() - t0
    print(f"\n  {G}All checks passed in {elapsed:.1f}s -- Ready to launch{RS}")

if __name__ == "__main__":
    bootstrap()
    launch()
