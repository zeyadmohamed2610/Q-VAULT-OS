# =============================================================
#  QUARANTINE_INFO.txt — Q-Vault OS
# =============================================================
# Status: Effective Quarantine (with mandatory banner)
# Date: 2026-04-18
# =============================================================
#
# Quarantine is IN-PLACE (header annotation) to:
# - Prevent accidental imports via explicit warnings
# - Preserve architectural knowledge
# - Clean runtime without deletion
#
# QUARANTINED MODULES (12):
# ==============================
# components/start_menu.py         - No imports in codebase
# components/desktop_icons.py     - Duplicate (dead code)
# components/feedback_dialog.py  - Only dynamic import (broken)
# components/error_dialog.py     - No imports in codebase
# components/welcome_screen.py   - No imports in codebase
# components/splash_screen.py   - No imports in codebase
# components/first_run_wizard.py  - No imports in codebase
# components/sudo_dialog.py   - No call sites (dead code)
# components/security_dashboard.py - No imports in codebase
# ==============================
# system/_quarantine/sandbox_system.py    - Not in runtime path
# system/_quarantine/secrets_manager.py - Not in runtime path
# ==============================
#
# Each quarantined module has a mandatory banner:
#   ⚠️ QUARANTINED MODULE ⚠️
#   Status: NOT PART OF RUNTIME
#   Warning: DO NOT IMPORT
# =============================================================