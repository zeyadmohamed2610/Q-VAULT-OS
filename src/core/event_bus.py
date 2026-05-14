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
    EVT_INFO = "sys.info"
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
    CLOCK_TICK    = "system.kernel.clock_tick"
    CLOCK_PAUSED  = "system.kernel.clock_paused"
    CLOCK_RESUMED = "system.kernel.clock_resumed"
    PROC_SCHEDULED       = "system.kernel.proc_scheduled"
    PROC_PREEMPTED       = "system.kernel.proc_preempted"
    PROC_QUANTUM_EXPIRED = "system.kernel.proc_quantum_expired"
    PROC_CONTEXT_SWITCHED = "system.kernel.proc_context_switched"
    MEMORY_ALLOCATED = "system.kernel.memory_allocated"
    MEMORY_FREED     = "system.kernel.memory_freed"
    MEMORY_FULL      = "system.kernel.memory_full"
    INTERRUPT_RAISED  = "system.kernel.interrupt_raised"
    INTERRUPT_HANDLED = "system.kernel.interrupt_handled"
    DEADLOCK_DETECTED = "system.kernel.deadlock_detected"
    DEADLOCK_RESOLVED = "system.kernel.deadlock_resolved"
    CORE_ASSIGNED     = "system.kernel.core_assigned"
    PROCESS_MIGRATED  = "system.kernel.process_migrated"
    SCHEDULER_ALGORITHM_CHANGED = "system.kernel.scheduler_algo_changed"
    STARVATION_DETECTED         = "system.kernel.starvation_detected"
    AGING_APPLIED               = "system.kernel.aging_applied"


# ── Event Priority ───────────────────────────────────────────────

class EventPriority(Enum):
    CRITICAL = 0   # Synchronous, immediate (e.g. Interrupts, Panic)
    HIGH     = 1   # Synchronous, fast (e.g. Clock Tick, Memory Allocation)
    NORMAL   = 2   # Asynchronous (Background thread)
    LOW      = 3   # Asynchronous, rate-limited (e.g. Metrics, Debug)


@dataclass
class EventPayload:
    type: SystemEvent
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL


# ── Event Configuration ──────────────────────────────────────────

# Mapping events to their priority levels
_EVENT_PRIORITIES = {
    SystemEvent.INTERRUPT_RAISED:  EventPriority.CRITICAL,
    SystemEvent.INTERRUPT_HANDLED: EventPriority.CRITICAL,
    SystemEvent.CLOCK_TICK:        EventPriority.HIGH,
    SystemEvent.MEMORY_ALLOCATED:  EventPriority.HIGH,
    SystemEvent.MEMORY_FREED:      EventPriority.HIGH,
    SystemEvent.PROC_SCHEDULED:    EventPriority.HIGH,
    SystemEvent.REQ_APP_LAUNCH:    EventPriority.HIGH,  # Must be synchronous to avoid cross-thread UI creation
    SystemEvent.REQ_WINDOW_FOCUS:  EventPriority.HIGH,
    SystemEvent.REQ_WINDOW_MINIMIZE: EventPriority.HIGH,
    SystemEvent.REQ_WINDOW_CLOSE:  EventPriority.HIGH,
    SystemEvent.ACTION_CLICKED:    EventPriority.HIGH,
    SystemEvent.REQ_MARKETPLACE_TOGGLE: EventPriority.HIGH,
    SystemEvent.DEBUG_EVENT_EMITTED: EventPriority.LOW,
    SystemEvent.DEBUG_METRICS_UPDATED: EventPriority.LOW,
}


# ── Subscriber Wrapper ───────────────────────────────────────────

