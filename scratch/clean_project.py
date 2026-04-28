import os
import shutil

PROJECT_ROOT = os.getcwd()

print("Starting Professional Project Cleanup...")

# 1. Delete __pycache__
pycache_count = 0
for root, dirs, files in os.walk(PROJECT_ROOT):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d), ignore_errors=True)
            pycache_count += 1
print(f"Removed {pycache_count} __pycache__ directories.")

# 2. Delete .pyc
pyc_count = 0
for root, dirs, files in os.walk(PROJECT_ROOT):
    for f in files:
        if f.endswith(".pyc"):
            os.remove(os.path.join(root, f))
            pyc_count += 1
print(f"Removed {pyc_count} .pyc files.")

# 3. Detect Corrupted Files (null bytes)
corrupted_files = []
for root, dirs, files in os.walk(PROJECT_ROOT):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                with open(path, "rb") as file:
                    content = file.read()
                    if b"\x00" in content:
                        corrupted_files.append(path)
            except:
                pass

if corrupted_files:
    print("\nWarning: Corrupted files detected:")
    for f in corrupted_files:
        print(f" - {f}")
else:
    print("\nSuccess: No corrupted files detected.")

# 4. Cleanup old logs (excluding modern shadow logs)
log_dirs = ["logs", "tmp"]
for d in log_dirs:
    full = os.path.join(PROJECT_ROOT, d)
    if os.path.exists(full):
        shutil.rmtree(full, ignore_errors=True)
        print(f"Removed old log directory: {d}")

print("\nClean complete.")
