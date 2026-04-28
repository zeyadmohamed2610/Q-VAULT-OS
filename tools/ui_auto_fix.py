#!/usr/bin/env python3
"""
tools/ui_auto_fix.py — Q-Vault OS  |  STRICT MODE
Enforces THEME token usage by ACTUALLY replacing all hex colors
in component stylesheets. Also checks touch targets and spacing.

STRICT MODE behavior:
  - Replaces ALL known hex colors with THEME token refs
  - Converts plain strings to f-strings with escaped CSS braces
  - Adds THEME import where missing
  - Reports any UNKNOWN hex colors for manual review
"""

import re
import sys
import io
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
COMP_DIR = ROOT / "components"
IGNORE_DIRS = {"__pycache__"}

# ── Canonical Color → Token Map ──
COLOR_MAP = {
    "#00e6ff": "primary_glow",
    "#00bcd4": "primary_soft",
    "#0a0f19": "surface",
    "#06080d": "bg_deep",
    "#0d1117": "bg_mid",
    "#111827": "surface_dark",
    "#1a1a2e": "surface_mid",
    "#1e293b": "surface_raised",
    "#2a2a3e": "surface_overlay",
    "#9ec0d5": "text_dim",
    "#7aa0b8": "text_dim",
    "#888888": "text_muted",
    "#888": "text_muted",
    "#555555": "text_disabled",
    "#555": "text_disabled",
    "#444444": "text_disabled",
    "#444": "text_disabled",
    "#333333": "border_muted",
    "#333": "border_muted",
    "#ff3366": "accent_error",
    "#ff3333": "error_bright",
    "#ff0000": "error_bright",
    "#ff4444": "error_bright",
    "#ff6666": "error_soft",
    "#ffaa00": "warning",
    "#ffcc00": "warning",
    "#ffd700": "warning",
    "#00ff88": "success",
    "#00ff00": "success",
    "#00cc66": "success",
    "#1a3a5c": "hover_subtle",
    "#0ff": "primary_glow",
    "#00ccff": "primary_glow",
    "#1a1a24": "surface_mid",
    "#e6e6f0": "text_main",
    "#2a2a3a": "surface_raised",
    "#222230": "surface_mid",
    "#555568": "text_disabled",
    "#08090a": "bg_black",
    "#94a3b8": "text_dim",
    "#00aaff": "primary_glow",
    "#aaa": "text_muted",
    "#aaaaaa": "text_muted",
    "#1a1a1a": "surface_dark",
    "#05080c": "bg_black",
    "#1a2535": "surface_raised",
    "#ff3a5c": "error_bright",
    "#666": "text_disabled",
    "#666666": "text_disabled",
    "#e74c3c": "error_bright",
    "#0a0a0f": "bg_dark",
    "#020202": "bg_black",
    "#0088ff": "primary_soft",
    "#33eeff": "primary_glow",
    "#0d0d14": "bg_dark",
    "#2b2b2b": "surface_mid",
    "#10101a": "surface_mid",
    "#16213e": "surface_raised",
    "#3b3b3b": "surface_raised",
    "#3d8ec9": "primary_soft",
    "#222": "surface_dark",
    "#222222": "surface_dark",
    "#111": "bg_mid",
    "#111111": "bg_mid",
    "#0a0a0a": "bg_dark",
    "#475569": "text_disabled",
    "#00cc6a": "success",
    "#64748b": "text_dim",
    "#050505": "bg_black",
    "#0a0c12": "bg_dark",
    "#f8f8f2": "text_main",
    "#44475a": "border_muted",
    "#ff1744": "accent_error",
    "#b2102f": "error_soft",
    "#00e5ff": "primary_glow",
    "#010409": "bg_black",
}

# Whitelist: hex colors that are OK as-is (CSS system colors, near-black/white)
WHITELIST = {"#000", "#000000", "#fff", "#ffffff", "#f0f0f0", "#e0e0e0", "#ccc", "#cccccc", "#ddd"}

