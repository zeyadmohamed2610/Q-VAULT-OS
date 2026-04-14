# =============================================================
#  lock_screen.py — Q-Vault OS Lock Screen
#
#  A fullscreen overlay that blocks all interaction.
#  Default PIN: 1234  (printed on screen as a hint)
#
#  Features:
#    • Large live clock
#    • PIN input field (masked)
#    • Error message on wrong PIN
#    • Calls on_unlock() callback when PIN is correct
# =============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt5.QtCore  import Qt, QTimer, QDateTime
from PyQt5.QtGui   import QPainter, QLinearGradient, QColor
from assets import theme


CORRECT_PIN = "1234"   # Change this to whatever you want


class LockScreen(QWidget):
    """
    Fullscreen translucent overlay.
    Sits on top of everything; blocks all interaction until PIN is entered.
    """

    def __init__(self, on_unlock, parent=None):
        super().__init__(parent)
        self.setObjectName("LockScreen")
        self.setStyleSheet(theme.LOCK_SCREEN_STYLE)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Called when the user successfully unlocks
        self._on_unlock = on_unlock
        self._attempts  = 0

        # ── Layout ────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)
        root.setSpacing(0)

        # ── Clock ─────────────────────────────────────────────
        self._clock_lbl = QLabel()
        self._clock_lbl.setObjectName("LockClock")
        self._clock_lbl.setAlignment(Qt.AlignCenter)

        self._date_lbl = QLabel()
        self._date_lbl.setObjectName("LockDate")
        self._date_lbl.setAlignment(Qt.AlignCenter)

        # ── User badge ────────────────────────────────────────
        self._user_lbl = QLabel("👤  user@q-vault")
        self._user_lbl.setObjectName("LockUser")
        self._user_lbl.setAlignment(Qt.AlignCenter)

        # ── PIN input ─────────────────────────────────────────
        self._pin = QLineEdit()
        self._pin.setObjectName("PinInput")
        self._pin.setPlaceholderText("Enter PIN…")
        self._pin.setEchoMode(QLineEdit.Password)
        self._pin.setAlignment(Qt.AlignCenter)
        self._pin.returnPressed.connect(self._check_pin)
        self._pin.setMaxLength(8)

        # ── Unlock button ──────────────────────────────────────
        self._unlock_btn = QPushButton("UNLOCK  →")
        self._unlock_btn.setObjectName("UnlockBtn")
        self._unlock_btn.clicked.connect(self._check_pin)

        # ── Error message (hidden until wrong attempt) ─────────
        self._error_lbl = QLabel("")
        self._error_lbl.setObjectName("LockError")
        self._error_lbl.setAlignment(Qt.AlignCenter)

        # ── Hint label ────────────────────────────────────────
        hint = QLabel("Default PIN: 1234")
        hint.setObjectName("LockHint")
        hint.setAlignment(Qt.AlignCenter)

        # ── Assemble ──────────────────────────────────────────
        root.addStretch(2)
        root.addWidget(self._clock_lbl)
        root.addSpacing(4)
        root.addWidget(self._date_lbl)
        root.addStretch(1)
        root.addWidget(self._user_lbl)
        root.addSpacing(20)

        # Centre the input block
        centre = QHBoxLayout()
        centre.setAlignment(Qt.AlignCenter)
        col = QVBoxLayout()
        col.setSpacing(10)
        col.setAlignment(Qt.AlignCenter)
        col.addWidget(self._pin)
        col.addWidget(self._unlock_btn)
        col.addWidget(self._error_lbl)
        col.addWidget(hint)
        centre.addLayout(col)
        root.addLayout(centre)

        root.addStretch(2)

        # ── Clock timer ───────────────────────────────────────
        self._tick()
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)

    # ── Clock ─────────────────────────────────────────────────
    def _tick(self):
        now = QDateTime.currentDateTime()
        self._clock_lbl.setText(now.toString("HH:mm"))
        self._date_lbl.setText(now.toString("dddd, MMMM d"))

    # ── Custom paint — dark gradient overlay ──────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(5,  8,  12, 245))
        grad.setColorAt(0.5, QColor(10, 18, 30, 240))
        grad.setColorAt(1.0, QColor(5,  8,  12, 245))
        painter.fillRect(self.rect(), grad)

    # ── PIN check ─────────────────────────────────────────────
    def _check_pin(self):
        entered = self._pin.text()

        if entered == CORRECT_PIN:
            self._error_lbl.setText("")
            self._pin.clear()
            self._attempts = 0
            if self._on_unlock:
                self._on_unlock()
        else:
            self._attempts += 1
            self._pin.clear()

            if self._attempts >= 3:
                self._error_lbl.setText(
                    f"⚠  {self._attempts} failed attempts. Try: 1234"
                )
            else:
                self._error_lbl.setText("✗  Wrong PIN. Try again.")

            # Shake the input field for visual feedback
            self._shake()

    def _shake(self):
        """Simple left-right shake animation on wrong PIN."""
        orig_x = self._pin.x()
        offsets = [6, -6, 4, -4, 2, -2, 0]
        self._shake_step(offsets, orig_x)

    def _shake_step(self, offsets: list, orig_x: int):
        if not offsets:
            return
        off = offsets[0]
        self._pin.move(self._pin.x() + off, self._pin.y())
        QTimer.singleShot(
            40,
            lambda: self._shake_step(offsets[1:], orig_x)
        )

    # ── Intercept all key presses while locked ────────────────
    def keyPressEvent(self, event):
        # Don't let any key event pass through the lock screen
        # (except to the PIN input which handles its own input)
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._pin.setFocus()
        self._pin.clear()
        self._error_lbl.setText("")
