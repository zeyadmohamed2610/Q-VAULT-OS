import os
import ast
import py_compile
import sys
import traceback

def scan_project(root_dir="."):
    errors = []
    total_files = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden dirs and virtual envs
        if any(d in root for d in [".git", ".venv", "__pycache__", "build", "dist"]):
            continue
            
        for file in files:
            if file.endswith(".py"):
                total_files += 1
                path = os.path.join(root, file)
                
                # Check 1: AST Parse
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source, filename=path)
                except SyntaxError as e:
                    errors.append({
                        "file": path,
                        "type": "SyntaxError",
                        "line": e.lineno,
                        "msg": str(e),
                        "snippet": e.text.strip() if e.text else ""
                    })
                    continue
                except Exception as e:
                    errors.append({
                        "file": path,
                        "type": "ParseError",
                        "msg": str(e)
                    })
                    continue
                
                # Check 2: Bytecode Compilation
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as e:
                    # Often redundant with ast.parse but catches some extra edge cases
                    errors.append({
                        "file": path,
                        "type": "CompileError",
                        "msg": str(e)
                    })
    
    return total_files, errors

def generate_report(total_files, errors):
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/runtime_integrity_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🛡️ Runtime Integrity Guard Report\n\n")
        f.write(f"**Total Python Files Scanned:** {total_files}\n")
        f.write(f"**Integrity Status:** {'❌ FAILED' if errors else '✅ PASSED'}\n\n")
        
        if not errors:
            f.write("## ✅ No Syntax or Compilation Errors Detected\n")
            f.write("The codebase is structurally sound for runtime execution.\n")
        else:
            f.write(f"## ❌ {len(errors)} Critical Failures Detected\n\n")
            f.write("| File | Type | Line | Message |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for err in errors:
                line = err.get("line", "N/A")
                msg = err.get("msg", "Unknown")
                f.write(f"| `{err['file']}` | {err['type']} | {line} | {msg} |\n")
            
            f.write("\n### Error Details\n")
            for err in errors:
                f.write(f"#### `{err['file']}`\n")
                f.write(f"- **Type:** {err['type']}\n")
                if "line" in err: f.write(f"- **Line:** {err['line']}\n")
                f.write(f"- **Message:** {err['msg']}\n")
                if err.get("snippet"):
                    f.write(f"```python\n{err['snippet']}\n```\n")
                f.write("\n---\n")

    print(f"[IntegrityGuard] Scan complete. Total Files: {total_files}, Errors: {len(errors)}")
    if errors:
        print(f"[!] REPORT GENERATED: {report_path}")
        return False
    return True

if __name__ == "__main__":
    total, errs = scan_project()
    success = generate_report(total, errs)
    if not success:
        sys.exit(1)
    sys.exit(0)
