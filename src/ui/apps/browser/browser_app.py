from __future__ import annotations
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QComboBox, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtGui import QFont

from resources.theme import THEME
logger = logging.getLogger(__name__)

# ── WebEngine availability ────────────────────────────────────
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
    _WEBENGINE = True
except ImportError as e:
    _WEBENGINE = False
    logger.warning("PyQtWebEngine not installed — browser shows install prompt. Error: %s", e, exc_info=True)

# ── Search engines ────────────────────────────────────────────
_ENGINES = {
    "Google":     "https://www.google.com/search?q={}",
    "Bing":       "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
}
_HOME = {
    "Google":     "https://www.google.com",
    "Bing":       "https://www.bing.com",
    "DuckDuckGo": "https://duckduckgo.com",
}

# ── Default startup page (overrides search-engine homepage) ───
_DEFAULT_HOME = "https://github.com/zeyadmohamed2610/Q-VAULT-OS"

# ── Stylesheets ───────────────────────────────────────────────
_TOOLBAR_STYLE = (
    f"QWidget#browser_toolbar{{"
    f"background:{THEME['bg_black']};"
    f"border-bottom:1px solid {THEME['border_subtle']};}}"
)

_URL_STYLE = (
    f"QLineEdit{{"
    f"background:{THEME['bg_dark']};"
    f"border:1px solid {THEME['border_color']};"
    f"border-radius:14px;"
    f"color:{THEME['text_main']};"
    f"font-family:'Segoe UI';"
    f"font-size:10pt;"
    f"padding:4px 14px;"
    f"selection-background-color:{THEME['hover_glow']};}}"
    f"QLineEdit:focus{{"
    f"border-color:{THEME['primary_glow']};"
    f"background:{THEME['bg_black']};}}"
)

_NAV_STYLE = (
    f"QPushButton{{"
    f"background:transparent;border:none;"
    f"color:{THEME['primary_glow']};font-size:14px;"
    f"border-radius:14px;padding:4px 8px;}}"
    f"QPushButton:hover{{background:{THEME['hover_glow']};}}"
    f"QPushButton:pressed{{background:{THEME['primary_soft']};}}"
    f"QPushButton:disabled{{color:{THEME['text_disabled']};}}"
)

_COMBO_STYLE = (
    f"QComboBox{{"
    f"background:{THEME['bg_dark']};"
    f"border:1px solid {THEME['border_subtle']};"
    f"border-radius:8px;color:{THEME['text_dim']};"
    f"font-family:'Segoe UI';font-size:9pt;"
    f"padding:3px 8px;min-width:90px;}}"
    f"QComboBox::drop-down{{border:none;}}"
    f"QComboBox:hover{{border-color:{THEME['primary_glow']};}}"
    f"QComboBox QAbstractItemView{{"
    f"background:{THEME['bg_dark']};color:{THEME['text_main']};"
    f"border:1px solid {THEME['border_color']};"
    f"selection-background-color:{THEME['hover_glow']};}}"
)

_PROGRESS_STYLE = (
    f"QProgressBar{{"
    f"background:{THEME['bg_black']};border:none;border-radius:1px;max-height:2px;}}"
    f"QProgressBar::chunk{{"
    f"background:{THEME['primary_glow']};border-radius:1px;}}"
)
if _WEBENGINE:
    class CustomWebPage(QWebEnginePage):
        def certificateError(self, error):
            logger.warning("Ignored SSL error: %s", error.errorDescription())
            return True  # Ignore SSL errors that might block rendering
        def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
            logger.debug("Browser JS: %s (%s:%s)", message, sourceID, lineNumber)


