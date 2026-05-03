import logging
import time
import weakref
import threading
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


# ── Event Taxonomy ───────────────────────────────────────────────

class SystemEvent(Enum):
    # App Lifecycle
    APP_LAUNCHED = "sys.app_launched"
    APP_CRASHED = "sys.app_crashed"
    
    # Process Lifecycle
    PROC_SPAWNED = "sys.proc_spawned"
    PROC_COMPLETED = "sys.proc_completed"
    PROC_STOPPED = "sys.proc_stopped"
    PROC_GC = "sys.proc_gc"
    
    # Filesystem Lifecycle
    FS_CHANGED = "sys.fs_changed"
    
    # System State
    STATE_CHANGED = "sys.state_changed"
    
    # Window Lifecycle (Facts — emitted by WindowManager)
    WINDOW_OPENED = "window.opened"
    WINDOW_CLOSED = "window.closed"
    WINDOW_FOCUSED = "window.focused"
    WINDOW_MINIMIZED = "window.minimized"
    WINDOW_RESTORED = "window.restored"
    WORKSPACE_CHANGED = "window.workspace_changed"  # emit-only (window_manager) — no subscriber yet
    
    # Window Actions (Requests / Commands — emitted by UI)
    REQ_WINDOW_FOCUS = "ui.window.request_focus"
    REQ_WINDOW_MINIMIZE = "ui.window.request_minimize"
    REQ_WINDOW_CLOSE = "ui.window.request_close"
    REQ_APP_LAUNCH = "ui.app.request_launch"
    
    # Window Physics & Drag (Phase 2)
    REQ_WINDOW_DRAG_START = "ui.window.drag_start"
    REQ_WINDOW_DRAG_UPDATE = "ui.window.drag_update"
    REQ_WINDOW_DRAG_END = "ui.window.drag_end"
    EVT_WINDOW_SNAPPED = "window.snapped"
    
    # User / Auth
    USER_IDLE = "auth.user_idle"
    SESSION_LOCKED = "auth.session_locked"
    SESSION_UNLOCKED = "auth.session_unlocked"
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"
    
    # Shell / Feed
    NOTIFICATION_SENT = "ui.notification_sent"
    ACTION_CLICKED = "ui.action_clicked"
    COMMAND_EXECUTED = "sys.command_executed"
    
    # Security / Health / Hardware Token
    SECURITY_ALERT = "sec.alert"
    EVENT_USB_DEVICE_CONNECTED = "hardware.usb_connected"
    EVENT_USB_DEVICE_DISCONNECTED = "hardware.usb_disconnected"
    EVENT_QVAULT_STARTED = "qvault.started"
    EVENT_QVAULT_STOPPED = "qvault.stopped"
    EVENT_QVAULT_CONNECTED = "qvault.connected"
    EVENT_QVAULT_DISCONNECTED = "qvault.disconnected"
    EVENT_QVAULT_LOCKED = "qvault.locked"
    EVENT_QVAULT_UNLOCKED = "qvault.unlocked"
    EVENT_QVAULT_ERROR = "qvault.error"
    
    # Intelligence Lifecycle
    UNDO_REQUESTED = "ai.undo_requested"
    UNDO_FAILED = "ai.undo_failed"
    UNDO_PERFORMED = "ai.undo_performed"
    SETTING_CHANGED = "sys.setting_changed"
    
    # Orchestration Layer
    PLAN_STARTED = "orch.plan_started"
    PLAN_STEP_COMPLETED = "orch.plan_step_completed"
    PLAN_COMPLETED = "orch.plan_completed"
    PLAN_FAILED = "orch.plan_failed"
    PLAN_ABORTED = "orch.plan_aborted"
    PLAN_STATS_UPDATED = "orch.plan_stats_updated"
    
    # AI Governance Pipeline (Phase 4.1)
    DECISION_MADE = "gov.decision_made"
    ACTION_TAKEN = "gov.action_taken"
    
    # Marketplace & Ecosystem (Phase 9)
    EVT_PLUGIN_INSTALLED = "mkt.plugin_installed"
    EVT_PLUGIN_ACTIVATED = "mkt.plugin_activated"
    EVT_PLUGIN_ERROR = "mkt.plugin_error"
    REQ_MARKETPLACE_TOGGLE = "ui.marketplace.toggle"
    
    # AI & Intelligence (Phase 4-8)
    REQ_USER_INPUT = "ui.user_input"
    EVT_AI_DECISION = "ai.decision"
    EVT_AI_REJECTED_ACTION = "ai.rejected"
    EVT_AI_THINKING_START = "ai.thinking_start"
    EVT_AI_THINKING_STOP = "ai.thinking_stop"
    EVT_AI_UNKNOWN_INTENT = "ai.unknown_intent"

    # Automation & Workflows (Phase 7)
    REQ_WORKFLOW_EXECUTE = "sys.workflow.execute"
    REQ_WORKFLOW_LIST = "sys.workflow.list"
    EVT_WORKFLOW_LIST = "sys.workflow.list_ready"
    EVT_WORKFLOW_STARTED = "sys.workflow.started"
    EVT_WORKFLOW_STEP = "sys.workflow.step"
    EVT_WORKFLOW_COMPLETED = "sys.workflow.completed"

    # Missing SDK bindings
    APP_TERMINATED = "sys.app_terminated"
    REQ_SYSTEM_CONTROL = "sys.control"

    # Debug & Observability (Phase 3)
    DEBUG_EVENT_EMITTED = "dbg.event_emitted"
    DEBUG_METRICS_UPDATED = "dbg.metrics_updated"
    REQ_DEBUG_TOGGLE = "ui.debug.toggle"
    
    # System Control & Health (Phase 3.5)
    EVT_ERROR = "sys.error"
    EVT_WARNING = "sys.warning"
    REQ_SYSTEM_RESTART = "sys.request_restart"
    REQ_PROCESS_KILL = "sys.request_kill"
    REQ_COMMAND_PALETTE_TOGGLE = "ui.command_palette.toggle"
    REQ_SETTINGS_TOGGLE = "ui.settings.toggle"
    REQ_AI_INSPECTOR_TOGGLE = "ui.ai_inspector.toggle"
    
    # ── Final Polishing Bindings (Phase 24.5) ──
    REQ_TERMINAL_OPEN_HERE = "ui.open_terminal_here"
    EVT_TRASH_STATE_CHANGED = "ui.trash_state_changed"
    EVT_WELCOME = "sys.welcome"

    # ── Kernel Simulation (kernel/*) ──
    CLOCK_TICK    = "kernel.clock_tick"
    CLOCK_PAUSED  = "kernel.clock_paused"
    CLOCK_RESUMED = "kernel.clock_resumed"
    PROC_SCHEDULED       = "kernel.proc_scheduled"
    PROC_PREEMPTED       = "kernel.proc_preempted"
    PROC_QUANTUM_EXPIRED = "kernel.proc_quantum_expired"
    PROC_CONTEXT_SWITCHED = "kernel.proc_context_switched"
    MEMORY_ALLOCATED = "kernel.memory_allocated"
    MEMORY_FREED     = "kernel.memory_freed"
    MEMORY_FULL      = "kernel.memory_full"
    INTERRUPT_RAISED  = "kernel.interrupt_raised"
    INTERRUPT_HANDLED = "kernel.interrupt_handled"
    DEADLOCK_DETECTED = "kernel.deadlock_detected"
    DEADLOCK_RESOLVED = "kernel.deadlock_resolved"
    CORE_ASSIGNED     = "kernel.core_assigned"
    PROCESS_MIGRATED  = "kernel.process_migrated"
    SCHEDULER_ALGORITHM_CHANGED = "kernel.scheduler_algo_changed"
    STARVATION_DETECTED         = "kernel.starvation_detected"
    AGING_APPLIED               = "kernel.aging_applied"


