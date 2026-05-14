import logging
import time
from PyQt5.QtCore import QObject, QPropertyAnimation, QEasingCurve
from core.event_bus import EVENT_BUS, SystemEvent
from ui.widgets.motion import MotionController

logger = logging.getLogger(__name__)


class WindowAnimationController(QObject):
    """
    v1.0 Stress-Hardened Animation Orchestrator.
    Key changes vs v1.0:
      - O(1) fast-path reject for events targeting OTHER windows
      - _animate_open uses 150ms fade (not full MotionController spawn)
      - _animate_close is instant (no fade-out race conditions)
      - _handle_focus skips animation under drag or while another anim runs
    """

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.window_id = window.window_id
        self._current_anim = None
        self._is_closing = False

        # Subscribe to lifecycle and focus events
        EVENT_BUS.subscribe(SystemEvent.WINDOW_OPENED,    self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_FOCUSED,   self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_MINIMIZED, self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_RESTORED,  self._on_window_event)
        EVENT_BUS.subscribe(SystemEvent.WINDOW_CLOSED,    self._on_window_event)

    def cleanup(self):
        """Safe unsubscribe — call before window destruction."""
        EVENT_BUS.unsubscribe_all(self)
        self.stop_current()

    def stop_current(self):
        """Interrupt any running animation to prevent property conflicts."""
        if self._current_anim and self._current_anim.state() == QPropertyAnimation.Running:
            self._current_anim.stop()
        self._current_anim = None

    def _on_window_event(self, payload):
        """
        FAST-PATH: reject events for other windows in O(1).
        Only do real work if this event targets OUR window.
        """
        wid   = payload.data.get("id")
        etype = payload.type

        # ── FAST REJECT: lifecycle events — only care about OUR window ──
        if etype in (
            SystemEvent.WINDOW_OPENED,
            SystemEvent.WINDOW_CLOSED,
            SystemEvent.WINDOW_MINIMIZED,
            SystemEvent.WINDOW_RESTORED,
        ):
            if wid != self.window_id:
                return    # O(1) reject — no work done

        # ── FOCUS: soft animation, handle regardless (is_target logic) ──
        if etype == SystemEvent.WINDOW_FOCUSED:
            self._handle_focus(wid == self.window_id)
            return

        # Defensive: catch anything else targeting other windows
        if wid != self.window_id:
            return

        # ── CONFLICT RESOLUTION & DISPATCH ──
        if etype == SystemEvent.WINDOW_OPENED:
            self.stop_current()
            self._current_anim = self._animate_open()

        elif etype == SystemEvent.WINDOW_MINIMIZED:
            # CRITICAL: We MUST stop any current anim, but minimize is top priority.
            self.stop_current()
            self._current_anim = MotionController.minimize_window(self.window)

        elif etype == SystemEvent.WINDOW_RESTORED:
            self.stop_current()
            self._current_anim = MotionController.restore_window(self.window, self.window.geometry())

        elif etype == SystemEvent.WINDOW_CLOSED:
            if not self._is_closing:
                self._is_closing = True
                self.stop_current()
                self._animate_close()

    def _animate_open(self):
        """Fade in over 150ms — fast enough to avoid the slow-handler warning."""
        if not self.window or not self.window.isVisible():
            return None
        anim = QPropertyAnimation(self.window, b"windowOpacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        return anim

    def _animate_close(self):
        """
        Instant close — no fade-out.
        """
        if self.window:
            self.window.setWindowOpacity(1.0)
        if hasattr(self.window, '_final_close'):
            self.window._final_close()

    def _handle_focus(self, is_target: bool):
        """
        Subtle focus animation — only if we ARE the target, and only if idle.
        Crucially, we do NOT stop the current animation if it is a lifecycle event.
        """
        if not is_target or not self.window:
            return

        # PROTECTION: If a minimize/restore/open animation is running, 
        # DO NOT interrupt it for a focus pulse. This prevents UI locking.
        if self._current_anim and self._current_anim.state() == QPropertyAnimation.Running:
            return

        # Skip if application is under drag
        from PyQt5.QtWidgets import QApplication
        if QApplication.instance() and QApplication.instance().overrideCursor() is not None:
            return

        MotionController.fade_focus(self.window, is_target)
        MotionController.focus_pulse(self.window)
