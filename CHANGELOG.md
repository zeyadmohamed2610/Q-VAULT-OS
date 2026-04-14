# Q-VAULT OS — Changelog

## v1.1.0 — Unified System Release (Final Polish)

### PART 1 — User System Unification
- **NEW `system/session_manager.py`** (492 lines) — single source of truth
  for all authentication, identity, session state, lockout, and sudo cache.
  Replaces the previously split `core/user_manager.py` + `system/user_system.py`.
- `core/user_manager.py` → thin 3-line compatibility shim; old `from core.user_manager import UM`
  imports still work unchanged via `UM_SHIM`.
- Login screen, Settings, and Terminal all now route through `SESSION`.
- `SessionUser` dataclass unifies the User model across the entire OS.
- Persistent user DB stored at `~/.qvault/users/users.json`.

### PART 2 — Real Sudo Authentication
- **NEW `components/sudo_dialog.py`** — modal password dialog for `sudo`.
- `sudo` in the terminal now shows a popup and verifies the user's real password.
- Elevation cached for **5 minutes** (`SESSION.sudo_granted` / `SESSION.sudo_remaining()`).
- `su` to a non-root account now drops the sudo cache.
- `su` without a password is blocked unless already root.
- 3 failed sudo attempts auto-rejects with 1.5s delay.

### PART 3 — Theme & UI Polish (v8)
- `assets/theme.py` rewritten with full design token system:
  - `FONT_MONO` — single font-stack definition used everywhere
  - `FONT_SIZE_XS/SM/MD/LG/XL/H1/H2/H3` — consistent type scale
  - `SPACING_XS/SM/MD/LG/XL` — 8pt spacing grid
  - `RADIUS_SM/MD/LG/XL` — border radius constants
  - `ICON_SIZE_DESKTOP=48`, `ICON_SIZE_TASKBAR=24`, `ICON_SIZE_APP=32`
  - `BUTTON_PRIMARY`, `BUTTON_SECONDARY`, `BUTTON_DANGER` — reusable button QSS
  - Windows: solid `#0f172a` background (no transparency), refined title bar
  - Taskbar: `rgba(10,18,38,252)` for near-opaque blur effect
- Desktop icon grid: 100px stride (84px cell + 16px gap), clean alignment.

### PART 4 — Application Polish
- **Terminal**: zero-margin layout, styled input bar with `border-top` separator,
  consistent `#060a10` background throughout, green-on-dark prompt styling.
- **File Explorer**: sidebar buttons now have proper hover states with border-radius;
  sidebar + file panel in correct horizontal layout (were stacked vertically before).
- All apps: `FONT_MONO` and `SPACING_*` constants used throughout.

### PART 5 — Security Hardening
- `sudo` requires real password via `SESSION.sudo_request()` — no bypass.
- `su` requires password for non-root users — no silent elevation.
- Sudo elevation dropped when switching to non-root user.
- All 19 files with bare `except:` clauses upgraded to `except Exception:`.

### PART 6 — Performance
- Desktop `_open_app` now has a `_creating` set guard — rapid double-clicks
  on an icon can never spawn two instances of the same window.
- File explorer: `_MAX_DISPLAY_ITEMS = 2000` guard prevents UI freeze on
  directories with thousands of files.
- All `time.sleep()` calls confirmed inside `daemon=True` background threads —
  none block the UI thread.
- Debug `print(f"[DESKTOP]...")` and `print(f"[UI]...")` calls removed.

### PART 7 — Validation
- 29/29 automated checks pass.
- 0 bare `except:` clauses.
- 0 blocking `time.sleep()` on main thread.
- All 68 Python source files pass `python3 -m py_compile`.

---

## v1.0.1 — Production Audit Release
- Added `Terminal = RealTerminal` and `FileExplorer = RealFileExplorer` aliases.
- Fixed `os_window.py` close/minimize signal stacking crashes.
- Fixed `STATE.is_root = False` overwriting method.
- Fixed `user_system.verify_password()` using wrong hash function.
- Added `closeEvent` to `NetworkTools` for thread cleanup.
- Fixed `AltTabOverlay` selection cycling.
- Removed dead `mouseSingleClickTap()` method.
- Removed unused `import random` from taskbar.
