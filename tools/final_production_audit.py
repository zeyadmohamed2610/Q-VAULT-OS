#!/usr/bin/env python3
"""
tools/final_production_audit.py — Q-Vault OS
Final Production Readiness Audit

Combines all audit dimensions into a single weighted score:
- Architecture (25%)
- Runtime Watchdog (20%)
- Threading Safety (15%)
- UI Consistency (15%)
- Crash Survivability (10%)
- EventBus Integrity (10%)
- State Integrity (5%)
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.append(os.getcwd())

REPORT_DIR = Path("reports")

# ── Score Weights ────────────────────────────────────────────────
WEIGHTS = {
    "architecture":       0.25,
    "runtime":            0.20,
    "threading":          0.15,
    "ui_consistency":     0.15,
    "crash_recovery":     0.10,
    "event_bus":          0.10,
    "state_integrity":    0.05,
}

# ────────────────────────────────────────────────────────────────

def run_tool(label: str, cmd: List[str], timeout: int = 90) -> Tuple[bool, str]:
    """Run a sub-tool and return (success, stdout)."""
    print(f"    ▶ Running {label}...", end=" ", flush=True)
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
        )
        ok = result.returncode == 0
        print("✓" if ok else "✗")
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")
        return ok, stdout + stderr
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return False, "TIMEOUT"
    except Exception as e:
        print(f"ERROR: {e}")
        return False, str(e)


# ── Individual Report Parsers ─────────────────────────────────────

def score_architecture() -> Tuple[float, str]:
    """Parse stabilization_report.md for violation count."""
    path = REPORT_DIR / "stabilization_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    if "Zero lateral/upward imports" in text or "All layer boundaries respected" in text:
        return 1.0, "0 layer violations"
    # Count violations
    violations = text.count("Layer Violation:")
    score = max(0.0, 1.0 - violations * 0.2)
    return score, f"{violations} violation(s) detected"


def score_runtime() -> Tuple[float, str]:
    """Parse long_runtime_report.md for stability verdict."""
    path = REPORT_DIR / "long_runtime_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    if "STABLE" in text and "UNSTABLE" not in text:
        return 1.0, "Runtime stable"
    if "MEMORY_LEAK" in text:
        return 0.3, "Memory leak detected"
    if "ZOMBIE_WIDGETS" in text:
        return 0.5, "Zombie widgets detected"
    return 0.7, "Runtime degraded"


def score_watchdog() -> Tuple[float, str]:
    """Parse runtime_watchdog_report.md."""
    path = REPORT_DIR / "runtime_watchdog_report.md"
    if not path.exists():
        return 0.5, "No watchdog report"
    text = path.read_text(encoding="utf-8")
    score = 1.0
    notes = []
    if "YES" in text:
        score -= 0.3
        notes.append("anomalies detected")
    mem_growth = 0.0
    for line in text.splitlines():
        if "Memory Growth" in line and "MB" in line:
            try:
                mem_growth = float(line.split("+")[-1].split("MB")[0].strip())
            except Exception:
                pass
    if mem_growth > 50:
        score -= 0.3
        notes.append(f"high memory growth +{mem_growth:.0f}MB")
    return max(0.0, score), ", ".join(notes) or "clean"


def score_threading() -> Tuple[float, str]:
    """Parse thread_safety_report.md."""
    path = REPORT_DIR / "thread_safety_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    highs = text.count("HIGH |") + text.count("| HIGH")
    warns = text.count("WARN |") + text.count("| WARN")
    score = 1.0 - (highs * 0.2) - (warns * 0.03)
    return max(0.0, min(1.0, score)), f"{highs} HIGH, {warns} WARN"


def score_ui_consistency() -> Tuple[float, str]:
    """Parse stabilization_report.md for UI score."""
    path = REPORT_DIR / "stabilization_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "UI Consistency Score" in line and "%" in line:
            try:
                pct = float(line.split(":")[1].replace("%", "").strip())
                return pct / 100.0, f"{pct:.0f}% token coverage"
            except Exception:
                pass
    return 0.5, "Could not parse score"


def score_crash_recovery() -> Tuple[float, str]:
    """Parse crash_recovery_report.md."""
    path = REPORT_DIR / "crash_recovery_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "Recovery Rate" in line and "%" in line:
            try:
                pct = float(line.split("|")[-2].replace("%", "").strip())
                return pct / 100.0, f"{pct:.0f}% recovery rate"
            except Exception:
                pass
    if "CRASH-RESILIENT" in text:
        return 1.0, "All scenarios passed"
    return 0.5, "Mixed results"


def score_event_bus() -> Tuple[float, str]:
    """Parse eventbus_cleanup_plan.md and final_system_report.md."""
    path = REPORT_DIR / "final_system_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    # Count EventBus issues from system report Phase 3
    issues = 0
    capturing = False
    for line in text.splitlines():
        if "phase_event_bus" in line.lower():
            capturing = True
        if capturing and "issues" in line.lower():
            try:
                issues = int(line.split(",")[1].split("issues")[0].strip())
            except Exception:
                pass
            capturing = False
    score = max(0.0, 1.0 - issues * 0.02)
    return score, f"{issues} event-bus issues"


def score_state_integrity() -> Tuple[float, str]:
    """Parse state_integrity_report.md."""
    path = REPORT_DIR / "state_integrity_report.md"
    if not path.exists():
        return 0.5, "No report found"
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "Integrity Score" in line and "%" in line:
            try:
                pct = float(line.split("|")[-2].replace("%", "").strip())
                return pct / 100.0, f"{pct:.0f}% integrity"
            except Exception:
                pass
    if "STATE INTEGRITY CONFIRMED" in text:
        return 1.0, "All checks passed"
    return 0.7, "Partial"


# ── History Regression Check ──────────────────────────────────────

def check_regression() -> Tuple[bool, str]:
    """Check if score regressed from last run."""
    path = REPORT_DIR / "progress_history.json"
    if not path.exists():
        return False, "No history"
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
        if len(history) >= 2:
            prev = history[-2].get("score", 0)
            curr = history[-1].get("score", 0)
            if curr < prev - 2:
                return True, f"Score dropped from {prev} → {curr}"
        return False, "No regression"
    except Exception:
        return False, "Could not parse history"


# ── Main Audit Runner ─────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — Final Production Readiness Audit  ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Run sub-tools first to generate fresh reports
    print("  Phase 1: Generating fresh sub-reports...")
    run_tool("Thread Safety Audit",    [sys.executable, "tools/thread_safety_audit.py"],      60)
    run_tool("State Integrity",         [sys.executable, "tools/state_integrity_validator.py"], 30)
    run_tool("Crash Recovery",          [sys.executable, "tools/crash_recovery_tester.py"],    60)
    run_tool("Stabilization Enforcer",  [sys.executable, "tools/stabilization_enforcer.py"],   30)
    run_tool("Telemetry Self-Test",     [sys.executable, "system/telemetry.py"],               10)
    print()

    print("  Phase 2: Scoring dimensions...")
    arch_score,  arch_note  = score_architecture()
    rt_score,    rt_note    = score_runtime()
    wd_score,    wd_note    = score_watchdog()
    thr_score,   thr_note   = score_threading()
    ui_score,    ui_note    = score_ui_consistency()
    crash_score, crash_note = score_crash_recovery()
    eb_score,    eb_note    = score_event_bus()
    si_score,    si_note    = score_state_integrity()

    # Runtime score = average of long-runtime + watchdog
    combined_rt = (rt_score + wd_score) / 2.0

    scores = {
        "architecture":   (arch_score,     arch_note),
        "runtime":        (combined_rt,    f"simulator={rt_note}, watchdog={wd_note}"),
        "threading":      (thr_score,      thr_note),
        "ui_consistency": (ui_score,       ui_note),
        "crash_recovery": (crash_score,    crash_note),
        "event_bus":      (eb_score,       eb_note),
        "state_integrity":(si_score,       si_note),
    }

    weighted_total = sum(scores[k][0] * WEIGHTS[k] for k in WEIGHTS)
    final_score = round(weighted_total * 100)

    regression, reg_note = check_regression()

    # ── Determine Readiness ───────────────────────────────────────
    production_ready = (
        final_score >= 70
        and arch_score >= 0.8
        and crash_score >= 0.8
        and not regression
    )

    # ── Generate Report ───────────────────────────────────────────
    lines = [
        "# 🏁 Final Production Readiness Report",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 🎯 Overall Score",
        f"### {final_score}/100",
        "",
        f"| Verdict | {'✅ PRODUCTION READY' if production_ready else '🔴 NOT PRODUCTION READY'} |",
        f"|---------|---|",
        f"| Regression Detected | {'🔴 YES — ' + reg_note if regression else '✅ None'} |",
        "",
        "## 📊 Dimension Breakdown",
        "| Dimension | Raw Score | Weight | Contribution | Notes |",
        "|-----------|-----------|--------|--------------|-------|",
    ]

    for dim, (score, note) in scores.items():
        weight = WEIGHTS.get(dim, 0)
        contrib = score * weight * 100
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        lines.append(
            f"| {dim.replace('_', ' ').title()} | {bar} {score*100:.0f}% | {weight*100:.0f}% | {contrib:.1f}pt | {note} |"
        )

    lines.extend([
        "",
        "## 📈 Score Composition",
        "```",
        f"Architecture      {arch_score*100:5.0f}% × 25% = {arch_score*25:5.1f}pt",
        f"Runtime           {combined_rt*100:5.0f}% × 20% = {combined_rt*20:5.1f}pt",
        f"Threading         {thr_score*100:5.0f}% × 15% = {thr_score*15:5.1f}pt",
        f"UI Consistency    {ui_score*100:5.0f}% × 15% = {ui_score*15:5.1f}pt",
        f"Crash Recovery    {crash_score*100:5.0f}% × 10% = {crash_score*10:5.1f}pt",
        f"EventBus          {eb_score*100:5.0f}% × 10% = {eb_score*10:5.1f}pt",
        f"State Integrity   {si_score*100:5.0f}% ×  5% = {si_score*5:5.1f}pt",
        f"                                 ─────────",
        f"                        TOTAL = {final_score:5d}pt",
        "```",
        "",
        "## 🔍 Critical Issues",
    ])

    critical_issues = []
    if arch_score < 0.8:
        critical_issues.append("🔴 **Architecture**: Layer violations present")
    if crash_score < 0.8:
        critical_issues.append("🔴 **Crash Recovery**: Fault isolation gaps")
    if combined_rt < 0.7:
        critical_issues.append("🔴 **Runtime**: Memory leak or widget accumulation")
    if thr_score < 0.7:
        critical_issues.append("🟡 **Threading**: Unsafe patterns detected")
    if ui_score < 0.7:
        critical_issues.append("🟡 **UI**: <70% token coverage")
    if regression:
        critical_issues.append(f"🔴 **Regression**: {reg_note}")

    if not critical_issues:
        lines.append("✅ No critical issues detected.")
    for issue in critical_issues:
        lines.append(f"- {issue}")

    lines.extend([
        "",
        "## 🗺️ Path to Production (Remaining Work)",
    ])

    if ui_score < 0.85:
        lines.append(f"- UI token coverage: {ui_score*100:.0f}% → target 85%+ via design_tokens.py auto-fix pass")
    if eb_score < 0.9:
        lines.append("- EventBus: document remaining dangling emits as Feature Hooks")
    if thr_score < 0.9:
        lines.append("- Threading: replace blocking calls with QTimer-based async patterns")
    if crash_score < 1.0:
        lines.append("- Crash: harden exception isolation in EventBus handler dispatch")

    if production_ready:
        lines.extend([
            "",
            "## ✅ Production Certification",
            "> This system has passed the minimum threshold for operational deployment.",
            f"> Certified score: **{final_score}/100**",
        ])
    else:
        lines.extend([
            "",
            "## ⏳ Next Milestone",
            f"> Current: **{final_score}/100** | Target: **70/100**",
            f"> Gap: {max(0, 70 - final_score)} points",
        ])

    report_text = "\n".join(lines)
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "final_production_readiness.md").write_text(report_text, encoding="utf-8")

    print()
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │  Production Readiness Score: {final_score}/100      │")
    print(f"  │  Verdict: {'✅ PRODUCTION READY      ' if production_ready else '🔴 NOT PRODUCTION READY'}    │")
    print(f"  └─────────────────────────────────────────┘")
    print()
    for dim, (score, note) in scores.items():
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"    {dim:20s} {bar} {score*100:5.0f}%  {note}")
    print()
    print(f"  Report: reports/final_production_readiness.md")


if __name__ == "__main__":
    main()
