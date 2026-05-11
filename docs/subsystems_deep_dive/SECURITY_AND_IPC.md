# SUBSYSTEM: EVENT_BUS_INTERNALS
## A) WHY
The Event Bus is the "Central Nervous System" of Q-Vault. It decouples components, allowing the UI, Kernel, and Applications to communicate without direct dependencies, which is critical for system stability and scalability.

## B) HOW
Implemented in `core/event_bus.py` as a singleton. It uses a Publish/Subscribe pattern with `threading.RLock` for thread safety. It supports weak references to prevent memory leaks from UI widgets.

## C) FLOW
1. **Emit:** A component calls `EVENT_BUS.emit(SystemEvent.TYPE, data)`.
2. **Snapshot:** The bus takes a thread-safe snapshot of current subscribers.
3. **Dispatch:** It iterates through subscribers and calls their callbacks.
4. **Monitoring:** It detects "Slow Handlers" ( > 50ms) and reports them to the telemetry engine.
5. **Cleanup:** Periodically sweeps dead weak references.

## D) SECURITY
- **Deadlock Prevention:** Uses recursive locks (`RLock`) to allow a callback to emit another event safely.
- **Throttling:** High-frequency events (like window dragging) are rate-limited to preserve UI responsiveness.

## E) LIMITATIONS
- Synchronous dispatch; a slow handler blocks the emitter thread.
- No support for "Event Priority" yet (all events are equal).

## F) FUTURE WORK
- Asynchronous dispatch via a dedicated worker pool.
- Persistent event logging for forensic replay.

---

# SUBSYSTEM: SANDBOX_ENFORCEMENT
## A) WHY
Sandbox Enforcement ensures that applications are "prisoners" of their own context. It is the primary defense against malware or accidental data corruption in a sovereign OS.

## B) HOW
Enforcement is multi-layered:
1. **Module Interdiction:** Raw Python imports (like `os` or `subprocess`) are blocked or monitored.
2. **Guard Objects:** Every resource (Files, Network, Processes) is wrapped in a "Guard" that enforces policies.
3. **Identity Binding:** All API calls are tagged with the app's `instance_id`.

## C) FLOW
1. **Request:** App calls `secure_api.fs.read("/secure/data.txt")`.
2. **Validation:** `FileSystemGuard` checks if the path is within the app's virtual root.
3. **Policy Check:** `PermissionManager` verifies the app has the `file_read` permission.
4. **Execution:** If valid, the real OS call is made; otherwise, a `PermissionError` is raised.

## D) SECURITY
- **Path Traversal Prevention:** Blocks attempts to use `..` or absolute host paths.
- **Resource Depletion Defense:** Guards enforce limits on number of open files or network sockets.

## E) LIMITATIONS
- Performance overhead due to multiple validation layers.
- Python's dynamic nature makes "perfect" sandboxing difficult without OS-level containers.

## F) FUTURE WORK
- Integration with OS-level namespaces (cgroups/namespaces) on supported hosts.
- Hardware-enforced memory isolation (TEE integration).

---

# SUBSYSTEM: SECURE_API_CALL_FLOW
## A) WHY
The Secure API Call Flow defines the mandatory protocol for app-to-kernel communication. It is the only "authorized bridge" between untrusted app code and the trusted system core.

## B) HOW
Every app is injected with a `SecureAPI` instance. This object acts as a proxy for all system services. It includes a "Forensic Integrity Check" that verifies the caller's stack frame.

## C) FLOW
1. **API Invocation:** App code calls a method on `self.secure_api`.
2. **Integrity Check:** `_verify_caller_integrity()` uses `inspect.stack()` to ensure the call originates from a registered app file.
3. **Context Check:** Verifies the API is not "Locked" (Quarantined).
4. **Delegation:** The request is passed to the specific Guard (FS, Net, etc.).
5. **Audit Logging:** The call is recorded in the forensic trace for introspection.

## D) SECURITY
- **Cross-Context Prevention:** Prevents an app from calling the API on behalf of another app.
- **Forensic Transparency:** Provides a complete audit trail of what every app tried to do.

## E) LIMITATIONS
- `inspect.stack()` is computationally expensive for high-frequency calls.
- Limited protection against direct memory manipulation of the API object.

## F) FUTURE WORK
- Transition to a Message-Passing IPC (like gRPC or sockets) for true process isolation.
- Digitally signed API tokens for every call.
