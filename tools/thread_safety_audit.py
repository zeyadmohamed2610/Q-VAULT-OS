#!/usr/bin/env python3
"""
tools/thread_safety_audit.py — Q-Vault OS
Static + Runtime Thread Safety Audit
"""

import sys
import os
import ast
import re
import time
import threading
import inspect
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(os.getcwd())

# ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(".")

# Patterns that indicate unsafe cross-thread UI access
UNSAFE_UI_PATTERNS = [
    (r"self\.(?:setText|setVisible|show|hide|update|repaint|resize|move|setStyleSheet|setEnabled|close)\(",
     "Direct UI mutation — may be called from non-UI thread"),
    (r"QTimer\.singleShot\s*\(\s*0,",
     "Zero-delay singleShot — race potential if obj destroyed"),
    (r"QApplication\.processEvents\(\)",
     "processEvents in logic path — re-entrancy risk"),
]

# Patterns that indicate unsafe shared state
SHARED_STATE_PATTERNS = [
    (r"^\s*(self\._\w+\s*=)",
     "Mutating private state — verify thread ownership"),
    (r"threading\.Thread\(",
     "Raw Thread usage — verify signals cross to UI thread"),
    (r"\.start\(\)(?!.*QTimer)",
     "Thread/process start — ensure no direct UI access"),
]

# Files to include
COMPONENT_DIRS = ["core", "system", "components", "apps", "tools"]


class ThreadSafetyAudit:
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.files_scanned = 0
        self.threads_detected = []

    def _add_issue(self, severity, category, file, line, code, note):
        self.issues.append({
            "severity": severity,
            "category": category,
            "file": file,
            "line": line,
            "code": code.strip(),
            "note": note,
        })

    # ── Static Analysis ───────────────────────────────────────────

    def scan_file(self, filepath: Path):
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        lines = text.splitlines()
        self.files_scanned += 1
        rel = str(filepath.relative_to(REPO_ROOT))

        inside_thread_body = False

        for i, line in enumerate(lines, 1):
            # Detect thread class bodies or Thread(target=) usage
            if re.search(r'threading\.Thread\(', line):
                self.threads_detected.append(f"{rel}:{i}")
                self._add_issue("WARN", "THREAD_USAGE", rel, i, line,
                                "Raw thread — ensure only signals cross UI boundary")

            if re.search(r'class \w+\(.*Thread.*\)', line):
                inside_thread_body = True

            # Check for direct UI in thread bodies (rough heuristic)
            for pattern, note in UNSAFE_UI_PATTERNS:
                if re.search(pattern, line):
                    self._add_issue("WARN", "UNSAFE_UI_ACCESS", rel, i, line, note)

            # Shared mutable state
            for pattern, note in SHARED_STATE_PATTERNS:
                if re.search(pattern, line):
                    self._add_issue("INFO", "SHARED_STATE", rel, i, line, note)

            # QMutex absence near QThread
            if "QThread" in line and "QMutex" not in text:
                self._add_issue("WARN", "MISSING_MUTEX", rel, i, line,
                                "QThread used but no QMutex found in file")

            # Blocking calls in UI thread risk
            for blocking in ["time.sleep(", "subprocess.run(", "subprocess.call("]:
                if blocking in line and "tools/" not in rel:
                    self._add_issue("HIGH", "BLOCKING_CALL", rel, i, line,
                                    f"Blocking call '{blocking}' may freeze UI thread")

            # Bare signal connections without thread guard
            if ".connect(" in line and "moveToThread" not in text and "QThread" in text:
                self._add_issue("INFO", "SIGNAL_CONNECT", rel, i, line,
                                "Signal connection with QThread present — verify thread affinity")

    def scan_all(self):
        print("  Scanning source files for thread safety issues...")
        for d in COMPONENT_DIRS:
            for f in Path(d).rglob("*.py"):
                self.scan_file(f)

    # ── Runtime Thread Check ──────────────────────────────────────

    def runtime_thread_check(self):
        """Enumerate active Python threads at audit time."""
        active = threading.enumerate()
        for t in active:
            if t.name not in ("MainThread", "Dummy-1"):
                self._add_issue("INFO", "ACTIVE_THREAD", "runtime", 0, "",
                                f"Active background thread: '{t.name}' daemon={t.daemon}")

    # ── Report ────────────────────────────────────────────────────

    def generate_report(self) -> str:
        high = [i for i in self.issues if i["severity"] == "HIGH"]
        warn = [i for i in self.issues if i["severity"] == "WARN"]
        info = [i for i in self.issues if i["severity"] == "INFO"]

        # Deduplicate INFO (shared state is noisy)
        info = info[:20]

        lines = [
            "# 🔒 Thread Safety Audit Report",
            f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files Scanned | {self.files_scanned} |",
            f"| Threads Detected | {len(self.threads_detected)} |",
            f"| HIGH Issues | {len(high)} |",
            f"| WARN Issues | {len(warn)} |",
            f"| INFO Notes | {len(info)} (capped at 20) |",
            "",
        ]

        if high:
            lines.extend(["## 🔴 HIGH — Blocking or Dangerous Patterns", ""])
            for i in high:
                lines.append(f"- **{i['file']}:{i['line']}** — {i['note']}")
                lines.append(f"  ```python\n  {i['code']}\n  ```")

        if warn:
            lines.extend(["", "## 🟡 WARN — Threading Risks", ""])
            for i in warn[:15]:
                lines.append(f"- **{i['file']}:{i['line']}** — {i['note']}")

        if self.threads_detected:
            lines.extend(["", "## 🧵 Detected Thread Spawning Sites", ""])
            for t in self.threads_detected[:10]:
                lines.append(f"- `{t}`")

        lines.extend([
            "",
            "## ✅ Recommendations",
            "1. Use `QMetaObject.invokeMethod` or emit signals (never call widget methods directly from threads)",
            "2. Replace `time.sleep()` in services with `QTimer` to avoid blocking the event loop",
            "3. Ensure any raw `threading.Thread` only communicates back to UI via `pyqtSignal`",
            "4. Add `QMutex` protection around any shared mutable state accessed from both UI and service threads",
            "",
            "## 🎯 Verdict",
        ])

        if len(high) == 0 and len(warn) < 10:
            lines.append("**✅ THREAD SAFETY: ACCEPTABLE** — No critical blocking patterns found.")
        elif len(high) > 0:
            lines.append(f"**🔴 HIGH RISK** — {len(high)} blocking patterns require immediate fix.")
        else:
            lines.append(f"**🟡 MODERATE RISK** — {len(warn)} threading warnings to review.")

        return "\n".join(lines)


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Q-Vault OS — Thread Safety Audit               ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    auditor = ThreadSafetyAudit()
    auditor.scan_all()
    auditor.runtime_thread_check()

    md = auditor.generate_report()
    os.makedirs("reports", exist_ok=True)
    with open("reports/thread_safety_report.md", "w", encoding="utf-8") as f:
        f.write(md)

    high = sum(1 for i in auditor.issues if i["severity"] == "HIGH")
    warn = sum(1 for i in auditor.issues if i["severity"] == "WARN")
    print(f"  Files scanned: {auditor.files_scanned}")
    print(f"  HIGH issues:   {high}")
    print(f"  WARN issues:   {warn}")
    print(f"  Threads found: {len(auditor.threads_detected)}")
    print(f"  Report: reports/thread_safety_report.md")


if __name__ == "__main__":
    main()
