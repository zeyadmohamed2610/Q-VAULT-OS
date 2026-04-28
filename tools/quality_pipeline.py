#!/usr/bin/env python3
"""
tools/quality_pipeline.py — Q-Vault OS
Master Continuous Quality Loop.

Runs the full pipeline in order:
  1. Full system audit (baseline)
  2. Refactor planner (generates plan)
  3. Safe auto-fixes (code quality)
  4. UI stabilization scan
  5. Full system audit (post-fix)
  6. Regression diff report

Usage: python tools/quality_pipeline.py
"""

import sys
import os
import io
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
PYTHON = sys.executable


def run_step(label: str, script: str) -> tuple:
    """Run a pipeline step and return (success, output)."""
    print(f"\n{'='*60}")
    print(f"  STEP: {label}")
    print(f"{'='*60}")
    
    script_path = ROOT / script
    if not script_path.exists():
        print(f"  [ERROR] Script not found: {script_path}")
        return False, ""
    
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [PYTHON, str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )
        duration = time.perf_counter() - t0
        output = result.stdout + result.stderr
        
        # Print output
        for line in output.strip().split("\n"):
            print(f"  {line}")
        
        print(f"\n  [{duration:.1f}s] {'PASS' if result.returncode == 0 else 'FAIL'}")
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] Step took > 120s")
        return False, "timeout"
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, str(e)


def extract_score(output: str) -> int:
    """Extract health score from audit output."""
    m = re.search(r"Health Score:\s*(\d+)/100", output)
    return int(m.group(1)) if m else -1


def extract_issue_counts(output: str) -> dict:
    """Extract critical/major/minor counts from audit output."""
    counts = {"critical": 0, "major": 0, "minor": 0}
    m = re.search(r"Critical:\s*(\d+)\s+Major:\s*(\d+)\s+Minor:\s*(\d+)", output)
    if m:
        counts["critical"] = int(m.group(1))
        counts["major"] = int(m.group(2))
        counts["minor"] = int(m.group(3))
    return counts


def generate_diff_report(baseline_score, baseline_counts, final_score, final_counts, steps_log):
    """Generate the regression diff report."""
    diff_path = ROOT / "reports" / "refactor_diff.md"
    
    score_delta = final_score - baseline_score
    delta_icon = "📈" if score_delta > 0 else ("📉" if score_delta < 0 else "➡️")
    
    lines = []
    lines.append("# 📊 Q-Vault OS — Refactoring Diff Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Score Comparison")
    lines.append("")
    lines.append("| Metric | Before | After | Delta |")
    lines.append("|--------|--------|-------|-------|")
    lines.append(f"| **Health Score** | {baseline_score}/100 | {final_score}/100 | {delta_icon} {score_delta:+d} |")
    
    for sev in ["critical", "major", "minor"]:
        b = baseline_counts.get(sev, 0)
        a = final_counts.get(sev, 0)
        d = a - b
        icon = "✅" if d < 0 else ("⚠️" if d > 0 else "—")
        lines.append(f"| {sev.title()} | {b} | {a} | {icon} {d:+d} |")
    lines.append("")
    
    # Regression check
    lines.append("## Regression Check")
    lines.append("")
    
    regressions = []
    if final_score < baseline_score:
        regressions.append(f"Score decreased by {abs(score_delta)} points")
    if final_counts.get("critical", 0) > baseline_counts.get("critical", 0):
        regressions.append("New critical issues introduced")
    if final_counts.get("major", 0) > baseline_counts.get("major", 0):
        regressions.append("New major issues introduced")
    
    if regressions:
        lines.append("### ⚠️ Regressions Detected")
        for r in regressions:
            lines.append(f"- {r}")
    else:
        lines.append("### ✅ No Regressions")
        lines.append("> All metrics improved or remained stable.")
    lines.append("")
    
    # Pipeline steps
    lines.append("## Pipeline Steps")
    lines.append("")
    lines.append("| Step | Status | Duration |")
    lines.append("|------|--------|----------|")
    for step in steps_log:
        icon = "✅" if step["ok"] else "❌"
        lines.append(f"| {step['label']} | {icon} | — |")
    lines.append("")
    
    # Verdict
    lines.append("---")
    lines.append("")
    if final_score >= 75 and final_counts.get("critical", 0) == 0:
        lines.append("## 🟢 VERDICT: Production Ready")
    elif final_score > baseline_score and not regressions:
        lines.append("## 🟡 VERDICT: Improving — Continue Hardening")
    else:
        lines.append("## 🔴 VERDICT: Not Ready — Issues Remain")
    lines.append("")
    
    diff_path.write_text("\n".join(lines), encoding="utf-8")
    
    # Update progress_history.json
    history_path = ROOT / "reports" / "progress_history.json"
    import json
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    history.append({
        "timestamp": datetime.now().isoformat(),
        "score": final_score,
        "critical": final_counts.get("critical", 0),
        "major": final_counts.get("major", 0),
        "minor": final_counts.get("minor", 0),
        "regressions": regressions
    })
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    
    return diff_path, len(regressions) > 0

def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — Continuous Quality Pipeline v1.0  ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps_log = []
    
    # Step 0: Runtime Integrity Guard (MANDATORY GATE)
    ok, out0 = run_step("0/6 — Runtime Integrity Guard", "tools/runtime_integrity_guard.py")
    steps_log.append({"label": "Integrity Guard", "ok": ok})
    if not ok:
        print("\n  [CRITICAL] Runtime Integrity Guard FAILED!")
        print("  System stability is compromised by syntax errors. Pipeline aborted.")
        sys.exit(1)
    
    # Step 1: Baseline audit
    ok, out1 = run_step("1/6 — Baseline Audit", "run_full_audit.py")
    steps_log.append({"label": "Baseline Audit", "ok": ok})
    baseline_score = extract_score(out1)
    baseline_counts = extract_issue_counts(out1)
    print(f"\n  Baseline: {baseline_score}/100 | C:{baseline_counts['critical']} M:{baseline_counts['major']} m:{baseline_counts['minor']}")
    
    # Step 2: Generate refactor plan
    ok, out2 = run_step("2/6 — Refactor Planner", "tools/refactor_planner.py")
    steps_log.append({"label": "Refactor Planner", "ok": ok})
    
    # Step 3: Safe auto-fixes
    ok, out3 = run_step("3/6 — Safe Auto-Fixes", "tools/refactor_executor.py")
    steps_log.append({"label": "Code Auto-Fixes", "ok": ok})
    
    # Step 4: UI stabilization
    ok, out4 = run_step("4/6 — UI Stabilization", "tools/ui_auto_fix.py")
    steps_log.append({"label": "UI Stabilization", "ok": ok})
    
    # Step 5: Post-fix audit
    ok, out5 = run_step("5/6 — Post-Fix Audit", "run_full_audit.py")
    steps_log.append({"label": "Post-Fix Audit", "ok": ok})
    final_score = extract_score(out5)
    final_counts = extract_issue_counts(out5)
    
    # Generate diff
    diff_path, has_regression = generate_diff_report(baseline_score, baseline_counts, final_score, final_counts, steps_log)
    
    # Final summary
    delta = final_score - baseline_score
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Baseline:  {baseline_score}/100")
    print(f"  Final:     {final_score}/100 ({'+'if delta>=0 else ''}{delta})")
    print(f"  Diff:      {diff_path}")
    print(f"  Plan:      {ROOT / 'reports' / 'refactor_plan.md'}")
    print(f"  Report:    {ROOT / 'reports' / 'final_system_report.md'}")
    
    if has_regression:
        print("\n  [FATAL] Pipeline failed due to detected regressions!")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