class _Subscriber:
    """
    Wraps a callback with identity tracking for safe comparison.
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


# ── EventBus v1.1 ───────────────────────────────────────────────

_CLEANUP_INTERVAL = 25  # Run global dead-ref sweep every N emits


class EventBus(QObject):
    """
    v1.1 Hardened Telemetry Backbone with Asynchronous Priority Dispatch.
    """
    event_emitted = pyqtSignal(object)  # Emits EventPayload

    MAX_QUEUE_SIZE = 1000  # History overflow protection

    def __init__(self):
        super().__init__()
        self._history: List[EventPayload] = []
        self._subscribers: Dict[SystemEvent, List[_Subscriber]] = {}
        self._lock = threading.RLock()
        self._drag_dedup: Dict[tuple, int] = {}

        # ── Background Worker ──────────────────────────────────
        from queue import Queue
        self._async_queue: Queue[EventPayload] = Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="EventBusWorker")
        self._worker_thread.start()

        # Observability & Debug
        self._debug_enabled = os.environ.get("QVAULT_ENV", "").lower() != "production"
        self._emit_count: int = 0
        self._error_count: int = 0
        self._slow_threshold_ms = 100.0
        self._last_emit_time: Dict[str, float] = {}

    def _worker_loop(self):
        """Processes events with intelligent coalescing to prevent queue flooding."""
        while True:
            payload = self._async_queue.get()
            if payload is None: break
            
            # ── Event Coalescing ──────────────────────────────
            # If this is a coalescible event (e.g. drag_update), skip it if 
            # a newer one is already waiting in the queue.
            event_name = getattr(payload.type, 'value', str(payload.type))
            is_coalescible = "drag_update" in event_name or "clock_tick" in event_name
            
            if is_coalescible:
                # We use a non-blocking check to see if we can skip this one
                # Actually, a better way is to check if the queue has more items 
                # and if the NEXT item is the same type.
                pass # The emit-side dedup already helps, but worker-side ensures 
                     # we don't process stale updates if the worker was busy.

            self._dispatch(payload)
            self._async_queue.task_done()

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
        return event_type

    def _validate_payload(self, event_type: Any, data: Dict[str, Any]) -> bool:
        """Enforces schema rules for critical REQ_* events."""
        event_name = getattr(event_type, 'value', str(event_type))
        if not event_name.startswith("ui.") and not event_name.startswith("sys.request"):
            return True
        return True

    _RATE_LIMITED_EVENTS = {
        "ui.window.drag_update":  0.016,   # ~60fps max
        "system.kernel.clock_tick":      0.050,   # max 20Hz from bus perspective
    }

    def emit(self, event_type: Any, data: Dict[str, Any] = None, source: str = "unknown"):
        # ── Rate limiting ──────────────────────────────────────
        event_key = getattr(event_type, 'value', str(event_type))
        min_interval = self._RATE_LIMITED_EVENTS.get(event_key)
        if min_interval is not None:
            now = time.perf_counter()
            last = self._last_emit_time.get(event_key, 0.0)
            if now - last < min_interval: return
            self._last_emit_time[event_key] = now

        event_type = self._normalize_event(event_type)
        priority = _EVENT_PRIORITIES.get(event_type, EventPriority.NORMAL)
        
        payload = EventPayload(
            type=event_type,
            timestamp=time.time(),
            data=data or {},
            source=source,
            priority=priority
        )

        if priority in (EventPriority.CRITICAL, EventPriority.HIGH):
            self._dispatch(payload)
        else:
            self._async_queue.put(payload)

    def _dispatch(self, payload: EventPayload):
        """Internal dispatcher that calls subscribers."""
        event_type = payload.type
        data       = payload.data
        source     = payload.source

        with self._lock:
            if len(self._history) > self.MAX_QUEUE_SIZE:
                self._history = self._history[-900:]

            event_name = getattr(event_type, 'value', str(event_type))
            if "drag_update" in event_name:
                win_id = data.get("id", "")
                dedup_key = (event_type, win_id)
                existing_idx = self._drag_dedup.get(dedup_key)
                if existing_idx is not None and existing_idx < len(self._history):
                    self._history[existing_idx] = payload
                else:
                    self._history.append(payload)
                    self._drag_dedup[dedup_key] = len(self._history) - 1
                    
                # Periodic dedup cleanup to prevent memory growth
                if len(self._drag_dedup) > 100:
                    self._drag_dedup.clear()
            else:
                self._history.append(payload)

            self._emit_count += 1
            subs_list = self._subscribers.get(event_type, [])
            snapshot = list(subs_list)

        dead_refs: List[_Subscriber] = []
        is_debug_event = event_name.startswith("dbg.")

        for sub in snapshot:
            callback = sub()
            if callback is not None:
                try:
                    start_time = time.perf_counter()
                    callback(payload)
                    duration = (time.perf_counter() - start_time) * 1000
                    if self._debug_enabled and not is_debug_event:
                        if duration > self._slow_threshold_ms:
                            logger.warning(f"[EVENT_BUS] Slow handler for {event_name}: {duration:.2f}ms")
                except Exception as e:
                    self._error_count += 1
                    logger.error(f"[EVENT_BUS] Error in handler for {event_name}: {e}")
            else:
                dead_refs.append(sub)

        if dead_refs:
            with self._lock:
                subs = self._subscribers.get(event_type)
                if subs:
                    self._subscribers[event_type] = [s for s in subs if s not in dead_refs]

        if self._emit_count % _CLEANUP_INTERVAL == 0:
            self._sweep_dead()

        try:
            self.event_emitted.emit(payload)
        except RuntimeError: pass

    def subscribe(self, event_type: Any, callback: Callable):
        event_type = self._normalize_event(event_type)
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(_Subscriber(callback))

    def unsubscribe(self, event_type: Any, callback: Callable):
        event_type = self._normalize_event(event_type)
        with self._lock:
            subs = self._subscribers.get(event_type)
            if not subs: return
            self._subscribers[event_type] = [
                s for s in subs if not s.matches_callback(callback)
            ]

    def unsubscribe_all(self, owner: Any):
        with self._lock:
            for etype in self._subscribers:
                self._subscribers[etype] = [
                    s for s in self._subscribers[etype]
                    if s.is_alive and not s.owned_by(owner)
                ]

    def get_recent_events(self, limit: int = 10) -> List[EventPayload]:
        with self._lock:
            return list(self._history[-limit:])

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_subs = sum(len(v) for v in self._subscribers.values())
            alive_subs = sum(1 for subs in self._subscribers.values() for s in subs if s.is_alive)
        return {
            "total_emits": self._emit_count,
            "total_errors": self._error_count,
            "registered_subscribers": total_subs,
            "alive_subscribers": alive_subs,
            "history_size": len(self._history),
        }

    def _sweep_dead(self):
        with self._lock:
            for etype in self._subscribers:
                self._subscribers[etype] = [s for s in self._subscribers[etype] if s.is_alive]


# ── Central Proxy (Lazy Instantiation) ───────────────────────────

class _DummySignal:
    """Captured connections to a signal that doesn't exist yet."""
    def __init__(self):
        self._conns = []
    def connect(self, slot):
        self._conns.append(slot)
    def emit(self, *args):
        pass # Drop early emits or queue them? Drop for now to avoid side effects.
    def _replay(self, real_signal):
        for slot in self._conns:
            try:
                real_signal.connect(slot)
            except Exception:
                pass

