from assets.theme import *
# =============================================================
#  components/onboarding_flow.py — Q-Vault OS
#
#  User Welcome & Education Layer.
#  Explains shortcuts and system capabilities on first run.
# =============================================================

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget
from PyQt5.QtCore import Qt, QRect
from core.event_bus import EVENT_BUS, SystemEvent

class OnboardingFlow(QFrame):
    """
    Step-by-step introduction to Q-Vault OS.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 400)
        self.setObjectName("Onboarding")
        
        self.setStyleSheet(f"""
            QFrame#Onboarding {{
                background: {THEME['surface_mid']};
                border: 2px solid {THEME['primary_glow']};
                border-radius: 20px;
            }}
            QLabel {{ color: white; font-family: 'Segoe UI'; text-align: center; }}
            QPushButton {{
                background: {THEME['primary_glow']};
                color: black;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background: white; }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        # ───── Close Button ─────
        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.move(460, 10)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {THEME['text_disabled']};
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ color: {THEME['accent_error']}; }}
        """)
        self.btn_close.clicked.connect(self._finish)

        self._drag_pos = None
        
        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_welcome_page())
        self.pages.addWidget(self._create_shortcuts_page())
        self.pages.addWidget(self._create_final_page())
        
        self.layout.addWidget(self.pages)

    def _create_welcome_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Welcome to Q-Vault OS")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        l.addWidget(title)
        
        desc = QLabel("The first fully autonomous, event-driven operating system simulation.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {THEME['text_muted']}; margin-top: 10px;")
        l.addWidget(desc)
        
        l.addStretch()
        btn = QPushButton("GET STARTED")
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        l.addWidget(btn)
        return page

    def _create_shortcuts_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        
        title = QLabel("Master the Interface")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        l.addWidget(title)
        
        shortcuts = [
            ("Ctrl + Space", "Command Palette / AI"),
            ("F12", "System Observability"),
            ("Ctrl + Alt + S", "Settings & Health"),
            ("Win / Super", "App Launcher")
        ]
        
        for key, desc in shortcuts:
            row = QLabel(f"<b>{key}</b> — {desc}")
            row.setStyleSheet("margin-top: 15px; font-size: 14px;")
            l.addWidget(row)
            
        l.addStretch()
        btn = QPushButton("CONTINUE")
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        l.addWidget(btn)
        return page

    def _create_final_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setAlignment(Qt.AlignCenter)
        
        title = QLabel("You're Ready.")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        l.addWidget(title)
        
        desc = QLabel("Explore the terminal, try the AI assistant, and watch the system orchestrate your workflows.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {THEME['text_muted']}; margin-top: 10px;")
        l.addWidget(desc)
        
        l.addStretch()
        btn = QPushButton("ENTER Q-VAULT")
        btn.clicked.connect(self._finish)
        l.addWidget(btn)
        return page

    def _finish(self):
        # Trigger welcome workflow (Phase 7)
        EVENT_BUS.emit(SystemEvent.REQ_WORKFLOW_EXECUTE, {"name": "welcome_sequence"}, source="Onboarding")
        self.hide()
        self.deleteLater()

    def show_centered(self, parent_rect: QRect):
        x = (parent_rect.width() - self.width()) // 2
        y = (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()

    # ───── DRAGGING LOGIC ─────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.pos() - self._drag_pos
            self.move(self.pos() + delta)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
