from PyQt5.QtCore import Qt, QRect
from system.window_manager import WindowState, WindowSlot

class SnapController:
    """
    Owns window tiling/snapping state and logic.
    Single Responsibility: Slot transitions, maximize toggle,
    keyboard snap shortcuts, physics snap reaction.
    """

    def __init__(self, window):
        self._window = window
        self.state = WindowState.NORMAL
        self.slot = WindowSlot.NORMAL
        self._prev_geometry = QRect()

    def snap_to_slot(self, slot_type, rect=None):
        """v1.4 Tiling Engine core."""
        w = self._window

        if slot_type == WindowSlot.NORMAL:
            self.state = WindowState.NORMAL
            self.slot = WindowSlot.NORMAL
            if self._prev_geometry and not self._prev_geometry.isEmpty():
                w.setGeometry(self._prev_geometry)
            w.btn_max.setText("□")
            return

        if self.state == WindowState.NORMAL:
            self._prev_geometry = w.geometry()

        self.slot = slot_type
        if slot_type == WindowSlot.MAXIMIZED:
            self.state = WindowState.MAXIMIZED
            w.btn_max.setText("❐")
        else:
            self.state = WindowState.TILED
            w.btn_max.setText("❐")

        if rect:
            w.setGeometry(rect)

    def toggle_maximize(self):
        """Toggle between maximized and normal states."""
        w = self._window
        if self.state == WindowState.MAXIMIZED:
            self.snap_to_slot(WindowSlot.NORMAL)
        else:
            p = w.parent().rect() if w.parent() else None
            if p:
                self.snap_to_slot(WindowSlot.MAXIMIZED, p)

    def handle_key_snap(self, key, parent_rect):
        """Handle Super+Arrow keyboard shortcuts for snapping. Returns True if handled."""
        if parent_rect.isEmpty():
            return False

        w, h = parent_rect.width(), parent_rect.height()

        if key == Qt.Key_Up:
            self.snap_to_slot(WindowSlot.MAXIMIZED, parent_rect)
        elif key == Qt.Key_Left:
            self.snap_to_slot(WindowSlot.HALF_LEFT, QRect(0, 0, w // 2, h))
        elif key == Qt.Key_Right:
            self.snap_to_slot(WindowSlot.HALF_RIGHT, QRect(w // 2, 0, w // 2, h))
        elif key == Qt.Key_Down:
            self.snap_to_slot(WindowSlot.NORMAL)
        else:
            return False
        return True

    def on_physics_snap(self, payload):
        """Reaction to snap fact from PhysicsController."""
        w = self._window
        if payload.data.get("id") != w.window_id:
            return

        slot = payload.data.get("slot")
        if slot:
            parent_rect = w.parent().rect() if w.parent() else QRect()
            pw, ph = parent_rect.width(), parent_rect.height()

            rect = parent_rect
            if slot == WindowSlot.HALF_LEFT:
                rect = QRect(0, 0, pw // 2, ph)
            elif slot == WindowSlot.HALF_RIGHT:
                rect = QRect(pw // 2, 0, pw // 2, ph)
            elif slot == WindowSlot.QUARTER_TL:
                rect = QRect(0, 0, pw // 2, ph // 2)
            elif slot == WindowSlot.QUARTER_TR:
                rect = QRect(pw // 2, 0, pw // 2, ph // 2)
            elif slot == WindowSlot.QUARTER_BL:
                rect = QRect(0, ph // 2, pw // 2, ph // 2)
            elif slot == WindowSlot.QUARTER_BR:
                rect = QRect(pw // 2, ph // 2, pw // 2, ph // 2)

            self.snap_to_slot(slot, rect)
