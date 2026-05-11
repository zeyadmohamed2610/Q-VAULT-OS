# SUBSYSTEM: TELEMETRY_ENGINE
## A) WHY
Telemetry is the "Eyes and Ears" of the Q-Vault Kernel. It provides the data necessary for trust scoring, performance monitoring, and forensic auditing.

## B) HOW
The Telemetry Engine collects metrics from various sources:
1. **App Workers:** Report CPU/Memory usage.
2. **SecureAPI:** Reports frequency of filesystem and network calls.
3. **Event Bus:** Reports event latency and slow handlers.
Data is aggregated in the `RuntimeManager`.

## C) FLOW
1. **Sampling:** Every $N$ ticks, metrics are collected from all active instances.
2. **Aggregation:** Raw data is converted into "Normalized Ratios" (0.0 to 1.0).
3. **Distribution:** Metrics are sent to the `EVENT_BUS` for UI updates (e.g., in Kernel Monitor).
4. **Storage:** Critical telemetry is written to `.logs/system/runtime_telemetry.ndjson`.

## D) SECURITY
- **Evidence Preservation:** Telemetry logs are append-only and cryptographically protected (simulated).
- **Anti-Tampering:** Apps cannot see or modify their own telemetry data.

## E) LIMITATIONS
- High sampling rates can consume significant CPU.
- Telemetry is current-session only; limited historical analytics.

## F) FUTURE WORK
- Offloading telemetry processing to a dedicated "Security Coprocessor" (thread).
- Advanced visualization of telemetry "heatmaps" for the whole OS.

---

# SUBSYSTEM: GOVERNANCE_STATES
## A) WHY
Governance States define the "Operational Posture" of the OS. They allow the kernel to scale its security enforcement based on the overall system health and perceived threat level.

## B) HOW
The system transitions between global states:
1. **STABLE:** Normal enforcement; high trust.
2. **DEGRADED:** Minor performance issues; soft throttling.
3. **CAUTION:** Suspicious activity detected; aggressive auditing.
4. **INTERDICTION:** Immediate threat; mandatory quarantine.

## C) FLOW
1. **Assessment:** `RuntimeManager` calculates the "Global Pressure Ratio."
2. **Threshold:** If pressure > 0.8, the state moves to `CAUTION`.
3. **Response:** In `CAUTION`, the `SecureAPI` adds artificial latency (10-50ms) to every call to "slow down" potential attackers.
4. **Escalation:** If a critical violation occurs, the state moves to `INTERDICTION`.

## D) SECURITY
- **Adaptive Defense:** Hardens the system automatically when under attack.
- **Fail-Safe Mode:** If the system is overwhelmed, it enters a "Locked" state to protect the Vault.

## E) LIMITATIONS
- State transitions are currently based on a few metrics (CPU/Memory).
- Lack of "Local Governance" (e.g., hardening only one app while keeping others stable).

## F) FUTURE WORK
- Per-application governance profiles.
- External triggers (e.g., from a Hardware Security Module) for state transitions.

---

# SUBSYSTEM: PRESSURE_MANAGEMENT
## A) WHY
Pressure Management prevents "Resource Starvation" attacks. It ensures that critical OS services (like the Terminal or Window Manager) always have enough resources to function, even if apps are behaving poorly.

## B) HOW
Implemented via the "Backpressure Mechanism" in the `RuntimeManager`. It monitors the ratio of allocated resources to available host resources.

## C) FLOW
1. **Monitoring:** Tracks host RSS memory and CPU load.
2. **Calculation:** Determines "Pressure Ratio" ($Used / Limit$).
3. **Feedback:** If ratio > 0.9, the `RUNTIME_MANAGER` sends `backpressure_applied` events.
4. **Throttling:** Applications are instructed to reduce their "worker frequency."
5. **Reclamation:** If necessary, the kernel kills the least-trusted non-core app to reclaim memory.

## D) SECURITY
- **DoS Resistance:** Prevents an app from crashing the system by consuming 100% CPU or RAM.
- **Fair-Share Scheduling:** Ensures all apps get a "slice" of the resources proportional to their trust.

## E) LIMITATIONS
- Reclamation (killing apps) can be disruptive to the user.
- Throttling depends on app-side cooperation (or heavy-handed kernel preemption).

## F) FUTURE WORK
- Dynamic resource quotas that adjust in real-time.
- User-driven "Energy/Security Profiles" to control pressure thresholds.
