#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  Q-Vault OS — Full System Validation Pipeline v3.0          ║
║  Senior QA Architect: Automated Pre-Release Gate            ║
║                                                             ║
║  Phases:                                                    ║
║    1. Static Analysis (AST linting + import safety)         ║
║    2. Architecture Audit (God Objects, SRP, coupling)       ║
║    3. Event Bus Health (orphans, wiring)                    ║
║    4. UI/Theme Audit (hardcoded colors, spacing)            ║
║    5. Test Suite Execution (pytest-compatible)              ║
║    6. Runtime Stress Simulation                             ║
║    7. Manual Checklist Generation                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import ast
import os
import re
import sys
import io
import time
import json
import unittest
import traceback
import importlib

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ── Setup ──
ROOT = Path(__file__).parent
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)
REPORT_PATH = REPORT_DIR / "final_system_report.md"

COMPONENT_DIRS = ["components", "system", "core", "apps", "sdk"]
IGNORE_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".ruff_cache", "scratch", "qvault-core", "testsprite_tests"}

# ── Data Models ──

@dataclass
class Issue:
    severity: str  # "critical", "major", "minor"
    phase: str
    file: str
    line: int
    message: str

@dataclass
class PhaseResult:
    name: str
    passed: int = 0
    failed: int = 0
    issues: List[Issue] = field(default_factory=list)
    duration_ms: float = 0
    details: Dict = field(default_factory=dict)

    @property
    def score(self):
        total = self.passed + self.failed
        return round((self.passed / max(total, 1)) * 100)