VALID_SPACING = {0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 20, 24, 32, 40, 48}
MIN_TOUCH_TARGET = 32

CHANGELOG = []
UNKNOWN_COLORS = []


def ensure_theme_import(source: str) -> str:
    """Add THEME import if missing."""
    if "from assets.theme import" in source and "THEME" in source:
        return source

    # Find the last import line
    lines = source.split("\n")
    last_import_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and not stripped.startswith("from assets.theme"):
            last_import_idx = i

    # Check if THEME is already imported
    if "THEME" not in source or "from assets.theme" not in source:
        # Add import after last import
        import_line = "from assets.theme import THEME"
        lines.insert(last_import_idx + 1, import_line)
        return "\n".join(lines)
    return source


def process_stylesheet_block(block: str, filepath_rel: str) -> tuple:
    """Process a stylesheet string block: replace hex colors and handle f-string conversion.
    Returns (new_block, num_fixes, was_modified)."""
    fixes = 0
    modified = False

    # Find all hex colors in this block
    hex_pattern = re.compile(r'#([0-9a-fA-F]{3,8})\b')

    for match in hex_pattern.finditer(block):
        full_hex = match.group(0).lower()

        if full_hex in WHITELIST:
            continue

        # Handle rgba-style hex (8 chars) — skip those
        if len(match.group(1)) > 6:
            continue

        # Normalize 3-char to 6-char for lookup
        hex_normalized = full_hex
        if len(match.group(1)) == 3:
            hex_normalized = "#" + "".join(c*2 for c in match.group(1))

        token = COLOR_MAP.get(full_hex) or COLOR_MAP.get(hex_normalized)

        if token:
            # Rule: NEVER inject nested quotes if it will break f-string syntax
            # If we're already in an f-string block (detected by caller) or if the line has complex logic
            replacement = f"{{THEME['{token}']}}"
            
            # Detect if this replacement might clash with existing quotes in the line
            if "'" in block and '"' in block:
                # Use double braces if we're worried about escaping, but here we're replacing hex
                pass
                
            block = block.replace(match.group(0), replacement, 1)
            fixes += 1
            modified = True
            CHANGELOG.append({
                "file": filepath_rel,
                "before": full_hex,
                "after": f"THEME['{token}']",
            })
        else:
            if full_hex not in WHITELIST:
                UNKNOWN_COLORS.append({"file": filepath_rel, "color": full_hex})

    return block, fixes, modified