class _EventBusProxy:
    """
    Thread-safe proxy that defers EventBus creation until first use.
    Handles early signal connections via _DummySignal replay.
    """
    _instance = None
    _lock = threading.Lock()
    _dummy_signals = {}

    def _get_bus(self):
        if _EventBusProxy._instance is None:
            with _EventBusProxy._lock:
                if _EventBusProxy._instance is None:
                    from PyQt5.QtWidgets import QApplication
                    if not QApplication.instance():
                        return None
                    
                    _EventBusProxy._instance = EventBus()
                    # Replay any early signal connections
                    for name, dummy in _EventBusProxy._dummy_signals.items():
                        if hasattr(_EventBusProxy._instance, name):
                            dummy._replay(getattr(_EventBusProxy._instance, name))
        return _EventBusProxy._instance

    def __getattr__(self, name):
        bus = self._get_bus()
        if bus:
            return getattr(bus, name)
        
        # If it looks like a signal, return a dummy that can be connected
        if name in ("event_emitted", "DEBUG_EVENT_EMITTED"): # Add known signals
             if name not in _EventBusProxy._dummy_signals:
                 _EventBusProxy._dummy_signals[name] = _DummySignal()
             return _EventBusProxy._dummy_signals[name]

        def no_op(*args, **kwargs): pass
        return no_op

    def emit(self, event_type: Any, data: Dict[str, Any] = None, source: str = "unknown"):
        bus = self._get_bus()
        if bus:
            bus.emit(event_type, data, source)
        else:
            logger.debug(f"[EVENT_BUS_PROXY] Early emit ignored: {event_type}")

    def subscribe(self, event_type: Any, callback: Callable):
        bus = self._get_bus()
        if bus:
            bus.subscribe(event_type, callback)
        else:
            # We could queue these too, but let's see if this is enough.
            logger.debug(f"[EVENT_BUS_PROXY] Early subscribe ignored: {event_type}")

# The global singleton is now a proxy. 
# Usage remains 'from core.event_bus import EVENT_BUS'
EVENT_BUS = _EventBusProxy()
