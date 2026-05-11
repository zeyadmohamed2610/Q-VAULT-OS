# SUBSYSTEM: PROCESS_GOVERNOR
## A) WHY
The Process Governor is responsible for "Sovereign Identity Management." It ensures that the host OS (Windows/Linux) is completely hidden from the user, providing a cinematic experience where only Q-Vault entities exist.

## B) HOW
Implemented in `system/runtime/process_governor.py`, it maintains a mapping between real OS PIDs and Q-Vault virtual PIDs. It also sanitizes file paths and process names in all telemetry output.

## C) FLOW
1. **Detection:** A process is spawned by the kernel.
2. **Alias Assignment:** The Governor assigns a "Cinematic Name" (e.g., `crypto-daemon`) to the OS process.
3. **Filtering:** All telemetry requests (e.g., `ps` command) pass through the Governor to replace real paths with virtual ones (e.g., `C:\Users\...` becomes `/secure/`).
4. **Monitoring:** It tracks process health and reports crashes to the `RuntimeManager`.

## D) SECURITY
- **Information Leak Prevention:** Prevents apps from discovering the underlying host environment.
- **Path Obfuscation:** Hides the actual physical location of sensitive vault files.

## E) LIMITATIONS
- Mapping is currently in-memory; lost if the Governor service restarts.
- Some low-level OS calls might still leak real PIDs if not properly wrapped.

## F) FUTURE WORK
- Persistent identity mapping across sessions.
- Dynamic "Process Masking" using kernel-level driver hooks (simulated).

---

# SUBSYSTEM: TRUST_ALGORITHM
## A) WHY
The Trust Algorithm is the heart of the Governed Runtime. It moves beyond static permissions to "Behavioral Security," where an app's access is determined by its ongoing behavior.

## B) HOW
Located in `system/runtime_manager.py`, it calculates a "Trust Score" (0-100) for every instance. It uses a weighted formula considering: CPU usage, Memory consumption, API call frequency, and Error rate.

## C) FLOW
1. **Telemetery Intake:** `RuntimeManager` receives periodic heartbeats from app workers.
2. **Analysis:** The algorithm compares current usage against "Normal Baseline" profiles.
3. **Penalty/Bonus:** Excessive calls or crashes trigger penalties. Stable behavior slowly restores trust.
4. **Enforcement:** If score < 20, the app is flagged for Quarantine.

## D) SECURITY
- **Heuristic Defense:** Detects zero-day threats or "rogue" apps that stay within their permissions but exhibit malicious patterns (e.g., file-flooding).
- **Backpressure Enforcement:** Slows down or halts apps that threaten system stability.

## E) LIMITATIONS
- Baselines are currently static; no AI-based "learning" of app behavior yet.
- Potential for false positives in high-performance computational apps.

## F) FUTURE WORK
- ML-based anomaly detection for trust scoring.
- User-adjustable "Aggression Levels" for the governance engine.

---

# SUBSYSTEM: QUARANTINE_PIPELINE
## A) WHY
The Quarantine Pipeline is the system's "Immune Response." It provides a safe way to isolate and investigate suspicious applications without crashing the entire OS.

## B) HOW
When an app's Trust Score fails, the `RuntimeManager` triggers a Quarantine sequence. This involves locking the app's `SecureAPI`, pausing its execution threads, and displaying a visual "Quarantine Overlay."

## C) FLOW
1. **Trigger:** Trust Score drops below the threshold.
2. **Interdiction:** `SecureAPI` enters `LOCKED` state; all future calls raise `PermissionError`.
3. **UI Feedback:** `WindowManager` is signaled to show the red "QUARANTINED" overlay on the app window.
4. **Containment:** Process execution is throttled to near-zero CPU.
5. **Resolution:** User/Admin must manually review the audit log to "Release" or "Terminate" the app.

## D) SECURITY
- **Immediate Containment:** Stops an attack in progress within milliseconds of detection.
- **Forensic Preservation:** Keeps the app state in memory for investigation rather than just killing it.

## E) LIMITATIONS
- Quarantine is instance-specific; a new launch of the same app starts with a fresh score (unless global penalty applied).
- Limited "Partial Quarantine" modes.

## F) FUTURE WORK
- "Sandboxed Investigation" mode where an app runs in a restricted sub-sandbox while quarantined.
- Automatic reporting to a central security dashboard.
