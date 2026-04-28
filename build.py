#!/usr/bin/env python3
"""
Q-Vault OS — Environment Setup Script
======================================

Usage:
    python build.py              # Full setup + Rust build
    python build.py --venv-only  # Only create/upgrade venv
    python build.py --deps-only  # Only install pip dependencies
    python build.py --rust-only  # Only build Rust module
    python build.py --check      # Check environment, don't build

Requirements:
    - Python 3.11 or 3.12 (for Rust/PyO3 abi3 compatibility)
    - Rust toolchain (https://rustup.rs)
    - maturin >= 1.5 (installed automatically)

What this script does:
    1. Verifies Python version is 3.11+
    2. Creates or upgrades .venv
    3. Installs Python dependencies (requirements.txt)
    4. Installs maturin
    5. Builds qvault-core Rust extension into core/binaries/
    6. Verifies import works
"""

import sys
import os
import subprocess
import shutil
import platform
from pathlib import Path

ROOT    = Path(__file__).parent.resolve()
VENV    = ROOT / ".venv"
IS_WIN  = platform.system() == "Windows"
BIN_DIR = ROOT / "core" / "binaries"

if IS_WIN:
    VENV_PYTHON  = VENV / "Scripts" / "python.exe"
    VENV_PIP     = VENV / "Scripts" / "pip.exe"
    VENV_MATURIN = VENV / "Scripts" / "maturin.exe"
else:
    VENV_PYTHON  = VENV / "bin" / "python"
    VENV_PIP     = VENV / "bin" / "pip"
    VENV_MATURIN = VENV / "bin" / "maturin"

RUST_DIR = ROOT / "qvault-core"


def _run(cmd, cwd=None, check=True, capture=False):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    if capture:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return subprocess.run(cmd, cwd=cwd, check=check)


def check_python_version():
    v = sys.version_info
    print(f"\n[1/5] Python version: {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    if v.major != 3 or v.minor < 11:
        print(f"  ⚠  Python 3.11+ required for PyO3 abi3 compatibility.")
        print(f"     Install from: https://python.org")
    else:
        print(f"  ✓  Python {v.major}.{v.minor} — compatible")


def check_rust():
    print("\n[2/5] Checking Rust toolchain...")
    r = _run(["rustc", "--version"], check=False, capture=True)
    c = _run(["cargo", "--version"], check=False, capture=True)
    if r.returncode != 0:
        print("  ✗  rustc not found. Install from: https://rustup.rs/")
        return False
    print(f"  ✓  {r.stdout.strip()}")
    print(f"  ✓  {c.stdout.strip()}")
    return True


def create_or_upgrade_venv():
    print(f"\n[3/5] Virtual environment at: {VENV}")
    if not VENV_PYTHON.exists():
        print("  Creating .venv...")
        _run([sys.executable, "-m", "venv", str(VENV)])
    else:
        print("  ✓  .venv already exists")
    _run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"])
    print("  ✓  pip upgraded")


def install_dependencies():
    print("\n[4/5] Installing Python dependencies...")
    req = ROOT / "requirements.txt"
    _run([str(VENV_PIP), "install", "-r", str(req), "-q"])
    _run([str(VENV_PIP), "install", "maturin>=1.5.0", "-q"])
    print("  ✓  All dependencies installed")


def build_rust_module():
    print(f"\n[5/5] Building Rust extension (qvault-core)...")
    if not RUST_DIR.exists():
        print("  ✗  qvault-core directory not found — skipping")
        return False

    result = _run(
        [str(VENV_MATURIN), "develop", "--release"],
        cwd=RUST_DIR,
        check=False,
    )

    if result.returncode != 0:
        print("  ✗  Rust build failed. Check Rust toolchain installation.")
        return False

    # Copy compiled binary into core/binaries/ for explicit path management
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = RUST_DIR / "target" / "release"
    copied = False
    for ext in ("*.pyd", "*.so"):
        for f in target.glob(ext):
            if "qvault_core" in f.name:
                dest = BIN_DIR / "qvault_core.pyd" if IS_WIN else BIN_DIR / "qvault_core.so"
                shutil.copy2(f, dest)
                print(f"  ✓  Copied {f.name} -> core/binaries/")
                copied = True
                break

    if not copied:
        print("  ⚠  No .pyd/.so found in target/release")

    return True


def verify_import():
    print("\n  Verifying qvault_core import...")
    result = _run(
        [str(VENV_PYTHON), "-c", "import qvault_core; print('  ✓  qvault_core OK')"],
        check=False, capture=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
        return True
    else:
        print(f"  ✗  Import failed: {result.stderr.strip()}")
        return False


def main():
    args = sys.argv[1:]
    venv_only  = "--venv-only"  in args
    deps_only  = "--deps-only"  in args
    rust_only  = "--rust-only"  in args
    check_only = "--check"      in args

    print("=" * 60)
    print("  Q-Vault OS — Environment Setup")
    print("=" * 60)

    check_python_version()

    if check_only:
        check_rust()
        return

    if not deps_only and not rust_only:
        create_or_upgrade_venv()

    if not venv_only and not rust_only:
        install_dependencies()

    if not venv_only and not deps_only:
        rust_ok = check_rust()
        if rust_ok:
            build_ok = build_rust_module()
            if build_ok:
                verify_import()
        else:
            print("\n  -> Skipping Rust build. Install Rust and rerun.")

    print("\n" + "=" * 60)
    print("  Setup complete! Run the system with:")
    print()
    print("    py main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
