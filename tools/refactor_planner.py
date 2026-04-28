#!/usr/bin/env python3
"""
tools/refactor_planner.py — Q-Vault OS
Parses final_system_report.md and generates a prioritized,
step-by-step refactor plan with risk levels and fix strategies.
"""

import re
import sys
import os
import io
from pathlib import Path
from datetime import datetime
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
REPORT_IN = ROOT / "reports" / "final_system_report.md"
PLAN_OUT = ROOT / "reports" / "refactor_plan.md"

# ── Fix Strategy Templates ──

STRATEGIES = {
    "bare_except": {
        "risk": "low",
        "auto": True,
        "steps": [
            "Replace `except:` with `except Exception as e:`",
            "Add `logger.error(f'...{e}')` if logger available",
            "Verify no intentional BaseException catch"
        ]
    },
    "long_function": {
        "risk": "medium",
        "auto": False,
        "steps": [
            "Identify logical sections via comment blocks",
            "Extract each section into a private helper method",
            "Call helpers from original method in sequence",
            "Run tests to verify behavior preserved"
        ]
    },
    "god_object": {
        "risk": "high",
        "auto": False,
        "steps": [
            "Identify responsibility clusters in the class",
            "Extract each cluster into a handler/mixin class",
            "Keep the original class as a facade delegating to handlers",
            "Preserve all public method signatures",
            "Update internal references only"
        ]
    },
    "circular_import": {
        "risk": "medium",
        "auto": False,
        "steps": [
            "Move shared types to a common module (e.g. core/types.py)",
            "Use lazy imports (inside functions) for runtime-only deps",
            "Verify with `python -c 'import <module>'` after change"
        ]
    },
    "hardcoded_color": {
        "risk": "low",
        "auto": True,
        "steps": [
            "Import THEME from assets.theme",
            "Map each hex color to the closest THEME token",
            "Replace hex literal with f-string THEME reference",
            "Convert surrounding string to f-string if needed",
            "Escape CSS braces as {{ }}"
        ]
    },
    "dead_event": {
        "risk": "low",
        "auto": True,
        "steps": [
            "Verify event is not referenced in SDK (sdk/events.py)",
            "Remove enum member from SystemEvent",
            "Run import check to confirm no NameError"
        ]
    },
    "emit_only": {
        "risk": "low",
        "auto": False,
        "steps": [
            "Determine if a subscriber should exist (feature gap)",
            "If yes: wire subscriber in appropriate controller",
            "If no: add `# emit-only` annotation comment",
            "Consider if SmartNotificationController should handle it"
        ]
    },
    "subscribe_only": {
        "risk": "medium",
        "auto": False,
        "steps": [
            "Find where this event SHOULD be emitted",
            "Add emit call at the correct lifecycle point",
            "Verify subscriber receives payload correctly"
        ]
    },
    "test_error": {
        "risk": "medium",
        "auto": False,
        "steps": [
            "Read the test file and identify the assertion",
            "Check if test relies on deprecated API",
            "Fix test payload or update assertion",
            "Run pytest on the specific file"
        ]
    },
    "mutable_default": {
        "risk": "low",
        "auto": True,
        "steps": [
            "Replace `def f(x=[]):` with `def f(x=None):`",
            "Add `if x is None: x = []` as first line",
        ]
    }
}


def classify_issue(text: str) -> str:
    """Map issue text to a strategy key."""
    t = text.lower()
    if "bare `except:`" in t or "bare except" in t:
        return "bare_except"
    if "long function" in t:
        return "long_function"
    if "god object" in t:
        return "god_object"
    if "circular import" in t:
        return "circular_import"
    if "hardcoded hex" in t:
        return "hardcoded_color"
    if "dead event" in t:
        return "dead_event"
    if "emit-only" in t:
        return "emit_only"
    if "subscribe-only" in t:
        return "subscribe_only"
    if "error:" in t or "fail:" in t:
        return "test_error"
    if "mutable default" in t:
        return "mutable_default"
    return "long_function"  # fallback


def parse_report(path: Path) -> dict:
    """Parse the markdown report into structured issue lists."""
    text = path.read_text(encoding="utf-8")
    
    result = {
        "score": 0,
        "critical": [],
        "major": [],
        "minor": [],
    }
    
    # Extract score
    m = re.search(r"Health Score\*\* \| \*\*(\d+)/100", text)
    if m:
        result["score"] = int(m.group(1))
    
    # Extract issues by section
    current_sev = None
    for line in text.split("\n"):
        line = line.strip()
        if "🚨 Critical" in line:
            current_sev = "critical"
            continue
        elif "⚠️ Major" in line:
            current_sev = "major"
            continue
        elif "📝 Minor" in line:
            current_sev = "minor"
            continue
        elif line.startswith("## ") and current_sev:
            current_sev = None
            continue
        
        if current_sev and line.startswith("- "):
            # Parse: - **[Phase]** `file:line` — message
            m = re.match(r"- \*\*\[(.+?)\]\*\* `(.+?)`\s*—\s*(.+)", line)
            if m:
                result[current_sev].append({
                    "phase": m.group(1),
                    "file": m.group(2),
                    "message": m.group(3),
                })
    
    return result


