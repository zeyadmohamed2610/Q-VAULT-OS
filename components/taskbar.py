# =============================================================
#  taskbar.py - Q-Vault OS  |  Taskbar (v2 - with CPU/RAM)
# =============================================================

from PyQt5.QtCore import QDateTime, Qt, QTimer
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from assets import theme


class Taskbar(QWidget):
    TASKBAR_HEIGHT = 42

    def __init__(self, on_start_clicked, parent=None):
        super().__init__(parent)
        self.setObjectName("Taskbar")
        self.setFixedHeight(self.TASKBAR_HEIGHT)
        self.setStyleSheet(theme.TASKBAR_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(4)

        self._start_btn = QPushButton(theme.BRAND_WORDMARK)
        self._start_btn.setObjectName("StartBtn")
        self._start_btn.clicked.connect(on_start_clicked)
        layout.addWidget(self._start_btn)

        sep = QWidget()
        sep.setObjectName("TbSep")
        sep.setFixedSize(1, 24)
        layout.addWidget(sep)

        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(2)
        self._btn_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addLayout(self._btn_layout)

        layout.addStretch()

        self._user_lbl = QLabel()
        self._user_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:11px;"
            f"font-family:'Consolas',monospace; padding:0 8px;"
        )
        self._refresh_user()
        layout.addWidget(self._user_lbl)

        sep2 = QWidget()
        sep2.setObjectName("TbSep")
        sep2.setFixedSize(1, 24)
        layout.addWidget(sep2)

        self._cpu_lbl = QLabel("CPU: 0%")
        self._cpu_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding:0 4px;"
        )
        layout.addWidget(self._cpu_lbl)

        self._ram_lbl = QLabel("RAM: 0%")
        self._ram_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding:0 4px;"
        )
        layout.addWidget(self._ram_lbl)

        sep_ws = QWidget()
        sep_ws.setObjectName("TbSep")
        sep_ws.setFixedSize(1, 24)
        layout.addWidget(sep_ws)

        self._workspace_lbl = QLabel("1/2")
        self._workspace_lbl.setToolTip("Workspace (Ctrl+Alt+Arrow)")
        self._workspace_lbl.setStyleSheet(
            f"color:{theme.ACCENT_CYAN}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding:0 4px;"
        )
        layout.addWidget(self._workspace_lbl)

        sep3 = QWidget()
        sep3.setObjectName("TbSep")
        sep3.setFixedSize(1, 24)
        layout.addWidget(sep3)

        self._risk_lbl = QLabel("  SHIELD: OK  ")
        self._risk_lbl.setStyleSheet(
            f"color: {theme.ACCENT_GREEN}; font-size: 10px; font-weight: bold;"
            f"font-family: 'Consolas', monospace; border: 1px solid {theme.ACCENT_GREEN};"
            "border-radius: 3px; padding: 2px 4px; margin-right: 5px;"
        )
        layout.addWidget(self._risk_lbl)

        self._hw_lbl = QLabel("● LINK")
        self._hw_lbl.setToolTip("Hardware Link Status")
        self._hw_lbl.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-size: 10px; font-weight: bold; padding: 0 5px;"
        )
        layout.addWidget(self._hw_lbl)

        self._clock = QLabel()
        self._clock.setObjectName("ClockLabel")
        self._tick()
        layout.addWidget(self._clock)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.timeout.connect(self._refresh_user)
        timer.timeout.connect(self._update_system_stats)
        timer.start(1000)

        self._buttons: dict[str, QPushButton] = {}
        self._active_id: str | None = None

    def _update_system_stats(self):
        from system.system_info import SYSINFO

        # Get real system stats
        cpu_val = SYSINFO.get_cpu_usage()
        ram_info = SYSINFO.get_ram_usage()
        ram_val = ram_info[2]  # percentage

        cpu_col = (
            theme.ACCENT_GREEN
            if cpu_val < 50
            else (theme.ACCENT_AMBER if cpu_val < 80 else theme.ACCENT_RED)
        )
        ram_col = (
            theme.ACCENT_GREEN
            if ram_val < 50
            else (theme.ACCENT_AMBER if ram_val < 80 else theme.ACCENT_RED)
        )

        self._cpu_lbl.setText(f"CPU: {cpu_val}%")
        self._cpu_lbl.setStyleSheet(
            f"color:{cpu_col}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding:0 4px;"
        )

        self._ram_lbl.setText(f"RAM: {ram_val}%")
        self._ram_lbl.setStyleSheet(
            f"color:{ram_col}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding:0 4px;"
        )

    def _tick(self):
        self._clock.setText(QDateTime.currentDateTime().toString("HH:mm  ddd dd MMM"))

    def _refresh_user(self):
        try:
            from core.system_state import STATE
            from system.security_system import SEC

            user = STATE.username()
            role = STATE.current_user.role if STATE.current_user else ""
            icon = "👑" if role == "admin" else "👤"
            tag = " [fake]" if STATE.session_type == "fake" else ""
            self._user_lbl.setText(f"{icon} {user}{tag}")

            level = SEC.risk_level
            if level == "HIGH":
                self._risk_lbl.setText("  SHIELD: CRITICAL  ")
                self._risk_lbl.setStyleSheet(
                    f"color: {theme.ACCENT_RED}; border: 1px solid {theme.ACCENT_RED};"
                    "border-radius:3px; padding:2px 4px;"
                )
            elif level == "MEDIUM":
                self._risk_lbl.setText("  SHIELD: WARNING   ")
                self._risk_lbl.setStyleSheet(
                    f"color: {theme.ACCENT_AMBER}; border: 1px solid {theme.ACCENT_AMBER};"
                    "border-radius:3px; padding:2px 4px;"
                )
            else:
                self._risk_lbl.setText("  SHIELD: OK        ")
                self._risk_lbl.setStyleSheet(
                    f"color: {theme.ACCENT_GREEN}; border: 1px solid {theme.ACCENT_GREEN};"
                    "border-radius:3px; padding:2px 4px;"
                )

            self._hw_lbl.setText("● SIM")
        except Exception:
            self._user_lbl.setText("")

    def add_window_button(self, window_id: str, title: str, on_click):
        btn = QPushButton(title)
        btn.setObjectName("TaskbarBtn")
        btn.clicked.connect(on_click)
        self._btn_layout.addWidget(btn)
        self._buttons[window_id] = btn

    def remove_window_button(self, window_id: str):
        btn = self._buttons.pop(window_id, None)
        if btn:
            self._btn_layout.removeWidget(btn)
            btn.deleteLater()
        if self._active_id == window_id:
            self._active_id = None

    def set_active(self, window_id: str | None):
        if self._active_id and self._active_id in self._buttons:
            self._set_btn_active(self._buttons[self._active_id], False)

        self._active_id = window_id

        if window_id and window_id in self._buttons:
            self._set_btn_active(self._buttons[window_id], True)

    def _set_btn_active(self, btn: QPushButton, active: bool):
        btn.setProperty("active", "true" if active else "false")
        try:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        except Exception:
            pass
        btn.update()

    def set_workspace(self, current: int, total: int):
        """Update workspace indicator"""
        self._workspace_lbl.setText(f"{current + 1}/{total}")
