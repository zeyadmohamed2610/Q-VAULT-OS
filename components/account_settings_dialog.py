"""
components/account_settings_dialog.py — Q-Vault OS
Account Settings: Change username and password with full validation.
"""

import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QStackedWidget,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient

logger = logging.getLogger(__name__)

# ── Shared style tokens ────────────────────────────────────────
_BG       = "#07111f"
_SURFACE  = "#0d1e33"
_BORDER   = "rgba(0, 210, 255, 0.18)"
_CYAN     = "#00e6ff"
_CYAN_DIM = "rgba(0,230,255,0.12)"
_TEXT     = "#cce8f4"
_MUTED    = "rgba(180,220,240,0.45)"
_RED      = "#ff5f5f"
_GREEN    = "#3dffa0"

_INPUT_STYLE = f"""
    QLineEdit {{
        background: rgba(0,0,0,0.35);
        border: 1px solid rgba(0,210,255,0.25);
        border-radius: 9px;
        color: {_TEXT};
        padding: 10px 14px;
        font-size: 12px;
        font-family: 'Segoe UI';
    }}
    QLineEdit:focus {{
        border: 1px solid {_CYAN};
        background: rgba(0,230,255,0.04);
    }}
    QLineEdit:disabled {{
        color: rgba(180,220,240,0.3);
        border-color: rgba(0,210,255,0.1);
    }}
"""

_BTN_PRIMARY = f"""
    QPushButton {{
        background: rgba(0,210,255,0.15);
        border: 1px solid rgba(0,210,255,0.35);
        border-radius: 9px;
        color: {_CYAN};
        padding: 10px 26px;
        font-size: 12px;
        font-weight: bold;
        font-family: 'Segoe UI';
        letter-spacing: 0.5px;
    }}
    QPushButton:hover {{
        background: rgba(0,210,255,0.28);
        border-color: {_CYAN};
    }}
    QPushButton:pressed {{
        background: rgba(0,210,255,0.38);
    }}
    QPushButton:disabled {{
        background: rgba(0,0,0,0.2);
        border-color: rgba(0,210,255,0.1);
        color: rgba(0,230,255,0.3);
    }}
"""

_BTN_GHOST = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 9px;
        color: {_MUTED};
        padding: 10px 22px;
        font-size: 12px;
        font-family: 'Segoe UI';
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.06);
        color: {_TEXT};
        border-color: rgba(255,255,255,0.2);
    }}
"""


class _StatusBar(QLabel):
    """Inline status label that auto-clears after a timeout."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Segoe UI", 10))
        self.setFixedHeight(22)
        self.clear_status()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear_status)

    def show_success(self, msg: str, duration_ms: int = 3500):
        self.setText(f"✓  {msg}")
        self.setStyleSheet(f"color: {_GREEN}; background: transparent;")
        self._timer.start(duration_ms)

    def show_error(self, msg: str, duration_ms: int = 4000):
        self.setText(f"✗  {msg}")
        self.setStyleSheet(f"color: {_RED}; background: transparent;")
        self._timer.start(duration_ms)

    def clear_status(self):
        self.setText("")
        self.setStyleSheet("background: transparent;")


