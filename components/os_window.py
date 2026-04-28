from assets.theme import *
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QRect, pyqtSignal, QTimer, QPointF, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from core.event_bus import EVENT_BUS, SystemEvent
from system.window_manager import get_window_manager, WindowState, WindowSlot, SnapZone

logger = logging.getLogger(__name__)

class OSTitleBar(QWidget):
    """Custom title bar to handle double-clicks targeting the OSWindow."""
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class OSWindow(QWidget):
    """
    v1.4 Modern Shell Window.
    Handles Slot-based Tiling, Zero-Lag Snap detection, and Focus Physics.
    """
    SNAP_THRESHOLD = 40

    def __init__(self, window_id: str, title: str, content_widget: QWidget, parent=None):
        super().__init__(parent)
        from assets.theme import SPACE_MD, RADIUS_MD, MOTION_SNAPPY, SPACE_XS
        self.window_id = window_id
        self.is_minimized = False

        self.setObjectName("OSWindow")
        # FORCE: Treat as widget inside workspace, not floating OS window
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ── GEOM AUTHORITY ──
        self._is_applying_geometry = False
        self._registered = False
        self._internal_move = super().move 
        self._internal_resize = super().resize
        self._internal_set_geometry = super().setGeometry

        self._setup_ui(window_id, title, content_widget)

    def move(self, *args):
        if self._is_applying_geometry:
            return self._internal_move(*args)
            
        if len(args) == 1 and isinstance(args[0], QPoint):
            x, y = args[0].x(), args[0].y()
        elif len(args) == 2:
            x, y = args[0], args[1]
        else: return
        get_window_manager().request_geometry(self.window_id, x, y, self.width(), self.height())

    def resize(self, *args):
        if self._is_applying_geometry:
            return self._internal_resize(*args)
            
        if len(args) == 1 and isinstance(args[0], QSize):
            w, h = args[0].width(), args[0].height()
        elif len(args) == 2:
            w, h = args[0], args[1]
        else: return
        get_window_manager().request_geometry(self.window_id, self.x(), self.y(), w, h)

    def setGeometry(self, *args):
        if self._is_applying_geometry:
            return self._internal_set_geometry(*args)
            
        if len(args) == 1 and isinstance(args[0], QRect):
            x, y, w, h = args[0].x(), args[0].y(), args[0].width(), args[0].height()
        elif len(args) == 4:
            x, y, w, h = args
        else: return
        get_window_manager().request_geometry(self.window_id, x, y, w, h)

    def show(self):
        """Enforce creation pipeline: No show without registration."""
        if not self._registered:
            logger.warning(f"[WINDOW] Blocked show() for {self.window_id}: Not registered yet.")
            return
        super().show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._is_applying_geometry:
            get_window_manager().constrain_to_workspace(self)

    def _apply_geometry(self, x, y, w, h):
        """Internal backdoor with recursion guard."""
        self._is_applying_geometry = True
        try:
            self._internal_set_geometry(x, y, w, h)
        finally:
            self._is_applying_geometry = False
        
    def _setup_ui(self, window_id: str, title: str, content_widget: QWidget):
        from assets.theme import SPACE_MD, RADIUS_MD, MOTION_SNAPPY, SPACE_XS
        # Margin and Layout using Design Tokens
        self._margin = SPACE_MD
        self.setMinimumSize(400, 300) # ── SYSTEMIC FIX: Prevent collapse ──
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(self._margin, self._margin, self._margin, self._margin)
        main_layout.setSpacing(0)

        # ───── TITLE BAR ─────
        self.title_bar = OSTitleBar()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(30)
        self.title_bar.double_clicked.connect(lambda: self._snap_ctrl.toggle_maximize())
        
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(SPACE_XS, 0, SPACE_XS // 2, 0)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("TitleLabel")
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # ───── CONTROLS ─────
        self.btn_min = QPushButton("‒")
        self.btn_min.setObjectName("BtnMinimize")
        self.btn_min.setFixedSize(24, 24)

        self.btn_max = QPushButton("□")
        self.btn_max.setObjectName("BtnMaximize")
        self.btn_max.setFixedSize(24, 24)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.setFixedSize(24, 24)

        self.btn_min.clicked.connect(self.minimize_window)
        self.btn_max.clicked.connect(lambda: self._snap_ctrl.toggle_maximize())
        self.btn_close.clicked.connect(self.close_window)

        # ───── Control Styling ─────
        btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {THEME['text_dim']};
                font-family: 'Segoe UI';
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {THEME['hover_subtle']}; color: white; }}
            #BtnClose:hover {{ background: {THEME['accent_error']}; color: white; }}
        """
        self.btn_min.setStyleSheet(btn_style)
        self.btn_max.setStyleSheet(btn_style)
        self.btn_close.setStyleSheet(btn_style)

        tb_layout.addWidget(self.lbl_title)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_min)
        tb_layout.addWidget(self.btn_max)
        tb_layout.addWidget(self.btn_close)

        # ───── CONTENT AREA ─────
        self.content_widget = content_widget
        content_container = QWidget()
        content_container.setObjectName("WindowContent")
        content_container.setAttribute(Qt.WA_StyledBackground, True)
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        if content_widget is not None:
            self.content_layout.addWidget(content_widget)

        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(content_container, stretch=1)
        
        # ── PHYSICS CONTROLLER (Temporarily Disabled for Stability) ──
        self.physics_controller = None

        # ── ANIMATION CONTROLLER (v2.1 Refinement) ──
        from components.window_animation_controller import WindowAnimationController
        self.anim_controller = WindowAnimationController(self)

        # ── DECOMPOSED HANDLERS (v2.0 God Object Fix) ──
        from components.focus_manager import FocusManager
        from components.snap_controller import SnapController
        from components.window_drag_handler import WindowDragHandler
        self._focus_mgr = FocusManager(self)
        self._snap_ctrl = SnapController(self)
        self._drag_handler = WindowDragHandler(self, self._snap_ctrl)

        # Subscribe to physics facts (delegates to SnapController)
        EVENT_BUS.subscribe(SystemEvent.EVT_WINDOW_SNAPPED, self._snap_ctrl.on_physics_snap)

        # ── v2.2 Init Debug ──
        logger.info(f"[WINDOW_CREATED] {window_id} | Title: {title} | Size: {self.size()} | Pos: {self.pos()}")


    def _apply_move(self, x, y):
        self._is_applying_geometry = True
        try:
            self._internal_move(x, y)
        finally:
            self._is_applying_geometry = False

    # ── BACKWARD-COMPATIBLE PROPERTIES (delegate to handlers) ──

    @property
    def _is_active(self):
        return self._focus_mgr.is_active

    def set_active_state(self, is_active: bool):
        """Facade — delegates to FocusManager."""
        self._focus_mgr.set_active_state(is_active)

    def mousePressEvent(self, event):
        # ── v2.2 Focus Layer (stays in OSWindow — UI concern) ──
        self.raise_()
        self.activateWindow()
        get_window_manager().focus_window(self.window_id)
        # Delegate drag logic to handler
        self._drag_handler.on_press(event)

    def mouseMoveEvent(self, event):
        self._drag_handler.on_move(event)

    def mouseReleaseEvent(self, event):
        self._drag_handler.on_release(event)

    def keyPressEvent(self, event):
        # v1.4 Shortcuts (Super + Arrows) — delegated to SnapController
        if event.modifiers() & Qt.MetaModifier or event.modifiers() & Qt.AltModifier:
            p = self.parent().rect() if self.parent() else QRect()
            if self._snap_ctrl.handle_key_snap(event.key(), p):
                event.accept()
                return

        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        from assets.theme import RADIUS_MD
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRect(self._margin, self._margin, self.width() - 2*self._margin, self.height() - 2*self._margin)
        if not self._is_active:
            painter.setPen(QColor(0, 230, 255, 40))
            painter.drawRoundedRect(rect, RADIUS_MD, RADIUS_MD)
            painter.fillRect(rect, QColor(0, 0, 0, 100))
            return
        painter.setPen(QColor(THEME["primary_glow"]))
        painter.drawRoundedRect(rect, RADIUS_MD, RADIUS_MD)

    def _final_close(self):
        if getattr(self, "_is_destroyed", False):
            return
        self._is_destroyed = True
        
        # 1. Clean up controller subscriptions
        if hasattr(self, "anim_controller"):
            self.anim_controller.cleanup()
            
        from system.runtime_manager import RUNTIME_MANAGER
        # Kill handles stopping logic and unlinking from WM
        RUNTIME_MANAGER.kill(self.window_id)
        # Physically purge from registry to prevent memory leak
        RUNTIME_MANAGER.unregister(self.window_id)
        
        # Break Circular References to ensure Python GC can reclaim
        if hasattr(self, "_drag_handler"): del self._drag_handler
        if hasattr(self, "_snap_ctrl"): del self._snap_ctrl
        if hasattr(self, "_focus_manager"): del self._focus_manager
        if hasattr(self, "anim_controller"): del self.anim_controller
        
        # Break signal cycles
        try: self.btn_max.clicked.disconnect()
        except: pass
        try: self.title_bar.double_clicked.disconnect()
        except: pass
        
        try:
            self.deleteLater()
        except RuntimeError:
            pass

    def minimize_window(self):
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.REQ_WINDOW_MINIMIZE, {"id": self.window_id}, source="OSWindow")

    def close_window(self):
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE, {"id": self.window_id}, source="OSWindow")

    # _on_window_event removed - logic moved to WindowAnimationController

    # ── QUARANTINE OVERLAY (Phase 8 + 9) ──────────────────────────
    def show_quarantine_overlay(self, trust_score: int, reason: str):
        """
        Freeze execution visually with a cinematic Physics-based drop.
        The overlay is a FREE-FLOATING child of the OSWindow (NOT inside a QLayout)
        so that MotionController can drive its geometry directly via QPropertyAnimation.
        """
        # 1. Disable content (keep visible underneath — overlay covers it)
        self.content_widget.setEnabled(False)

        # 2. Build the overlay frame as a direct child of self
        quarantine_frame = QWidget(self)
        quarantine_frame.setAttribute(Qt.WA_StyledBackground, True)
        quarantine_frame.setStyleSheet(f"background-color: rgba(10, 10, 15, 240); border-top: 2px solid {THEME['error_bright']};")
        quarantine_frame.raise_()

        qlayout = QVBoxLayout(quarantine_frame)
        qlayout.setAlignment(Qt.AlignCenter)
        qlayout.setSpacing(12)

        icon_lbl = QLabel("🔒")
        icon_lbl.setFont(QFont("Segoe UI", 52))
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")

        title_lbl = QLabel("APPLICATION QUARANTINED")
        title_lbl.setStyleSheet(
            f"color: {THEME['error_bright']}; font-size: 18px; font-weight: bold;"
            " letter-spacing: 2px; background: transparent;"
        )
        title_lbl.setAlignment(Qt.AlignCenter)

        score_color = THEME["danger_score"] if trust_score < 10 else THEME["warning_score"]
        reason_lbl = QLabel(
            f"Trust Score: <b style='color:{score_color}'>{trust_score}</b> / 100"
            f"<br><small style='color:#888;'>{reason}</small>"
        )
        reason_lbl.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 13px; background: transparent;")
        reason_lbl.setTextFormat(Qt.RichText)
        reason_lbl.setAlignment(Qt.AlignCenter)

        btn_close = QPushButton("⏏  FORCE CLOSE")
        btn_close.setFixedSize(160, 38)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {THEME['error_bright']};
                color: {THEME['error_bright']};
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 51, 51, 0.18);
                color: {THEME['error_soft']};
            }}
        """)
        btn_close.clicked.connect(self.close_window)

        qlayout.addStretch()
        qlayout.addWidget(icon_lbl)
        qlayout.addWidget(title_lbl)
        qlayout.addWidget(reason_lbl)
        qlayout.addSpacing(12)
        qlayout.addWidget(btn_close, alignment=Qt.AlignCenter)
        qlayout.addStretch()

        # 3. Size to cover the entire OSWindow
        final_rect = self.rect()
        quarantine_frame.resize(final_rect.width(), final_rect.height())

        # 4. Lock title bar controls
        self.btn_max.setDisabled(True)
        self.btn_min.setDisabled(True)

        # 5. Trigger the cinematic drop
        from components.motion import MotionController
        MotionController.quarantine_drop(quarantine_frame, final_rect)