# ── Payload ──────────────────────────────────────────────────────

@dataclass
class EventPayload:
    type: SystemEvent
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"


# ── Subscriber Wrapper ───────────────────────────────────────────

class _Subscriber:
    """
    Wraps a callback with identity tracking for safe comparison.

    - Bound methods  -> stored as WeakMethod (dies with the object).
    - Plain functions -> stored as strong reference (lives forever).
    - Identity key    -> (id(obj), func_name) for methods, id(func) for functions.
                        Used for reliable unsubscribe comparisons.
    """
    __slots__ = ("_ref", "_identity", "_is_weak")

    def __init__(self, callback: Callable):
        if hasattr(callback, "__self__") and callback.__self__ is not None:
            # Bound method -> weak reference
            self._ref = weakref.WeakMethod(callback)
            self._identity: Tuple = (id(callback.__self__), callback.__func__.__name__)
            self._is_weak = True
        else:
            # Plain function / static -> strong reference
            self._ref = callback
            self._identity = id(callback)
            self._is_weak = False

    def __call__(self) -> Optional[Callable]:
        """Resolve the reference. Returns None if the weak target is dead."""
        if self._is_weak:
            return self._ref()      # WeakMethod.__call__
        return self._ref            # strong ref, always alive

    @property
    def is_alive(self) -> bool:
        return self() is not None

    @property
    def identity(self):
        return self._identity

    @property
    def owner_id(self) -> Optional[int]:
        """Returns id() of the owning object for bound methods, None otherwise."""
        if self._is_weak:
            cb = self._ref()
            if cb is not None:
                return id(cb.__self__)
        return None

    def matches_callback(self, callback: Callable) -> bool:
        """Reliable comparison that works for both methods and functions."""
        if hasattr(callback, "__self__") and callback.__self__ is not None:
            return self._identity == (id(callback.__self__), callback.__func__.__name__)
        return self._identity == id(callback)

    def owned_by(self, obj: Any) -> bool:
        """Check if this subscriber belongs to a specific object."""
        if not self._is_weak:
            return False
        cb = self._ref()
        if cb is None:
            return False
        return cb.__self__ is obj


