from assets.theme import *
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont


class LockScreen(QWidget):
    """
    v2.0 Two-Phase Lock Screen.
    
    Phase 1: Clock-only (ambient). Any keypress/click reveals auth.
    Phase 2: Auth card fades in. User enters passphrase to unlock.
    """

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self._auth_revealed = False
        self._is_unlocking = False

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget#LockScreen {{
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:1,
                    fx:0.5, fy:0.5,
                    stop:0 {THEME['bg_dark']}, stop:1 {THEME['bg_black']}
                );
            }}
            QLabel {{ color: white; background: transparent; font-family: 'Outfit', 'Segoe UI', sans-serif; }}
            QLineEdit {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(0, 230, 255, 0.2);
                border-radius: 20px;
                color: white;
                padding: 0 20px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {THEME['primary_glow']};
                background: rgba(0, 230, 255, 0.08);
            }}
            QPushButton#BtnUnlock {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary_glow']}, stop:1 {THEME['primary_soft']});
                border-radius: 20px;
                color: black;
                font-weight: bold;
                font-size: 13px;
                transition: all 0.3s ease;
            }}
            QPushButton#BtnUnlock:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['primary_glow']}, stop:1 {THEME['primary_glow']});
            }}
            QPushButton#BtnUnlock:pressed {{
                background: {THEME['primary_soft']};
            }}
        """)
        self.setObjectName("LockScreen")
        self.setFocusPolicy(Qt.StrongFocus)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ───── CLOCK STACK ─────
        self.clock_container = QWidget()
        clock_layout = QVBoxLayout(self.clock_container)
        clock_layout.setSpacing(0)
        
        self.lbl_clock = QLabel()
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setFont(QFont("Segoe UI Light", 72))
        
        self.lbl_date = QLabel()
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_date.setStyleSheet("color: rgba(0, 230, 255, 0.6); font-size: 16px; letter-spacing: 2px;")

        self.lbl_hint = QLabel("Press any key to unlock")
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        self.lbl_hint.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 12px; margin-top: 40px;")
        
        clock_layout.addWidget(self.lbl_clock)
        clock_layout.addWidget(self.lbl_date)
        clock_layout.addWidget(self.lbl_hint)
        main_layout.addWidget(self.clock_container)
        main_layout.addSpacing(30)
        
        # Clock Opacity effect for Phase 1 fade out
        self._clock_opacity = QGraphicsOpacityEffect(self.clock_container)
        self._clock_opacity.setOpacity(1.0)
        self.clock_container.setGraphicsEffect(self._clock_opacity)

        # ───── AUTH STACK (hidden initially) ─────
        self.auth_container = QWidget()
        self.auth_container.setFixedWidth(340)
        auth_layout = QVBoxLayout(self.auth_container)
        auth_layout.setSpacing(15)

        # Biometric Icon
        self.scan_lbl = QLabel("󱗑")
        self.scan_lbl.setAlignment(Qt.AlignCenter)
        self.scan_lbl.setFont(QFont("Segoe UI", 48))
        self.scan_lbl.setStyleSheet(f"color: {THEME['primary_glow']};")
        
        lbl_user = QLabel(f"Welcome back, {username.upper()}")
        lbl_user.setAlignment(Qt.AlignCenter)
        lbl_user.setStyleSheet(f"font-weight: bold; font-size: 14px; letter-spacing: 2px; color: {THEME['text_muted']};")

        self.pw_field = QLineEdit()
        self.pw_field.setEchoMode(QLineEdit.Password)
        self.pw_field.setPlaceholderText("Enter secure passphrase...")
        self.pw_field.setFixedHeight(40)
        self.pw_field.setAlignment(Qt.AlignCenter)
        self.pw_field.returnPressed.connect(self._try_unlock)

        self.btn_unlock = QPushButton("AUTHENTICATE")
        self.btn_unlock.setObjectName("BtnUnlock")
        self.btn_unlock.setFixedHeight(40)
        self.btn_unlock.clicked.connect(self._try_unlock)

        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setStyleSheet(f"color: {THEME['error_bright']}; font-size: 11px;")

        auth_layout.addWidget(self.scan_lbl)
        auth_layout.addWidget(lbl_user)
        auth_layout.addWidget(self.pw_field)
        auth_layout.addWidget(self.btn_unlock)
        auth_layout.addWidget(self.lbl_error)
        
        main_layout.addWidget(self.auth_container, alignment=Qt.AlignCenter)

        # ── Start with auth HIDDEN ───────────────────────────────
        self._auth_opacity = QGraphicsOpacityEffect(self.auth_container)
        self._auth_opacity.setOpacity(0.0)
        self.auth_container.setGraphicsEffect(self._auth_opacity)
        self.auth_container.setVisible(False)

        # ── Wire to AuthManager ──────────────────────────────────
        from system.auth_manager import get_auth_manager
        self._auth = get_auth_manager()
        self._auth.state_changed.connect(self._on_auth_state_changed)
        self._auth.login_failed.connect(self._on_fail)

        # ── Timers ───────────────────────────────────────────────
        self._tick()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)

    def closeEvent(self, e):
        """Explicitly disconnect signals to prevent ghost calls if deleted."""
        try:
            self._auth.state_changed.disconnect(self._on_auth_state_changed)
            self._auth.login_failed.disconnect(self._on_fail)
        except Exception:
            pass
        super().closeEvent(e)

    # ── Phase 1: Clock-only ──────────────────────────────────────

    def _tick(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime()
        self.lbl_clock.setText(now.toString("h:mm AP"))
        self.lbl_date.setText(now.toString("dddd, MMMM d").upper())

    def keyPressEvent(self, event):
        """Phase 1 -> Phase 2: Any keypress reveals auth card."""
        if not self._auth_revealed:
            self._reveal_auth()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Phase 1 -> Phase 2: Any click reveals auth card."""
        if not self._auth_revealed:
            self._reveal_auth()
            return
        super().mousePressEvent(event)

    def _reveal_auth(self):
        """Fade out clock, fade in and slide up the auth card."""
        from PyQt5.QtCore import QParallelAnimationGroup, QPoint
        self._auth_revealed = True
        self.lbl_hint.hide()
        self.auth_container.setVisible(True)

        self._anim_group = QParallelAnimationGroup(self)

        # 1. Fade out clock (ambient blur feel)
        anim_clock = QPropertyAnimation(self._clock_opacity, b"opacity")
        anim_clock.setDuration(400)
        anim_clock.setStartValue(1.0)
        anim_clock.setEndValue(0.15)
        anim_clock.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_group.addAnimation(anim_clock)

        # 2. Fade in Auth card
        anim_auth = QPropertyAnimation(self._auth_opacity, b"opacity")
        anim_auth.setDuration(500)
        anim_auth.setStartValue(0.0)
        anim_auth.setEndValue(1.0)
        anim_auth.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_group.addAnimation(anim_auth)

        # 3. Slide Auth card up slightly
        anim_slide = QPropertyAnimation(self.auth_container, b"pos")
        anim_slide.setDuration(500)
        end_pos = self.auth_container.pos()
        start_pos = end_pos + QPoint(0, 30)
        anim_slide.setStartValue(start_pos)
        anim_slide.setEndValue(end_pos)
        anim_slide.setEasingCurve(QEasingCurve.OutBack)
        self._anim_group.addAnimation(anim_slide)

        self._anim_group.start()

        # Step 2 requirement: Auto focus immediately after reveal animation
        QTimer.singleShot(450, self.pw_field.setFocus)

    # ── Phase 2: Authentication ──────────────────────────────────

    def _try_unlock(self):
        if self._is_unlocking:
            return
        pw = self.pw_field.text()
        if not pw:
            self._shake_auth()
            return

        self._is_unlocking = True
        self.btn_unlock.setEnabled(False)
        self.pw_field.setEnabled(False)
        self.btn_unlock.setText("VERIFYING IDENTITY...")
        self.scan_lbl.setStyleSheet(f"color: {THEME['warning']};")

        # Pulse animation for scan icon
        self._scan_opacity = QGraphicsOpacityEffect(self.scan_lbl)
        self.scan_lbl.setGraphicsEffect(self._scan_opacity)
        self._pulse_anim = QPropertyAnimation(self._scan_opacity, b"opacity")
        self._pulse_anim.setDuration(400)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.3)
        self._pulse_anim.setLoopCount(2)
        self._pulse_anim.start()

        # Biometric delay then request unlock via AuthManager
        QTimer.singleShot(800, lambda: self._auth.request_unlock(pw))

    # ── AuthManager callbacks ────────────────────────────────────

    def _on_auth_state_changed(self, new_state: str, old_state: str):
        if old_state == "authenticating" and new_state == "logged_in":
            # Success — stop pulse, show green, AppController switches screen
            self._stop_pulse()
            self.scan_lbl.setStyleSheet(f"color: {THEME['success']};")
            self.btn_unlock.setText("ACCESS GRANTED")

    def _on_fail(self, error_dict: dict):
        self._is_unlocking = False
        self._stop_pulse()

        self.btn_unlock.setEnabled(True)
        self.pw_field.setEnabled(True)
        self.btn_unlock.setText("AUTHENTICATE")
        self.scan_lbl.setStyleSheet(f"color: {THEME['error_bright']};")
        self.lbl_error.setText("ACCESS DENIED")
        
        # Step 3 requirement: Red glow border on fail
        self.pw_field.setStyleSheet(f"""
            border: 1px solid {THEME['error_bright']}; 
            background: rgba(255, 51, 51, 0.05);
            color: {THEME['error_bright']};
        """)
        self._shake_auth()
        self.pw_field.clear()
        self.pw_field.setFocus()

        # Revert style after 1 second
        QTimer.singleShot(1000, lambda: self.pw_field.setStyleSheet(""))

    def _stop_pulse(self):
        if hasattr(self, "_pulse_anim"):
            self._pulse_anim.stop()
        if hasattr(self, "_scan_opacity"):
            self._scan_opacity.setOpacity(1.0)

    # ── Animations ───────────────────────────────────────────────

    def _shake_auth(self):
        """Physical feedback: Shake the auth container on error."""
        curr = self.auth_container.pos()
        self.auth_container.move(curr.x() + 10, curr.y())
        QTimer.singleShot(50, lambda: self.auth_container.move(curr.x() - 10, curr.y()))
        QTimer.singleShot(100, lambda: self.auth_container.move(curr))

    # ── Reset on show ────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        # Reset to Phase 1 (clock-only)
        self._auth_revealed = False
        self._is_unlocking = False
        self.auth_container.setVisible(False)
        self._auth_opacity.setOpacity(0.0)
        self.lbl_hint.show()
        self.lbl_error.setText("")
        self.pw_field.clear()
        self.btn_unlock.setText("AUTHENTICATE")
        self.btn_unlock.setEnabled(True)
        self.pw_field.setEnabled(True)
        self.scan_lbl.setStyleSheet(f"color: {THEME['primary_glow']};")
        self._clock_opacity.setOpacity(1.0)
        self.setFocus()
