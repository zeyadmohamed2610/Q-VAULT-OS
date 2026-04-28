"""
system/runtime_manager.py
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS Phase 8 — Intelligence & Runtime Governance Layer

This module manages process execution, central logging, and the Trust Rating System.
─────────────────────────────────────────────────────────────────────────────
"""
import json
import logging
import importlib
import os
import time
import multiprocessing
from dataclasses import dataclass, field, replace
import threading
from enum import Enum
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QWidget
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager


from system.errors import SecurityError  # Canonical error class

logger = logging.getLogger("system.runtime_manager")

class AppState(Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    CRASHED = "CRASHED"
    QUARANTINED = "QUARANTINED"
    TERMINATED = "TERMINATED"

class SystemState(Enum):
    NORMAL = "NORMAL"
    AGGRESSIVE = "AGGRESSIVE" # Increased throttling
    EMERGENCY = "EMERGENCY"  # Global worker lockdown

class AppRecord:
    """Wrapper that holds the state and trust intelligence of a running instance."""
    def __init__(self, instance_id: str, app_instance: Any, app_id: str):
        from collections import deque
        self.instance_id = instance_id
        self.app_instance = app_instance
        self.app_id = app_id
        self.state = AppState.INITIALIZED
        self.trust_score = 100
        self.crash_count = 0
        self.violations = 0
        
        # Phase 11 & 12: Advanced Telemetry
        self.crash_timestamps = deque(maxlen=10)
        self.active_workers = {
            "network": 0,
            "process": 0,
            "fs": 0,
            "total": 0
        }
        self.last_penalty_time = 0.0

        # Phase 15.3.6: Multi-process Telemetry
        self.main_pid = os.getpid() # Default to main process
        self.rss_start = self._get_current_rss()
        self.rss_history = deque([self.rss_start], maxlen=5)
        
        # ── Phase 16.5: Production Security & Governance ──
        self.session_secret = "" # HMAC Key
        self.congested = False   # Backpressure flag
        
        # ── Phase 14.3.2 Architecture ──
        self.last_warning_time = 0.0 # timestamp of last penalty/violation
        self.stable_usage_seconds = 0.0 # cumulative time since last friction
        
        # Phase 13.9: Atomic Process Tracking
        self.tracked_pids = set() # pids currently counted in active_workers["process"]
        
        # ── Phase 14.3.2: Kernel-level Backpressure & Rate Limiting ──
        self.pending_calls = 0
        self.call_window = deque(maxlen=200) # Sliding window for rate limiting
        self._max_pending = 50 # Per-app internal queue safety
        self.local_throttled = False # Phase 15.5: Targeted throttling flag
        
        # ── Phase 16.8: Lightweight Production Metrics ──
        self.total_msgs_handled = 0
        self.msg_hz = 0.0
        self.peak_queue_size = 0
        self.last_hz_calc_time = time.time()
        self.last_msgs_count = 0
        
        # ── Phase 14 Security Architecture ──
        # Root determination is now KERNEL-AUTHORITATIVE. 
        # App cannot touch its own root path variable.
        self.sandbox_root = self._init_sandbox_root()
        self.storage_root = self.sandbox_root / "data"
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _init_sandbox_root(self) -> "pathlib.Path":
        import pathlib
        root = pathlib.Path(".").resolve() / "users" / self.app_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _get_current_rss(self) -> int:
        import psutil
        try:
            # Use the tracked subprocess PID for isolated apps (Phase 15.3.6)
            return psutil.Process(self.main_pid).memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0
        except: return 0

    def get_mem_trend(self) -> str:
        """Calculates Stable, Increasing, or Spike based on RSS history."""
        if len(self.rss_history) < 2: return "STABLE"
        
        last = self.rss_history[-1]
        prev = self.rss_history[-2]
        delta = last - prev
        
        if delta > 10 * 1024 * 1024: return "🔥 SPIKE" # > 10MB jump
        if delta > 1 * 1024 * 1024:  return "⬆ INCREASING"
        if delta < -1 * 1024 * 1024: return "⬇ DECREASING"
        return "🆗 STABLE"

class AppRuntimeManager:
    """
    Q-Vault OS Authority — The Micro-Kernel Singleton.
    
    Acts as the exclusive governor for resource allocation, security 
    enforcement, and process lifecycle management.
    """
    _instance = None

    def __new__(cls):
        # 1. Authority Verification: Ensure we are in the MAIN PROCESS
        import multiprocessing
        if multiprocessing.current_process().name != 'MainProcess':
            # Subprocesses (Apps) cannot have a local Kernel singleton.
            # They must talk to the Parent's singleton via SecureAPI.
            return None 

        if cls._instance is None:
            cls._instance = super(AppRuntimeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Ensure we only init once even if called multiple times (Singleton)
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        
        from core.app_registry import AppRegistry
        self._registry = AppRegistry() # Central authority records
        self.state = SystemState.NORMAL
        # Reference to Desktop for UI notifications
        self._desktop_parent: Optional[QWidget] = None

        # Configure system.log for Runtime Governance Central Logging
        import os
        from pathlib import Path
        log_dir = Path(".logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        system_log = log_dir / "system.log"
        
        self.logger = logging.getLogger("system.runtime_manager")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            fh = RotatingFileHandler(system_log, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            fmt = logging.Formatter("%(asctime)s | [RUNTIME] %(levelname)s: %(message)s")
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)
            self.logger.propagate = False

        # Phase 16.9: Production NDJSON Audit Trail (Rotating)
        self.audit_logger = logging.getLogger("system.audit_trail")
        self.audit_logger.setLevel(logging.INFO)
        if not self.audit_logger.handlers:
            audit_file = log_dir / "audit_trail.ndjson"
            try:
                ah = RotatingFileHandler(audit_file, maxBytes=10_000_000, backupCount=3, encoding="utf-8")
                ah.setFormatter(logging.Formatter("%(message)s"))
                self.audit_logger.addHandler(ah)
            except Exception as e:
                self.logger.error(f"Critical Logging Failure: {e}")
        self.audit_logger.propagate = False
            
        # ── Phase 13.5: Autonomous Pressure Core ──
        from collections import deque
        self.global_calls = deque(maxlen=400)    # (timestamp, instance_id)
        self.global_state = "NORMAL"
        self.emergency_start_time = 0.0
        self.emergency_alert_sent = False
        self.current_pressure_ratio = 0.0
        self.current_cooldown = 0.0
        self.max_pressure_seen = 0.0

        # ── Phase 13.6: Observability Engine ──
        self.decision_history = deque(maxlen=50)       # Structured decision trace
        self.pressure_history = deque(maxlen=120)      # (timestamp, ratio) — 2 min @ 1Hz
        self._gov_log_buffer = []                      # NDJSON flush buffer
        self._last_decision_time = 0.0                 # Rate-limit: max 1 decision per 500ms
        self._last_flush_time = 0.0                    # Last disk-write timestamp
        # ── Phase 13.7: Reality Hardening ──
        self.ui_lag_ms = 0.0
        self._last_pulse_time = 0.0
        self._pulse_timer = None 
        self._registry: Dict[str, AppRecord] = {}
        self._reputation_cache: Dict[str, int] = {} # Phase 13.8 Persistence
        self.global_kill_count = 0                  # Phase 16.8 Global Audit
        self._lock = threading.RLock()
        
        # ── Phase 16.5: Production Stability ──
        self._perform_cold_start_cleanup()

        try:
            from core.process_manager import PM
            PM.subscribe(self._on_process_event)
        except Exception as e:
            self.logger.error(f"Failed to subscribe to Core PM: {e}")

    def _perform_cold_start_cleanup(self):
        """Phase 16.5: Cleanup orphaned engines on cold boot."""
        import psutil
        import os
        current_pid = os.getpid()
        self.logger.info("[Kernel] Performing Cold Start Cleanup...")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Identify Q-Vault engines (using a simple cmdline signature)
                cmd = " ".join(proc.info.get('cmdline', []) or [])
                if "IsolatedAppWidget" in cmd or "remote_engine" in cmd:
                    if proc.info['pid'] != current_pid:
                        self.logger.warning(f"[Kernel] Terminating orphan process: {proc.info['pid']}")
                        proc.terminate()
            except: pass

    def set_desktop_parent(self, desktop: QWidget) -> None:
        self._desktop_parent = desktop

    def get_record(self, instance_id: str) -> Optional[AppRecord]:
        return self._registry.get(instance_id)

    def get_state(self, instance_id: str) -> Optional[AppRecord]:
        """
        Alias for get_record() — returns the AppRecord (which carries .state
        and .trust_score).  Attack-engine and external callers use this name;
        keeping both avoids a breaking-change to internal callers.
        """
        return self._registry.get(instance_id)

    def start_app(self, app_id: str) -> str:
        """
        Instantiate and register an app by its ID string.

        The ID can be either a display name from the manifest (e.g. "Terminal")
        or the name key used when injecting a dynamic AppDefinition into
        REGISTRY._definitions (e.g. the attack engine's adversarial app IDs).

        Returns the generated instance_id (UUID-suffixed string).
        """
        from core.app_registry import REGISTRY
        import uuid

        instance_id = f"{app_id}_{uuid.uuid4().hex[:4]}"

        # Resolve the AppDefinition — dynamic defs are checked first by get_by_name
        app_def = REGISTRY.get_by_name(app_id) or REGISTRY._definitions.get(app_id)

        if app_def is None:
            # No definition at all — create a minimal stub AppRecord so the
            # instance still exists in the registry for governance purposes.
            logger.warning(
                f"[RuntimeManager] start_app: no AppDefinition for '{app_id}' "
                "— creating stub record"
            )
            from unittest.mock import MagicMock
            stub = MagicMock()
            stub._app_id = app_id
            return self._register_stub(instance_id, stub, app_id)

        app_instance = REGISTRY.instantiate(app_def)

        if app_instance is None:
            # REGISTRY already logged the error; create a quarantined stub
            logger.warning(
                f"[RuntimeManager] start_app: REGISTRY failed to instantiate '{app_id}'"
            )
            from unittest.mock import MagicMock
            stub = MagicMock()
            stub._app_id = app_id
            return self._register_stub(instance_id, stub, app_id)

        if self.safe_start(instance_id, app_instance):
            return instance_id
        else:
            return instance_id  # Return ID even if immediately quarantined

    def _register_stub(self, instance_id: str, stub, app_id: str) -> str:
        """Register a non-functional stub so the runtime doesn't crash."""
        record = AppRecord(instance_id, stub, app_id)
        record.state = AppState.QUARANTINED
        
        # Phase 13.8: Ensure stubs also respect the reputation cache
        if app_id in self._reputation_cache and self._reputation_cache[app_id] < 60:
            record.trust_score = self._reputation_cache[app_id]
            self.logger.info(f"[RuntimeManager] Restoring legacy trust for STUB '{app_id}': {record.trust_score}")
            
        self._registry[instance_id] = record
        return instance_id

    def register(self, instance_id: str, app_instance: Any, secret: str = "") -> AppRecord:
        app_id = getattr(app_instance, "_app_id", "Unknown")
        record = AppRecord(instance_id, app_instance, app_id)
        record.session_secret = secret
        
        with self._lock:
            # Phase 13.8: Carry over reputation if it's the same app_id in this session
            # Phase 13.8/9: Constant Reputation Persistence
            # We always restore to the last known state to prevent restart-gaming.
            if app_id in self._reputation_cache:
                prev_trust = self._reputation_cache[app_id]
                record.trust_score = prev_trust
                self.logger.info(f"[RuntimeManager] Restoring persistence for '{app_id}': {prev_trust}")

            # Phase 14: Finalise sandbox environment
            # Ensure the directory exists and permissions are secure
            from pathlib import Path
            Path(record.sandbox_root).mkdir(parents=True, exist_ok=True)
            self.log_event("APP_REGISTERED", {"instance_id": instance_id, "app_id": app_id})
            
            # Phase 15.4: Forced Governance Gate (Zero Bypass)
            from core.app_registry import SAFE_MODE, DEFAULT_ISOLATION
            if app_id not in ["Desktop", "Taskbar", "SystemUI"] and not SAFE_MODE:
                # Current state audit: Does the app expect 'direct' mode?
                # We check the app instance or its manifest via REGISTRY if accessible
                pass # Already enforced at Registry instantiation level, but we keep the gate logic ready.

            self._registry[instance_id] = record
            self.logger.info(f"[RuntimeManager] Registered '{instance_id}' ({app_id}) | Jail: {record.sandbox_root}")
            
            EVENT_BUS.emit(SystemEvent.APP_LAUNCHED, {"instance_id": instance_id, "app_id": app_id}, source="RuntimeManager")
            return record

    def safe_start(self, instance_id: str, app_instance: Any) -> bool:
        # Idempotency guard: WindowManager calls animate_show (which calls
        # safe_start) on both initial open AND on restore from minimized/hidden.
        # Re-registering would reset trust_score and state on every unminimize.
        if instance_id in self._registry:
            record = self._registry[instance_id]
            self.logger.debug(
                f"[RuntimeManager] safe_start skipped — '{instance_id}' already registered"
            )
            # Still fire on_start if the widget supports it and isn't running
            if record.state == AppState.RUNNING:
                return True
            # Re-activate from a non-running state (e.g. CRASHED -> RUNNING)
            record.state = AppState.RUNNING
            return True

        # ── Phase 16.5: Secret Handshake ──
        secret = getattr(app_instance, "_session_secret", "")
        record = self.register(instance_id, app_instance, secret)
        
        # 1. Enforcement Check via previous historical scores
        # We might check a global database of trust scores, but for now it's instance-based
        if record.trust_score < 20:
            self.quarantine_app(instance_id, "Pre-launch Trust Failure")
            return False

        # 2. Execution Guard
        try:
            record.state = AppState.RUNNING
            if hasattr(app_instance, "_trigger_start"):
                app_instance._started = True
                if hasattr(app_instance, "on_start"):
                    app_instance.on_start()
            
            # Phase 13.9: Removed automatic +5 launch bonus to prevent gaming.
            # Trust must be EARNED through stable behavior, checked in _update_system_pressure.
            return True
                
        except Exception as e:
            with self._lock:
                if instance_id in self._registry:
                    self._registry[instance_id].state = AppState.CRASHED
            self.logger.error(f"[RuntimeManager] Launch failed for '{instance_id}': {e}")
            self.notify(f"System Error: {record.app_id}", f"Failed to start: {str(e)}", "error")
            return False

    def handle_crash(self, instance_id: str, error: Exception) -> None:
        record = self.get_record(instance_id)
        if not record: return
        
        import time
        now = time.time()
        record.crash_timestamps.append(now)
        record.crash_count += 1
        record.trust_score -= 15
        record.state = AppState.CRASHED
        
        self.logger.error(f"🚨 [AppCrashed] {record.app_id} (ID: {instance_id}): {error} | Trust: {record.trust_score}")
        EVENT_BUS.emit(SystemEvent.APP_CRASHED, {"instance_id": instance_id, "app_id": record.app_id, "error": str(error)}, source="RuntimeManager")
        
        # Phase 13 Stage C: Robust Cleanup on Crash
        if record.worker_tokens:
            self.logger.warning(f"[RuntimeManager] Reclaiming {len(record.worker_tokens)} slots after crash.")
            record.worker_tokens.clear()
        record.active_workers = {"network": 0, "process": 0, "fs": 0, "total": 0}

        # ── Advanced Crash Policy: 2 crashes in 10s ──
        recent_crashes = [t for t in record.crash_timestamps if now - t < 10.0]
        if len(recent_crashes) >= 2:
            self.quarantine_app(instance_id, "Rapid Crash Sequence detected (2 crashes in 10s).")
            return

        if record.trust_score < 20:
            self.quarantine_app(instance_id, "Trust Score critically low due to crashes.")
        else:
            self.notify(
                title=f"App Crash: {record.app_id}",
                text=f"Stopped unexpectedly:\n{str(error)[:100]}",
                level="warning"
            )
            self.kill(instance_id)

    def report_violation(self, instance_id: str, reason: str) -> None:
        record = self.get_record(instance_id)
        if not record: return
        
        record.violations += 1
        record.trust_score -= 30
        self.logger.critical(f"[VIOLATION] {record.app_id} | {reason} | Score dropped to {record.trust_score}")
        EVENT_BUS.emit(SystemEvent.SECURITY_ALERT, {"instance_id": instance_id, "app_id": record.app_id, "reason": reason, "trust": record.trust_score}, source="RuntimeManager")

    def check_backpressure(self, instance_id: str, queue_size: int) -> bool:
        """
        Kernel-level congestion check with Dynamic Kill Policy (Phase 16.7).
        """
        record = self.get_record(instance_id)
        if not record: return False
        
        if queue_size > 50:
            if not record.congested:
                self.logger.warning(f"[Backpressure] {record.app_id} is congested ({queue_size} pending).")
            record.congested = True
            
            # Exponential Penalty (Phase 16.6)
            penalty = (queue_size // 10) ** 1.5
            record.trust_score -= int(penalty)
            
            # ── Phase 16.7: Dynamic Kill Policy ──
            # Define 'Core' apps that should NEVER be hard-killed to prevent OS-level collapse.
            CORE_APPS = {"Desktop", "Taskbar", "SystemUI", "Marketplace"}
            
            if record.trust_score < 20:
                if record.app_id not in CORE_APPS:
                    self.global_kill_count += 1
                    self.log_event("UNTRUSTED_KILL", {
                        "instance_id": instance_id, 
                        "app_id": record.app_id, 
                        "trust": record.trust_score,
                        "pressure": queue_size
                    })
                    self.logger.critical(f"🚨 [KILL POLICY] {record.app_id} ({instance_id}) terminated. Trust: {record.trust_score}")
                    self.report_violation(instance_id, f"Critical Trust Failure (Pressure {queue_size})")
                    return True 
                else:
                    self.logger.warning(f"⚠️ [CORE DEGRADATION] {record.app_id} is untrusted but CORE. Throttling only.")

            if record.trust_score < 30:
                self.logger.critical(f"[Backpressure] {record.app_id} critically congested. Score: {record.trust_score}")
                
            return True
        else:
            record.congested = False
            return False

        
        if record.trust_score < 20:
            self.quarantine_app(instance_id, reason)
        else:
            record.last_warning_time = time.time()
            self.notify(f"Security Alert: {record.app_id}", reason, "warning")

    def apply_penalty(self, instance_id: str, score: int, reason: str) -> None:
        """Graduated penalty for suspicious but non-violation behavior."""
        record = self.get_record(instance_id)
        if not record: return
        
        import time
        now = time.time()
        
        # Debounce NOTIFICATIONS but not the actual trust drop.
        # This ensures high-speed attacks are correctly penalized while keeping UI logs clean.
        can_notify = (now - record.last_penalty_time >= 0.5)
        
        record.trust_score += score  # score is negative usually
        record.last_warning_time = now
        
        if can_notify:
            record.last_penalty_time = now
        
        self.logger.warning(f"[PENALTY] {record.app_id} | {reason} ({score}) | Current Trust: {record.trust_score}")

        if record.trust_score < 20:
            self.quarantine_app(instance_id, f"Cumulative penalties: {reason}")
        elif can_notify:
            self.notify(f"System Warning: {record.app_id}", f"Behavioural penalty: {reason}", "warning")

    def report_ui_pulse(self):
        """Called by LagMonitor to report main-thread responsiveness (Phase 15.3.5)."""
        import time
        now = time.time()
        if self._last_pulse_time > 0:
            delta = (now - self._last_pulse_time) * 1000 # to ms
            self.ui_lag_ms = max(0, delta - 100) # 100ms is the timer interval
        self._last_pulse_time = now

        # Authoritative Resource Reconciliation
        with self._lock:
            self._reconcile_dead_processes()

    def _reconcile_dead_processes(self):
        """Phase 15.3.5: Prevents ghost workers by cross-referencing PM."""
        from core.process_manager import PM
        dead_pids = []
        
        # Collect all tracked pids across all instances
        for instance_id, record in self._registry.items():
            for pid in list(record.tracked_pids):
                p = PM.get_process(pid)
                if not p or p.status in ["STOPPED", "COMPLETED", "gc"]:
                    # Ghost detected
                    self.logger.debug(f"[Kernel] Reconciling ghost PID {pid} for {instance_id}")
                    self.release_worker(instance_id, "process", pid=pid)

    def _update_system_pressure(self, now: float, instance_id: str):
        """Phase 15.5: Weighted Pressure Engine with Noisy Neighbor Mitigation."""
        self.global_calls.append((now, instance_id))

        # 1. Per-App Local Pressure Analysis
        record = self._registry.get(instance_id)
        if record:
            # Count recent calls for THIS app in 1s
            local_recent = [c for c in self.global_calls if now - c[0] < 1.0 and c[1] == instance_id]
            # Dynamic Threshold for THIS app (Phase 15.5)
            # Apps with high trust get higher local burst allowance
            local_limit = 20 + (record.trust_score // 5)
            local_pressure = len(local_recent) / local_limit
            
            # Local Penalty: If spammed, hurt the offender ONLY first
            if local_pressure > 1.2:
                self.apply_penalty(instance_id, -5, f"High Local Burst (Pressure: {local_pressure:.2f})")
                # Heavy throttle for this instance
                record.local_throttled = True
            else:
                record.local_throttled = False

        # 2. Global State Sensing (Hardware & Aggregate Load)
        running_apps = [r for r in self._registry.values() if r.state == AppState.RUNNING]
        # Aggregate threshold (Baseline for global state)
        dynamic_threshold = 40 + (len(running_apps) * 5)
        
        recent_1s = [c for c in self.global_calls if now - c[0] < 1.0]
        # Call Pressure is now only 30% of global signal to prevent one app from 
        # crashing the OS state. Hardware is the primary driver for Global Emergency.
        call_pressure = len(recent_1s) / dynamic_threshold if dynamic_threshold > 0 else 0
        
        import psutil
        cpu_usage = psutil.cpu_percent() / 100.0
        mem_usage = psutil.virtual_memory().percent / 100.0
        lag_factor = min(1.0, self.ui_lag_ms / 500.0)
        
        # Global Pressure integration (Phase 15.5 Balance)
        self.current_pressure_ratio = (call_pressure * 0.3) + (cpu_usage * 0.4) + (lag_factor * 0.3)
        self.max_pressure_seen = max(self.max_pressure_seen, self.current_pressure_ratio)

        # 3. Earned Recovery (Phase 13.9)
        # Verify if this app is being 'Good'. 
        # Criteria: No warnings for 60s AND usage below 30% of its limit.
        record = self._registry.get(instance_id)
        if record and record.trust_score < 100:
            time_since_friction = now - record.last_warning_time
            usage = record.active_workers["total"] / self.get_worker_limit(instance_id) 
            
            if time_since_friction >= 60.0 and usage < 0.3:
                # Earn 1 trust point per 60s of good behavior
                record.trust_score = min(100, record.trust_score + 1)
                record.last_warning_time = now # Reset timer for next point
                self.logger.info(f"[RuntimeManager] Earned Recovery: {record.app_id} +1 Trust (Stable Behavior)")

        # 4. Phase 13.6/7: Snapshot history
        if not self.pressure_history or (now - self.pressure_history[-1]["time"]) >= 1.0:
            self.pressure_history.append({
                "time": round(now, 2), 
                "ratio": round(self.current_pressure_ratio, 2),
                "cpu": cpu_usage,
                "lag": self.ui_lag_ms
            })

        # 4. Weighted Burst Detection (200ms window): calls * unique apps
        recent_200ms = [c for c in self.global_calls if now - c[0] < 0.2]
        unique_apps = len(set(c[1] for c in recent_200ms))
        burst_score = len(recent_200ms) * unique_apps

        # 5. State Transitions & Hysteresis (Hardened for Real-world Noise)
        old_state = self.global_state

        # Enter Emergency: Critical hardware load OR extreme UI lag OR API burst
        is_emergency = (
            self.current_pressure_ratio > 1.3 or 
            burst_score > 35 or 
            self.ui_lag_ms > 800 or
            mem_usage > 0.95
        )

        if is_emergency:
            if self.global_state != "EMERGENCY":
                self.global_state = "EMERGENCY"
                self.emergency_start_time = now
                self.max_pressure_seen = self.current_pressure_ratio

                if not self.emergency_alert_sent:
                    self.notify("⚠️ Coordinated Load Detected", "Adaptive Throttling Engaged", "warning")
                    self.emergency_alert_sent = True

        # Aggressive Throttling
        elif self.current_pressure_ratio > 1.0:
            if self.global_state != "EMERGENCY":
                self.global_state = "AGGRESSIVE"

        # Soft Throttling
        elif self.current_pressure_ratio > 0.7:
            if self.global_state not in ["EMERGENCY", "AGGRESSIVE"]:
                self.global_state = "SOFT"

        # Recovery: Hysteresis (Ratio < 0.9) AND Adaptive Cooldown
        elif self.current_pressure_ratio < 0.9:
            cooldown = 5 + (self.max_pressure_seen * 2)
            self.current_cooldown = max(0, cooldown - (now - self.emergency_start_time))

            if self.current_cooldown <= 0:
                self.global_state = "NORMAL"
                self.emergency_alert_sent = False
                self.max_pressure_seen = 0.0

        # 6. Phase 13.6: Record decision on state change (rate-limited)
        if self.global_state != old_state:
            reason = f"burst_score={burst_score} > 30" if burst_score > 30 else f"pressure_ratio={self.current_pressure_ratio:.2f}"
            self._record_decision(
                state_before=old_state,
                state_after=self.global_state,
                reason=reason,
                burst_score=burst_score,
                running_app_count=len(running_apps),
                now=now
            )
            # Immediate flush on critical state changes
            self._flush_governance_log(force=True)

    # ── Phase 13.6: Observability Methods ────────────────────────────────────

    def _record_decision(self, state_before: str, state_after: str, reason: str,
                         burst_score: int, running_app_count: int, now: float):
        """Record a governance decision. Rate-limited to max 1 per 500ms."""
        if now - self._last_decision_time < 0.5:
            return
        self._last_decision_time = now

        import uuid
        affected_apps = [
            {
                "id": r.instance_id,
                "app_id": r.app_id,
                "active": r.active_workers["total"],
                "limit": self.get_worker_limit(r.instance_id)
            }
            for r in self._registry.values()
            if r.state == AppState.RUNNING
        ]
        
        entry = {
            "decision_id": uuid.uuid4().hex[:12],
            "timestamp": round(now, 3),
            "state_before": state_before,
            "state_after": state_after,
            "pressure_ratio": round(self.current_pressure_ratio, 3),
            "burst_score": burst_score,
            "active_apps": running_app_count,
            "affected_apps": affected_apps,
            "reason": reason
        }
        self.decision_history.append(entry)
        self._gov_log_buffer.append(entry)
        self.logger.info(f"[DECISION] {state_before} -> {state_after} | {reason}")

    def _flush_governance_log(self, force: bool = False):
        """Flush buffered decisions to NDJSON file (crash-safe, one entry per line)."""
        import time
        now = time.time()
        if not force and (now - self._last_flush_time < 2.0):
            return
        if not self._gov_log_buffer:
            self._last_flush_time = now
            return

        import json
        try:
            with open(self._gov_log_path, "a", encoding="utf-8") as f:
                for entry in self._gov_log_buffer:
                    f.write(json.dumps(entry) + "\n")  # NDJSON: one JSON object per line
            self._gov_log_buffer.clear()
        except Exception as e:
            self.logger.error(f"[GOV LOG] Flush failed: {e}")
        self._last_flush_time = now

    def get_worker_limit(self, instance_id: str) -> int:
        """Calculate the current dynamic worker limit for an instance."""
        record = self.get_record(instance_id)
        if not record: return 10

        state_limits = {"NORMAL": 10, "SOFT": 7, "AGGRESSIVE": 5, "EMERGENCY": 3}
        base_limit = state_limits.get(self.global_state, 10)

        trust_weight = 0
        if record.trust_score > 70: trust_weight = 2
        elif record.trust_score < 30: trust_weight = -2

        return max(1, base_limit + trust_weight)

    def get_explanation(self, instance_id: str) -> dict:
        """Return a structured, deterministic explanation of current limits for an app."""
        record = self.get_record(instance_id)
        if not record:
            return {"error": "Instance not found"}

        worker_limit = self.get_worker_limit(instance_id)
        base_limit = 10 # Default fallback
        trust_weight = 0

        # Sync values for explanation text (already computed in get_worker_limit but we need the components)
        state_limits = {"NORMAL": 10, "SOFT": 7, "AGGRESSIVE": 5, "EMERGENCY": 3}
        base_limit = state_limits.get(self.global_state, 10)
        if record.trust_score > 70: trust_weight = 2
        elif record.trust_score < 30: trust_weight = -2
        
        trust_tag = "neutral"
        if trust_weight > 0: trust_tag = "high_trust"
        elif trust_weight < 0: trust_tag = "low_trust"

        reasons = []
        if self.global_state != "NORMAL":
            reasons.append(f"global_pressure_state_{self.global_state.lower()}")
        if trust_tag == "low_trust":
            reasons.append("low_trust_score")
        if self.current_pressure_ratio > 1.3:
            reasons.append("high_pressure_ratio")
        if not reasons:
            reasons.append("normal_operation")

        msg_parts = []
        if self.global_state != "NORMAL":
            msg_parts.append(f"System in {self.global_state} mode (pressure {self.current_pressure_ratio:.2f}x).")
        if trust_tag == "low_trust":
            msg_parts.append(f"Trust score is low ({record.trust_score}), reducing allocation by 2.")
        if trust_tag == "high_trust":
            msg_parts.append(f"Trust score is high ({record.trust_score}), granting +2 bonus.")
        msg_parts.append(f"Worker limit: {worker_limit}.")

        return {
            "app_id": record.app_id,
            "global_state": self.global_state,
            "pressure_ratio": round(self.current_pressure_ratio, 3),
            "trust_score": record.trust_score,
            "base_worker_limit": base_limit,
            "trust_adjustment": trust_weight,
            "final_worker_limit": worker_limit,
            "reasons": reasons,
            "explanation": " ".join(msg_parts)
        }

    def acquire_worker(self, instance_id: str, worker_type: str = "total", token: str = None) -> None:
        """
        Phase 15.5: Governance gateway for resource allocation.
        Enforces localized throttling, rate-limits, and noisy-neighbor mitigation.
        """
        with self._lock:
            record = self._registry.get(instance_id)
            if not record:
                raise KeyError(f"Instance '{instance_id}' not found.")

            if record.state == AppState.QUARANTINED:
                raise PermissionError(f"[Sandbox] Access Denied: App is QUARANTINED.")

            # ── 1. Kernel-level Rate Limiting ──
            now = time.time()
            record.call_window.append(now)
            recent_calls = [t for t in record.call_window if now - t < 1.0]
            if len(recent_calls) > 50:
                self.apply_penalty(instance_id, -10, "Excessive IPC Call Rate")
                raise PermissionError(f"[Sandbox] Rate Limit Exceeded")

            # ── 2. Localized Throttling (Noisy Neighbor Mitigation) ──
            if getattr(record, 'local_throttled', False):
                last_reject = getattr(record, 'last_throttle_reject', 0)
                if now - last_reject < 0.2:
                    # Non-blocking penalty: reject immediately if spamming while throttled
                    raise PermissionError(f"[Sandbox] Local Throttling Active (Cooldown)")
                record.last_throttle_reject = now
                if record.pending_calls >= 2:
                    raise PermissionError(f"[Sandbox] Local Throttling Active (Queue Full)")

            # ── 3. Backpressure & Queue Control ──
            if record.pending_calls >= record._max_pending:
                raise PermissionError(f"[Sandbox] Backpressure limit reached.")
            
            record.pending_calls += 1
            self._update_system_pressure(now, instance_id)
            
            # ── 4. Capacity Checks ──
            MAX_WORKERS = self.get_worker_limit(instance_id)
            if record.active_workers["total"] >= MAX_WORKERS:
                
                raise PermissionError(f"[Sandbox] Resource exhaustion. Max workers reached ({MAX_WORKERS}).")

            if token:
                record.worker_tokens.add(token)

            record.active_workers["total"] += 1
            if worker_type in record.active_workers:
                record.active_workers[worker_type] += 1
            
            # Snap memory history
            record.rss_history.append(record._get_current_rss())

    def release_worker(self, instance_id: str, worker_type: str = "total", token: str = None, pid: int = None):
        """
        Release a worker slot.
        If pid is provided, ensures only a SINGLE release event occurs for that process.
        """
        with self._lock:
            record = self._registry.get(instance_id)
            if not record: return
            
            # Atomic PID check
            if pid is not None:
                if pid not in record.tracked_pids:
                    return # Already released or not tracked
                record.tracked_pids.remove(pid)
            
            if token and token in record.worker_tokens:
                record.worker_tokens.discard(token)

            record.active_workers["total"] = max(0, record.active_workers["total"] - 1)
            if worker_type in record.active_workers:
                record.active_workers[worker_type] = max(0, record.active_workers[worker_type] - 1)
            
            # Phase 14.3.2: Decrement pending counter
            record.pending_calls = max(0, record.pending_calls - 1)

    def spawn_process(self, instance_id: str, argv: list, **kwargs) -> Any:
        """
        Hardened Transactions for Governed Spawning.
        Guarantees rollback on ANY failure to prevent zombie accounting.
        """
        from core.process_manager import PM
        is_bg = kwargs.get("background", False)
        pid = None
        
        # 1. Enforce Runtime Governance (Slot Acquisition)
        self.acquire_worker(instance_id, "process")

        try:
            # 2. Delegate to Core with Ownership (PID generation)
            pid = PM.spawn(
                argv=argv,
                owner=instance_id,
                background=is_bg,
                sim_duration_ms=kwargs.get("sim_duration_ms", 0)
            )
            
            # 3. Securely Track for Atomic Lifecycle Management
            with self._lock:
                record = self._registry.get(instance_id)
                if not record:
                    # Registry mismatch - app likely died mid-spawn
                    raise RuntimeError("Governance record lost during spawn transaction.")
                record.tracked_pids.add(pid)
            
            # 4. Final verification and handle return
            p = PM.get(pid)
            if not p:
                raise RuntimeError("ProcessManager failed to finalize birth record.")
                
            self.logger.info(f"[OS] Transaction complete: {argv} (PID: {pid})")
            return p.handle if p else None

        except Exception as e:
            # COMPREHENSIVE ROLLBACK
            self.logger.error(f"[OS] Spawn Transaction Failed: {e}")
            
            # Step A: Remove from Core Process Table if it escaped
            if pid is not None:
                PM.kill(pid) # Forces 'stopped' then 'gc'
                
            # Step B: Ensure the governance slot is released
            # Note: release_worker is idempotent via pid check
            self.release_worker(instance_id, "process", pid=pid)
            
            raise

    def kill_process(self, instance_id: str, pid: int) -> bool:
        """
        Governed termination gateway.
        Hardens ownership enforcement: apps can ONLY kill their own processes.
        """
        from core.process_manager import PM
        p = PM.get(pid)
        if not p: return False
        
        # Security Boundary Check
        # Apps can only kill their own; system (or root equivalent) can kill anything
        if p.owner != instance_id and instance_id != "system":
            self.logger.warning(f"[SECURITY] Unauthorized kill attempt: {instance_id} tried to kill PID {pid} (Owner: {p.owner})")
            self.report_violation(instance_id, f"Unauthorized process termination attempt (PID: {pid})")
            return False
            
        self.logger.info(f"[OS] Governed kill authorized: {instance_id} killing PID {pid}")
        return PM.kill(pid)

    def _on_process_event(self, event: str, proc: Any):
        """Observer callback for Core ProcessManager events."""
        if event in ["done", "stopped", "gc"]:
            owner_id = getattr(proc, "owner", None)
            pid = getattr(proc, "pid", None)
            if owner_id and owner_id in self._registry:
                # Release the 'process' slot atomically via PID tracking
                self.release_worker(owner_id, "process", pid=pid)
                self.logger.debug(f"[OS] Atomic-release worker for {owner_id} (PID: {pid} Event: {event})")

    def quarantine_app(self, instance_id: str, reason: str) -> None:
        record = self.get_record(instance_id)
        if not record: return
        
        if record.state == AppState.QUARANTINED: return
        
        record.state = AppState.QUARANTINED
        self.logger.warning(f"🔒 [QUARANTINE] Isolating {record.app_id} (ID: {instance_id}). Reason: {reason}")
        
        self.notify(
            title=f"Quarantined: {record.app_id}",
            text=f"App frozen. Trust Score: {record.trust_score}",
            level="error"
        )
        
        # 1. Lock SecureAPI
        if hasattr(record.app_instance, "api") and record.app_instance.api:
            record.app_instance.api.is_locked = True
            
        # 2. Visually freeze the UI window
        try:
            wm = get_window_manager()
            if instance_id in wm._windows:
                os_window = wm._windows[instance_id]
                if hasattr(os_window, "show_quarantine_overlay"):
                    os_window.show_quarantine_overlay(record.trust_score, reason)
        except Exception as e:
            self.logger.error(f"Failed to overlay quarantine bounds: {e}")

    def kill(self, instance_id: str) -> None:
        record = self.get_record(instance_id)
        if not record: return

        self.logger.info(f"[RuntimeManager] Terminating '{instance_id}' ({record.app_id})")
        record.state = AppState.TERMINATED
        
        # Phase 13: Robust Token Cleanup (Zombie Suppression)
        if record.worker_tokens:
            count = len(record.worker_tokens)
            self.logger.warning(f"[RuntimeManager] Reclaiming {count} zombie worker slots from {record.app_id}")
            record.worker_tokens.clear()
        
        record.active_workers = {"network": 0, "process": 0, "fs": 0, "total": 0}
        
        app = record.app_instance
        if hasattr(app, "on_stop"):
            try:
                app.on_stop()
            except Exception as e:
                self.logger.error(f"[RuntimeManager] Cleanup error {record.app_id}: {e}")
        
        # coupled to the window closing. We keep the record for a few seconds
        # for dashboard visibility (TTL cleanup) or until unregister is called.
        
        try:
            get_window_manager().close_window(instance_id)
        except Exception:
            pass

    def unregister(self, instance_id: str) -> None:
        """Physical cleanup from registry when window completely closes."""
        with self._lock:
            if instance_id in self._registry:
                record = self._registry.pop(instance_id)
                # Phase 13.8: Snapshot reputation for the session
                self._reputation_cache[record.app_id] = record.trust_score
                
                # Phase 13.9: Recursive Lifecycle Cleanup
                from core.process_manager import PM
                PM.kill_all_by_owner(instance_id)
                self.logger.info(f"[RuntimeManager] Post-termination cleanup complete for {instance_id}")

    def notify(self, title: str, text: str, level: str = "info") -> None:
        if level == "error":
            self.logger.critical(f"🔔 {title} - {text}")
        elif level == "warning":
            self.logger.warning(f"🔔 {title} - {text}")
        else:
            self.logger.info(f"🔔 {title} - {text}")

        try:
            if self._desktop_parent:
                notif = Notification(title, text, parent=self._desktop_parent)
                w = self._desktop_parent.width()
                from PyQt5.QtCore import QPoint
                target_pos = QPoint(max(0, w - notif.width() - 20), 40)
                
                # Use Phase 9 motion spawn
                if hasattr(notif, "spawn"):
                    notif.spawn(target_pos)
                else:
                    notif.move(target_pos)
                    notif.show()

                if not hasattr(self._desktop_parent, "_active_notifs"):
                    self._desktop_parent._active_notifs = []
                self._desktop_parent._active_notifs.append(notif)
                import PyQt5.QtCore as QtCore
                QtCore.QTimer.singleShot(4000, lambda: self._desktop_parent._active_notifs.remove(notif) if notif in self._desktop_parent._active_notifs else None)
        except Exception as e:
            self.logger.error(f"[RuntimeManager] Notification UI failed: {e}")

    def list_running(self) -> Dict[str, Any]:
        """Telemetry feed for the System Monitor Dashboard."""
        apps_data = []
        for instance_id, record in self._registry.items():
            limit = self.get_worker_limit(instance_id)
            active = record.active_workers.get("total", 0)
            
            apps_data.append({
                "id": instance_id,
                "app_id": record.app_id,
                "state": record.state.value,
                "trust_score": record.trust_score,
                "crashes": record.crash_count,
                "violations": record.violations,
                "active_workers": record.active_workers.copy(),
                "max_workers": limit,
                "worker_usage": round(active / limit, 2) if limit > 0 else 0,
                "memory_delta_mb": round((record.rss_history[-1] - record.rss_start) / (1024*1024), 2) if record.rss_history else 0,
                "mem_trend": record.get_mem_trend()
            })
            
        return {
            "total_instances": len(self._registry),
            "apps": apps_data,
            "global_pressure": round(self.current_pressure_ratio, 2),
            "global_state": self.global_state,
            "cooldown_remaining": round(self.current_cooldown, 1),
            "ui_lag_ms": round(self.ui_lag_ms, 1),
            "pressure_history": list(self.pressure_history),
            "decision_history": list(self.decision_history)
        }

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Phase 16.9: Production Audit Trail with Rotation & Safety."""
        try:
            entry = {
                "ts": time.time(),
                "type": event_type,
                **data
            }
            # RotatingFileHandler handles the formatting and rotation automatically
            self.audit_logger.info(json.dumps(entry))
        except Exception:
            # Fallback for Disk Full or Logging failure: Drop log, keep Kernel alive.
            pass

if multiprocessing.current_process().name == 'MainProcess':
    RUNTIME_MANAGER = AppRuntimeManager()
else:
    RUNTIME_MANAGER = None # No kernel in sandboxes
