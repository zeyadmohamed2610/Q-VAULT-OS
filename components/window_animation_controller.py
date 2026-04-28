import logging
from PyQt5.QtCore import QObject, QPropertyAnimation, QParallelAnimationGroup
from core.event_bus import EVENT_BUS, SystemEvent
from components.motion import MotionController

logger = logging.getLogger(__name__)

class WindowAnimationController(QObject):
    """
    v2.1 Refinement: Decoupled Animation Orchestrator.
    Responsible for:
    1. Efficient event filtering (Fact-driven).
    2. Animation conflict resolution (Interrupts).
    3. Lifecycle coordination (Animation-then-Destroy).
    """
    
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.window_id = window.window_id
        self._current_anim = None
        self._is_closing = False
        
        # Subscribe to facts
        EVENT_BUS.subscribe(SystemEvent.WINDOW_OPENED, self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_FOCUSED, self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_MINIMIZED, self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_RESTORED, self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED, self._on_window_event)

    def cleanup(self):
        """Safe unsubscribe."""
        EVENT_BUS.unsubscribe_all(self)
        self.stop_current()

    def stop_current(self):
        """Interrupt any running animation to prevent property conflicts."""
        if self._current_anim and self._current_anim.state() == QPropertyAnimation.Running:
            self._current_anim.stop()
        self._current_anim = None

    def _on_window_event(self, payload):
        """Strict Filtered Reaction Layer."""
        wid = payload.data.get("id")
        etype = payload.type

        # ── 1. Efficient Global Filter ──
        if etype == SystemEvent.WINDOW_FOCUSED:
            is_target = (wid == self.window_id)
            # Focus is a "Soft" animation, we don't necessarily stop everything for it,
            # but we should handle its own concurrency.
            self._handle_focus(is_target)
            return

        # ── 2. Strict ID Filter for lifecycle events ──
        if wid != self.window_id:
            return

        # ── 3. Conflict Resolution & Dispatch ──
        if etype == SystemEvent.WINDOW_OPENED:
            self.stop_current()
            self._current_anim = MotionController.spawn_window(self.window, self.window.geometry())
            
        elif etype == SystemEvent.WINDOW_MINIMIZED:
            self.stop_current()
            self._current_anim = MotionController.minimize_window(self.window)
            
        elif etype == SystemEvent.WINDOW_RESTORED:
            self.stop_current()
            self._current_anim = MotionController.restore_window(self.window, self.window.geometry())
            
        elif etype == SystemEvent.WINDOW_CLOSED:
            if not self._is_closing:
                self._is_closing = True
                self.stop_current()
                self._current_anim = self._animate_close()

    def _handle_focus(self, is_target: bool):
        """Focus animations are handled snapily."""
        MotionController.fade_focus(self.window, is_target)
        if is_target:
            MotionController.focus_pulse(self.window)

    def _animate_close(self):
        """Lifecycle-safe close: Animation -> Signal -> Destroy."""
        from assets import theme
        anim = QPropertyAnimation(self.window, b"windowOpacity")
        anim.setDuration(theme.MOTION_SNAPPY)
        anim.setStartValue(self.window.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self.window._final_close)
        anim.start()
        return anim