class BrowserApp(QWidget):
    """
    Q-Vault Browser — embedded browser with dark UI.
    Degrades gracefully when PyQtWebEngine is absent.
    """

    def __init__(self, secure_api=None, parent=None):
        super().__init__(parent)
        self.secure_api = secure_api
        self.setObjectName("BrowserApp")
        self._engine  = "Google"
        self._view    = None

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"background:transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._make_toolbar())
        layout.addWidget(self._make_progress())

        if _WEBENGINE:
            layout.addWidget(self._make_webview())
        else:
            layout.addWidget(self._make_install_prompt())

    def _make_toolbar(self) -> QWidget:
        tb = QWidget()
        tb.setObjectName("browser_toolbar")
        tb.setFixedHeight(52)
        tb.setStyleSheet(_TOOLBAR_STYLE)

        lay = QHBoxLayout(tb)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        self._btn_back   = self._nav_btn("←", "Back")
        self._btn_fwd    = self._nav_btn("→", "Forward")
        self._btn_reload = self._nav_btn("↺", "Reload")
        self._btn_home   = self._nav_btn("⌂", "Home")
        for b in (self._btn_back, self._btn_fwd, self._btn_reload, self._btn_home):
            lay.addWidget(b)

        self._url_bar = QLineEdit()
        self._url_bar.setStyleSheet(_URL_STYLE)
        self._url_bar.setPlaceholderText("Search or enter URL…")
        self._url_bar.returnPressed.connect(self._navigate_from_bar)
        lay.addWidget(self._url_bar, 1)

        self._combo = QComboBox()
        self._combo.addItems(list(_ENGINES.keys()))
        self._combo.setStyleSheet(_COMBO_STYLE)
        self._combo.currentTextChanged.connect(self._on_engine_changed)
        lay.addWidget(self._combo)

        return tb

    def _nav_btn(self, text: str, tip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tip)
        btn.setStyleSheet(_NAV_STYLE)
        return btn

    def _make_progress(self) -> QProgressBar:
        self._progress = QProgressBar()
        self._progress.setStyleSheet(_PROGRESS_STYLE)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        return self._progress

    def _make_webview(self) -> QWidget:
        self._view = QWebEngineView()
        self._page = CustomWebPage(self._view)
        self._view.setPage(self._page)
        self._view.setStyleSheet("background:transparent;")

        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        s.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        s.setAttribute(QWebEngineSettings.PdfViewerEnabled, True)
        
        # Set the ultra-modern User-Agent (v147) as requested by the user
        self._page.profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        )

        self._view.loadStarted.connect(self._on_load_started)
        self._view.loadProgress.connect(self._on_load_progress)
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.urlChanged.connect(self._on_url_changed)

        self._btn_back.clicked.connect(self._view.back)
        self._btn_fwd.clicked.connect(self._view.forward)
        self._btn_reload.clicked.connect(self._view.reload)
        self._btn_home.clicked.connect(self._go_home)

        self._go_home()
        return self._view

    def _make_install_prompt(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{THEME['bg_black']};")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(16)

        icon = QLabel("🌐")
        icon.setFont(QFont("Segoe UI", 48))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"color:{THEME['primary_glow']}; background:transparent;")

        title = QLabel("WebEngine Not Installed")
        title.setFont(QFont("Segoe UI Semibold", 14))
        title.setStyleSheet(f"color:{THEME['text_main']}; background:transparent;")
        title.setAlignment(Qt.AlignCenter)

        msg = QLabel(
            "Q-Vault Browser requires PyQtWebEngine.\n"
            "Install it with:\n\n"
            "pip install PyQtWebEngine"
        )
        msg.setFont(QFont("Cascadia Code, Consolas", 10))
        msg.setStyleSheet(
            f"color:{THEME['text_muted']};"
            f"background:{THEME['bg_dark']};"
            f"border:1px solid {THEME['border_subtle']};"
            f"border-radius:10px;"
            f"padding:16px 24px;"
        )
        msg.setAlignment(Qt.AlignCenter)

        for b in (self._btn_back, self._btn_fwd, self._btn_reload):
            b.setEnabled(False)
        self._btn_home.setEnabled(False)

        lay.addWidget(icon)
        lay.addWidget(title)
        lay.addWidget(msg)
        return w

    # ── Navigation ────────────────────────────────────────────

    def _navigate_from_bar(self):
        text = self._url_bar.text().strip()
        if not text:
            return
        # Detect URL vs search query
        if (text.startswith(("http://", "https://", "ftp://")) or
                ("." in text.split("/")[0] and " " not in text)):
            if not text.startswith("http"):
                text = "https://" + text
            url = QUrl(text)
        else:
            import urllib.parse
            query = urllib.parse.quote_plus(text)
            url = QUrl(_ENGINES[self._engine].format(query))
        if self._view:
            self._view.setUrl(url)

    def _go_home(self):
        """Navigate to the default home page (GitHub profile)."""
        if self._view:
            self._view.setUrl(QUrl(_DEFAULT_HOME))

    def _on_engine_changed(self, engine: str):
        self._engine = engine
        # When switching engines, navigate to that engine's home page for immediate use
        if self._view:
            self._view.setUrl(QUrl(_HOME[engine]))

    # ── WebView signals ───────────────────────────────────────

    @pyqtSlot()
    def _on_load_started(self):
        self._progress.setVisible(True)
        self._progress.setValue(0)

    @pyqtSlot(int)
    def _on_load_progress(self, pct: int):
        self._progress.setValue(pct)

    @pyqtSlot(bool)
    def _on_load_finished(self, ok: bool):
        self._progress.setVisible(False)
        self._progress.setValue(0)
        if self._view:
            hist = self._view.history()
            self._btn_back.setEnabled(hist.canGoBack())
            self._btn_fwd.setEnabled(hist.canGoForward())

    @pyqtSlot(QUrl)
    def _on_url_changed(self, url: QUrl):
        self._url_bar.setText(url.toString())
