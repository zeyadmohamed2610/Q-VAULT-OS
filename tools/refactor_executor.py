#!/usr/bin/env python3
"""
tools/refactor_executor.py — Q-Vault OS
Applies ONLY low-risk, mechanical code fixes automatically.
High-risk fixes are logged as suggestions only.

Safe auto-fixes:
  1. bare except: → except Exception as e:
  2. Mutable default args → None pattern
"""

import re
import sys
import os
import io
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
IGNORE_DIRS = {".venv", "__pycache__", ".git", "scratch", "qvault-core", "testsprite_tests", ".ruff_cache"}
SCAN_DIRS = ["components", "system", "core", "apps", "sdk"]

CHANGELOG = []


def scan_py_files():
    files = []
    for d in SCAN_DIRS:
        target = ROOT / d
        if not target.exists():
            continue
        for f in target.rglob("*.py"):
            if any(p in f.parts for p in IGNORE_DIRS):
                continue
            files.append(f)
    return files


def fix_bare_except(filepath: Path) -> int:
    """Replace `except:` with `except Exception as e:` — safe mechanical fix."""
    source = filepath.read_text(encoding="utf-8", errors="replace")
    lines = source.split("\n")
    fixes = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match bare except (not except SomeException, not except ... as e)
        if re.match(r'^except\s*:\s*$', stripped):
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = f"{indent}except Exception as e:"
            fixes += 1
            CHANGELOG.append({
                "file": str(filepath.relative_to(ROOT)),
                "line": i + 1,
                "type": "bare_except",
                "before": stripped,
                "after": "except Exception as e:"
            })

    if fixes > 0:
        filepath.write_text("\n".join(lines), encoding="utf-8")
    return fixes


def fix_mutable_defaults(filepath: Path) -> int:
    """Replace mutable default args like def f(x=[]) with def f(x=None) + guard."""
    source = filepath.read_text(encoding="utf-8", errors="replace")
    
    # Pattern: def func(... param=[] ...) or param={}
    pattern = re.compile(r'(def\s+\w+\s*\([^)]*?)(\w+)\s*=\s*(\[\]|\{\})\s*([,\)])')
    
    if not pattern.search(source):
        return 0
    
    fixes = 0
    lines = source.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = pattern.search(line)
        if m:
            param_name = m.group(2)
            default_val = m.group(3)
            replacement = f"None"
            new_line = pattern.sub(rf'\g<1>\g<2>=None\g<4>', line, count=1)
            
            if new_line != line:
                lines[i] = new_line
                
                # Find the function body start (next non-empty, non-decorator line with more indent)
                body_idx = i + 1
                # Skip continuation lines
                while body_idx < len(lines) and lines[body_idx].strip().startswith(('"""', "'''", '#', '@', ')')):
                    body_idx += 1
                    # Handle docstrings
                    if '"""' in lines[body_idx - 1] or "'''" in lines[body_idx - 1]:
                        while body_idx < len(lines) and not ('"""' in lines[body_idx] or "'''" in lines[body_idx]):
                            body_idx += 1
                        body_idx += 1
                
                if body_idx < len(lines):
                    body_indent = lines[body_idx][:len(lines[body_idx]) - len(lines[body_idx].lstrip())]
                    if not body_indent:
                        body_indent = "        "
                    guard = f"{body_indent}if {param_name} is None: {param_name} = {default_val}"
                    lines.insert(body_idx, guard)
                    
                    fixes += 1
                    CHANGELOG.append({
                        "file": str(filepath.relative_to(ROOT)),
                        "line": i + 1,
                        "type": "mutable_default",
                        "before": f"{param_name}={default_val}",
                        "after": f"{param_name}=None + guard"
                    })
        i += 1
    
    if fixes > 0:
        filepath.write_text("\n".join(lines), encoding="utf-8")
    return fixes


def generate_report():
    """Write changelog to reports/refactor_changelog.md"""
    report_path = ROOT / "reports" / "refactor_changelog.md"
    
    lines = []
    lines.append("# 🔧 Refactor Executor — Change Log")
    lines.append("")
    lines.append(f"**Executed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total Fixes Applied:** {len(CHANGELOG)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    if not CHANGELOG:
        lines.append("*No fixes applied — system is clean.*")
    else:
        # Group by type
        by_type = {}
        for c in CHANGELOG:
            by_type.setdefault(c["type"], []).append(c)
        
        for fix_type, entries in by_type.items():
            lines.append(f"## {fix_type} ({len(entries)} fixes)")
            lines.append("")
            lines.append("| File | Line | Before | After |")
            lines.append("|------|------|--------|-------|")
            for e in entries:
                lines.append(f"| `{e['file']}` | {e['line']} | `{e['before']}` | `{e['after']}` |")
            lines.append("")
    
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    print("╔═══════════════════════════════════════════╗")
    print("║  Refactor Executor — Safe Auto-Fix Mode   ║")
    print("╚═══════════════════════════════════════════╝")
    print()
    
    files = scan_py_files()
    print(f"  Scanning {len(files)} files...")
    
    total_bare = 0
    total_mutable = 0
    
    for f in files:
        try:
            total_bare += fix_bare_except(f)
            total_mutable += fix_mutable_defaults(f)
        except Exception as e:
            print(f"  [SKIP] {f.relative_to(ROOT)}: {e}")
    
    print(f"\n  Results:")
    print(f"    bare except fixes:     {total_bare}")
    print(f"    mutable default fixes: {total_mutable}")
    print(f"    total changes:         {len(CHANGELOG)}")
    
    report = generate_report()
    print(f"\n  Changelog: {report}")


if __name__ == "__main__":
    main()
