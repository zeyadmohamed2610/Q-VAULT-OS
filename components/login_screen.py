# =============================================================
#  login_screen.py - Q-Vault OS  |  Login Screen
# =============================================================

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from assets import theme
from core.system_state import STATE
from system.session_manager import SESSION


STYLE = f"""
    QWidget#LoginScreen {{
        background: transparent;
    }}
    QFrame#LoginCard {{
        background: rgba(9, 17, 29, 232);
        border: 1px solid {theme.BORDER_BRIGHT};
        border-radius: 18px;
    }}
    QLabel#LogoLabel {{
        background: transparent;
        padding-bottom: 4px;
    }}
    QLabel#BrandTitle {{
        color: {theme.ACCENT_ICE};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 22px;
        font-weight: bold;
        letter-spacing: 1px;
        background: transparent;
    }}
    QLabel#TagLine {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
    }}
    QLabel#FieldLabel {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
    }}
    QLineEdit#LoginField {{
        background: rgba(4, 9, 19, 220);
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 14px;
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 8px;
        padding: 10px 12px;
        min-width: 360px;
    }}
    QLineEdit#LoginField:focus {{
        border: 1px solid {theme.BORDER_BRIGHT};
    }}
    QPushButton#LoginBtn {{
        background: {theme.ACCENT_CYAN};
        color: {theme.BG_DARK};
        border: none;
        border-radius: 8px;
        padding: 11px 0;
        font-size: 13px;
        font-weight: bold;
        font-family: 'Consolas', monospace;
        min-width: 360px;
    }}
    QPushButton#LoginBtn:hover {{
        background: #43e0ff;
    }}
    QPushButton#LoginBtn:pressed {{
        background: #0ab6e2;
    }}
    QLabel#ErrorLabel {{
        color: {theme.ACCENT_RED};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
        min-height: 16px;
    }}
    QLabel#HintLabel {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 10px;
        background: rgba(4, 9, 19, 150);
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 8px;
        padding: 8px 12px;
    }}
    QLabel#FakeLabel {{
        color: {theme.ACCENT_AMBER};
        font-family: 'Consolas', monospace;
        font-size: 10px;
        background: transparent;
        padding: 2px 0;
    }}
"""