class AuditEngine:
    def __init__(self):
        self.phases: List[PhaseResult] = []
        self.py_files: List[Path] = []
        self._discover_files()

    def _discover_files(self):
        for d in COMPONENT_DIRS:
            target = ROOT / d
            if not target.exists():
                continue
            for f in target.rglob("*.py"):
                if any(p in f.parts for p in IGNORE_DIRS):
                    continue
                self.py_files.append(f)

    # ═══════════════════════════════════════════════════════
    # PHASE 1: STATIC ANALYSIS
    # ═══════════════════════════════════════════════════════
    def phase_static_analysis(self) -> PhaseResult:
        r = PhaseResult(name="Static Analysis")
        t0 = time.perf_counter()

        for f in self.py_files:
            try:
                source = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(f))
                r.passed += 1

                rel = f.relative_to(ROOT)
                lines = source.split("\n")

                # Check 1: bare except
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler) and node.type is None:
                        r.issues.append(Issue("minor", r.name, str(rel), node.lineno, "Bare `except:` — should catch specific exceptions"))
                        r.failed += 1

                # Check 2: wildcard imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.names and node.names[0].name == "*":
                        mod = node.module or "unknown"
                        r.issues.append(Issue("minor", r.name, str(rel), node.lineno, f"Wildcard import: from {mod} import *"))
                        r.failed += 1

                # Check 3: long functions (>80 lines)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        end = getattr(node, "end_lineno", node.lineno + 50)
                        length = end - node.lineno
                        if length > 80:
                            sev = "major" if length > 120 else "minor"
                            r.issues.append(Issue(sev, r.name, str(rel), node.lineno, f"Long function `{node.name}`: {length} lines"))
                            r.failed += 1

                # Check 4: TODO/FIXME/HACK
                for i, line in enumerate(lines, 1):
                    for tag in ["TODO", "FIXME", "HACK", "XXX"]:
                        if tag in line and not line.strip().startswith("#!"):
                            r.issues.append(Issue("minor", r.name, str(rel), i, f"{tag} found: {line.strip()[:80]}"))

                # Check 5: mutable default arguments
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for default in node.args.defaults + node.args.kw_defaults:
                            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                r.issues.append(Issue("major", r.name, str(rel), node.lineno, f"Mutable default arg in `{node.name}`"))
                                r.failed += 1

            except SyntaxError as e:
                r.issues.append(Issue("critical", r.name, str(f.relative_to(ROOT)), e.lineno or 0, f"SyntaxError: {e.msg}"))
                r.failed += 1

        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 2: ARCHITECTURE AUDIT
    # ═══════════════════════════════════════════════════════
    def phase_architecture(self) -> PhaseResult:
        r = PhaseResult(name="Architecture Audit")
        t0 = time.perf_counter()

        god_objects = []
        circular_risks = defaultdict(set)

        for f in self.py_files:
            try:
                source = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(f))
                rel = str(f.relative_to(ROOT))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                        attrs = set()
                        for m in methods:
                            for n2 in ast.walk(m):
                                if isinstance(n2, ast.Attribute) and isinstance(getattr(n2, 'value', None), ast.Name) and n2.value.id == 'self':
                                    attrs.add(n2.attr)

                        mc, ac = len(methods), len(attrs)
                        if mc > 15:
                            sev = "major" if mc > 20 else "minor"
                            r.issues.append(Issue(sev, r.name, rel, node.lineno, f"God Object: `{node.name}` has {mc} methods, {ac} attributes"))
                            god_objects.append(node.name)
                            r.failed += 1
                        else:
                            r.passed += 1

                # Cross-module imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        mod = node.module.split(".")[0]
                        src = rel.split(os.sep)[0] if os.sep in rel else rel.split("/")[0]
                        if mod in COMPONENT_DIRS and mod != src:
                            circular_risks[src].add(mod)

            except Exception:
                pass

        # Check for circular pairs (deduplicated)
        seen_pairs = set()
        for src, deps in circular_risks.items():
            for dep in deps:
                pair = tuple(sorted([src, dep]))
                if dep in circular_risks and src in circular_risks[dep] and pair not in seen_pairs:
                    seen_pairs.add(pair)
                    r.issues.append(Issue("major", r.name, f"{pair[0]} ↔ {pair[1]}", 0, f"Circular import risk: {pair[0]} ↔ {pair[1]}"))

        r.details["god_objects"] = god_objects
        r.details["cross_deps"] = {k: list(v) for k, v in circular_risks.items()}
        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 3: EVENT BUS HEALTH
    # ═══════════════════════════════════════════════════════
    def phase_event_bus(self) -> PhaseResult:
        r = PhaseResult(name="Event Bus Health")
        t0 = time.perf_counter()

        # Parse SystemEvent enum
        bus_file = ROOT / "core" / "event_bus.py"
        source = bus_file.read_text(encoding="utf-8", errors="replace")
        events = set(re.findall(r'^    ((?:[A-Z][A-Z_0-9]+)?)\s*=\s*"[\w.]+"', source, re.MULTILINE))
        events.discard('')

        # Scan all files for emit and subscribe
        all_sources = ""
        for f in self.py_files:
            try:
                all_sources += f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        emitted = set(re.findall(r'\.emit\(SystemEvent\.(\w+)', all_sources))
        subscribed = set(re.findall(r'\.subscribe\(SystemEvent\.(\w+)', all_sources))
        sdk_refs = set(re.findall(r'SystemEvent\.(\w+)\.value', all_sources))

        for ev in events:
            is_emit = ev in emitted
            is_sub = ev in subscribed
            is_sdk = ev in sdk_refs

            if is_emit and is_sub:
                r.passed += 1  # fully wired
            elif is_emit and not is_sub:
                r.issues.append(Issue("minor", r.name, "event_bus.py", 0, f"Emit-only: {ev} (no subscriber)"))
                r.failed += 1
            elif not is_emit and is_sub:
                r.issues.append(Issue("minor", r.name, "event_bus.py", 0, f"Subscribe-only: {ev} (never emitted)"))
                r.failed += 1
            elif is_sdk:
                r.passed += 1  # SDK-exposed, acceptable
            elif not is_emit and not is_sub and not is_sdk:
                r.issues.append(Issue("major", r.name, "event_bus.py", 0, f"Dead event: {ev} (never used anywhere)"))
                r.failed += 1

        r.details["total_events"] = len(events)
        r.details["fully_wired"] = len(emitted & subscribed)
        r.details["emit_only"] = len(emitted - subscribed)
        r.details["sub_only"] = len(subscribed - emitted)
        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 4: UI / THEME AUDIT
    # ═══════════════════════════════════════════════════════
    def phase_ui_theme(self) -> PhaseResult:
        r = PhaseResult(name="UI / Theme Audit")
        t0 = time.perf_counter()

        hex_pattern = re.compile(r'#[0-9a-fA-F]{6}\b')
        theme_ref = re.compile(r"THEME\[")
        bad_spacing = re.compile(r'(?:margin|padding|spacing|contentsMargins)\s*[:(]\s*(\d+)')

        valid_spacing = {0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 20, 24, 32, 40, 48}
        comp_dir = ROOT / "components"

        for f in comp_dir.rglob("*.py"):
            if any(p in f.parts for p in IGNORE_DIRS):
                continue
            try:
                source = f.read_text(encoding="utf-8", errors="replace")
                rel = str(f.relative_to(ROOT))
                lines = source.split("\n")

                # Count hardcoded hex colors
                hex_count = len(hex_pattern.findall(source))
                theme_count = len(theme_ref.findall(source))

                if hex_count > 0:
                    sev = "major" if hex_count > 5 else "minor"
                    r.issues.append(Issue(sev, r.name, rel, 0, f"{hex_count} hardcoded hex colors (vs {theme_count} THEME refs)"))
                    r.failed += 1
                else:
                    r.passed += 1

                # Check spacing values
                for i, line in enumerate(lines, 1):
                    for m in bad_spacing.finditer(line):
                        val = int(m.group(1))
                        if val not in valid_spacing and val < 100:
                            r.issues.append(Issue("minor", r.name, rel, i, f"Non-standard spacing: {val}px"))

            except Exception:
                pass

        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 5: TEST SUITE EXECUTION
    # ═══════════════════════════════════════════════════════
    def phase_test_suite(self) -> PhaseResult:
        r = PhaseResult(name="Test Suite")
        t0 = time.perf_counter()

        test_dir = ROOT / "tests"
        if not test_dir.exists():
            r.issues.append(Issue("critical", r.name, "tests/", 0, "Test directory missing"))
            r.duration_ms = (time.perf_counter() - t0) * 1000
            return r

        # Discover and run tests
        sys.path.insert(0, str(ROOT))
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        for test_file in test_dir.rglob("test_*.py"):
            try:
                rel = test_file.relative_to(ROOT)
                module_path = str(rel).replace(os.sep, ".").replace("/", ".")
                if module_path.endswith(".py"):
                    module_path = module_path[:-3]
                import importlib.util as ilu
                spec = ilu.spec_from_file_location(module_path, test_file)
                if spec and spec.loader:
                    mod = ilu.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(mod)
                        file_suite = loader.loadTestsFromModule(mod)
                        suite.addTests(file_suite)
                    except Exception as e:
                        r.issues.append(Issue("major", r.name, str(rel), 0, f"Test load failed: {e}"))
                        r.failed += 1
            except Exception as e:
                r.issues.append(Issue("major", r.name, str(test_file.name), 0, f"Discovery error: {e}"))

        # Run
        class QuietResult(unittest.TextTestRunner):
            pass

        from io import StringIO
        buf = StringIO()
        runner = unittest.TextTestRunner(stream=buf, verbosity=0)
        result = runner.run(suite)

        r.passed = result.testsRun - len(result.failures) - len(result.errors)
        r.failed = len(result.failures) + len(result.errors)

        for test, tb in result.failures:
            r.issues.append(Issue("major", r.name, str(test), 0, f"FAIL: {tb.split(chr(10))[-2][:120]}"))
        for test, tb in result.errors:
            r.issues.append(Issue("critical", r.name, str(test), 0, f"ERROR: {tb.split(chr(10))[-2][:120]}"))

        r.details["tests_run"] = result.testsRun
        r.details["failures"] = len(result.failures)
        r.details["errors"] = len(result.errors)
        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 6: IMPORT CHAIN STRESS TEST
    # ═══════════════════════════════════════════════════════
    def phase_stress_test(self) -> PhaseResult:
        r = PhaseResult(name="Runtime Stress Test")
        t0 = time.perf_counter()

        # Test 1: Import chain integrity
        chains = [
            ("Core EventBus", "core.event_bus", "EVENT_BUS"),
            ("SDK Events", "sdk.events", None),
            ("Window Manager", "system.window_manager", "get_window_manager"),
            ("App Controller", "system.app_controller", "get_app_controller"),
            ("Desktop", "components.desktop", "Desktop"),
            ("OSWindow", "components.os_window", "OSWindow"),
            ("Handlers", "components.focus_manager", "FocusManager"),
            ("Snap", "components.snap_controller", "SnapController"),
            ("Drag", "components.window_drag_handler", "WindowDragHandler"),
            ("Theme", "assets.theme", "THEME"),
            ("Runtime", "system.runtime_manager", "RUNTIME_MANAGER"),
        ]

        for label, module, attr in chains:
            try:
                mod = importlib.import_module(module)
                if attr and not hasattr(mod, attr):
                    r.issues.append(Issue("critical", r.name, module, 0, f"Missing export: {attr}"))
                    r.failed += 1
                else:
                    r.passed += 1
            except Exception as e:
                r.issues.append(Issue("critical", r.name, module, 0, f"Import failed: {e}"))
                r.failed += 1

        # Test 2: EventBus emit/subscribe cycle
        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            received = []
            def _test_cb(payload):
                received.append(payload)
            EVENT_BUS.subscribe(SystemEvent.APP_LAUNCHED, _test_cb)
            EVENT_BUS.emit(SystemEvent.APP_LAUNCHED, {"test": True}, source="audit")
            EVENT_BUS.unsubscribe(SystemEvent.APP_LAUNCHED, _test_cb)
            if received:
                r.passed += 1
            else:
                r.issues.append(Issue("critical", r.name, "event_bus", 0, "EventBus round-trip failed"))
                r.failed += 1
        except Exception as e:
            r.issues.append(Issue("critical", r.name, "event_bus", 0, f"EventBus stress failed: {e}"))
            r.failed += 1

        # Test 3: THEME token count
        try:
            from assets.theme import THEME
            if len(THEME) < 20:
                r.issues.append(Issue("major", r.name, "theme.py", 0, f"Low token count: {len(THEME)} (expected 30+)"))
                r.failed += 1
            else:
                r.passed += 1
        except Exception as e:
            r.issues.append(Issue("critical", r.name, "theme.py", 0, f"Theme import failed: {e}"))
            r.failed += 1

        r.duration_ms = (time.perf_counter() - t0) * 1000
        return r

    # ═══════════════════════════════════════════════════════
    # PHASE 7: MANUAL CHECKLIST
    # ═══════════════════════════════════════════════════════
    def phase_manual_checklist(self) -> PhaseResult:
        r = PhaseResult(name="Manual Checklist")
        checklist = [
            ("Boot Sequence", "App launches without crash via `python run.py`"),
            ("Login Flow", "Login screen appears, credentials work, desktop loads"),
            ("Window Drag", "Windows can be dragged by title bar, snap preview appears"),
            ("Window Tiling", "Super+Arrow snaps windows to half/quarter/maximize"),
            ("Window Focus", "Clicking a window brings it to front with glow"),
            ("Taskbar", "Clock updates, CPU/RAM stats visible, app buttons appear"),
            ("Quick Panel", "Flyout opens from control button, toggles work"),
            ("Command Palette", "Ctrl+Space opens palette, commands execute"),
            ("Notifications", "Toast notifications appear, auto-dismiss after delay"),
            ("Theme Consistency", "No raw hex colors visible, text is readable"),
            ("Shutdown", "Closing the window exits cleanly without RuntimeError"),
        ]
        r.details["checklist"] = checklist
        r.passed = len(checklist)
        return r

    # ═══════════════════════════════════════════════════════
    # ORCHESTRATOR
    # ═══════════════════════════════════════════════════════
    def run_all(self):
        print("╔══════════════════════════════════════════════╗")
        print("║  Q-Vault OS — Full System Validation v3.0   ║")
        print("╚══════════════════════════════════════════════╝")
        print()

        runners = [
            ("Phase 1", self.phase_static_analysis),
            ("Phase 2", self.phase_architecture),
            ("Phase 3", self.phase_event_bus),
            ("Phase 4", self.phase_ui_theme),
            ("Phase 5", self.phase_test_suite),
            ("Phase 6", self.phase_stress_test),
            ("Phase 7", self.phase_manual_checklist),
        ]

        for label, fn in runners:
            print(f"  ▶ {label}: {fn.__name__} ...", end=" ", flush=True)
            try:
                result = fn()
                self.phases.append(result)
                crit = sum(1 for i in result.issues if i.severity == "critical")
                print(f"✓ ({result.passed}P/{result.failed}F, {len(result.issues)} issues, {crit} critical) [{result.duration_ms:.0f}ms]")
            except Exception as e:
                print(f"✗ CRASHED: {e}")
                err_r = PhaseResult(name=fn.__name__)
                err_r.issues.append(Issue("critical", fn.__name__, "", 0, f"Phase crashed: {e}"))
                err_r.failed = 1
                self.phases.append(err_r)

        print()
        self._generate_report()

    def _calculate_health(self) -> int:
        all_issues = [i for p in self.phases for i in p.issues]
        critical = sum(1 for i in all_issues if i.severity == "critical")
        major = sum(1 for i in all_issues if i.severity == "major")
        minor = sum(1 for i in all_issues if i.severity == "minor")

        score = 100
        score -= critical * 15
        score -= major * 2
        score -= minor * 0.3
        return max(0, min(100, int(score)))

    def _grade(self, score: int) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 50: return "D"
        return "F"

    def _generate_report(self):
        score = self._calculate_health()
        grade = self._grade(score)
        all_issues = [i for p in self.phases for i in p.issues]
        critical = [i for i in all_issues if i.severity == "critical"]
        major = [i for i in all_issues if i.severity == "major"]
        minor = [i for i in all_issues if i.severity == "minor"]

        verdict = "🟢 PRODUCTION READY" if score >= 75 and len(critical) == 0 else "🔴 NOT PRODUCTION READY"

        lines = []
        lines.append("# 🔬 Q-Vault OS — Final System Validation Report v3.0")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Files Scanned:** {len(self.py_files)}")
        lines.append(f"**Pipeline Duration:** {sum(p.duration_ms for p in self.phases):.0f}ms")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| **Health Score** | **{score}/100 (Grade: {grade})** |")
        lines.append(f"| **Verdict** | **{verdict}** |")
        lines.append(f"| Critical Issues | {len(critical)} |")
        lines.append(f"| Major Issues | {len(major)} |")
        lines.append(f"| Minor Issues | {len(minor)} |")
        lines.append(f"| Total Issues | {len(all_issues)} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Phase Summary Table
        lines.append("## Phase Results")
        lines.append("")
        lines.append("| # | Phase | Pass | Fail | Issues | Score | Time |")
        lines.append("|---|-------|------|------|--------|-------|------|")
        for i, p in enumerate(self.phases, 1):
            lines.append(f"| {i} | {p.name} | {p.passed} | {p.failed} | {len(p.issues)} | {p.score}% | {p.duration_ms:.0f}ms |")
        lines.append("")

        # Critical Issues
        if critical:
            lines.append("## 🚨 Critical Issues")
            lines.append("")
            for i in critical:
                lines.append(f"- **[{i.phase}]** `{i.file}:{i.line}` — {i.message}")
            lines.append("")

        # Major Issues
        if major:
            lines.append("## ⚠️ Major Issues")
            lines.append("")
            for i in major:
                lines.append(f"- **[{i.phase}]** `{i.file}:{i.line}` — {i.message}")
            lines.append("")

        # Minor Issues (grouped by phase)
        if minor:
            lines.append("## 📝 Minor Issues")
            lines.append("")
            by_phase = defaultdict(list)
            for i in minor:
                by_phase[i.phase].append(i)
            for phase, issues in by_phase.items():
                lines.append(f"### {phase} ({len(issues)})")
                for i in issues[:15]:
                    lines.append(f"- `{i.file}:{i.line}` — {i.message}")
                if len(issues) > 15:
                    lines.append(f"- ... and {len(issues)-15} more")
                lines.append("")

        # Event Bus Details
        for p in self.phases:
            if p.name == "Event Bus Health" and p.details:
                lines.append("## 📡 Event Bus Health Details")
                lines.append("")
                for k, v in p.details.items():
                    lines.append(f"- **{k}:** {v}")
                lines.append("")

        # Manual Checklist
        for p in self.phases:
            if p.name == "Manual Checklist" and p.details.get("checklist"):
                lines.append("## ✅ Manual Testing Checklist")
                lines.append("")
                lines.append("| # | Area | Verification Step | Status |")
                lines.append("|---|------|-------------------|--------|")
                for idx, (area, step) in enumerate(p.details["checklist"], 1):
                    lines.append(f"| {idx} | {area} | {step} | ☐ |")
                lines.append("")

        # Final Verdict
        lines.append("---")
        lines.append("")
        lines.append(f"## Final Verdict: {verdict}")
        lines.append("")
        if score >= 75 and len(critical) == 0:
            lines.append("> The system passes automated validation. Complete the manual checklist above before release.")
        else:
            lines.append("> The system has outstanding issues that must be resolved before release.")
            if critical:
                lines.append(f"> **{len(critical)} critical issue(s)** require immediate attention.")
        lines.append("")

        report = "\n".join(lines)
        REPORT_PATH.write_text(report, encoding="utf-8")

        # Track progress history
        self._update_progress_history(score, len(critical), len(major), len(minor))

        print(f"  ┌─────────────────────────────────────────┐")
        print(f"  │  Health Score: {score}/100 (Grade: {grade})         │")
        print(f"  │  Verdict: {verdict:<29}│")
        print(f"  │  Critical: {len(critical):>3}  Major: {len(major):>3}  Minor: {len(minor):>3}  │")
        print(f"  └─────────────────────────────────────────┘")
        print(f"\n  📄 Report: {REPORT_PATH}")

    def _update_progress_history(self, score, critical, major, minor):
        history_path = REPORT_DIR / "progress_history.json"
        history = []
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append({
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "critical": critical,
            "major": major,
            "minor": minor,
            "total": critical + major + minor,
            "files_scanned": len(self.py_files)
        })
        history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")


if __name__ == "__main__":
    engine = AuditEngine()
    engine.run_all()
