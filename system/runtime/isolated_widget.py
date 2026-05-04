import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QPushButton
from PyQt5.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, pyqtProperty, QTimer
from PyQt5.QtGui import QColor, QPalette

from system.runtime.app_controller_isolated import IsolatedAppController, RuntimeState
from assets.theme import THEME

logger = logging.getLogger("runtime.isolated_widget")

class StatusOverlay(QFrame):
    """Semi-transparent status layer with smooth transitions and recovery actions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.hide()
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setSpacing(15)
        
        self.label = QLabel("SYSTEM STATE")
        self.label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.layout.addWidget(self.label)
        
        self.reason_label = QLabel("")
        self.reason_label.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.7);")
        self.layout.addWidget(self.reason_label)

        # ✕ Close Button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setStyleSheet(f"background: transparent; color: {THEME['text_disabled']}; font-size: 18px; border: none;")
        self.close_btn.setCursor(Qt.PointingHandCursor)

        # 🟢 Phase 1.2: Restart Button
        self.restart_btn = QPushButton("RESTART APPLICATION")
        self.restart_btn.setFixedSize(220, 40)
        self.restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 23, 68, 0.2);
                border: 1px solid {THEME['accent_error']};
                color: {THEME['accent_error']};
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent_error']};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {THEME['error_soft']};
            }}
        """)
        self.restart_btn.hide()
        self.layout.addWidget(self.restart_btn)
        
        # Opacity Animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(150) # 🟢 Standardized Phase 1.2.1
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Pulsing Animation for Booting
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._toggle_pulse)
        self._pulse_up = True

    def _toggle_pulse(self):
        op = self.opacity_effect.opacity()
        if self._pulse_up:
            self.opacity_effect.setOpacity(op - 0.05)
            if op <= 0.4: self._pulse_up = False
        else:
            self.opacity_effect.setOpacity(op + 0.05)
            if op >= 1.0: self._pulse_up = True

    def show_state(self, state, reason=""):
        colors = {
            RuntimeState.BOOTING: "rgba(0, 0, 0, 0.7)",
            RuntimeState.RUNNING: "transparent",
            RuntimeState.CONGESTED: "rgba(255, 214, 0, 0.15)",
            RuntimeState.THROTTLED: "rgba(255, 109, 0, 0.2)",
            RuntimeState.RECOVERING: "rgba(118, 255, 3, 0.15)",
            RuntimeState.TERMINATED: "rgba(10, 10, 10, 0.85)",
            RuntimeState.BOOT_FAILED: "rgba(10, 10, 10, 0.9)"
        }
        
        # Identity bar for states
        accents = {
            RuntimeState.TERMINATED: "#ff1744",
            RuntimeState.BOOT_FAILED: "#ff1744",
            RuntimeState.CONGESTED: "#ffd600",
            RuntimeState.THROTTLED: "#ff6d00"
        }
        
        text = {
            RuntimeState.BOOTING: "INITIALIZING SANDBOX...",
            RuntimeState.RUNNING: "",
            RuntimeState.CONGESTED: "OPTIMIZING LOAD...", # User-friendly term
            RuntimeState.THROTTLED: "RESOURCE LIMIT REACHED",
            RuntimeState.RECOVERING: "RESTORED",
            RuntimeState.TERMINATED: "PROCESS STOPPED",
            RuntimeState.BOOT_FAILED: "INITIALIZATION FAILED"
        }
        
        color = colors.get(state, "transparent")
        accent = accents.get(state, "transparent")
        self.setStyleSheet(f"""
            background-color: {color}; 
            border-top: 2px solid {accent};
            border-radius: 4px;
        """)
        
        display_text = text.get(state, "")
        self.label.setText(display_text)
        self.label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {accent if accent != 'transparent' else 'white'};")
        
        self.reason_label.setText(reason if state in [RuntimeState.TERMINATED, RuntimeState.BOOT_FAILED] else "")
        
        # Toggle Restart Button
        if state in [RuntimeState.TERMINATED, RuntimeState.BOOT_FAILED]:
            self.restart_btn.show()
        else:
            self.restart_btn.hide()

        # Handle Animations/Timers
        if state == RuntimeState.BOOTING:
            self.show()
            self.opacity_effect.setOpacity(1.0)
            self.pulse_timer.start(50)
        else:
            self.pulse_timer.stop()
            if state == RuntimeState.RUNNING:
                self.anim.setStartValue(self.opacity_effect.opacity())
                self.anim.setEndValue(0.0)
                self.anim.finished.connect(self.hide)
                self.anim.start()
            else:
                self.show()
                self.anim.setStartValue(self.opacity_effect.opacity())
                self.anim.setEndValue(1.0)
                try: self.anim.finished.disconnect()
                except Exception:
                    pass
                self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.close_btn.move(self.width() - 40, 10)

