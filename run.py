# ═══════════════════════════════════════════════════════════════════
#  run.py — Q-Vault OS Sovereign Bootstrap Engine
#  Single-command bootstrap: python run.py
#  Target: Zero-Config Portability across all 1,660 files.
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
import io
import os
import subprocess
import sys
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ── Environment & Unicode Stability ─────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        os.system("") # Enable ANSI processing
        # Modern HiDPI handling
        os.environ.pop("QT_DEVICE_PIXEL_RATIO", None)
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    except Exception:
        pass

# ── ANSI Sovereign Palette ──────────────────────────────────────────
R  = "\x1b[38;2;248;81;73m"    # red
G  = "\x1b[38;2;63;185;80m"    # green
Y  = "\x1b[38;2;210;153;34m"   # yellow
C  = "\x1b[38;2;84;177;198m"   # cyan
D  = "\x1b[38;2;74;104;128m"   # dim
B  = "\x1b[1m"                  # bold
RS = "\x1b[0m"                  # reset

def _print(symbol: str, color: str, message: str) -> None:
    print(f"  {color}{symbol}{RS}  {message}")

def count_project_files() -> tuple[int, int]:
    """Sovereign audit: counts all files and directories in the project."""
    f_count = 0
    d_count = 0
    for root, dirs, files in os.walk(ROOT):
        # Sovereign exclusion: Skip build artifacts, caches, and VCS
        exclude = {'.git', '.venv', 'node_modules', '__pycache__', 'target', 'build', 'dist', 'backups'}
        dirs[:] = [d for d in dirs if d not in exclude and not d.startswith('.')]
        
        f_count += len(files)
        d_count += len(dirs)
    return f_count, d_count

def ok(msg: str)    -> None: _print("[OK]", G, msg)
def warn(msg: str)  -> None: _print("!", Y, msg)
def fail(msg: str)  -> None: _print("[FAIL]", R, msg)
def info(msg: str)  -> None: _print("->", C, msg)
def step(msg: str)  -> None: print(f"\n{C}{B}{'='*60}{RS}\n  {B}{msg}{RS}")

def print_logo() -> None:
    logo_path = ROOT / "resources" / "ascii_logo.txt"
    if logo_path.exists():
        content = logo_path.read_text(encoding="utf-8")
        # Colorize the logo with cyan glow
        print(f"{C}{B}{content}{RS}")
    else:
        print(f"\n{C}{B}  Q-VAULT SOVEREIGN OS{RS}\n")

# ════════════════════════════════════════════════════════════════════
# PHASE 1 — PYTHON INTEGRITY
# ════════════════════════════════════════════════════════════════════
def check_python() -> None:
    step("PHASE 1 — Validating Python Runtime")
    version = sys.version_info
    v_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        fail(f"Python {v_str} detected. Q-Vault requires 3.10+")
        sys.exit(1)
    
    ok(f"Python Runtime: {v_str} (Verified)")

