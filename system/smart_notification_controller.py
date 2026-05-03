import logging
import time
from typing import Dict, Callable, Optional
from PyQt5.QtCore import QObject, QTimer
from system.notification_service import NOTIFICATION_SERVICE, NotificationLevel
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload

logger = logging.getLogger(__name__)


# ── Event -> Notification Mapping ─────────────────────────────────
# Each entry defines how an EventBus Fact becomes a user-facing toast.
#
# Keys:
#   message   — static string OR callable(payload.data) -> str
#   title     — toast header
#   level     — NotificationLevel (INFO / WARNING / DANGER)
#
# To add a new notification, add ONE line here. Nothing else changes.

_EVENT_NOTIFICATION_MAP: Dict[SystemEvent, dict] = {
    SystemEvent.LOGIN_SUCCESS: {
        "message": lambda d: f"Welcome back, {d.get('user', 'User')}",
        "title": "Authentication",
        "level": NotificationLevel.INFO,
    },
    SystemEvent.LOGIN_FAILED: {
        "message": "Authentication Failed",
        "title": "Security",
        "level": NotificationLevel.DANGER,
    },
    SystemEvent.SESSION_LOCKED: {
        "message": "Session locked",
        "title": "Security",
        "level": NotificationLevel.INFO,
    },
    SystemEvent.SECURITY_ALERT: {
        "message": lambda d: d.get("message", "Security Alert"),
        "title": "Security",
        "level": NotificationLevel.DANGER,
    },
}


class SmartNotificationController(QObject):
    """
    v3.0 Event-Driven Smart Notification Router.

    Subscribes to EventBus Facts and translates them into user-facing
    toasts via the NotificationService. Handles:
      - Stable keying (source:event_type)
      - 10-second reset windows
      - Debounced grouped notifications
      - Level escalation on spam
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True

        self._history: Dict[str, list] = {}
        self._debounce_timers: Dict[str, QTimer] = {}
        self._pending_notifications: Dict[str, dict] = {}

        # Subscribe to all mapped events
        for event_type in _EVENT_NOTIFICATION_MAP:
            EVENT_BUS.subscribe(event_type, self._on_event)

        logger.info(f"[SmartNotifier] Initialized. Watching {len(_EVENT_NOTIFICATION_MAP)} event types.")

    # ── Public API: Runtime Extension ────────────────────────────

    def register_mapping(self, event_type: SystemEvent, config: dict):
        """
        Allow plugins to add new event -> notification mappings at runtime.
        
        Usage:
            SMART_NOTIFIER.register_mapping(SystemEvent.SOME_EVENT, {
                "message": "Something happened",
                "title": "Plugin",
                "level": NotificationLevel.INFO,
            })
        """
        _EVENT_NOTIFICATION_MAP[event_type] = config
        EVENT_BUS.subscribe(event_type, self._on_event)
        logger.info(f"[SmartNotifier] Registered mapping for {event_type.value}")

    # ── Core Handler ─────────────────────────────────────────────

    def _on_event(self, payload: EventPayload):
        """Central handler: translates an EventBus Fact into a notification."""
        config = _EVENT_NOTIFICATION_MAP.get(payload.type)
        if not config:
            return

        # Resolve message (static string or dynamic callable)
        msg_template = config["message"]
        if callable(msg_template):
            message = msg_template(payload.data)
        else:
            message = msg_template

        title = config["title"]
        level = config["level"]
        source = payload.source

        self._route_notification(
            event_type=payload.type,
            message=message,
            title=title,
            level=level,
            source=source,
        )

    # ── Smart Routing (dedup, grouping, escalation) ──────────────

    def _route_notification(self, event_type: SystemEvent, message: str,
                            title: str, level: str, source: str):
        now = time.time()

        # 1. Stable key based on source and event_type
        key = f"{source}:{event_type.value}"

        if key not in self._history:
            self._history[key] = []

        # 2. Reset window: If last event was more than 10 seconds ago, reset
        if self._history[key] and (now - self._history[key][-1]) > 10.0:
            self._history[key] = []

        self._history[key].append(now)
        count = len(self._history[key])

        # 3. Grouping behavior
        if count == 1:
            # First occurrence -> emit immediately
            NOTIFICATION_SERVICE.notify(message, title=title, level=level, notif_id=key)
        else:
            # Spam detected -> debounce and escalate
            escalated_level = level
            if level == NotificationLevel.WARNING:
                escalated_level = NotificationLevel.DANGER
            elif level == NotificationLevel.INFO and count >= 5:
                escalated_level = NotificationLevel.WARNING

            final_message = f"{message} (x{count})"

            # Save pending payload
            self._pending_notifications[key] = {
                "message": final_message,
                "title": title,
                "level": escalated_level,
                "count": count,
            }

            # Create or restart debounce timer
            if key not in self._debounce_timers:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda k=key: self._emit_pending(k))
                self._debounce_timers[key] = timer

            # Wait 1.5 seconds of silence before emitting grouped toast
            self._debounce_timers[key].start(1500)

    def _emit_pending(self, key: str):
        """Called when the spam/rapid firing has stopped."""
        if key in self._pending_notifications:
            p = self._pending_notifications.pop(key)
            logger.info(f"[SmartNotifier] Emitting grouped notification: {key} (Count: {p['count']})")
            NOTIFICATION_SERVICE.notify(p["message"], title=p["title"], level=p["level"], notif_id=key)


# ── Singleton ────────────────────────────────────────────────────
SMART_NOTIFIER = SmartNotificationController()
