# =============================================================
#  settings_app.py — Q-Vault OS  |  Settings (Finalized)
#
#  Finalization fixes:
#    ✓ Danger Zone has three distinct actions:
#        Log Out   — returns to login screen
#        Restart   — toast + 800ms delay → login
#        Shut Down — toast + 1s delay → QApplication.quit()
#    ✓ Devices page shows live STATE values
# =============================================================

from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QStackedWidget,
    QCheckBox,
    QComboBox,
    QFrame,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QTimer

from core.system_state import STATE
from system.session_manager import SESSION
from system.security_system import SEC
from assets import theme


STYLE = f"""
    QWidget#Settings {{ background: {theme.BG_WINDOW}; }}

    QWidget#Sidebar {{
        background: #0a0e14;
        border-right: 1px solid {theme.BORDER_DIM};
        min-width: 170px; max-width: 170px;
    }}
    QLabel#SideTitle {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 13px; font-weight: bold;
        padding: 16px 14px 8px 14px; background: transparent;
    }}
    QPushButton#SideBtn {{
        background: transparent; color: {theme.TEXT_DIM};
        border: none; border-left: 3px solid transparent;
        padding: 10px 14px; font-size: 12px;
        font-family: 'Consolas', monospace; text-align: left;
    }}
    QPushButton#SideBtn:hover {{
        background: {theme.BG_HOVER}; color: {theme.TEXT_PRIMARY};
    }}
    QPushButton#SideBtn[active="true"] {{
        color: {theme.ACCENT_CYAN};
        border-left: 3px solid {theme.ACCENT_CYAN};
        background: {theme.BG_SELECTED};
    }}

    QWidget#SettingsPage {{ background: {theme.BG_WINDOW}; }}
    QLabel#PageTitle {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 15px; font-weight: bold;
        padding: 16px 0 6px 0; background: transparent;
    }}
    QLabel#SectionLabel {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 10px; letter-spacing: 1px;
        background: transparent; padding: 10px 0 2px 0;
    }}
    QLabel#InfoValue {{
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace; font-size: 12px;
        background: rgba(0,0,0,40);
        border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; padding: 6px 10px;
    }}
    QLineEdit#SettingField {{
        background: {theme.BG_DARK}; color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace; font-size: 13px;
        border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; padding: 7px 10px;
    }}
    QLineEdit#SettingField:focus {{ border: 1px solid {theme.BORDER_BRIGHT}; }}
    QPushButton#ActionBtn {{
        background: {theme.ACCENT_CYAN}; color: {theme.BG_DARK};
        border: none; border-radius: 4px; padding: 7px 20px;
        font-family: 'Consolas', monospace; font-size: 12px; font-weight: bold;
    }}
    QPushButton#ActionBtn:hover {{ background: #33ddff; }}
    QPushButton#DangerBtn {{
        background: transparent; color: {theme.ACCENT_RED};
        border: 1px solid {theme.ACCENT_RED}; border-radius: 4px; padding: 7px 20px;
        font-family: 'Consolas', monospace; font-size: 12px;
    }}
    QPushButton#DangerBtn:hover {{
        background: {theme.ACCENT_RED}; color: white;
    }}
    QPushButton#SecondaryBtn {{
        background: transparent; color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; padding: 7px 20px;
        font-family: 'Consolas', monospace; font-size: 12px;
    }}
    QPushButton#SecondaryBtn:hover {{
        background: {theme.BG_HOVER}; color: {theme.TEXT_PRIMARY};
    }}
    QCheckBox {{
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace; font-size: 12px; spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {theme.BORDER_DIM}; border-radius: 3px;
        background: {theme.BG_DARK};
    }}
    QCheckBox::indicator:checked {{
        background: {theme.ACCENT_CYAN}; border: 1px solid {theme.ACCENT_CYAN};
    }}
    QLabel#StatusOk   {{ color: {theme.ACCENT_GREEN}; font-family:'Consolas',monospace; font-size:12px; }}
    QLabel#StatusWarn {{ color: {theme.ACCENT_RED};   font-family:'Consolas',monospace; font-size:12px; }}
    QLabel#FeedbackOk  {{ color:{theme.ACCENT_GREEN}; font-family:'Consolas',monospace; font-size:11px; }}
    QLabel#FeedbackErr {{ color:{theme.ACCENT_RED};   font-family:'Consolas',monospace; font-size:11px; }}
"""


