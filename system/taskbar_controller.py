import logging
from typing import Dict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QTime
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
from system.window_manager import get_window_manager

logger = logging.getLogger(__name__)


class TaskbarController(QObject):
    """
    v1.0 Event-Driven Taskbar State Machine.
    Subscribes to EventBus Facts. Emits Commands for actions.
    The state_updated signal is intra-component only (-> TaskbarUI).
    """
    state_updated = pyqtSignal(dict)  # Local UI signal: {'apps': [], 'active_id': str, 'time': str}

    def __init__(self):
        super().__init__()
        self._active_id = None
        self._apps: Dict[str, str] = {}  # id -> title

        # Clock Timer (local concern)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._current_time = ""

        # Subscribe to Window Facts via EventBus
        EVENT_BUS.subscribe(SystemEvent.WINDOW_OPENED, self._on_window_opened)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED, self._on_window_closed)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_FOCUSED, self._on_window_focused)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_MINIMIZED, self._on_window_minimized)

        # Initial state
        self._update_clock()
        self._sync_with_wm()

    def _sync_with_wm(self):
        """Initial sync if some windows are already open before subscription."""
        wm = get_window_manager()
        self._apps = {wid: win.lbl_title.text() for wid, win in wm._windows.items()}
        self._active_id = getattr(wm, "_active", None)
        self._emit_state()

    def _update_clock(self):
        new_time = QTime.currentTime().toString("h:mm AP")
        if new_time != self._current_time:
            self._current_time = new_time
            self._emit_state()

    # ── EventBus Handlers (receive EventPayload) ─────────────────

    def _on_window_opened(self, payload: EventPayload):
        wid = payload.data.get("id")
        title = payload.data.get("title", "Untitled")
        if wid:
            self._apps[wid] = title
            self._emit_state()

    def _on_window_closed(self, payload: EventPayload):
        wid = payload.data.get("id")
        if wid and wid in self._apps:
            del self._apps[wid]
        if self._active_id == wid:
            self._active_id = None
        self._emit_state()

    def _on_window_focused(self, payload: EventPayload):
        wid = payload.data.get("id")
        if wid:
            self._active_id = wid
            self._emit_state()

    def _on_window_minimized(self, payload: EventPayload):
        wid = payload.data.get("id")
        if wid and self._active_id == wid:
            self._active_id = None
            self._emit_state()

    # ── State Emission ───────────────────────────────────────────

    def _emit_state(self):
        state = {
            "apps": [{"id": wid, "title": title} for wid, title in self._apps.items()],
            "active_id": self._active_id,
            "time": self._current_time,
        }
        self.state_updated.emit(state)

    # ── Actions (Commands via EventBus) ──────────────────────────

    def request_focus(self, window_id: str):
        # Smart Toggle Logic
        if self._active_id == window_id:
            # Already active? Minimize it.
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_MINIMIZE, {"id": window_id}, source="Taskbar")
        else:
            # Not active? Focus it (this also restores if minimized).
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS, {"id": window_id}, source="Taskbar")

    def request_toggle_launcher(self):
        EVENT_BUS.emit(SystemEvent.ACTION_CLICKED, {"command": "@launcher"}, source="Taskbar")

    def handle_shortcut(self, name: str):
        """Processes static taskbar shortcut clicks."""
        if name == "terminal":
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": "Terminal"}, source="Taskbar")
        elif name == "files":
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": "Files"}, source="Taskbar")
        elif name == "ai":
            EVENT_BUS.emit(SystemEvent.REQ_COMMAND_PALETTE_TOGGLE, source="Taskbar")
        elif name == "flows":
            # For now, open command palette with 'workflows' filter or a special event
            EVENT_BUS.emit(SystemEvent.REQ_WORKFLOW_LIST, source="Taskbar")
