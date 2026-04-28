import logging

logger = logging.getLogger(__name__)
# ⚠️ QUARANTINED MODULE ⚠️
# ==============================
# Module: feedback_dialog.py
# Status: NOT PART OF RUNTIME
# Warning: DO NOT IMPORT
# Reason: Only dynamically imported (lazy load pattern broken)
# ==============================

# =============================================================
#  feedback_dialog.py — Q-VAULT OS  |  Feedback Dialog
#
#  In-app feedback collection
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
    QComboBox,
    QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from assets import theme


class FeedbackDialog(QDialog):
    feedback_submitted = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Feedback - Q-VAULT OS")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Send Feedback")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {theme.ACCENT_CYAN};")
        layout.addWidget(title)

        desc = QLabel(
            "Help us improve Q-VAULT OS! Report bugs, suggest features, "
            "or share your experience."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 12px;")
        layout.addWidget(desc)

        type_label = QLabel("Feedback Type:")
        type_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(type_label)

        self._type_combo = QComboBox()
        self._type_combo.addItems(
            ["Bug Report", "Feature Request", "General Feedback", "Security Issue"]
        )
        layout.addWidget(self._type_combo)

        email_label = QLabel("Email (optional - for follow-up):")
        email_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(email_label)

        self._email_field = QLineEdit()
        self._email_field.setPlaceholderText("your@email.com")
        self._email_field.setMaximumHeight(30)
        layout.addWidget(self._email_field)

        message_label = QLabel("Your Feedback:")
        message_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(message_label)

        self._message_field = QTextEdit()
        self._message_field.setPlaceholderText(
            "Describe the issue or suggestion in detail...\n\n"
            "Include steps to reproduce if this is a bug.\n"
            "Include use case if this is a feature request."
        )
        layout.addWidget(self._message_field)

        layout.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        self._submit_btn = QPushButton("Submit")
        self._submit_btn.setMinimumWidth(100)
        self._submit_btn.setStyleSheet(
            f"background: {theme.ACCENT_CYAN}; color: {theme.BG_DARK};"
            f"font-weight: bold; border: none; border-radius: 4px;"
        )
        self._submit_btn.clicked.connect(self._submit)
        btns.addWidget(self._submit_btn)

        layout.addLayout(btns)

    def _submit(self):
        message = self._message_field.toPlainText().strip()
        if not message:
            self._message_field.setStyleSheet(f"border: 2px solid {THEME['error_bright']};")
            return

        feedback = {
            "type": self._type_combo.currentText(),
            "email": self._email_field.text().strip(),
            "message": message,
            "version": "1.2.0",
        }

        self._save_feedback(feedback)

        self.feedback_submitted.emit(feedback)
        self.accept()

    def _save_feedback(self, feedback: dict):
        import json
        from pathlib import Path
        from datetime import datetime
        from assets.theme import THEME

        feedback_dir = Path.home() / ".qvault" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)

        feedback_file = feedback_dir / "pending_feedback.json"

        try:
            existing = []
            if feedback_file.exists():
                with open(feedback_file, "r") as f:
                    existing = json.load(f)

            existing.append({**feedback, "timestamp": datetime.now().isoformat()})

            with open(feedback_file, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as _exc:
            logger.debug("Suppressed exception in feedback_dialog.py: %s", _exc)


def show_feedback_dialog(parent=None):
    dialog = FeedbackDialog(parent)
    return dialog.exec_() == QDialog.Accepted
