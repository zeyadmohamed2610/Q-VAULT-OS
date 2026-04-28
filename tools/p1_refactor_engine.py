#!/usr/bin/env python3
"""
tools/p1_refactor_engine.py — Q-Vault OS
Controlled Refactor Engine (One-by-One Execution)

Applies a given code transformation to a file, then:
1. Runs tests
2. Runs audit
3. Compares score
If score drops or tests fail -> ROLLBACK
If score improves or stays stable with fewer issues -> COMMIT
"""

import sys
import os
import io
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
AUDIT_SCRIPT = ROOT / "run_full_audit.py"
HISTORY_FILE = ROOT / "reports" / "progress_history.json"


def get_latest_metrics():
    """Run audit and return the latest metrics from progress history."""
    print("  [ENGINE] Running full system audit...", end=" ", flush=True)
    res = subprocess.run([sys.executable, str(AUDIT_SCRIPT)], capture_output=True, text=True)
    if res.returncode != 0:
        print("CRASHED")
        return None
    
    if not HISTORY_FILE.exists():
        print("NO HISTORY")
        return None

    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        print(f"Score: {history[-1]['score']}/100")
        return history[-1]
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def run_tests():
    """Run pytest suite directly."""
    print("  [ENGINE] Running test suite...", end=" ", flush=True)
    res = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], capture_output=True, text=True, cwd=str(ROOT))
    if res.returncode == 0:
        print("PASS")
        return True
    else:
        print("FAIL")
        return False


def apply_and_verify(filepath: Path, transform_func, description: str):
    """
    Apply a transformation function to a file.
    The transform_func takes the file content string and returns the new string.
    """
    print(f"\n{'='*60}")
    print(f"  Attempting: {description}")
    print(f"  Target: {filepath.relative_to(ROOT)}")
    print(f"{'='*60}")

    # 1. Get baseline
    baseline = get_latest_metrics()
    if not baseline:
        print("❌ Cannot get baseline metrics. Aborting.")
        return False

    # 2. Backup original file
    original_content = filepath.read_text(encoding="utf-8", errors="replace")

    # 3. Apply transformation
    try:
        new_content = transform_func(original_content)
        if new_content == original_content:
            print("  [ENGINE] No changes needed. Skipping.")
            return True
        
        filepath.write_text(new_content, encoding="utf-8")
        print("  [ENGINE] Transformation applied. Verifying...")
    except Exception as e:
        print(f"❌ Transformation failed: {e}")
        return False

    # 4. Verify tests
    if not run_tests():
        print("❌ Tests failed! Rolling back...")
        filepath.write_text(original_content, encoding="utf-8")
        return False

    # 5. Verify audit score
    new_metrics = get_latest_metrics()
    if not new_metrics:
        print("❌ Audit crashed! Rolling back...")
        filepath.write_text(original_content, encoding="utf-8")
        return False

    # 6. Compare
    score_diff = new_metrics["score"] - baseline["score"]
    issues_diff = new_metrics["total"] - baseline["total"]

    print(f"\n  [RESULT] Score: {baseline['score']} -> {new_metrics['score']} ({score_diff:+#d})")
    print(f"  [RESULT] Issues: {baseline['total']} -> {new_metrics['total']} ({issues_diff:+#d})")

    if score_diff < 0:
        print("❌ Score dropped! Rolling back...")
        filepath.write_text(original_content, encoding="utf-8")
        return False
    
    if score_diff == 0 and issues_diff >= 0:
        print("⚠️ No actual improvement. Rolling back to keep git clean...")
        filepath.write_text(original_content, encoding="utf-8")
        return False

    print("✅ Change VERIFIED and COMMITTED.")
    return True


# ── Example Transformers ──

def example_remove_bare_except(content: str) -> str:
    """Mechanical fix: replace `except:` with `except Exception as e:`"""
    lines = content.split("\n")
    for i in range(len(lines)):
        if lines[i].strip() == "except:":
            lines[i] = lines[i].replace("except:", "except Exception as e:")
    return "\n".join(lines)


def run_ui_auto_fix_on_file(filepath: Path):
    """Bridge to use ui_auto_fix on a single file safely."""
    # We will import the fix_file function from ui_auto_fix
    sys.path.insert(0, str(ROOT / "tools"))
    import ui_auto_fix

    def transform(content):
        # The ui_auto_fix mutates the file directly.
        # So we write the content, call fix_file, read it back, then return it.
        # The engine will write it again, which is fine.
        temp_path = filepath.with_suffix('.py.tmp')
        temp_path.write_text(content, encoding="utf-8")
        fixes = ui_auto_fix.fix_file(temp_path)
        new_content = temp_path.read_text(encoding="utf-8")
        temp_path.unlink()
        return new_content

    apply_and_verify(filepath, transform, f"Strict THEME UI Fix on {filepath.name}")


if __name__ == "__main__":
    print("Q-Vault OS — Controlled Refactor Engine")
    print("Run this file by importing it and calling apply_and_verify(),")
    print("or pass a specific script argument (not yet implemented).")
