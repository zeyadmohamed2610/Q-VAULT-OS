import logging

logger = logging.getLogger(__name__)
# =============================================================
#  first_run_wizard.py — Q-VAULT OS  |  First Run Wizard
#
#  First-time setup wizard for new installations
# =============================================================
# ⚠️ QUARANTINED: 2026-04-18
# Reason: No import references found in codebase

import os
import json
from pathlib import Path
from assets.theme import THEME
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QWidget,
    QStackedWidget,
    QProgressBar,
    QComboBox,
    QTextEdit,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor


class FirstRunWizard(QDialog):
    wizard_complete = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Q-VAULT OS v1.2.0 - Setup Wizard")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._step = 0
        self._data = {
            "username": "",
            "password": "",
            "display_name": "",
            "telemetry_enabled": False,
            "auto_update": True,
            "create_demo_user": True,
        }

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QLabel("Q-VAULT OS Setup")
        header.setFont(QFont("Segoe UI", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._build_welcome_page()
        self._build_user_page()
        self._build_security_page()
        self._build_telemetry_page()
        self._build_summary_page()

        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        self._back_btn = QPushButton("Back")
        self._back_btn.setMinimumWidth(100)
        self._back_btn.clicked.connect(self._go_back)
        nav_layout.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setMinimumWidth(100)
        self._next_btn.clicked.connect(self._go_next)
        nav_layout.addWidget(self._next_btn)

        layout.addLayout(nav_layout)

        self._update_buttons()

    def _build_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        logo_label = QLabel()
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor(20, 30, 40))
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        title = QLabel("Welcome to Q-VAULT OS")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "This wizard will guide you through the initial setup of "
            "Q-VAULT OS, a secure desktop operating system.\n\n"
            "Press Next to begin the setup process."
        )
        desc.setFont(QFont("Segoe UI", 11))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()
        self._stack.addWidget(page)

    def _build_user_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Create Your Account")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        username_label = QLabel("Username:")
        username_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(username_label)

        self._username_field = QLineEdit()
        self._username_field.setPlaceholderText("Enter username")
        self._username_field.setMinimumHeight(35)
        layout.addWidget(self._username_field)

        display_label = QLabel("Display Name:")
        display_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(display_label)

        self._display_field = QLineEdit()
        self._display_field.setPlaceholderText("Enter display name")
        self._display_field.setMinimumHeight(35)
        layout.addWidget(self._display_field)

        layout.addStretch()
        self._stack.addWidget(page)

    def _build_security_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Set Password")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        password_label = QLabel("Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(password_label)

        self._password_field = QLineEdit()
        self._password_field.setPlaceholderText("Enter password")
        self._password_field.setEchoMode(QLineEdit.Password)
        self._password_field.setMinimumHeight(35)
        layout.addWidget(self._password_field)

        confirm_label = QLabel("Confirm Password:")
        confirm_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(confirm_label)

        self._confirm_field = QLineEdit()
        self._confirm_field.setPlaceholderText("Confirm password")
        self._confirm_field.setEchoMode(QLineEdit.Password)
        self._confirm_field.setMinimumHeight(35)
        layout.addWidget(self._confirm_field)

        self._password_error = QLabel("")
        self._password_error.setStyleSheet(f"color: {THEME['error_bright']};")
        layout.addWidget(self._password_error)

        self._demo_checkbox = QCheckBox("Create demo account for testing")
        self._demo_checkbox.setChecked(True)
        layout.addWidget(self._demo_checkbox)

        layout.addStretch()
        self._stack.addWidget(page)

    def _build_telemetry_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Telemetry & Updates")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        self._telemetry_check = QCheckBox(
            "Enable anonymous telemetry to help improve Q-VAULT OS"
        )
        self._telemetry_check.setChecked(False)
        layout.addWidget(self._telemetry_check)

        telemetry_info = QTextEdit()
        telemetry_info.setHtml("""
        <p style='color: #7f8c8d;'>
        Telemetry collects anonymous usage data such as:<br>
        - Application usage statistics<br>
        - Command frequency<br>
        - System performance metrics<br><br>
        <b>No personal data is collected.</b><br>
        You can disable this at any time in Settings.
        </p>
        """)
        telemetry_info.setReadOnly(True)
        telemetry_info.setMaximumHeight(100)
        layout.addWidget(telemetry_info)

        self._auto_update_check = QCheckBox(
            "Automatically check for and install updates"
        )
        self._auto_update_check.setChecked(True)
        layout.addWidget(self._auto_update_check)

        layout.addStretch()
        self._stack.addWidget(page)

    def _build_summary_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Setup Complete")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        summary = QLabel(
            "Q-VAULT OS is now ready to use!\n\n"
            "Your settings have been saved. You can modify them later "
            "through the Settings application."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setMaximumHeight(150)
        layout.addWidget(self._summary_text)

        layout.addStretch()
        self._stack.addWidget(page)

    def _update_buttons(self):
        if self._step == 0:
            self._back_btn.setEnabled(False)
        else:
            self._back_btn.setEnabled(True)

        if self._step == self._stack.count() - 1:
            self._next_btn.setText("Finish")
        else:
            self._next_btn.setText("Next")

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self._stack.setCurrentIndex(self._step)
            self._update_buttons()

    def _go_next(self):
        if not self._validate_current_step():
            return

        self._save_current_step()

        if self._step < self._stack.count() - 1:
            self._step += 1
            self._stack.setCurrentIndex(self._step)
            self._update_buttons()
        else:
            self._finish()

    def _validate_current_step(self):
        if self._step == 1:
            username = self._username_field.text().strip()
            if not username:
                self._username_field.setStyleSheet(f"border: 2px solid {THEME['error_bright']};")
                return False
            self._username_field.setStyleSheet("")

        elif self._step == 2:
            password = self._password_field.text()
            confirm = self._confirm_field.text()
            if password != confirm or len(password) < 4:
                self._password_error.setText(
                    "Passwords must match and be at least 4 characters"
                )
                return False
            self._password_error.setText("")

        return True

    def _save_current_step(self):
        if self._step == 1:
            self._data["username"] = self._username_field.text().strip()
            self._data["display_name"] = (
                self._display_field.text().strip() or self._data["username"]
            )

        elif self._step == 2:
            self._data["password"] = self._password_field.text()
            self._data["create_demo_user"] = self._demo_checkbox.isChecked()

        elif self._step == 3:
            self._data["telemetry_enabled"] = self._telemetry_check.isChecked()
            self._data["auto_update"] = self._auto_update_check.isChecked()

        elif self._step == 4:
            self._update_summary()

    def _update_summary(self):
        summary_html = f"""
        <p><b>Account:</b> {self._data["username"]}</p>
        <p><b>Display Name:</b> {self._data["display_name"]}</p>
        <p><b>Telemetry:</b> {"Enabled" if self._data["telemetry_enabled"] else "Disabled"}</p>
        <p><b>Auto-Update:</b> {"Enabled" if self._data["auto_update"] else "Disabled"}</p>
        <p><b>Demo Account:</b> {"Created" if self._data["create_demo_user"] else "Skipped"}</p>
        """
        self._summary_text.setHtml(summary_html)

    def _finish(self):
        self._save_settings()
        self.accept()
        self.wizard_complete.emit(self._data)

    def _save_settings(self):
        config_dir = Path.home() / ".qvault"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.json"
        config = {
            "version": "1.2.0",
            "first_run": False,
            "telemetry_enabled": self._data["telemetry_enabled"],
            "auto_update": self._data["auto_update"],
            "username": self._data["username"],
        }

        try:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as _exc:
            logger.debug("Suppressed exception in first_run_wizard.py: %s", _exc)

        user_dir = config_dir / "users"
        user_file = user_dir / "users.json"
        user_dir.mkdir(parents=True, exist_ok=True)

        import hashlib

        def hash_password(password):
            import base64
            import os
            from assets.theme import THEME

            salt = os.urandom(32)
            hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            return base64.b64encode(salt + hash_obj).decode()

        users = {
            self._data["username"]: {
                "username": self._data["username"],
                "display_name": self._data["display_name"],
                "role": "admin",
                "uid": 0,
                "gid": 0,
                "home": "/root",
                "password_hash": hash_password(self._data["password"]),
                "created": "2026-01-01T00:00:00",
            }
        }

        if self._data["create_demo_user"]:
            users["demo"] = {
                "username": "demo",
                "display_name": "Demo User",
                "role": "user",
                "uid": 1000,
                "gid": 1000,
                "home": "/home/demo",
                "password_hash": hash_password("demo"),
                "created": "2026-01-01T00:00:00",
            }

        try:
            with open(user_file, "w") as f:
                json.dump(users, f, indent=2)
        except Exception as _exc:
            logger.debug("Suppressed exception in first_run_wizard.py: %s", _exc)


def is_first_run():
    config_file = Path.home() / ".qvault" / "config.json"
    if not config_file.exists():
        return True

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get("first_run", True)
    except Exception:
        return True


def run_first_run_wizard():
    return is_first_run()
