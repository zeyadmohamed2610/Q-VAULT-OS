# SUBSYSTEM: BOOT_FLOW
## A) WHY
The Boot Flow is the critical sequence that transitions Q-Vault from a collection of scripts into a Governed Runtime Environment. It ensures that the Kernel is initialized, the Secure API is ready, and the user environment is cryptographically isolated before any UI is shown.

## B) HOW
The boot process is managed by `run.py` (the Entry Point) and coordinated by the `SystemController`. It utilizes a multi-stage initialization where components are loaded based on their dependency level (Core -> UI -> App Layer).

## C) FLOW
1. **Host Environment Check:** `run.py` validates Python dependencies and OS permissions.
2. **Kernel Initialization:** The `ProcessGovernor` and `RuntimeManager` are instantiated.
3. **Event Bus Activation:** The central `EVENT_BUS` is started to handle IPC.
4. **Login Sequence:** The `SplashScreen` and `LoginWindow` are displayed to establish user identity.
5. **Desktop Mounting:** Upon successful auth, the `WindowManager` mounts the Desktop environment and registers core apps (Terminal, File Manager).

## D) SECURITY
- **Verification Pass:** `AppRegistry` runs a dry-run import of core apps to ensure integrity.
- **Identity Isolation:** The boot flow ensures that `current_user` is set globally before any app can request filesystem access.

## E) LIMITATIONS
- Current boot is synchronous; failure in one core component can stall the entire system.
- Limited rollback capability if a hardware token check fails mid-boot.

## F) FUTURE WORK
- Implementation of a "Safe Mode" boot that bypasses non-essential app registration.
- Parallelized component loading to improve startup time.

---

# SUBSYSTEM: WINDOW_MANAGER
## A) WHY
The Window Manager (WM) provides the visual abstraction of the Q-Vault OS. It is responsible for window lifecycle, layout, and ensuring that sandboxed applications cannot interfere with each other's visual space.

## B) HOW
Implemented in `system/window_manager.py`, it manages a collection of `AppWindow` objects. It handles Z-index stacking, focus management, and minimizes/restores windows via the `EVENT_BUS`.

## C) FLOW
1. **Request:** An app or the system emits `REQ_APP_LAUNCH`.
2. **Validation:** `WindowManager` checks if the app is already running (focus instead) or needs a new window.
3. **Creation:** A new `AppWindow` is instantiated, and a `SecureAPI` is injected.
4. **Registration:** The window is registered in the taskbar and assigned a Z-order.
5. **Interaction:** User clicks/drags emit events that the WM translates into geometry updates.

## D) SECURITY
- **Visual Isolation:** Apps cannot "draw outside" their window bounds (enforced by PyQt parentage).
- **Control Interdiction:** Only the WM can terminate a window; apps cannot "force-close" other apps without kernel permission.

## E) LIMITATIONS
- Basic tiling support; lacks advanced snapping found in host OSs.
- Heavy reliance on the Main UI thread for geometry calculations.

## F) FUTURE WORK
- Virtual Desktops (Workspaces) support.
- Hardware-accelerated transparency and glassmorphism optimizations.

---

# SUBSYSTEM: TERMINAL_ENGINE
## A) WHY
The Terminal is the primary interface for system interaction and forensic analysis. It provides a familiar shell-like environment while enforcing strict governance on all executed commands.

## B) HOW
Located in `apps/terminal/terminal_engine.py`, it uses a class-based command registry. It separates command parsing (flags/args) from execution logic, and all filesystem/process operations are routed through the `SecureAPI`.

## C) FLOW
1. **Input:** User types a command and presses Enter.
2. **Parsing:** `CommandParser` breaks the string into parts and flags.
3. **Lookup:** The `COMMAND_REGISTRY` identifies the corresponding `BaseCommand` class.
4. **Execution:** The command's `execute()` method is called with a `CommandContext`.
5. **Output:** Results are formatted via `OutputFormatter` and displayed.

## D) SECURITY
- **Path Sanitization:** Every command (ls, cd, rm) validates that the target path is within the user's sandbox.
- **Command Injection Prevention:** Shell characters are interdicted before execution.

## E) LIMITATIONS
- Lacks full `pty` (pseudo-terminal) support for complex interactive CLI apps.
- No support for pipe chaining (`|`) in the current version.

## F) FUTURE WORK
- Support for complex scripting (VaultScript).
- Integrated forensic visualizer for command execution traces.
