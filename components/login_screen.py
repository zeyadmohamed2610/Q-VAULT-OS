import os
import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFrame
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen

# Resolve assets via centralized resource loader
from core.resources import get_asset_path


class _GlowCard(QFrame):
    """LoginCard with a painted neon glow border for depth."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 3 layers of glow — outer -> inner
        for i, alpha in enumerate([18, 38, 65]):
            pen = QPen(QColor(0, 230, 255, alpha))
            pen.setWidth(i + 1)
            painter.setPen(pen)
            inset = i
            painter.drawRoundedRect(
                QRect(inset, inset,
                      self.width() - inset * 2,
                      self.height() - inset * 2),
                10, 10
            )


class LoginScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginGateway")
        self._bg_pixmap = QPixmap(get_asset_path("qvault_vault.jpg"))

        # Dark overlay for readability
        self.overlay = QWidget(self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay.lower()

        # ── Compact Card ── (no logo, no title — just credentials)
        self.card = _GlowCard(self)
        self.card.setObjectName("LoginCard")
        self.card.setFixedSize(320, 210)       # tight, purposeful

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(10)

        # Username
        self.user_field = QLineEdit()
        self.user_field.setPlaceholderText("username")
        self.user_field.setFixedHeight(38)
        card_layout.addWidget(self.user_field)

        # Password
        self.pass_field = QLineEdit()
        self.pass_field.setPlaceholderText("password")
        self.pass_field.setEchoMode(QLineEdit.Password)
        self.pass_field.setFixedHeight(38)
        self.pass_field.returnPressed.connect(self._do_login)
        card_layout.addWidget(self.pass_field)

        # Error label — compact, no extra height when empty
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(
            "color: #ff3366; font-size: 11px; padding: 0px;"
        )
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setFixedHeight(16)
        card_layout.addWidget(self.error_lbl)

        # No LOGIN button — Windows Hello style
        self.btn = None

        # ── Wire to AuthManager (NOT SecurityController) ─────────
        from system.auth_manager import get_auth_manager
        self._auth = get_auth_manager()
        self._auth.state_changed.connect(self._on_auth_state_changed)
        self._auth.login_failed.connect(self._on_failed)

    # ── Background rendering ──────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            x = (scaled.width()  - self.width())  // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), Qt.black)

    def resizeEvent(self, event):
        """Dynamic pixel alignment — 75% vertical tracks the vault door zone."""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

        target_y = int(self.height() * 0.75)
        card_x   = (self.width() - self.card.width()) // 2
        max_y    = self.height() - self.card.height() - 20
        self.card.move(card_x, min(target_y, max_y))

    # ── Logic ─────────────────────────────────────────────────────
    def _do_login(self):
        user = self.user_field.text().strip()
        pwd  = self.pass_field.text()
        if not user or not pwd:
            self.error_lbl.setText("Credentials required.")
            return
        self.set_busy(True)
        self._auth.request_login(user, pwd)

    def _on_auth_state_changed(self, new_state: str, old_state: str):
        """React to auth transitions."""
        if old_state == "authenticating" and new_state == "logged_in":
            # Success — AppController will switch screens
            self.set_busy(False)
        elif new_state == "logged_out" and old_state == "authenticating":
            # Login failed -> revert handled by login_failed signal
            self.set_busy(False)

    def _on_failed(self, error_dict: dict):
        self.set_busy(False)
        self.error_lbl.setText(error_dict.get("message", "Access Denied."))

    def set_busy(self, busy: bool):
        self.user_field.setEnabled(not busy)
        self.pass_field.setEnabled(not busy)
        if busy:
            self.error_lbl.setStyleSheet("color: #00ffcc; font-size: 11px; padding: 0px;")
            self.error_lbl.setText("VERIFYING...")
        else:
            self.error_lbl.setStyleSheet("color: #ff3366; font-size: 11px; padding: 0px;")
            self.error_lbl.setText("")

    def showEvent(self, event):
        super().showEvent(event)
        self.set_busy(False)
        self.user_field.clear()
        self.pass_field.clear()
        self.user_field.setFocus()