class _SectionCard(QFrame):
    """Dark glass card with a labelled top border."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(13, 30, 51, 200);
                border: 1px solid rgba(0,200,255,0.2);
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background: rgba(0,0,0,0.4);
                border: 1px solid rgba(0,200,255,0.25);
                border-radius: 9px;
                color: #cce8f4;
                padding: 10px 14px;
                font-size: 12px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 1px solid #00e6ff;
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl.setStyleSheet(f"color: {_CYAN}; letter-spacing: 1.5px; background: transparent; border: none;")
        outer.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {_BORDER}; border: none; background: rgba(0,210,255,0.15); max-height: 1px;")
        sep.setFixedHeight(1)
        outer.addWidget(sep)

        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        outer.addLayout(self.body)

    def add_row(self, label: str, widget: QWidget):
        # Add spacing before each row (except the first)
        if self.body.count() > 0:
            self.body.addSpacing(16)
        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color: {_MUTED}; background: transparent; border: none;")
        self.body.addWidget(lbl)
        self.body.addSpacing(6)
        self.body.addWidget(widget)

    def add_widget(self, w: QWidget):
        self.body.addWidget(w)

    def add_layout(self, l):
        self.body.addLayout(l)


class AccountSettingsDialog(QDialog):
    """
    Full-screen account settings dialog.
    Allows changing username (display name) and password with current-password verification.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(460, 720)
        self._drag_pos = None
        self._build_ui()
        self._load_current_username()
        self._center_on_screen()

    # ── Layout ────────────────────────────────────────────────

    def _build_ui(self):
        # Outer container — explicit dark background, no inheritance issues
        self._container = QWidget(self)
        self._container.setGeometry(0, 0, 460, 720)
        self._container.setAutoFillBackground(True)

        # Force background via palette (works even when parent is translucent)
        from PyQt5.QtGui import QPalette
        pal = self._container.palette()
        pal.setColor(QPalette.Window, QColor(7, 17, 31))
        self._container.setPalette(pal)

        self._container.setStyleSheet("""
            QWidget {
                background: #07111f;
                color: #cce8f4;
            }
            QFrame {
                background: transparent;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self._container.setGraphicsEffect(shadow)

        root = QVBoxLayout(self._container)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # ── Header ──
        header = QHBoxLayout()
        icon_lbl = QLabel("⚙")
        icon_lbl.setFont(QFont("Segoe UI", 20))
        icon_lbl.setStyleSheet(f"color: {_CYAN}; background: transparent;")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Account Settings")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet(f"color: {_TEXT}; background: transparent;")
        subtitle = QLabel("Manage your credentials securely")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet(f"color: {_MUTED}; background: transparent;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {_MUTED};
                font-size: 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: rgba(255,80,80,0.15); color: {_RED}; }}
        """)
        btn_close.clicked.connect(self.reject)

        header.addWidget(icon_lbl)
        header.addSpacing(12)
        header.addLayout(title_col)
        header.addStretch()
        header.addWidget(btn_close)
        root.addLayout(header)
        root.addSpacing(20)

        # ── Username card ──
        uname_card = _SectionCard("USERNAME")
        self._uname_current = QLabel("")
        self._uname_current.setFont(QFont("Segoe UI", 10))
        self._uname_current.setStyleSheet(f"color: {_MUTED}; background: transparent; border: none;")
        uname_card.add_widget(self._uname_current)

        self._uname_field = QLineEdit()
        self._uname_field.setPlaceholderText("New username…")
        self._uname_field.setStyleSheet(_INPUT_STYLE)
        self._uname_field.setMaxLength(32)
        self._uname_field.textChanged.connect(self._validate_username)
        uname_card.add_row("New Username", self._uname_field)

        uname_btn_row = QHBoxLayout()
        uname_btn_row.addStretch()
        self._btn_uname_save = QPushButton("Update Username")
        self._btn_uname_save.setStyleSheet(_BTN_PRIMARY)
        self._btn_uname_save.setCursor(Qt.PointingHandCursor)
        self._btn_uname_save.setEnabled(False)
        self._btn_uname_save.clicked.connect(self._save_username)
        uname_btn_row.addWidget(self._btn_uname_save)
        uname_card.add_layout(uname_btn_row)

        self._uname_status = _StatusBar()
        uname_card.add_widget(self._uname_status)
        root.addWidget(uname_card)
        root.addSpacing(14)

        # ── Password card ──
        pwd_card = _SectionCard("CHANGE PASSWORD")

        self._pwd_current = QLineEdit()
        self._pwd_current.setPlaceholderText("Current password…")
        self._pwd_current.setEchoMode(QLineEdit.Password)
        self._pwd_current.setStyleSheet(_INPUT_STYLE)
        self._pwd_current.textChanged.connect(self._validate_password_form)
        pwd_card.add_row("Current Password", self._pwd_current)

        self._pwd_new = QLineEdit()
        self._pwd_new.setPlaceholderText("New password (min 6 chars)…")
        self._pwd_new.setEchoMode(QLineEdit.Password)
        self._pwd_new.setStyleSheet(_INPUT_STYLE)
        self._pwd_new.textChanged.connect(self._validate_password_form)
        pwd_card.add_row("New Password", self._pwd_new)

        self._pwd_confirm = QLineEdit()
        self._pwd_confirm.setPlaceholderText("Confirm new password…")
        self._pwd_confirm.setEchoMode(QLineEdit.Password)
        self._pwd_confirm.setStyleSheet(_INPUT_STYLE)
        self._pwd_confirm.textChanged.connect(self._validate_password_form)
        self._pwd_confirm.returnPressed.connect(self._save_password)
        pwd_card.add_row("Confirm New Password", self._pwd_confirm)

        # Password strength bar
        self._strength_bar = QFrame()
        self._strength_bar.setFixedHeight(3)
        self._strength_bar.setStyleSheet("background: rgba(255,255,255,0.07); border-radius: 2px; border: none;")
        pwd_card.add_widget(self._strength_bar)

        pwd_btn_row = QHBoxLayout()
        pwd_btn_row.addStretch()
        self._btn_pwd_save = QPushButton("Change Password")
        self._btn_pwd_save.setStyleSheet(_BTN_PRIMARY)
        self._btn_pwd_save.setCursor(Qt.PointingHandCursor)
        self._btn_pwd_save.setEnabled(False)
        self._btn_pwd_save.clicked.connect(self._save_password)
        pwd_btn_row.addWidget(self._btn_pwd_save)
        pwd_card.add_layout(pwd_btn_row)

        self._pwd_status = _StatusBar()
        pwd_card.add_widget(self._pwd_status)
        root.addWidget(pwd_card)
        root.addStretch()

        # ── Bottom close ──
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_done = QPushButton("Done")
        btn_done.setStyleSheet(_BTN_GHOST)
        btn_done.setCursor(Qt.PointingHandCursor)
        btn_done.clicked.connect(self.accept)
        bottom.addWidget(btn_done)
        root.addLayout(bottom)

    # ── Data ──────────────────────────────────────────────────

    def _get_auth_manager(self):
        try:
            from system.security.auth_manager import AuthManager
            return AuthManager()
        except Exception as e:
            logger.error("Could not get AuthManager: %s", e)
            return None

    def _get_current_username(self) -> str:
        try:
            from system.auth_manager import get_auth_manager
            return get_auth_manager().username or "admin"
        except Exception:
            return "admin"

    def _load_current_username(self):
        name = self._get_current_username()
        self._uname_current.setText(f"Current: {name}")
        self._uname_field.setPlaceholderText(f"New username (currently '{name}')…")

    # ── Validation ────────────────────────────────────────────

    def _validate_username(self):
        text = self._uname_field.text().strip()
        valid = 3 <= len(text) <= 32 and text.replace("_", "").replace("-", "").isalnum()
        self._btn_uname_save.setEnabled(valid)
        if text and not valid:
            self._uname_field.setStyleSheet(
                _INPUT_STYLE.replace("rgba(0,210,255,0.25)", "rgba(255,80,80,0.4)")
            )
        else:
            self._uname_field.setStyleSheet(_INPUT_STYLE)

    def _validate_password_form(self):
        cur = self._pwd_current.text()
        new = self._pwd_new.text()
        conf = self._pwd_confirm.text()
        valid = len(cur) > 0 and len(new) >= 6 and new == conf
        self._btn_pwd_save.setEnabled(valid)

        # Strength bar
        strength = self._password_strength(new)
        colors = ["rgba(255,80,80,0.6)", "rgba(255,160,60,0.7)", "rgba(255,220,80,0.8)", f"{_GREEN}"]
        widths = [25, 50, 75, 100]
        if new:
            self._strength_bar.setStyleSheet(
                f"background: {colors[strength]}; border-radius: 2px; border: none;"
            )
            self._strength_bar.setFixedWidth(int(self._strength_bar.parent().width() * widths[strength] / 100))
        else:
            self._strength_bar.setStyleSheet("background: rgba(255,255,255,0.07); border-radius: 2px; border: none;")

        # Confirm field color
        if conf and new != conf:
            self._pwd_confirm.setStyleSheet(
                _INPUT_STYLE.replace("rgba(0,210,255,0.25)", "rgba(255,80,80,0.4)")
            )
        else:
            self._pwd_confirm.setStyleSheet(_INPUT_STYLE)

    def _password_strength(self, pw: str) -> int:
        """Returns 0-3 strength score."""
        if len(pw) < 6:
            return 0
        score = 0
        if len(pw) >= 10:
            score += 1
        if any(c.isdigit() for c in pw):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw):
            score += 1
        return min(score, 3)

    # ── Save actions ──────────────────────────────────────────

    def _save_username(self):
        new_name = self._uname_field.text().strip()
        if not new_name:
            return
        try:
            # Update in-memory auth manager
            from system.auth_manager import get_auth_manager
            am = get_auth_manager()
            am._username = new_name

            # Persist via QSettings (Python side)
            from PyQt5.QtCore import QSettings
            s = QSettings("QVault", "Account")
            s.setValue("username", new_name)
            s.sync()

            # Also try Rust core if available
            try:
                from system.security_api import get_security_api
                api = get_security_api()
                if api and api._token:
                    api._rust_engine.update_username(api._token, new_name)
            except Exception:
                pass  # Rust may not support this — Python layer is source of truth

            self._uname_status.show_success(f"Username changed to '{new_name}'")
            self._uname_current.setText(f"Current: {new_name}")
            self._uname_field.clear()
            self._btn_uname_save.setEnabled(False)
            logger.info("[AccountSettings] Username changed to: %s", new_name)
        except Exception as e:
            self._uname_status.show_error(f"Failed: {e}")
            logger.error("[AccountSettings] Username change failed: %s", e)

    def _save_password(self):
        if not self._btn_pwd_save.isEnabled():
            return
        current_pw = self._pwd_current.text()
        new_pw = self._pwd_new.text()
        confirm_pw = self._pwd_confirm.text()

        if new_pw != confirm_pw:
            self._pwd_status.show_error("Passwords do not match")
            return

        if len(new_pw) < 6:
            self._pwd_status.show_error("Password must be at least 6 characters")
            return

        # Verify current password
        am = self._get_auth_manager()
        if am is None:
            self._pwd_status.show_error("Auth system unavailable — check logs")
            return

        if not am.verify_password(current_pw):
            self._pwd_status.show_error("Incorrect current password")
            self._pwd_current.clear()
            self._pwd_current.setFocus()
            self._shake_field(self._pwd_current)
            return

        # Change password
        try:
            am.set_password(new_pw)
            am.log_audit("PASSWORD_CHANGE", f"User changed their password")

            self._pwd_status.show_success("Password changed successfully!")
            self._pwd_current.clear()
            self._pwd_new.clear()
            self._pwd_confirm.clear()
            self._btn_pwd_save.setEnabled(False)
            logger.info("[AccountSettings] Password changed successfully")
        except Exception as e:
            self._pwd_status.show_error(f"Failed: {e}")
            logger.error("[AccountSettings] Password change failed: %s", e)

    # ── UX helpers ────────────────────────────────────────────

    def _shake_field(self, field: QLineEdit):
        """Shake animation on failed input."""
        orig_x = field.x()
        offsets = [8, -8, 6, -6, 3, -3, 0]

        def step(offs):
            if not offs:
                return
            field.move(orig_x + offs[0], field.y())
            QTimer.singleShot(35, lambda: step(offs[1:]))

        step(offsets)

    def _center_on_screen(self):
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    # ── Draggable window ──────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Paint: rounded corners ────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Rounded dark background with cyan border
        path = QPainterPath()
        path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 16, 16)

        # Fill dark
        painter.fillPath(path, QColor(7, 17, 31))

        # Cyan border
        from PyQt5.QtGui import QPen
        painter.setPen(QPen(QColor(0, 200, 255, 55), 1.0))
        painter.drawPath(path)
        painter.end()


def open_account_settings(parent=None):
    """Convenience function — open the dialog from anywhere."""
    dlg = AccountSettingsDialog(parent)
    dlg.exec_()