def generate_plan(data: dict) -> str:
    """Generate the refactor plan markdown."""
    lines = []
    lines.append("# 🔧 Q-Vault OS — Refactoring Plan")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Baseline Score:** {data['score']}/100")
    lines.append(f"**Total Issues:** {len(data['critical']) + len(data['major']) + len(data['minor'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group into batches
    batches = [
        ("Batch 1: Critical Fixes 🚨", data["critical"], "Must fix before ANY deployment"),
        ("Batch 2: Architecture (God Objects)", [i for i in data["major"] if "god object" in i["message"].lower()], "Split safely without changing public API"),
        ("Batch 3: UI Consistency (THEME)", [i for i in data["major"] + data["minor"] if "hardcoded hex" in i["message"].lower()], "Auto-fixable — replace hex → THEME tokens"),
        ("Batch 4: EventBus Wiring", [i for i in data["major"] + data["minor"] if any(k in i["message"].lower() for k in ["dead event", "emit-only", "subscribe-only"])], "Wire orphan events or remove dead ones"),
        ("Batch 5: Code Quality", [i for i in data["major"] + data["minor"] if any(k in i["message"].lower() for k in ["long function", "bare", "mutable"])], "Safe mechanical refactors"),
    ]
    
    # Summary table
    lines.append("## Batch Summary")
    lines.append("")
    lines.append("| Batch | Issues | Auto-Fixable | Risk |")
    lines.append("|-------|--------|-------------|------|")
    for title, issues, _ in batches:
        auto = sum(1 for i in issues if STRATEGIES.get(classify_issue(i["message"]), {}).get("auto", False))
        max_risk = "low"
        for i in issues:
            r = STRATEGIES.get(classify_issue(i["message"]), {}).get("risk", "low")
            if r == "high": max_risk = "high"
            elif r == "medium" and max_risk == "low": max_risk = "medium"
        lines.append(f"| {title.split(':')[0]}:{title.split(':')[1][:30]} | {len(issues)} | {auto} | {max_risk} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed batches
    for title, issues, desc in batches:
        lines.append(f"## {title}")
        lines.append(f"> {desc}")
        lines.append("")
        
        if not issues:
            lines.append("*No issues in this batch.*")
            lines.append("")
            continue
        
        for idx, issue in enumerate(issues, 1):
            strategy_key = classify_issue(issue["message"])
            strategy = STRATEGIES.get(strategy_key, STRATEGIES["long_function"])
            
            risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}[strategy["risk"]]
            auto_tag = " `[AUTO-FIX]`" if strategy["auto"] else ""
            
            lines.append(f"### {idx}. `{issue['file']}`{auto_tag}")
            lines.append(f"- **Problem:** {issue['message']}")
            lines.append(f"- **Risk:** {risk_icon} {strategy['risk'].upper()}")
            lines.append(f"- **Fix Strategy:**")
            for step in strategy["steps"]:
                lines.append(f"  1. {step}")
            lines.append("")
    
    # Execution order
    lines.append("---")
    lines.append("")
    lines.append("## Recommended Execution Order")
    lines.append("")
    lines.append("```")
    lines.append("1. python tools/refactor_executor.py   # Batch 5 auto-fixes (bare except, mutable defaults)")
    lines.append("2. python tools/ui_auto_fix.py         # Batch 3 auto-fixes (hex → THEME)")
    lines.append("3. python run_full_audit.py             # Verify score improved")
    lines.append("4. Manual: Batch 1 critical fixes       # Fix failing tests")
    lines.append("5. Manual: Batch 2 God Objects           # Careful decomposition")
    lines.append("6. Manual: Batch 4 EventBus wiring       # Connect orphan events")
    lines.append("7. python tools/quality_pipeline.py     # Full regression check")
    lines.append("```")
    lines.append("")
    
    return "\n".join(lines)


def main():
    if not REPORT_IN.exists():
        print(f"[ERROR] Report not found: {REPORT_IN}")
        print("Run `python run_full_audit.py` first.")
        sys.exit(1)
    
    print("[PLANNER] Parsing report...", end=" ")
    data = parse_report(REPORT_IN)
    print(f"found {len(data['critical'])}C / {len(data['major'])}M / {len(data['minor'])}m issues")
    
    print("[PLANNER] Generating refactor plan...", end=" ")
    plan = generate_plan(data)
    PLAN_OUT.write_text(plan, encoding="utf-8")
    print(f"done → {PLAN_OUT}")


if __name__ == "__main__":
    main()