# ── EventBus v2.0 ───────────────────────────────────────────────

_CLEANUP_INTERVAL = 25  # Run global dead-ref sweep every N emits


class EventBus(QObject):
    """
    v2.0 Hardened Telemetry Backbone.

    Production guarantees:
      - WeakMethod for bound methods -> no memory leaks from dead UI.
      - Strong refs for plain functions -> stable system services.
      - RLock -> safe if a callback subscribes/unsubscribes during emit.
      - Safe iteration -> snapshot-based, never mutates during loop.
      - Lazy global cleanup -> dead refs swept every N emits.
    """
    event_emitted = pyqtSignal(object)  # Emits EventPayload

    MAX_QUEUE_SIZE = 1000  # History overflow protection

    def __init__(self):
        super().__init__()
        self._history: List[EventPayload] = []
        self._subscribers: Dict[SystemEvent, List[_Subscriber]] = {}
        self._lock = threading.RLock()
        # Dedup cache for high-frequency drag events: (event_type, window_id) -> index
        self._drag_dedup: Dict[tuple, int] = {}

        # Observability & Debug (Phase 3)
        self._debug_enabled = os.environ.get("QVAULT_ENV", "").lower() != "production"
        self._emit_count: int = 0
        self._error_count: int = 0
        self._slow_threshold_ms = 50.0  # Raised from 10ms — animation handlers need headroom
        self._last_emit_time: Dict[str, float] = {}  # For rate limiting high-freq events

    # ── Core API ─────────────────────────────────────────────────

    def enable_debug(self, enabled: bool):
        self._debug_enabled = enabled
        logger.info(f"[EVENT_BUS] Debug Mode: {'ENABLED' if enabled else 'DISABLED'}")

    def _normalize_event(self, event_type: Any) -> Any:
        """Converts string event names to SystemEvent members if possible."""
        if isinstance(event_type, str):
            for member in SystemEvent:
                if member.value == event_type:
                    return member
            logger.warning(f"[EVENT_BUS] Using raw string event: {event_type}. Use SystemEvent enum.")
        return event_type

    def _validate_payload(self, event_type: Any, data: Dict[str, Any]) -> bool:
        """Enforces schema rules for critical REQ_* events."""
        event_name = getattr(event_type, 'value', str(event_type))
        if not event_name.startswith("ui.") and not event_name.startswith("sys.request"):
            return True # Facts don't need strict validation here
            
        # Standardized Q-Vault v2.2 Schema Rules
        if "request_launch" in event_name and "name" not in data:
            return False
        if "drag_update" in event_name and ("x" not in data or "y" not in data):
            return False
            
        return True

    # Rate limiting config: event_type_value -> min_interval_seconds
    _RATE_LIMITED_EVENTS = {
        "ui.window.drag_update":  0.016,   # ~60fps max
        "kernel.clock_tick":      0.050,   # max 20Hz from bus perspective
    }

    def emit(self, event_type: Any, data: Dict[str, Any] = None, source: str = "unknown"):
        # ── Rate limiting for high-frequency events ──────────────
        event_key = getattr(event_type, 'value', str(event_type))
        min_interval = self._RATE_LIMITED_EVENTS.get(event_key)
        if min_interval is not None:
            now = time.perf_counter()
            last = self._last_emit_time.get(event_key, 0.0)
            if now - last < min_interval:
                return   # drop — too frequent
            self._last_emit_time[event_key] = now

        # ── 0. Normalize & Validate ─────────────────────────────
        event_type = self._normalize_event(event_type)
        data = data or {}
        
        if not self._validate_payload(event_type, data):
            err_msg = f"Validation failed for {event_type} from {source}: Missing metadata."
            logger.error(f"[EVENT_BUS] {err_msg}")
            # Emit error but don't stop (Fail-safe with notification)
            self.emit(SystemEvent.EVT_ERROR, {"type": "validation_failure", "msg": err_msg}, source="EventBus_Validator")
            return

        payload = EventPayload(
            type=event_type,
            timestamp=time.time(),
            data=data or {},
            source=source
        )

        # ── 1. Thread-safe state update ──────────────────────────
        with self._lock:
            # Queue overflow protection: drop oldest if over limit
            if len(self._history) > self.MAX_QUEUE_SIZE:
                self._history = self._history[-900:]  # Keep last 900

            # Deduplication for high-frequency drag_update events
            event_name_check = getattr(event_type, 'value', str(event_type))
            if "drag_update" in event_name_check:
                win_id = data.get("id", "")
                dedup_key = (event_type, win_id)
                existing_idx = self._drag_dedup.get(dedup_key)
                if existing_idx is not None and existing_idx < len(self._history):
                    # Replace the existing payload with the newer one
                    self._history[existing_idx] = payload
                else:
                    self._history.append(payload)
                    self._drag_dedup[dedup_key] = len(self._history) - 1
            else:
                self._history.append(payload)

            self._emit_count += 1

            # Snapshot for safe iteration
            subs_list = self._subscribers.get(event_type, [])
            snapshot = list(subs_list)
            sub_count = len(subs_list)

        # ── 2. Log & Debug Fact ──────────────────────────────────
        event_name = getattr(event_type, 'value', str(event_type))
        logger.debug(f"[EVENT_BUS] {event_name} from {source}: {data}")
        
        is_debug_event = event_name.startswith("dbg.")
        is_high_freq = "drag_update" in event_name
        
        if self._debug_enabled and not is_debug_event and not is_high_freq:
            # Emit a fact ABOUT the emission (Metadata)
            # We use a separate thread or just careful timing to avoid recursion
            # Actually, we can just call emit recursively but it will be caught 
            # by 'is_debug_event' check above.
            self.emit(SystemEvent.DEBUG_EVENT_EMITTED, {
                "event": event_name,
                "source": source,
                "subscribers": sub_count,
                "payload_size": len(str(data))
            }, source="EventBus_Monitor")

        # ── 3. Notify subscribers (outside lock -> prevents deadlock) ─
        dead_refs: List[_Subscriber] = []
        is_debug_event = str(event_type.value if hasattr(event_type, 'value') else event_type).startswith("dbg.")

        for sub in snapshot:
            callback = sub()
            if callback is not None:
                try:
                    start_time = time.perf_counter()
                    callback(payload)
                    duration = (time.perf_counter() - start_time) * 1000 # ms
                    
                    if self._debug_enabled and not is_debug_event:
                        if duration > self._slow_threshold_ms:
                            logger.warning(f"[EVENT_BUS] Slow handler for {event_name}: {duration:.2f}ms")
                            self.emit(SystemEvent.EVT_WARNING, {
                                "type": "slow_handler",
                                "event": event_name,
                                "duration_ms": round(duration, 2),
                                "callback": str(callback)
                            }, source="EventBus_Guardian")
                        
                        # Emit metadata about the call if debugging
                        # Note: We do this sparingly to avoid overhead
                except Exception as e:
                    self._error_count += 1
                    event_name = getattr(event_type, 'value', str(event_type))
                    logger.error(f"[EVENT_BUS] Error in handler for {event_name}: {e}", exc_info=True)
                    
                    if not is_debug_event:
                        self.emit(SystemEvent.EVT_ERROR, {
                            "type": "handler_exception",
                            "event": event_name,
                            "error": str(e)
                        }, source="EventBus_Guardian")
            else:
                dead_refs.append(sub)

        # ── 4. Cleanup dead refs from this event type ────────────
        if dead_refs:
            with self._lock:
                subs = self._subscribers.get(event_type)
                if subs:
                    self._subscribers[event_type] = [s for s in subs if s not in dead_refs]

        # ── 5. Periodic global sweep ─────────────────────────────
        if self._emit_count % _CLEANUP_INTERVAL == 0:
            self._sweep_dead()

        # ── 6. Qt signal for UI listeners (DebugOverlay etc.) ────
        try:
            self.event_emitted.emit(payload)
        except RuntimeError:
            # This happens during shutdown if background threads emit while
            # the QApplication (and thus EVENT_BUS QObject) is being deleted.
            pass

    def subscribe(self, event_type: Any, callback: Callable):
        """Register a callback for an event type. Thread-safe."""
        event_type = self._normalize_event(event_type)
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(_Subscriber(callback))

    def unsubscribe(self, event_type: Any, callback: Callable):
        """Remove a specific callback from an event type. Thread-safe."""
        event_type = self._normalize_event(event_type)
        with self._lock:
            subs = self._subscribers.get(event_type)
            if not subs:
                return
            self._subscribers[event_type] = [
                s for s in subs if not s.matches_callback(callback)
            ]

    def unsubscribe_all(self, owner: Any):
        """
        Remove ALL subscriptions belonging to an object.
        Call this in your widget's closeEvent / cleanup.
        """
        with self._lock:
            for etype in self._subscribers:
                self._subscribers[etype] = [
                    s for s in self._subscribers[etype]
                    if s.is_alive and not s.owned_by(owner)
                ]

    # ── Query API ────────────────────────────────────────────────

    def get_recent_events(self, limit: int = 10) -> List[EventPayload]:
        """Returns the most recent events up to the specified limit."""
        with self._lock:
            return list(self._history[-limit:])

    @property
    def stats(self) -> Dict[str, Any]:
        """Observability snapshot for debug tools."""
        with self._lock:
            total_subs = sum(len(v) for v in self._subscribers.values())
            alive_subs = sum(
                1 for subs in self._subscribers.values()
                for s in subs if s.is_alive
            )
        return {
            "total_emits": self._emit_count,
            "total_errors": self._error_count,
            "registered_subscribers": total_subs,
            "alive_subscribers": alive_subs,
            "history_size": len(self._history),
        }

    # ── Internal ─────────────────────────────────────────────────

    def _sweep_dead(self):
        """Global lazy cleanup of all dead weak references."""
        with self._lock:
            for etype in self._subscribers:
                self._subscribers[etype] = [
                    s for s in self._subscribers[etype] if s.is_alive
                ]


# ── Central Singleton ────────────────────────────────────────────
EVENT_BUS = EventBus()
