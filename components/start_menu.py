# =============================================================
#  start_menu.py - Q-Vault OS Start Menu
# =============================================================

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from assets import theme
from core.app_registry import AppDefinition
from core.system_state import STATE


class StartMenu(QWidget):
    """
    Floating app launcher shown above the taskbar.
    The Desktop passes the active app list for the current session.
    """

    WIDTH = 340
    HEIGHT = 458

    def __init__(self, app_defs: list[AppDefinition], on_launch, parent=None):
        super().__init__(parent)
        self.setObjectName("StartMenu")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setStyleSheet(theme.START_MENU_STYLE)

        self._app_defs = list(app_defs)
        self._on_launch = on_launch
        self._app_buttons: list[tuple[str, QPushButton]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        header = QLabel(theme.BRAND_WORDMARK)
        header.setStyleSheet(
            f"color:{theme.ACCENT_ICE}; font-size:16px; font-weight:bold;"
            f"font-family:'Consolas',monospace; letter-spacing:1px;"
        )
        root.addWidget(header)

        subtitle = QLabel("Secure Workspace Control Surface")
        subtitle.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px;"
            f"font-family:'Consolas',monospace; padding-bottom:4px;"
        )
        root.addWidget(subtitle)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Search Q-Vault modules...")
        self._search.textChanged.connect(self._filter_apps)
        root.addWidget(self._search)

        lbl = QLabel("APPLICATIONS")
        lbl.setObjectName("MenuHeader")
        root.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(grid_widget)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)

        self._build_app_grid()

        scroll.setWidget(grid_widget)
        root.addWidget(scroll, stretch=1)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{theme.BORDER_DIM};")
        root.addWidget(sep)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        user_lbl = QLabel(f"👤  {STATE.username()}@q-vault")
        user_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:11px;"
            f"font-family:'Consolas',monospace;"
        )

        btn_lock = QPushButton("🔒 Lock")
        btn_lock.setObjectName("PowerBtn")
        btn_lock.clicked.connect(self._lock)

        btn_power = QPushButton("⏻ Quit")
        btn_power.setObjectName("PowerBtn")
        btn_power.clicked.connect(self._quit)

        bottom.addWidget(user_lbl)
        bottom.addStretch()
        bottom.addWidget(btn_lock)
        bottom.addWidget(btn_power)
        root.addLayout(bottom)

    def _build_app_grid(self):
        for i, app_def in enumerate(self._app_defs):
            btn = QPushButton(f"{app_def.emoji}\n{app_def.name}")
            btn.setObjectName("AppBtn")
            btn.setFixedSize(92, 76)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {theme.TEXT_PRIMARY};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    font-size: 11px;
                    font-family: 'Consolas', monospace;
                }}
                QPushButton:hover {{
                    background: {theme.BG_HOVER};
                    border: 1px solid {theme.BORDER_BRIGHT};
                    color: {theme.ACCENT_ICE};
                }}
                """
            )
            btn.clicked.connect(lambda _, n=app_def.name: self._launch(n))
            row, col = divmod(i, 3)
            self._grid.addWidget(btn, row, col)
            self._app_buttons.append((app_def.name, btn))

    def _filter_apps(self, text: str):
        query = text.lower().strip()
        for name, btn in self._app_buttons:
            btn.setVisible(not query or query in name.lower())

    def _launch(self, name: str):
        self.hide()
        self._search.clear()
        if self._on_launch:
            self._on_launch(name)

    def _lock(self):
        self.hide()
        parent = self.parent()
        if parent and hasattr(parent, "lock"):
            parent.lock()

    def _quit(self):
        from PyQt5.QtWidgets import QApplication

        QApplication.quit()

    def reposition(self):
        if not self.parent():
            return
        from components.taskbar import Taskbar

        x = 8
        y = self.parent().height() - Taskbar.TASKBAR_HEIGHT - self.HEIGHT - 8
        self.move(x, y)

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(event)
