# SUBSYSTEM: THREADING_ANALYSIS
## A) WHY
Q-Vault is a multi-threaded system to ensure that UI responsiveness (60fps) is maintained even during intensive security scans or cryptographic operations.

## B) HOW
The system uses a "UI-Primary, Worker-Secondary" model.
1. **Main Thread:** Handles PyQt5 event loop, rendering, and input.
2. **Worker Threads:** `AppWorker` handles the logic of sandboxed apps.
3. **Kernel Threads:** `RuntimeManager` and `EventBus` use background threads for health monitoring.

## C) FLOW
1. **Spawn:** App launch creates a new `QThread` and an `AppWorker`.
2. **Communication:** Workers communicate with the UI thread via `pyqtSignal` and the `EVENT_BUS`.
3. **Synchronization:** Critical system state is protected by `threading.RLock`.
4. **Safety:** The `SecureAPI` ensures that workers never touch UI elements directly.

## D) SECURITY
- **Blocking Protection:** Prevents a rogue app from "freezing" the UI by executing an infinite loop (since it's in a worker thread).
- **Deadlock Avoidance:** Strict hierarchy for lock acquisition (Bus -> Kernel -> App).

## E) LIMITATIONS
- Python's Global Interpreter Lock (GIL) limits true multi-core utilization for CPU-bound tasks.
- Complexity in managing object ownership across thread boundaries.

## F) FUTURE WORK
- Transition to `multiprocessing` for true process isolation and bypass of the GIL.
- Automated deadlock detection in the `RuntimeManager`.

---

# SUBSYSTEM: RUNTIME_LIFECYCLE
## A) WHY
The Runtime Lifecycle governs the "Birth, Life, and Death" of an application. It ensures that resources are allocated safely and, more importantly, cleaned up completely.

## B) HOW
The lifecycle is managed by the `AppRuntimeManager`. It tracks states: `SPAWNING` -> `ACTIVE` -> `THROTTLED` -> `QUARANTINED` -> `TERMINATING`.

## C) FLOW
1. **Birth:** `REQ_APP_LAUNCH` creates the instance and registers it in the telemetry engine.
2. **Growth:** App gains trust through stable operation and receives resources.
3. **Decay:** If the app misbehaves, it moves to `THROTTLED` or `QUARANTINED`.
4. **Death:** `REQ_APP_TERMINATE` triggers a graceful shutdown (signaling threads to stop).
5. **GC:** The `GarbageCollector` (in `runtime_manager`) deallocates memory and removes the instance ID.

## D) SECURITY
- **Orphan Prevention:** Ensures that no "zombie" processes remain running after a window is closed.
- **State Rollback:** If an app crashes during startup, the kernel rolls back its resource allocations.

## E) LIMITATIONS
- Graceful shutdown depends on the app's responsiveness; "Force Kill" is sometimes necessary.
- Limited persistent state recovery if the system crashes.

## F) FUTURE WORK
- "Snapshot & Restore" capabilities (hibernating apps).
- Predictive resource allocation based on historical usage.

---

# SUBSYSTEM: OVERLAY_SYSTEM
## A) WHY
Overlays provide "Out-of-Band" communication with the user. They are used for critical security alerts, login screens, and system-wide notifications that must bypass normal app windows.

## B) HOW
Implemented as a specialized layer in the `WindowManager`. Overlays are full-screen, translucent widgets that sit on top of all other windows. They use `Qt.WindowStaysOnTopHint`.

## C) FLOW
1. **Trigger:** A system event (e.g., `SECURITY_ALERT`) is received.
2. **Selection:** The `OverlayController` selects the appropriate overlay (e.g., `QuarantineOverlay`).
3. **Display:** The overlay is animated into view, often blurring the background desktop.
4. **Interaction:** User inputs are captured by the overlay; background interaction is usually blocked (Modal).
5. **Dismissal:** Once resolved, the overlay is animated out and destroyed.

## D) SECURITY
- **Unforgeable UI:** Apps cannot create their own "System Overlays"; only the Kernel-trusted WM can.
- **Critical Visibility:** Ensures that security alerts cannot be hidden by a malicious app window.

## E) LIMITATIONS
- Performance cost of blur effects on older hardware.
- UI "Flicker" if multiple overlays are triggered simultaneously.

## F) FUTURE WORK
- Unified "Notification Center" for non-modal overlays.
- 3D-accelerated transition effects for cinematic impact.
