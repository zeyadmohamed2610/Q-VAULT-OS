import time
from PyQt5.QtCore import Qt, QPoint
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager, WindowState, SnapZone

class WindowDragHandler:
    """
    Owns all drag interaction state and logic.
    Single Responsibility: Drag initiation, movement tracking,
    snap preview during drag, and snap execution on release.
    """

    _DRAG_EMIT_INTERVAL = 0.033   # ~30fps max for drag_update events

    def __init__(self, window, snap_ctrl):
        self._window = window
        self._snap_ctrl = snap_ctrl
        self._drag_pos = QPoint()
        self._last_drag_emit = 0.0

    def on_press(self, event):
        """Handle mouse press for drag initiation. Returns True if drag started."""
        w = self._window
        sc = self._snap_ctrl

        if event.button() != Qt.LeftButton:
            return False

        # Only start drag if clicking in title bar area (accounts for margin)
        if event.pos().y() > (30 + getattr(w, '_margin', 0)):
            return False

        if sc.state == WindowState.MAXIMIZED or sc.state == WindowState.TILED:
            # Restore first before dragging
            from system.window_manager import WindowSlot
            sc.snap_to_slot(WindowSlot.NORMAL)
            self._drag_pos = QPoint(w.width() // 2, event.pos().y())
        else:
            self._drag_pos = event.pos()

        sc.state = WindowState.DRAGGING
        EVENT_BUS.emit(SystemEvent.REQ_WINDOW_DRAG_START, {"id": w.window_id}, source="WindowDragHandler")
        return True

    def on_move(self, event):
        """Handle mouse move during drag."""
        w = self._window
        sc = self._snap_ctrl

        if sc.state != WindowState.DRAGGING:
            return

        new_pos = w.mapToParent(event.pos() - self._drag_pos)
        wm = get_window_manager()
        wm.set_window_position(w.window_id, new_pos.x(), new_pos.y())

        # ── SNAP PREVIEW ──
        parent = w.parent()
        if parent:
            zone = wm.detect_snap_zone(new_pos.x(), new_pos.y(), parent.rect())
            # Navigate up to find Desktop (Workspace -> Desktop)
            desktop = parent.parent()
            if hasattr(desktop, "snap_preview"):
                if zone != SnapZone.NONE:
                    target_rect = wm.calculate_snap_geometry(zone, parent.rect())
                    desktop.snap_preview.show_preview(target_rect)
                else:
                    desktop.snap_preview.hide_preview()

        # Throttle drag event emission to ~30fps to prevent event bus flood
        now = time.perf_counter()
        if now - self._last_drag_emit >= self._DRAG_EMIT_INTERVAL:
            self._last_drag_emit = now
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_DRAG_UPDATE, {
                "id": w.window_id,
                "x": new_pos.x(),
                "y": new_pos.y()
            }, source="WindowDragHandler")

    def on_release(self, event):
        """Handle mouse release — finalize drag and execute snap."""
        w = self._window
        sc = self._snap_ctrl

        if sc.state != WindowState.DRAGGING:
            return

        sc.state = WindowState.NORMAL

        # ── SNAP EXECUTION ──
        wm = get_window_manager()
        parent = w.parent()
        if parent:
            # Hide preview immediately
            desktop = parent.parent()
            if hasattr(desktop, "snap_preview"):
                desktop.snap_preview.hide_preview()

            # Check for snap
            zone = wm.detect_snap_zone(w.x(), w.y(), parent.rect())
            if zone != SnapZone.NONE:
                wm.apply_snap(w.window_id, zone)

        EVENT_BUS.emit(SystemEvent.REQ_WINDOW_DRAG_END, {"id": w.window_id}, source="WindowDragHandler")
