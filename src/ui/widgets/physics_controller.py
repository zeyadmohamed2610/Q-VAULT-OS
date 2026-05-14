import time
import logging
from PyQt5.QtCore import QObject, QPoint, QTimer, QRect, Qt
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import WindowSlot

logger = logging.getLogger(__name__)

class PhysicsController(QObject):
    """
    Decoupled Physics layer for Window interaction.
    - Drag smoothing
    - Velocity calculation (dx/dt)
    - Snap preview & detection
    - Momentum/Inertia after release
    """
    FRICTION = 0.92      # Speed multiplier per frame
    STOP_THRESHOLD = 0.5  # Min speed to stop animation
    SNAP_THRESHOLD = 40   # Distance to screen edge
    
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.window_id = window.window_id
        
        # ── Physics State ──
        self.velocity = QPoint(0, 0)
        self._last_pos = QPoint(0, 0)
        self._last_time = 0.0
        
        # ── Momentum Timer ──
        self._momentum_timer = QTimer(self)
        self._momentum_timer.setInterval(16) # ~60fps
        self._momentum_timer.timeout.connect(self._apply_momentum)
        
        # ── Snap State ──
        self.pending_slot = None
        
        # Subscribe to Events
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_DRAG_START, self._on_drag_start)
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_DRAG_UPDATE, self._on_drag_update)
        EVENT_BUS.subscribe(SystemEvent.REQ_WINDOW_DRAG_END, self._on_drag_end)

    def _on_drag_start(self, payload):
        if payload.data.get("id") != self.window_id: return
        
        self._momentum_timer.stop()
        self.velocity = QPoint(0, 0)
        self._last_pos = self.window.pos()
        self._last_time = time.time()

    def _on_drag_update(self, payload):
        if payload.data.get("id") != self.window_id: return
        
        pos = payload.data.get("pos") # Absolute global position target
        if not pos: return
        
        now = time.time()
        dt = now - self._last_time
        if dt > 0:
            # Calculate velocity: (Current - Last) / dt
            current_pos = self.window.pos()
            dx = (current_pos.x() - self._last_pos.x()) / dt
            dy = (current_pos.y() - self._last_pos.y()) / dt
            
            # Simple EMA for smoothing velocity
            self.velocity = QPoint(
                int(self.velocity.x() * 0.4 + dx * 0.6),
                int(self.velocity.y() * 0.4 + dy * 0.6)
            )
        
        self._last_pos = self.window.pos()
        self._last_time = now
        
        # Move window
        self.window.move(pos)
        
        # ── v1.0 Constraint Guard ──
        from system.window_manager import get_window_manager
        get_window_manager().constrain_to_workspace(self.window)
        
        # Check Snapping
        self._check_snap(payload.data.get("mouse_pos"))

    def _on_drag_end(self, payload):
        if payload.data.get("id") != self.window_id: return

        if self.pending_slot:
            # Apply Snap — compute rect from parent dimensions
            parent_rect = self.window.parent().rect() if self.window.parent() else QRect()
            pw, ph = parent_rect.width(), parent_rect.height()
            slot = self.pending_slot
            if slot == WindowSlot.MAXIMIZED:
                rect = parent_rect
            elif slot == WindowSlot.HALF_LEFT:
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
            else:
                rect = parent_rect
            self.window._snap_ctrl.snap_to_slot(slot, rect)
            self.pending_slot = None
        else:
            # Start Momentum if velocity is high enough
            if abs(self.velocity.x()) > 100 or abs(self.velocity.y()) > 100:
                # Limit initial velocity
                vx = max(-2000, min(2000, self.velocity.x()))
                vy = max(-2000, min(2000, self.velocity.y()))
                self.velocity = QPoint(int(vx * 0.016), int(vy * 0.016)) # Scale for 16ms step
                self._momentum_timer.start()

    def _apply_momentum(self):
        """Physics Step: Newton's Law with Friction."""
        # Update position
        new_pos = self.window.pos() + self.velocity
        
        # Boundary check (don't fly off screen completely)
        parent = self.window.parent()
        if parent:
            prect = parent.rect()
            # If window is outside + margin, bounce or stop
            if new_pos.x() + self.window.width() < 50 or new_pos.x() > prect.width() - 50:
                self.velocity.setX(-self.velocity.x() * 0.5)
            if new_pos.y() < 0 or new_pos.y() > prect.height() - 50:
                self.velocity.setY(-self.velocity.y() * 0.5)

        self.window.move(new_pos)
        
        # Apply Friction
        vx = self.velocity.x() * self.FRICTION
        vy = self.velocity.y() * self.FRICTION
        self.velocity = QPoint(int(vx), int(vy))
        
        # Stop condition
        if abs(self.velocity.x()) < self.STOP_THRESHOLD and abs(self.velocity.y()) < self.STOP_THRESHOLD:
            self._momentum_timer.stop()
            self.velocity = QPoint(0, 0)

    def _check_snap(self, mouse_pos):
        """Ghost rectangle logic with correct coordinate system."""
        if not mouse_pos: return

        parent = self.window.parent()
        if not parent: return

        parent_rect = parent.rect()
        pw, ph = parent_rect.width(), parent_rect.height()
        mx, my = mouse_pos.x(), mouse_pos.y()

        new_slot = None

        # TOP → maximize
        if my <= self.SNAP_THRESHOLD:
            new_slot = WindowSlot.MAXIMIZED
        # LEFT edge
        elif mx <= self.SNAP_THRESHOLD:
            if my >= ph - self.SNAP_THRESHOLD:
                new_slot = WindowSlot.QUARTER_BL
            elif my <= self.SNAP_THRESHOLD + 40:
                new_slot = WindowSlot.QUARTER_TL
            else:
                new_slot = WindowSlot.HALF_LEFT
        # RIGHT edge — use pw from parent rect (fixes snap-right bug)
        elif mx >= pw - self.SNAP_THRESHOLD:
            if my >= ph - self.SNAP_THRESHOLD:
                new_slot = WindowSlot.QUARTER_BR
            elif my <= self.SNAP_THRESHOLD + 40:
                new_slot = WindowSlot.QUARTER_TR
            else:
                new_slot = WindowSlot.HALF_RIGHT

        if new_slot != self.pending_slot:
            self.pending_slot = new_slot
            if self.pending_slot is None:
                EVENT_BUS.emit(SystemEvent.STATE_CHANGED, {
                    "type": "snap_preview_hide",
                    "id": self.window_id,
                })
            else:
                # Emit for UI Preview (Desktop will show the ghost)
                EVENT_BUS.emit(SystemEvent.STATE_CHANGED, {
                    "type": "snap_preview",
                    "id": self.window_id,
                    "slot": self.pending_slot
                })