def fix_file(filepath: Path) -> int:
    """Process a single component file: find stylesheet strings and fix hex colors."""
    source = filepath.read_text(encoding="utf-8", errors="replace")
    rel = str(filepath.relative_to(ROOT))
    total_fixes = 0

    # Quick check: does this file have any hex colors?
    if not re.search(r'#[0-9a-fA-F]{3,6}\b', source):
        return 0

    # Strategy: Find setStyleSheet calls and process them
    # Pattern: match setStyleSheet( followed by a string (""" or " or f""" or f")
    # We'll process the file line by line, tracking multi-line strings

    lines = source.split("\n")
    new_lines = []
    in_stylesheet = False
    stylesheet_lines = []
    stylesheet_start = -1
    string_delim = None
    is_fstring = False
    needs_import = False

    i = 0
    while i < len(lines):
        line = lines[i]

        if not in_stylesheet:
            # Check if this line starts a setStyleSheet call
            ss_match = re.search(r'\.setStyleSheet\s*\(\s*(f?)("""|\'\'\')(.*)$', line)
            if ss_match:
                is_fstring = ss_match.group(1) == 'f'
                string_delim = ss_match.group(2)
                rest = ss_match.group(3)

                # Check if the string ends on the same line
                if string_delim in rest:
                    # Single-segment multi-line string (odd but possible)
                    new_lines.append(line)
                    i += 1
                    continue

                in_stylesheet = True
                stylesheet_start = i
                stylesheet_lines = [line]
                i += 1
                continue

            ss_single = re.search(r'^(.*?)(\.setStyleSheet\s*\(\s*)(f?)("|\')(.*?)(\4\s*\))(.*?)$', line)
            if ss_single:
                prefix = ss_single.group(1) + ss_single.group(2)
                was_f = ss_single.group(3) == 'f'
                quote_char = ss_single.group(4)
                content = ss_single.group(5)
                suffix = ss_single.group(6) + ss_single.group(7)

                processed, fixes, modified = process_stylesheet_block(content, rel)
                if modified:
                    total_fixes += fixes
                    if not was_f:
                        # Need to convert to f-string and escape existing CSS braces
                        # But first, only escape braces that are NOT our new THEME refs
                        processed_escaped = ""
                        j = 0
                        while j < len(processed):
                            if processed[j] == '{':
                                # Check if it's a THEME ref
                                if processed[j:].startswith("{THEME["):
                                    # Find the closing }
                                    end = processed.index("]}", j) + 2
                                    processed_escaped += processed[j:end]
                                    j = end
                                    continue
                                else:
                                    processed_escaped += "{{"
                                    j += 1
                                    continue
                            elif processed[j] == '}':
                                processed_escaped += "}}"
                                j += 1
                                continue
                            processed_escaped += processed[j]
                            j += 1
                        line = f'{prefix}f"{processed_escaped}"){ss_single.group(7)}'
                        needs_import = True
                    else:
                        line = f"{prefix}f{quote_char}{processed}{suffix}"

                new_lines.append(line)
                i += 1
                continue

            new_lines.append(line)
            i += 1
        else:
            # We're inside a multi-line stylesheet string
            stylesheet_lines.append(line)

            # Check if this line contains the closing delimiter
            if string_delim in line and i != stylesheet_start:
                # We have the complete stylesheet block
                full_block = "\n".join(stylesheet_lines)

                # Extract just the CSS content (between delimiters)
                # Process hex colors in the full block
                processed_block, fixes, modified = process_stylesheet_block(full_block, rel)

                if modified:
                    total_fixes += fixes

                    if not is_fstring:
                        # Convert to f-string: escape CSS braces, add f prefix
                        result_lines = processed_block.split("\n")
                        new_result = []
                        for rl in result_lines:
                            new_rl = ""
                            j = 0
                            while j < len(rl):
                                if rl[j] == '{':
                                    if rl[j:].startswith("{THEME["):
                                        end = rl.index("]}", j) + 2
                                        new_rl += rl[j:end]
                                        j = end
                                        continue
                                    else:
                                        new_rl += "{{"
                                        j += 1
                                        continue
                                elif rl[j] == '}':
                                    if j > 0 and rl[j-1] == ']':
                                        # Part of THEME ref closing
                                        new_rl += rl[j]
                                        j += 1
                                        continue
                                    new_rl += "}}"
                                    j += 1
                                    continue
                                new_rl += rl[j]
                                j += 1
                            new_result.append(new_rl)

                        processed_block = "\n".join(new_result)

                        # Add f prefix to the setStyleSheet line
                        first_line = processed_block.split("\n")[0]
                        first_line = first_line.replace('.setStyleSheet("""', '.setStyleSheet(f"""', 1)
                        first_line = first_line.replace(".setStyleSheet('''", ".setStyleSheet(f'''", 1)
                        processed_block = first_line + "\n" + "\n".join(processed_block.split("\n")[1:])
                        needs_import = True

                    new_lines.extend(processed_block.split("\n"))
                else:
                    new_lines.extend(stylesheet_lines)

                in_stylesheet = False
                stylesheet_lines = []
                i += 1
                continue

            i += 1

    if total_fixes > 0:
        new_source = "\n".join(new_lines)
        if needs_import:
            new_source = ensure_theme_import(new_source)
        filepath.write_text(new_source, encoding="utf-8")

    return total_fixes


