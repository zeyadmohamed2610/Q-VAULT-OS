import logging
from PyQt5.QtCore import QObject, pyqtSignal, QRect
from core.event_bus import EVENT_BUS, SystemEvent
logger = logging.getLogger(__name__)

class WindowSlot:
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    HALF_LEFT = "half_left"
    HALF_RIGHT = "half_right"
    QUARTER_TL = "quarter_tl" # Top-Left
    QUARTER_TR = "quarter_tr" # Top-Right
    QUARTER_BL = "quarter_bl" # Bottom-Left
    QUARTER_BR = "quarter_br" # Bottom-Right

import enum

class SnapZone(enum.Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    MAXIMIZE = "maximize"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"

class WindowState(enum.Enum):
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    TILED = "tiled"
    DRAGGING = "dragging"

class WindowManager(QObject):
    """
    WindowManager for maintaining desktop OSWindow frames.
    v2.0 Passive Executor — Event-Driven Architecture.
    """

    def __init__(self):
        super().__init__()
        self._windows = {}
        self._active = None
        self.z_counter = 0

        self._window_order = []
        self._workspaces = {
            0: [],
            1: []
        }
        self.current_workspace = 0
    
    @property
    def windows(self):
        """Legacy access for backward compatibility."""
        return self._windows

    def register_window(self, window):
        logger.info(f"Registering window: {window.window_id}")
        window._registered = True # AUTHORIZATION: Window is now allowed to show()
        window.z_index = self.z_counter
        self._windows[window.window_id] = window
        self._workspaces[self.current_workspace].append(window.window_id)
        
        title = window.lbl_title.text() if hasattr(window, "lbl_title") else "Unknown Window"
        EVENT_BUS.emit(SystemEvent.WINDOW_OPENED, {
            "id": window.window_id,
            "title": title,
        }, source="WindowManager")
        self.focus_window(window.window_id)

    def find_by_title(self, title):
        for wid in self._workspaces[self.current_workspace]:
            if wid in self._windows:
                w = self._windows[wid]
                if hasattr(w, "lbl_title") and w.lbl_title.text() == title:
                    return w
        return None

    def focus_window(self, window_id: str):
        logger.info(f"Focusing window: {window_id}")
        if window_id not in self._windows:
            return

        window = self._windows[window_id]
        
        if window_id in self._window_order:
            self._window_order.remove(window_id)
        self._window_order.append(window_id)
        
        if hasattr(window, "is_minimized") and window.is_minimized:
            window.is_minimized = False
            # Restoration fact will be emitted by restore_window if called directly,
            # or we can emit it here if needed. 
            # However, focus_window is usually called AFTER register or restore.
        elif window.isHidden():
            pass # Fact-driven UI will show it

        # Deterministic Z-Index Tracker
        self.z_counter += 1
        window.z_index = self.z_counter

        # Force render ordering system-wide
        sorted_windows = sorted(self._windows.values(), key=lambda w: getattr(w, 'z_index', 0))
        for w in sorted_windows:
            w.raise_()
            if w.window_id == window_id:
                w.activateWindow()
                w.setFocus()

        self._active = window_id

        # Centralized Focus Management (Architectural Pattern)
        for wid, w in self._windows.items():
            is_target = (wid == window_id)
            if hasattr(w, "set_active_state"):
                w.set_active_state(is_target)

        EVENT_BUS.emit(SystemEvent.WINDOW_FOCUSED, {"id": window_id}, source="WindowManager")

    def request_geometry(self, window_id: str, x: int, y: int, w: int, h: int):
        """
        CENTRAL AUTHORITY: Validates and applies ALL geometry changes.
        This is the single gatekeeper for move, resize, and setGeometry.
        """
        if window_id not in self._windows: return
        window = self._windows[window_id]
        
        # 1. Fetch Constraints
        parent = window.parent()
        pw = parent.width() if parent else 1920
        ph = parent.height() if parent else 1080
        
        # 2. Hard Constraints (Min Size / Max Size)
        min_w, min_h = 400, 300
        max_w, max_h = pw, ph
        
        target_w = max(min_w, min(w, max_w))
        target_h = max(min_h, min(h, max_h))
        
        # 3. Position Constraints (Workspace Bounds)
        new_x = max(-target_w + 100, min(x, pw - 100))
        new_y = max(0, min(y, ph - 40))
        
        # ── JITTER PROTECTION (Tolerance 2px) ──
        # Prevent micro-vibration between drag and constraint layers
        if abs(new_x - window.x()) < 2: new_x = window.x()
        if abs(new_y - window.y()) < 2: new_y = window.y()
        if abs(target_w - window.width()) < 2: target_w = window.width()
        if abs(target_h - window.height()) < 2: target_h = window.height()
        
        # 4. Debug & Log (Catch Bypasses)
        if new_x != window.x() or new_y != window.y() or target_w != window.width() or target_h != window.height():
            logger.debug(f"[WM_LOCK] {window_id} -> Req: ({x},{y},{w}x{h}) | Validated: ({new_x},{new_y},{target_w}x{target_h})")
        
        # 5. Execute via backdoor
        if hasattr(window, "_apply_geometry"):
            window._apply_geometry(new_x, new_y, target_w, target_h)
        else:
            window.move(new_x, new_y)
            window.resize(target_w, target_h)

    def set_window_position(self, window_id: str, x: int, y: int):
        """Legacy shim - redirects to request_geometry."""
        if window_id in self._windows:
            w = self._windows[window_id]
            self.request_geometry(window_id, x, y, w.width(), w.height())

    def constrain_to_workspace(self, window):
        """Ensures the window stays within the visible workspace bounds."""
        if hasattr(window, "window_id"):
            self.request_geometry(window.window_id, window.x(), window.y(), window.width(), window.height())

    def minimize_window(self, window_id: str):
        """Fact Layer: Executes minimization and emits result."""
        if window_id not in self._windows: return
        window = self._windows[window_id]
        if not window.is_minimized:
            window.is_minimized = True
            # Logic only: hiding is handled by animation reaction
            # If we minimize the active window, clear active pointer
            if self._active == window_id:
                self._active = None
            
            EVENT_BUS.emit(SystemEvent.WINDOW_MINIMIZED, {
                "id": window_id,
                "title": window.lbl_title.text(),
            }, source="WindowManager")
            logger.info(f"[WM] Minimized: {window_id}")

    def restore_window(self, window_id: str):
        """Fact Layer: Executes restoration/focus and emits result."""
        if window_id not in self._windows: return
        window = self._windows[window_id]
        
        # Restore if minimized
        if window.is_minimized:
            window.is_minimized = False
            # show() is handled by animation reaction
            EVENT_BUS.emit(SystemEvent.WINDOW_RESTORED, {
                "id": window_id,
                "title": window.lbl_title.text(),
            }, source="WindowManager")
            logger.info(f"[WM] Restored: {window_id}")
            
        # Always focus when restoring
        self.focus_window(window_id)

    def cycle_windows(self):
        if not self._window_order:
            return
            
        last = self._window_order.pop(0)
        self._window_order.append(last)

        for wid in reversed(self._window_order):
            if wid in self._workspaces[self.current_workspace]:
                self.focus_window(wid)
                break

    def switch_workspace(self, index):
        if index not in self._workspaces:
            return

        for wid in self._workspaces[self.current_workspace]:
            if wid in self._windows:
                self._windows[wid].hide()

        self.current_workspace = index

        for wid in self._workspaces[self.current_workspace]:
            if wid in self._windows:
                w = self._windows[wid]
                if not (hasattr(w, "is_minimized") and w.is_minimized):
                    # For workspace switching, we might still need direct show/hide 
                    # unless we want workspace facts too.
                    # Let's keep it simple for now as per Phase 1.
                    w.show()

        EVENT_BUS.emit(SystemEvent.WORKSPACE_CHANGED, {"index": index}, source="WindowManager")

    def close_window(self, window_id: str):
        if window_id in self._windows:
            logger.info(f"Closing window: {window_id}")
            w = self._windows.pop(window_id)
            title = w.lbl_title.text() if hasattr(w, 'lbl_title') else 'unknown'
            
            # Note: w.deleteLater() is deliberately NOT called immediately.
            # OSWindow handles its own close animation via WindowAnimationController.
            # 🚨 FAILSAFE: If the UI Event Loop is starved and animation never finishes,
            # force cleanup after 500ms to prevent memory and EventBus subscriber leaks.
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._failsafe_destroy(w))
            
            if window_id in self._window_order:
                self._window_order.remove(window_id)
                
            for ws, wids in self._workspaces.items():
                if window_id in wids:
                    wids.remove(window_id)
            
            EVENT_BUS.emit(SystemEvent.WINDOW_CLOSED, {
                "id": window_id,
                "title": title,
            }, source="WindowManager")
            if self._active == window_id:
                self._active = None

    def _failsafe_destroy(self, w):
        """Forces idempotent cleanup if animations failed due to event loop starvation."""
        try:
            if hasattr(w, "_final_close") and not getattr(w, "_is_destroyed", False):
                logger.warning("[WindowManager] Failsafe Triggered — forcing cleanup.")
                w._final_close()
        except RuntimeError:
            pass  # Object already deleted cleanly by animation

    def close_all(self):
        logger.info("Closing all active windows.")
        # Create a copy of keys to iterate safely while modifying the dict
        for wid in list(self._windows.keys()):
            self.close_window(wid)
        self._window_order.clear()
        self._workspaces = {0: [], 1: []}
        self.current_workspace = 0
        self._active = None

    def calculate_snap_geometry(self, zone: SnapZone, parent_rect: QRect) -> QRect:
        """Calculates the target rectangle for a specific snap zone."""
        pw, ph = parent_rect.width(), parent_rect.height()

        if zone == SnapZone.LEFT:
            return QRect(0, 0, pw // 2, ph)
        elif zone == SnapZone.RIGHT:
            return QRect(pw // 2, 0, pw // 2, ph)
        elif zone == SnapZone.MAXIMIZE:
            return QRect(0, 0, pw, ph)
        elif zone == SnapZone.TOP_LEFT:
            return QRect(0, 0, pw // 2, ph // 2)
        elif zone == SnapZone.TOP_RIGHT:
            return QRect(pw // 2, 0, pw // 2, ph // 2)
        return QRect()

    def detect_snap_zone(self, x: int, y: int, parent_rect: QRect) -> SnapZone:
        """Determines if coordinates are within a snap trigger threshold."""
        pw, ph = parent_rect.width(), parent_rect.height()
        THRESHOLD = 30

        if y < THRESHOLD:
            # Top corners take priority over plain top
            if x < THRESHOLD:
                return SnapZone.TOP_LEFT
            if x > pw - THRESHOLD:
                return SnapZone.TOP_RIGHT
            return SnapZone.MAXIMIZE
        if x < THRESHOLD:
            return SnapZone.LEFT
        if x > pw - THRESHOLD:
            return SnapZone.RIGHT
        return SnapZone.NONE

    def apply_snap(self, window_id: str, zone: SnapZone):
        """Executes a snap action with system-level validation."""
        if window_id not in self._windows or zone == SnapZone.NONE: return
        window = self._windows[window_id]
        
        parent = window.parent()
        if not parent: return
        
        target_rect = self.calculate_snap_geometry(zone, parent.rect())
        
        # Use existing request_geometry for validation & application
        self.request_geometry(window_id, 
                             target_rect.x(), target_rect.y(), 
                             target_rect.width(), target_rect.height())
        
        # Emit fact for UI effects
        EVENT_BUS.emit(SystemEvent.ACTION_TAKEN, {
            "action": "window_snap",
            "id": window_id,
            "zone": zone.value
        }, source="WindowManager")

_instance = None

def get_window_manager() -> WindowManager:
    global _instance
    if _instance is None:
        _instance = WindowManager()
    return _instance
