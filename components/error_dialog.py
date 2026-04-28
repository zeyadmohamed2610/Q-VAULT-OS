# ⚠️ QUARANTINED MODULE ⚠️
# ==============================
# Module: error_dialog.py
# Status: NOT PART OF RUNTIME
# Warning: DO NOT IMPORT
# Reason: Pending architectural verification
# ==============================

# =============================================================
#  error_dialog.py — Q-Vault OS  |  Global Error Dialog
#
#  Shows user-friendly error messages without crashing
# =============================================================
# ⚠️ QUARANTINED: 2026-04-18
# =============================================================

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from assets import theme


class ErrorDialog(QDialog):
    """Global error dialog that shows crash information safely."""

    def __init__(self, title: str, message: str, details: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 300)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._setup_ui(message, details)

    def _setup_ui(self, message: str, details: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel("System Error")
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {theme.ACCENT_RED};"
            f"font-family: Consolas;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setStyleSheet(
            f"font-size: 14px; color: {theme.TEXT_PRIMARY};"
            f"font-family: Consolas; padding: 10px;"
            f"background: rgba(0,0,0,30); border-radius: 4px;"
        )
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        self._details_edit = QTextEdit()
        self._details_edit.setReadOnly(True)
        self._details_edit.setStyleSheet(
            f"background: {theme.BG_DARK}; color: {theme.TEXT_DIM};"
            f"font-family: Consolas; font-size: 11px;"
            f"border: 1px solid {theme.BORDER_DIM};"
        )
        self._details_edit.setText(details)
        self._details_edit.setMaximumHeight(0)
        layout.addWidget(self._details_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        if details:
            self._btn_details = QPushButton("View Details")
            self._btn_details.setStyleSheet(theme.BUTTON_SECONDARY)
            self._btn_details.clicked.connect(self._toggle_details)
            btn_row.addWidget(self._btn_details)

        self._btn_continue = QPushButton("Continue")
        self._btn_continue.setStyleSheet(theme.BUTTON_PRIMARY)
        self._btn_continue.clicked.connect(self.accept)
        self._btn_continue.setDefault(True)
        btn_row.addWidget(self._btn_continue)

        layout.addLayout(btn_row)

    def _toggle_details(self):
        if self._details_edit.maximumHeight() > 0:
            self._details_edit.setMaximumHeight(0)
            self._btn_details.setText("View Details")
        else:
            self._details_edit.setMaximumHeight(150)
            self._btn_details.setText("Hide Details")


def show_error(title: str, message: str, details: str = "", parent=None) -> bool:
    """
    Show an error dialog and return True if user wants to continue.
    """
    dialog = ErrorDialog(title, message, details, parent)
    return dialog.exec() == QDialog.Accepted


def show_crash_error(
    exc_type: str, exc_value: str, exc_traceback: str, parent=None
) -> bool:
    """
    Show a crash error dialog with formatted traceback.
    """
    message = "Something went wrong. The system recovered safely."
    details = f"Exception: {exc_type}\n{exc_value}\n\nTraceback:\n{exc_traceback}"
    return show_error("System Error", message, details, parent)
