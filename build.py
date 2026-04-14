# =============================================================
#  Q-VAULT OS  |  Build Script
#
#  This script builds the Q-VAULT OS application
#  Run: python build.py
# =============================================================

import os
import sys
import shutil
from pathlib import Path

# Configuration
APP_NAME = "QVAULT"
VERSION = "1.2.0"
DIST_DIR = Path("dist")
BUILD_DIR = Path("build")


def clean():
    """Clean previous build artifacts."""
    print("Cleaning previous builds...")

    # Remove build directories
    for dir_name in [DIST_DIR, BUILD_DIR]:
        if dir_name.exists():
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")

    # Remove spec cache
    spec_cache = Path(f"{APP_NAME}_spec")
    if spec_cache.exists():
        shutil.rmtree(spec_cache)
        print(f"  Removed {spec_cache}/")

    print("Clean complete!")


def build():
    """Build the application using PyInstaller."""
    print(f"Building {APP_NAME} v{VERSION}...")

    # Run PyInstaller
    spec_file = "qvault.spec"

    result = os.system(f'pyinstaller "{spec_file}" --noconfirm')

    if result == 0:
        print("\nBuild successful!")
        print(f"Output: dist/{APP_NAME}/")

        # List output files
        dist_path = DIST_DIR / APP_NAME
        if dist_path.exists():
            print("\nOutput files:")
            for f in dist_path.iterdir():
                size = f.stat().st_size / 1024 / 1024
                print(f"  {f.name} ({size:.1f} MB)")
    else:
        print("\nBuild failed!")
        sys.exit(1)


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "clean":
            clean()
        elif cmd == "build":
            build()
        elif cmd == "rebuild":
            clean()
            build()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python build.py [clean|build|rebuild]")
    else:
        # Default: rebuild
        clean()
        build()


if __name__ == "__main__":
    main()
