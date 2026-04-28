#!/usr/bin/env python3
"""
tools/god_object_splitter.py — Q-Vault OS
AST-based God Object analyzer. Suggests extraction of method clusters
into handler classes. DOES NOT auto-apply — suggestion only.
"""

import ast
import sys
import io
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
SCAN_DIRS = ["components", "system", "core", "apps"]
IGNORE_DIRS = {".venv", "__pycache__", ".git", "scratch", "qvault-core"}
GOD_THRESHOLD = 15  # methods


def analyze_class(node: ast.ClassDef, source_lines: list) -> dict:
    """Analyze a class and detect method clusters."""
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Find what self.attributes this method accesses
            attrs_read = set()
            attrs_write = set()
            calls_to_self = set()

            for n in ast.walk(item):
                if isinstance(n, ast.Attribute):
                    val = getattr(n, 'value', None)
                    if isinstance(val, ast.Name) and val.id == 'self':
                        if isinstance(getattr(n, 'ctx', None), ast.Store):
                            attrs_write.add(n.attr)
                        else:
                            attrs_read.add(n.attr)
                # Self method calls
                if isinstance(n, ast.Call):
                    func = getattr(n, 'func', None)
                    if isinstance(func, ast.Attribute):
                        fval = getattr(func, 'value', None)
                        if isinstance(fval, ast.Name) and fval.id == 'self':
                            calls_to_self.add(func.attr)

            end_line = getattr(item, 'end_lineno', item.lineno + 10)
            methods.append({
                "name": item.name,
                "lineno": item.lineno,
                "length": end_line - item.lineno,
                "attrs_read": attrs_read,
                "attrs_write": attrs_write,
                "calls": calls_to_self,
                "is_private": item.name.startswith("_") and not item.name.startswith("__"),
                "is_dunder": item.name.startswith("__") and item.name.endswith("__"),
            })

    if len(methods) < GOD_THRESHOLD:
        return None

    # Cluster methods by shared attribute access
    clusters = _cluster_methods(methods)

    return {
        "name": node.name,
        "lineno": node.lineno,
        "total_methods": len(methods),
        "methods": methods,
        "clusters": clusters,
    }


def _cluster_methods(methods: list) -> list:
    """Group methods into logical clusters based on shared state access."""
    clusters = defaultdict(list)

    for m in methods:
        if m["is_dunder"]:
            clusters["Core (lifecycle)"].append(m["name"])
            continue

        all_attrs = m["attrs_read"] | m["attrs_write"]
        name = m["name"].lower()

        # Heuristic clustering by naming convention
        if any(k in name for k in ["drag", "mouse", "press", "release", "move"]):
            clusters["DragHandler"].append(m["name"])
        elif any(k in name for k in ["snap", "tile", "zone", "edge"]):
            clusters["SnapController"].append(m["name"])
        elif any(k in name for k in ["focus", "activate", "raise", "bring"]):
            clusters["FocusManager"].append(m["name"])
        elif any(k in name for k in ["anim", "fade", "glow", "effect"]):
            clusters["AnimationController"].append(m["name"])
        elif any(k in name for k in ["style", "theme", "css", "color"]):
            clusters["StyleManager"].append(m["name"])
        elif any(k in name for k in ["menu", "context", "action", "click"]):
            clusters["MenuHandler"].append(m["name"])
        elif any(k in name for k in ["state", "status", "mode", "toggle"]):
            clusters["StateController"].append(m["name"])
        elif any(k in name for k in ["layout", "setup", "init", "build", "create"]):
            clusters["UIBuilder"].append(m["name"])
        elif any(k in name for k in ["event", "signal", "emit", "subscribe", "on_"]):
            clusters["EventWiring"].append(m["name"])
        elif any(k in name for k in ["save", "load", "persist", "config"]):
            clusters["PersistenceManager"].append(m["name"])
        elif any(k in name for k in ["process", "spawn", "kill", "terminate"]):
            clusters["ProcessController"].append(m["name"])
        elif any(k in name for k in ["security", "auth", "trust", "quarantine"]):
            clusters["SecurityHandler"].append(m["name"])
        else:
            clusters["Uncategorized"].append(m["name"])

    # Filter out small clusters (< 2 methods)
    return {k: v for k, v in clusters.items() if len(v) >= 2 or k == "Core (lifecycle)"}


def scan_all() -> list:
    """Scan all Python files for God Objects."""
    results = []

    for d in SCAN_DIRS:
        target = ROOT / d
        if not target.exists():
            continue
        for f in target.rglob("*.py"):
            if any(p in f.parts for p in IGNORE_DIRS):
                continue
            try:
                source = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(f))
                source_lines = source.split("\n")
                rel = str(f.relative_to(ROOT))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        result = analyze_class(node, source_lines)
                        if result:
                            result["file"] = rel
                            results.append(result)
            except Exception:
                pass

    return sorted(results, key=lambda x: x["total_methods"], reverse=True)


def generate_report(results: list):
    """Generate the God Object analysis report."""
    report_path = ROOT / "reports" / "god_object_analysis.md"
    lines = []
    lines.append("# God Object Analysis Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**God Objects Found:** {len(results)} (threshold: {GOD_THRESHOLD}+ methods)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Class | File | Methods | Clusters | Severity |")
    lines.append("|-------|------|---------|----------|----------|")
    for r in results:
        sev = "CRITICAL" if r["total_methods"] > 30 else ("HIGH" if r["total_methods"] > 20 else "MEDIUM")
        lines.append(f"| `{r['name']}` | `{r['file']}` | {r['total_methods']} | {len(r['clusters'])} | {sev} |")
    lines.append("")

    # Detailed analysis for each God Object
    for r in results:
        lines.append(f"## `{r['name']}` ({r['total_methods']} methods)")
        lines.append(f"> File: `{r['file']}` Line: {r['lineno']}")
        lines.append("")

        lines.append("### Suggested Extraction")
        lines.append("")
        for cluster_name, methods in r["clusters"].items():
            if cluster_name == "Core (lifecycle)":
                lines.append(f"**{cluster_name}** (keep in main class)")
                for m in methods:
                    lines.append(f"  - `{m}`")
            else:
                lines.append(f"**Extract -> `{cluster_name}`** ({len(methods)} methods)")
                for m in methods:
                    lines.append(f"  - `{m}`")
            lines.append("")

        # Generate example refactored code
        extractable = {k: v for k, v in r["clusters"].items() if k != "Core (lifecycle)" and k != "Uncategorized" and len(v) >= 2}
        if extractable:
            lines.append("### Example Refactored Structure")
            lines.append("```python")
            for handler_name, methods in list(extractable.items())[:3]:
                lines.append(f"class {handler_name}:")
                lines.append(f"    def __init__(self, parent):")
                lines.append(f"        self._parent = parent")
                for m in methods[:4]:
                    lines.append(f"    def {m}(self, ...): ...")
                lines.append("")
            lines.append(f"class {r['name']}:  # Refactored facade")
            lines.append(f"    def __init__(self):")
            for handler_name in list(extractable.keys())[:3]:
                attr = handler_name[0].lower() + handler_name[1:]
                lines.append(f"        self._{attr} = {handler_name}(self)")
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    print("=" * 50)
    print("  God Object Splitter — Analysis Mode")
    print("=" * 50)
    print()

    results = scan_all()
    print(f"  Found {len(results)} God Objects:")
    for r in results:
        print(f"    {r['name']:30s} {r['total_methods']:3d} methods  ({r['file']})")

    report = generate_report(results)
    print(f"\n  Report: {report}")


if __name__ == "__main__":
    main()