class LoginScreen(QWidget):
    login_success = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginScreen")
        self.setStyleSheet(STYLE)

        self._lockout_timer = QTimer(self)
        self._lockout_timer.timeout.connect(self._update_lockout)

        self._build_ui()

    def _build_ui(self):
        page = QVBoxLayout(self)
        page.setContentsMargins(24, 24, 24, 24)
        page.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(520)
        col = QVBoxLayout(card)
        col.setContentsMargins(36, 28, 36, 28)
        col.setSpacing(14)

        logo_lbl = QLabel()
        logo_lbl.setObjectName("LogoLabel")
        logo_lbl.setAlignment(Qt.AlignCenter)
        pix = QPixmap(theme.BRAND_LOGO)
        if not pix.isNull():
            logo_lbl.setPixmap(
                pix.scaled(230, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo_lbl.setText(theme.BRAND_WORDMARK)
            logo_lbl.setStyleSheet(
                f"color:{theme.ACCENT_ICE}; font-size:28px; font-weight:bold;"
            )
        col.addWidget(logo_lbl)

        brand_title = QLabel(theme.BRAND_WORDMARK)
        brand_title.setObjectName("BrandTitle")
        brand_title.setAlignment(Qt.AlignCenter)
        col.addWidget(brand_title)

        tag = QLabel("Secure access required to open the vault workspace.")
        tag.setObjectName("TagLine")
        tag.setAlignment(Qt.AlignCenter)
        col.addWidget(tag)

        col.addSpacing(6)

        col.addWidget(self._field_label("Username"))
        self._user_field = QLineEdit()
        self._user_field.setObjectName("LoginField")
        self._user_field.setPlaceholderText("Enter username...")
        self._user_field.returnPressed.connect(self._try_login)
        col.addWidget(self._user_field)

        col.addWidget(self._field_label("Password"))
        self._pass_field = QLineEdit()
        self._pass_field.setObjectName("LoginField")
        self._pass_field.setPlaceholderText("Enter password...")
        self._pass_field.setEchoMode(QLineEdit.Password)
        self._pass_field.returnPressed.connect(self._try_login)
        col.addWidget(self._pass_field)

        self._error_lbl = QLabel("")
        self._error_lbl.setObjectName("ErrorLabel")
        self._error_lbl.setAlignment(Qt.AlignCenter)
        col.addWidget(self._error_lbl)

        self._login_btn = QPushButton("LOGIN  ->")
        self._login_btn.setObjectName("LoginBtn")
        self._login_btn.clicked.connect(self._try_login)
        col.addWidget(self._login_btn)

        fake_lbl = QLabel("Fake-mode remains available for safe decoy sessions.")
        fake_lbl.setObjectName("FakeLabel")
        fake_lbl.setAlignment(Qt.AlignCenter)
        col.addWidget(fake_lbl)

        col.addSpacing(6)

        hint = QLabel(
            "Demo credentials\n"
            "  admin  /  admin123  (root)\n"
            "  user   /  user123   (standard)\n"
            "  Fake:  admin / decoy123"
        )
        hint.setObjectName("HintLabel")
        hint.setAlignment(Qt.AlignCenter)
        col.addWidget(hint)

        page.addWidget(card)

        self._clock_lbl = QLabel()
        self._clock_lbl.setAlignment(Qt.AlignCenter)
        self._clock_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:11px;"
            f"font-family:'Consolas',monospace; background:transparent;"
        )
        page.addWidget(self._clock_lbl)

        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._tick_clock)
        clock_timer.start(1000)
        self._tick_clock()

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(theme.DESKTOP_GRADIENT_START))
        grad.setColorAt(0.55, QColor(theme.DESKTOP_GRADIENT_MID))
        grad.setColorAt(1.0, QColor(theme.DESKTOP_GRADIENT_END))
        painter.fillRect(self.rect(), grad)

        painter.setPen(QColor(24, 215, 255, 10))
        for y in range(0, self.height(), 5):
            painter.drawLine(0, y, self.width(), y)

        painter.setPen(QColor(24, 215, 255, 8))
        for x in range(0, self.width(), 48):
            painter.drawLine(x, 0, x, self.height())

    def _try_login(self):
        try:
            username = self._user_field.text().strip()
            password = self._pass_field.text()

            if not username:
                self._show_error("Username cannot be empty.")
                self._shake(self._user_field)
                return
            if not password:
                self._show_error("Password cannot be empty.")
                self._shake(self._pass_field)
                return

            result = SESSION.authenticate(username, password)

            if result.success:
                self._error_lbl.setText("")
                STATE.current_user = result.user
                STATE.session_type = result.session_type

                if result.session_type == "fake":
                    self._show_error("Fake session loaded.")
                self.login_success.emit()
            else:
                self._show_error(result.message)
                self._shake(self._pass_field)
                self._pass_field.clear()
                if result.locked:
                    self._login_btn.setEnabled(False)
                    self._lockout_timer.start(1000)

        except Exception as exc:
            import traceback

            print(f"[LOGIN ERROR] {exc}")
            print(traceback.format_exc())
            self._show_error(f"Login error: {str(exc)[:50]}")

    def _show_error(self, msg: str):
        self._error_lbl.setText(msg)

    def _update_lockout(self):
        try:
            user = SESSION.get_user(self._user_field.text().strip())
            if user and user.is_locked():
                secs = user.seconds_until_unlock()
                self._show_error(f"Account locked. Retry in {secs}s.")
            else:
                self._lockout_timer.stop()
                self._login_btn.setEnabled(True)
                self._show_error("Account unlocked. You may try again.")
        except Exception:
            self._lockout_timer.stop()
            self._login_btn.setEnabled(True)

    def _shake(self, widget: QLineEdit):
        offsets = [8, -8, 6, -6, 3, -3, 0]
        self._do_shake(widget, offsets)

    def _do_shake(self, widget, offsets):
        if not offsets:
            return
        widget.move(widget.x() + offsets[0], widget.y())
        QTimer.singleShot(35, lambda: self._do_shake(widget, offsets[1:]))

    def _tick_clock(self):
        import time as _time

        self._clock_lbl.setText(_time.strftime("%A, %B %d  |  %H:%M:%S"))

    def showEvent(self, event):
        try:
            super().showEvent(event)
            self._user_field.setFocus()
            self._user_field.clear()
            self._pass_field.clear()
            self._error_lbl.clear()
        except Exception as e:
            import logging

            logging.warning(f"Login screen showEvent error: {e}")