# ════════════════════════════════════════════════════════════════════
# PHASE 2 — DYNAMIC DEPENDENCY RESOLUTION
# ════════════════════════════════════════════════════════════════════
def resolve_dependencies() -> None:
    step("PHASE 2 — Autonomous Dependency Resolution")
    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        fail("requirements.txt missing. Attempting critical recovery...")
        # Fallback list (minimal)
        missing = ["PyQt5", "psutil", "requests", "argon2-cffi", "cryptography", "pynacl", "Pillow"]
    else:
        # Proper way to check for missing packages while respecting markers
        try:
            import pkg_resources
            from packaging.requirements import Requirement
            with open(req_file, "r") as f:
                raw_reqs = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
            missing = []
            for r in raw_reqs:
                req = Requirement(r)
                if req.marker and not req.marker.evaluate():
                    continue # Skip if marker doesn't apply to this platform
                
                try:
                    pkg_resources.require(str(req))
                except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                    missing.append(str(req))
        except ImportError:
            # If packaging/pkg_resources not available, just use pip directly to be safe
            info("Advanced dependency check unavailable. Running verification...")
            missing = ["-r", "requirements.txt"]

    if missing:
        info(f"Environmental gap detected. Synchronizing...")
        try:
            if missing == ["-r", "requirements.txt"]:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"])
            else:
                for pkg in missing:
                    info(f"Provisioning {pkg}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
            ok("Dependency State: SYNCHRONIZED")
        except Exception as e:
            fail(f"Provisioning failed: {e}")
            sys.exit(1)
    else:
        ok("Dependency State: NOMINAL")


# ════════════════════════════════════════════════════════════════════
# PHASE 3 — SECURITY CORE AUDIT (Rust/PQC)
# ════════════════════════════════════════════════════════════════════
def audit_security_binaries() -> None:
    step("PHASE 3 — Security Subsystem Audit")
    
    bin_dir = ROOT / "src" / "core" / "binaries"
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    core_ext = ".pyd" if sys.platform == "win32" else ".so"
    core_path = bin_dir / f"qvault_core{core_ext}"
    
    if core_path.exists():
        ok("Rust Security Core: ACTIVE")
    else:
        warn("Rust Security Core: BINARY NOT FOUND")
        if shutil.which("cargo"):
            info("Cargo detected. Initiating autonomous compilation...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "maturin", "--quiet"])
                subprocess.check_call([sys.executable, "-m", "maturin", "develop", "--release"], cwd=ROOT / "engine_rust")
                ok("Compilation Successful: Security Core instantiated.")
            except Exception as e:
                warn(f"Compilation failed: {e}. Falling back to Python-limited mode.")
        else:
            warn("Cargo not found. Security features will be computationally restricted.")

    pqc_name = "PQC-Vault.exe" if sys.platform == "win32" else "PQC-Vault"
    pqc_path = ROOT / "src" / "system" / "subsystems" / "pqc-mediator" / pqc_name
    if pqc_path.exists():
        ok("Post-Quantum Mediator: ACTIVE")
    else:
        warn("Post-Quantum Mediator: MISSING. Sovereign protections downgraded.")

# ════════════════════════════════════════════════════════════════════
# PHASE 4 — INFRASTRUCTURE PROVISIONING
# ════════════════════════════════════════════════════════════════════
def provision_infrastructure() -> None:
    step("PHASE 4 — Infrastructure Provisioning")
    dirs = [
        ROOT / "vault_data" / "logs",
        ROOT / "vault_data" / "db",
        ROOT / "vault_data" / "backups",
        ROOT / "src" / "system" / "subsystems" / "storage"
    ]
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            ok(f"Created: {d.relative_to(ROOT)}")
        else:
            ok(f"Verified: {d.relative_to(ROOT)}")

    try:
        sys.path.insert(0, str(ROOT / "src"))
        from system.config import init_environment
        init_environment()
        ok("Persistent Storage: READY")
    except Exception as e:
        fail(f"Infrastructure Failure: {e}")
        sys.exit(1)

# ════════════════════════════════════════════════════════════════════
# EXECUTION LAYER
# ════════════════════════════════════════════════════════════════════
def launch() -> None:
    print_logo()
    step("PHASE 5 — Sovereign Launch")
    print(f"\n  {C}{B}Executing Q-Vault Sovereign Interface...{RS}\n")
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from main import main
        print(">>> [RUN.PY] Calling main()...")
        main()
    except Exception:
        import traceback
        fail("CRITICAL RUNTIME COLLAPSE")
        print(f"\n{R}{traceback.format_exc()}{RS}")
        sys.exit(1)

def bootstrap() -> None:
    t0 = time.time()
    f_total, d_total = count_project_files()
    
    print(f"\n  {C}{B}Q-Vault OS  |  Sovereign Bootstrap Engine v2.0{RS}")
    print(f"  {D}Targeting {f_total:,} Files & {d_total:,} Folders | Platform: {sys.platform} | Build: 2026.05.13{RS}")
    
    try:
        check_python()
        resolve_dependencies()
        audit_security_binaries()
        provision_infrastructure()
    except KeyboardInterrupt:
        print(f"\n  {Y}Bootstrap aborted by user.{RS}")
        sys.exit(0)

    elapsed = time.time() - t0
    print(f"\n  {G}{B}Bootstrap Complete ({elapsed:.1f}s). All systems nominal.{RS}")

if __name__ == "__main__":
    bootstrap()
    launch()