# ── Helpers ───────────────────────────────────────────────────


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(
        f"color:{theme.BORDER_DIM}; background:{theme.BORDER_DIM}; max-height:1px;"
    )
    return f


def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("SectionLabel")
    return lbl


def _info_row(label: str, value: str) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(f"{label}:")
    lbl.setStyleSheet(
        f"color:{theme.TEXT_DIM}; font-family:'Consolas',monospace; font-size:12px;"
    )
    lbl.setFixedWidth(130)
    val = QLabel(value)
    val.setObjectName("InfoValue")
    row.addWidget(lbl)
    row.addWidget(val, stretch=1)
    return row


class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Settings")
        self.setStyleSheet(STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sb_col = QVBoxLayout(sidebar)
        sb_col.setContentsMargins(0, 0, 0, 0)
        sb_col.setSpacing(0)

        title = QLabel("⚙  Settings")
        title.setObjectName("SideTitle")
        sb_col.addWidget(title)
        sb_col.addWidget(_divider())

        self._side_btns = []
        sections = [
            ("👤  User", self._make_user_page),
            ("🔐  Security", self._make_security_page),
            ("🖥  System", self._make_system_page),
            ("💬  Feedback", self._make_feedback_page),
        ]

        self._stack = QStackedWidget()

        for i, (label, factory) in enumerate(sections):
            btn = QPushButton(label)
            btn.setObjectName("SideBtn")
            btn.clicked.connect(lambda _, idx=i: self._show_page(idx))
            self._side_btns.append(btn)
            sb_col.addWidget(btn)

            page = factory()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            scroll.setStyleSheet("background:transparent;")
            scroll.setWidget(page)
            self._stack.addWidget(scroll)

        sb_col.addStretch()
        root.addWidget(sidebar)
        root.addWidget(self._stack, stretch=1)

        self._show_page(0)

    def _show_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._side_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    # ── Page scaffolding ──────────────────────────────────────

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("SettingsPage")
        col = QVBoxLayout(page)
        col.setContentsMargins(28, 0, 28, 20)
        col.setSpacing(8)
        col.setAlignment(Qt.AlignTop)
        lbl = QLabel(title)
        lbl.setObjectName("PageTitle")
        col.addWidget(lbl)
        col.addWidget(_divider())
        return page, col

    # ── USER PAGE ─────────────────────────────────────────────

    def _make_user_page(self) -> QWidget:
        page, col = self._page("User Account")

        col.addWidget(_section("Current Session"))
        u = STATE.current_user
        col.addLayout(_info_row("Username", u.username if u else "—"))
        col.addLayout(_info_row("Display Name", u.display_name if u else "—"))
        col.addLayout(_info_row("Role", u.role if u else "—"))
        col.addLayout(_info_row("Session Type", STATE.session_type))

        col.addSpacing(10)
        col.addWidget(_section("Change Password"))

        old_pw = QLineEdit()
        old_pw.setObjectName("SettingField")
        old_pw.setPlaceholderText("Current password")
        old_pw.setEchoMode(QLineEdit.Password)
        new_pw = QLineEdit()
        new_pw.setObjectName("SettingField")
        new_pw.setPlaceholderText("New password")
        new_pw.setEchoMode(QLineEdit.Password)
        conf_pw = QLineEdit()
        conf_pw.setObjectName("SettingField")
        conf_pw.setPlaceholderText("Confirm new password")
        conf_pw.setEchoMode(QLineEdit.Password)

        feedback = QLabel("")
        feedback.setObjectName("FeedbackOk")

        def _change():
            if new_pw.text() != conf_pw.text():
                feedback.setObjectName("FeedbackErr")
                feedback.setText("New passwords do not match.")
                feedback.setStyleSheet(STYLE)
                return
            if not STATE.current_user:
                return
            if not SESSION.verify_password(STATE.current_user.username, old_pw.text()):
                feedback.setObjectName("FeedbackErr")
                feedback.setText("Current password is incorrect.")
                feedback.setStyleSheet(STYLE)
                return
            ok, msg = SESSION.change_password(
                STATE.current_user.username, new_pw.text()
            )
            feedback.setObjectName("FeedbackOk" if ok else "FeedbackErr")
            feedback.setText(msg)
            feedback.setStyleSheet(STYLE)
            if ok:
                old_pw.clear()
                new_pw.clear()
                conf_pw.clear()

        btn = QPushButton("Save Password")
        btn.setObjectName("ActionBtn")
        btn.clicked.connect(_change)

        col.addWidget(old_pw)
        col.addWidget(new_pw)
        col.addWidget(conf_pw)
        col.addWidget(btn)
        col.addWidget(feedback)
        col.addStretch()
        return page

    # ── SECURITY PAGE ─────────────────────────────────────────

    def _make_security_page(self) -> QWidget:
        page, col = self._page("Security Settings")

        col.addWidget(_section("Risk Level"))

        from system.security_system import RISK_COLORS

        risk_lbl = QLabel(f"Current: {SEC.risk_level}")
        risk_lbl.setStyleSheet(
            f"color:{RISK_COLORS.get(SEC.risk_level, theme.TEXT_DIM)};"
            f"font-family:'Consolas',monospace; font-size:14px; font-weight:bold;"
        )
        col.addWidget(risk_lbl)

        def _clear_risk():
            SEC.clear_risk()
            from system.security_system import RISK_COLORS

            risk_lbl.setText(f"Current: {SEC.risk_level}")
            risk_lbl.setStyleSheet(
                f"color:{RISK_COLORS.get(SEC.risk_level, theme.TEXT_DIM)};"
                f"font-family:'Consolas',monospace;font-size:14px;font-weight:bold;"
            )

        btn_clear = QPushButton("✓  Clear Risk to LOW")
        btn_clear.setObjectName("ActionBtn")
        btn_clear.clicked.connect(_clear_risk)
        col.addWidget(btn_clear)

        col.addSpacing(10)
        col.addWidget(_section("Alert Settings"))

        chk = QCheckBox("Enable Security Alerts")
        chk.setChecked(STATE.alerts_enabled)
        chk.stateChanged.connect(lambda v: setattr(STATE, "alerts_enabled", bool(v)))
        col.addWidget(chk)

        col.addSpacing(10)
        col.addWidget(_section("Event Log"))
        col.addWidget(self._dim_label(f"Total events logged: {len(SEC.get_log())}"))

        btn_test = QPushButton("🧪 Inject Test Intrusion")
        btn_test.setObjectName("SecondaryBtn")
        btn_test.clicked.connect(
            lambda: SEC.report(
                "INTRUSION_DETECTED",
                source="settings_test",
                detail="Manual test from Settings.",
                escalate=True,
            )
        )
        col.addWidget(btn_test)
        col.addStretch()
        return page

    # ── SYSTEM PAGE ───────────────────────────────────────────

    def _make_system_page(self) -> QWidget:
        page, col = self._page("System Settings")

        col.addWidget(_section("Session Information"))
        for label, value in STATE.summary().items():
            col.addLayout(_info_row(label.replace("_", " ").title(), str(value)))

        col.addSpacing(10)
        col.addWidget(_section("Preferences"))

        chk_anim = QCheckBox("Enable Window Animations")
        chk_anim.setChecked(STATE.animations_enabled)
        chk_anim.stateChanged.connect(
            lambda v: setattr(STATE, "animations_enabled", bool(v))
        )
        col.addWidget(chk_anim)

        col.addSpacing(10)
        col.addWidget(_section("Wallpaper"))

        wallpaper_label = QLabel("Select desktop background:")
        col.addWidget(wallpaper_label)

        wallpaper_combo = QComboBox()
        wallpaper_combo.addItems(
            ["Cyberpunk Dark", "Deep Blue", "Hacker Green", "Minimal"]
        )
        col.addWidget(wallpaper_combo)

        def _set_wallpaper(index):
            from assets.theme import (
                DESKTOP_GRADIENT_START,
                DESKTOP_GRADIENT_MID,
                DESKTOP_GRADIENT_END,
            )

            gradients = [
                ("#0a0a0f", "#0f172a", "#020617"),
                ("#0a0a1a", "#0f1a2e", "#020412"),
                ("#0a0f0a", "#0f1f0f", "#020806"),
                ("#0a0a0a", "#0d0d0d", "#050505"),
            ]
            if index < len(gradients):
                from assets import theme

                theme.DESKTOP_GRADIENT_START = gradients[index][0]
                theme.DESKTOP_GRADIENT_MID = gradients[index][1]
                theme.DESKTOP_GRADIENT_END = gradients[index][2]
                from PyQt5.QtWidgets import QApplication

                QApplication.processEvents()
                parent = self
                while parent:
                    if hasattr(parent, "update"):
                        parent.update()
                    parent = parent.parent()

        wallpaper_combo.currentIndexChanged.connect(_set_wallpaper)

        col.addSpacing(10)
        col.addWidget(_section("Danger Zone"))

        btn_logout = QPushButton("⏻  Log Out")
        btn_logout.setObjectName("DangerBtn")
        btn_logout.clicked.connect(self._logout)
        col.addWidget(btn_logout)

        btn_restart = QPushButton("🔄  Restart System")
        btn_restart.setObjectName("DangerBtn")
        btn_restart.clicked.connect(self._restart)
        col.addWidget(btn_restart)

        btn_shutdown = QPushButton("⏹  Shut Down")
        btn_shutdown.setObjectName("DangerBtn")
        btn_shutdown.clicked.connect(self._shutdown)
        col.addWidget(btn_shutdown)

        note = self._dim_label(
            "Restart returns to login.  Shut Down closes the application."
        )
        col.addWidget(note)

        col.addStretch()
        return page

    def _logout(self):
        """Walk up the widget tree to find QVaultOS.show_login()."""
        parent = self
        while parent:
            if hasattr(parent, "show_login"):
                parent.show_login()
                return
            parent = parent.parent()
        from PyQt5.QtWidgets import QApplication

        QApplication.quit()

    def _restart(self):
        try:
            from system.notification_system import NOTIFY

            NOTIFY.send("Restarting", "Returning to login screen…", level="warning")
        except Exception:
            pass
        QTimer.singleShot(800, self._logout)

    def _shutdown(self):
        try:
            from system.notification_system import NOTIFY

            NOTIFY.send(
                "Shutting Down", "Goodbye. Closing Q-Vault OS…", level="warning"
            )
        except Exception:
            pass
        from PyQt5.QtWidgets import QApplication

        QTimer.singleShot(1000, QApplication.quit)

    # ── Widget helpers ────────────────────────────────────────

    @staticmethod
    def _status_lbl(text: str, ok: bool) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("StatusOk" if ok else "StatusWarn")
        return lbl

    @staticmethod
    def _dim_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px;font-family:'Consolas',monospace;"
        )
        return lbl

    def _make_feedback_page(self) -> QWidget:
        page, col = self._page('Feedback')

        info = QLabel(
            'Help us improve Q-VAULT OS! Submit feedback, report bugs, '
            'or suggest new features.'
        )
        info.setWordWrap(True)
        info.setStyleSheet(f'color: {theme.TEXT_DIM}; font-size: 12px; margin-bottom: 10px;')
        col.addWidget(info)

        send_btn = QPushButton('📝 Submit Feedback')
        send_btn.setObjectName('ActionBtn')
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self._open_feedback_dialog)
        col.addWidget(send_btn)

        col.addWidget(_divider())

        stats_label = QLabel('Feedback Statistics')
        stats_label.setStyleSheet(f'color: {theme.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;')
        col.addWidget(stats_label)

        from pathlib import Path
        feedback_dir = Path.home() / '.qvault' / 'feedback'
        feedback_file = feedback_dir / 'pending_feedback.json'

        count = 0
        if feedback_file.exists():
            try:
                import json
                with open(feedback_file, 'r') as f:
                    count = len(json.load(f))
            except Exception:
                pass

        count_label = QLabel(f'Pending submissions: {count}')
        count_label.setStyleSheet(f'color: {theme.TEXT_DIM}; font-size: 12px;')
        col.addWidget(count_label)

        col.addStretch()
        return page

    def _open_feedback_dialog(self):
        try:
            from components.feedback_dialog import show_feedback_dialog
            show_feedback_dialog(self)
        except Exception as e:
            from system.notification_system import NOTIFY
            NOTIFY.send('Error', f'Could not open feedback: {e}', level='error')