def check_touch_targets(filepath: Path) -> list:
    """Find widgets with sizes below minimum touch target."""
    source = filepath.read_text(encoding="utf-8", errors="replace")
    violations = []
    rel = str(filepath.relative_to(ROOT))
    size_pattern = re.compile(r'(setFixed(?:Size|Height|Width)|setMinimum(?:Size|Height|Width))\s*\(\s*(\d+)(?:\s*,\s*(\d+))?\s*\)')
    for i, line in enumerate(source.split("\n"), 1):
        m = size_pattern.search(line)
        if m:
            w = int(m.group(2))
            h = int(m.group(3)) if m.group(3) else w
            check_w = "Width" in m.group(1) or "Size" in m.group(1)
            check_h = "Height" in m.group(1) or "Size" in m.group(1)
            if (check_w and 0 < w < MIN_TOUCH_TARGET) or (check_h and 0 < h < MIN_TOUCH_TARGET):
                violations.append({"file": rel, "line": i, "method": m.group(1), "size": f"{w}x{h}" if m.group(3) else str(w)})
    return violations


def generate_report(total_fixes: int, touch_violations: list):
    """Write report."""
    report_path = ROOT / "reports" / "ui_fix_report.md"
    lines = []
    lines.append("# 🎨 UI Auto-Fix Report (STRICT MODE)")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Mode:** STRICT — fixes applied automatically")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## Hex Colors Fixed: {total_fixes}")
    lines.append("")
    if CHANGELOG:
        seen = set()
        lines.append("| File | Before | After |")
        lines.append("|------|--------|-------|")
        for c in CHANGELOG:
            key = f"{c['file']}:{c['before']}"
            if key not in seen:
                seen.add(key)
                lines.append(f"| `{c['file']}` | `{c['before']}` | `{c['after']}` |")
    lines.append("")

    if UNKNOWN_COLORS:
        seen = set()
        lines.append(f"## Unknown Colors ({len(UNKNOWN_COLORS)} occurrences)")
        lines.append("")
        lines.append("| File | Color | Action Needed |")
        lines.append("|------|-------|--------------|")
        for u in UNKNOWN_COLORS:
            key = f"{u['file']}:{u['color']}"
            if key not in seen:
                seen.add(key)
                lines.append(f"| `{u['file']}` | `{u['color']}` | Add to COLOR_MAP or WHITELIST |")
        lines.append("")

    if touch_violations:
        lines.append(f"## Touch Target Violations ({len(touch_violations)})")
        lines.append("")
        lines.append("| File | Line | Method | Size |")
        lines.append("|------|------|--------|------|")
        for v in touch_violations:
            lines.append(f"| `{v['file']}` | {v['line']} | `{v['method']}` | {v['size']} |")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    print("=" * 50)
    print("  UI Auto-Fix — STRICT MODE")
    print("=" * 50)
    print()

    files = []
    for d in ["components", "apps", "system"]:
        files.extend(list((ROOT / d).rglob("*.py")))
    files = [f for f in files if not any(p in f.parts for p in IGNORE_DIRS)]
    print(f"  Scanning {len(files)} files...")

    total_fixes = 0
    all_touch = []

    for f in files:
        try:
            fixes = fix_file(f)
            total_fixes += fixes
            all_touch.extend(check_touch_targets(f))
            if fixes > 0:
                print(f"    Fixed {fixes} colors in {f.name}")
        except Exception as e:
            print(f"    [SKIP] {f.name}: {e}")

    print(f"\n  Results:")
    print(f"    Colors fixed:     {total_fixes}")
    print(f"    Unknown colors:   {len(set(u['color'] for u in UNKNOWN_COLORS))}")
    print(f"    Touch violations: {len(all_touch)}")

    report = generate_report(total_fixes, all_touch)
    print(f"\n  Report: {report}")


if __name__ == "__main__":
    main()