class MetricsBadge(QFrame):
    """Smart metrics observer. Shows human-readable status, expands for Pro data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 24)
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(0, 229, 255, 0.3);
            border-radius: 12px;
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.label = QLabel("Optimal")
        self.label.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 11px; font-weight: bold;")
        self.layout.addWidget(self.label)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(150) # 🟢 Standardized Phase 1.2.1
        
        self._detailed = False
        self._current_metrics = (0, 0, 100)

    def update_metrics(self, hz, qsize, trust):
        self._current_metrics = (hz, qsize, trust)
        if not self._detailed:
            # Smart Logic Mapping (Phase 1.2)
            if qsize > 50: text, color = "Busy", "#ffd600"
            elif qsize > 20: text, color = "Heavy Load", "#ff6d00"
            elif trust < 70: text, color = "Caution", "#ff6d00"
            elif hz > 150: text, color = "Hyper-Fast", "#00e5ff"
            else: text, color = "Optimal", "#00e5ff"
            
            self.label.setText(text)
            self.label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        else:
            self.label.setText(f"{int(hz)}Hz | Q:{qsize} | T:{trust}")
            self.label.setStyleSheet(f"color: {THEME['primary_glow']}; font-size: 9px; font-family: monospace;")

    def enterEvent(self, event):
        self._detailed = True
        self.setFixedSize(160, 24)
        self.opacity_effect.setOpacity(1.0)
        self.update_metrics(*self._current_metrics)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._detailed = False
        self.setFixedSize(100, 24)
        self.update_metrics(*self._current_metrics)
        super().leaveEvent(event)

    def set_focus_mode(self, active: bool):
        """🟢 Phase 1.2: Immersive Focus Logic."""
        self.fade_anim.stop()
        self.fade_anim.setEndValue(0.1 if active else 1.0)
        self.fade_anim.start()

    def setOpacity(self, value):
        self.opacity_effect.setOpacity(value)

class IsolatedAppWidget(QWidget):
    """
    Top-Tier UX Layer for isolated applications (v1.0 Stable).
    Manages loading, recovery, and snappy transitions.
    """
    def __init__(self, app_id, module_path, class_name, secure_api=None, parent=None, boot_timeout=5.0):
        super().__init__(parent)
        self.app_id = app_id
        self.secure_api = secure_api  # RC-2 fix: store for proxy subclass access
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300) # ── SYSTEMIC FIX: Prevent collapse ──
        
        # 1. Initialize Controller
        instance_id = secure_api.instance_id if secure_api else "unknown"
        self.controller = IsolatedAppController(app_id, instance_id, secure_api, boot_timeout=boot_timeout)
        
        # 2. UI Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame(self)
        self.container.setObjectName("AppContainerFrame")
        self.container.setStyleSheet(f"QFrame#AppContainerFrame {{ background-color: rgba(11, 22, 45, 0.95); border-radius: 8px; }}")
        
        # ── FIXED: Container must have its own layout to host app UI ──
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        self.main_layout.addWidget(self.container)
        
        # Status Overlays
        self.overlay = StatusOverlay(self.container)
        self.badge = MetricsBadge(self)
        self.badge.hide() # Hidden globally per user request
        
        # 3. Connect Logic
        self.controller.state_changed.connect(self._on_state_changed)
        self.controller.metrics_updated.connect(self.badge.update_metrics)
        self.controller.crashed.connect(self._on_crash)
        self.controller.event_received.connect(self.handle_event)
        
        # 🟢 Phase 1.2: Functional Restart & Close
        self.overlay.restart_btn.clicked.connect(self.controller.restart)
        self.overlay.close_btn.clicked.connect(self._request_close)
        
        # 4. Launch
        self.controller.start(module_path, class_name)

    def set_content(self, widget):
        """RC-1 fix: Embed a UI widget inside the isolated container frame."""
        self.container_layout.addWidget(widget)
        widget.show()

    def _on_state_changed(self, state: RuntimeState):
        self.overlay.show_state(state)
        
        # ── Phase 3.6.3: Visual Hygiene ──
        self.badge.hide() # Hidden globally per user request

        # Update badge border color
        colors = {
            RuntimeState.BOOTING: "rgba(100, 100, 100, 0.5)",
            RuntimeState.RUNNING: "rgba(0, 229, 255, 0.3)",
            RuntimeState.CONGESTED: "#ffd600",
            RuntimeState.THROTTLED: "#ff6d00",
            RuntimeState.RECOVERING: "#76ff03",
            RuntimeState.TERMINATED: "#ff1744",
            RuntimeState.BOOT_FAILED: "#ff1744"
        }
        color = colors.get(state, "rgba(0, 229, 255, 0.3)")
        self.badge.setStyleSheet(f"background-color: rgba(0, 0, 0, 0.6); border: 1px solid {color}; border-radius: 12px;")

    def _on_crash(self, reason: str):
        # We handle state update via the controller's state_changed signal now, 
        # but reason is explicitly sent here.
        pass

    def setOpacity(self, value):
        self.opacity_effect.setOpacity(value)

    def focusInEvent(self, event):
        self.badge.setOpacity(1.0) # Full opacity when active
        self.badge.set_focus_mode(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.badge.setOpacity(0.4) # Dim when inactive
        self.badge.set_focus_mode(False)
        super().focusOutEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.container.size())
        # Move badge to bottom-right
        self.badge.move(self.width() - self.badge.width() - 10, self.height() - self.badge.height() - 10)
        self.badge.raise_()

    def call_remote(self, method, *args, callback=None, **kwargs):
        self.controller.call_remote(method, *args, callback=callback, **kwargs)

    def handle_event(self, event, data):
        """Default handler for IPC events. Override in subclasses."""
        pass

    def _request_close(self):
        """Signals the parent OSWindow to close this app instance."""
        # This will trigger the standard OSWindow animation and cleanup
        if self.parent() and hasattr(self.parent(), "parent"):
            # The parent of self.container is self (IsolatedAppWidget)
            # The parent of self (IsolatedAppWidget) is the OSWindow (usually)
            # Or we can just find the ancestor that is an OSWindow
            p = self.parent()
            while p:
                if p.objectName() == "OSWindow" and hasattr(p, "close_window"):
                    p.close_window()
                    return
                p = p.parent()

    def closeEvent(self, event):
        self.controller.stop()
        super().closeEvent(event)
