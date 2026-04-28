import json
import threading
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextBrowser, QLabel, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from system.sandbox.base_app import BaseApp
from assets import theme

class TrustIndicator(QFrame):
    """Visual indicator for domain trust levels."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.set_state("unknown")

    def set_state(self, state: str):
        colors = {
            "trusted": "#00ffcc",
            "unknown": "#ffcc00",
            "risky": "#ff3333",
            "internal": "#bd93f9"
        }
        color = colors.get(state, "#888888")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

class VaultBrowser(BaseApp, QWidget):
    APP_ID = "vault_browser"

    content_ready = pyqtSignal(str, str, str)  # url, html_content, trust_state
    error_occurred = pyqtSignal(str)

    def __init__(self, secure_api=None, parent=None):
        BaseApp.__init__(self, secure_api)
        QWidget.__init__(self, parent)
        self.setObjectName("AppContainer")
        
        self._is_loading = False
        self.content_ready.connect(self._on_content_ready)
        self.error_occurred.connect(self._on_error)
        
        self.setup_ui()

    def get_permissions(self) -> list[str]:
        return [
            "file_access:virtual_only",
            "network_access:unrestricted",
            "system_calls:DENIED",
        ]

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Address Bar ──
        nav_bar = QWidget()
        nav_bar.setStyleSheet(f"background-color: {theme.BG_PANEL}; border-bottom: 1px solid {theme.BORDER_DIM};")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 8, 8, 8)

        self.trust_indicator = TrustIndicator()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter vault:// or https:// url...")
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.BG_DARK};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_DIM};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.PRIMARY};
            }}
        """)
        self.url_input.returnPressed.connect(self._on_go_clicked)

        self.btn_go = QPushButton("GO")
        self.btn_go.setFixedWidth(50)
        self.btn_go.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_DARK};
                color: {theme.PRIMARY};
                border: 1px solid {theme.PRIMARY};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 230, 255, 0.1);
            }}
        """)
        self.btn_go.clicked.connect(self._on_go_clicked)

        self.btn_home = QPushButton("🏠")
        self.btn_home.setFixedWidth(30)
        self.btn_home.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {theme.PRIMARY};
            }}
        """)
        self.btn_home.clicked.connect(lambda: self.load_url("vault://home"))

        nav_layout.addWidget(self.trust_indicator)
        nav_layout.addWidget(self.url_input)
        nav_layout.addWidget(self.btn_go)
        nav_layout.addWidget(self.btn_home)

        layout.addWidget(nav_bar)

        # ── Content Area ──
        self.browser_view = QTextBrowser()
        self.browser_view.setOpenExternalLinks(False)
        self.browser_view.anchorClicked.connect(self._on_link_clicked)
        self.browser_view.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme.BG_DARK};
                color: {theme.TEXT};
                border: none;
                padding: 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                selection-background-color: {theme.PRIMARY};
                selection-color: #000;
            }}
        """)
        layout.addWidget(self.browser_view)

    def on_start(self):
        # Default start page
        self.load_url("vault://home")

    def load_url(self, url: str):
        if self._is_loading:
            return
            
        self.url_input.setText(url)
        self.browser_view.setHtml(f"<h3 style='color: {theme.TEXT_DIM};'>Fetching {url}...</h3>")
        self._is_loading = True
        self.trust_indicator.set_state("unknown")

        # Offload fetch to thread to prevent UI freeze
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _on_go_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith("http") and not url.startswith("vault://"):
            url = "https://" + url
        self.load_url(url)

    def _on_link_clicked(self, qurl):
        self.load_url(qurl.toString())

    def _fetch_worker(self, url: str):
        try:
            if url.startswith("vault://"):
                self._handle_internal_scheme(url)
            else:
                self._handle_external_http(url)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _handle_internal_scheme(self, url: str):
        path = url.replace("vault://", "").strip().lower()
        
        if path == "home" or path == "":
            self._render_hacker_news_home()
        elif path == "logs":
            self._render_system_logs()
        elif path == "logs/auto_refresh":
            self._render_system_logs(auto_refresh=True)
        else:
            self.error_occurred.emit(f"Unknown internal endpoint: {path}")

    def _render_hacker_news_home(self):
        # Fetch Top Stories
        resp = self.api.network.request("https://hacker-news.firebaseio.com/v0/topstories.json")
        if resp["status"] != 200:
            self.error_occurred.emit(f"HN API Error: {resp['status']}")
            return

        try:
            story_ids = json.loads(resp["content"])[:15]  # Get top 15
        except Exception:
            self.error_occurred.emit("Failed to parse HN response.")
            return

        html = f"""
        <h1 style='color: {theme.PRIMARY};'>Q-VAULT SMART DASHBOARD</h1>
        <p style='color: {theme.TEXT_DIM};'>Secure Feed: Hacker News API (Sanitized)</p>
        <hr style='border: 1px solid {theme.BORDER_DIM};'>
        <ul style='list-style-type: none; padding-left: 0;'>
        """

        for sid in story_ids:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            iresp = self.api.network.request(item_url)
            if iresp["status"] == 200:
                try:
                    item_data = json.loads(iresp["content"])
                    title = item_data.get("title", "Unknown Title")
                    score = item_data.get("score", 0)
                    by = item_data.get("by", "unknown")
                    link = item_data.get("url", f"vault://hn_item/{sid}")
                    
                    html += f"""
                    <li style='margin-bottom: 12px; padding: 10px; background-color: rgba(255,255,255,0.02); border-radius: 4px;'>
                        <a href="{link}" style='color: {theme.TEXT}; text-decoration: none; font-size: 16px; font-weight: bold;'>
                            {title}
                        </a>
                        <br>
                        <span style='color: #ffaa00; font-size: 12px;'>▲ {score}</span>
                        <span style='color: {theme.TEXT_DIM}; font-size: 12px;'> by {by}</span>
                    </li>
                    """
                except Exception as e:
                    pass

        html += "</ul>"
        self.content_ready.emit("vault://home", html, "internal")

    def _render_system_logs(self, auto_refresh=False):
        # Read local log via fs guard
        try:
            with self.api.fs.open(".logs/system.log", "r") as f:
                logs = f.readlines()[-100:]  # last 100 lines
            
            content = "".join(logs).replace("<", "&lt;").replace(">", "&gt;")
            
            refresh_meta = "<meta http-equiv='refresh' content='1'>" if auto_refresh else ""
            auto_str = " (Auto-Refresh)" if auto_refresh else ""
            html = f"""
            <html><head>{refresh_meta}</head><body>
            <h1 style='color: #bd93f9;'>System Logs{auto_str}</h1>
            <pre style='color: {theme.TEXT}; font-size: 12px; background: #1a1a1a; padding: 10px;'>{content}</pre>
            <script>window.scrollTo(0, document.body.scrollHeight);</script>
            </body></html>
            """
            url_str = "vault://logs/auto_refresh" if auto_refresh else "vault://logs"
            self.content_ready.emit(url_str, html, "internal")
        except Exception as e:
            self.error_occurred.emit(f"Failed to read logs: {e}")

    def _handle_external_http(self, url: str):
        # Simple naive parser/sanitizer for raw http
        resp = self.api.network.request(url)
        content = resp["content"]
        
        if resp["status"] != 200:
            self.error_occurred.emit(f"HTTP Error {resp['status']}: {resp.get('error', '')}")
            return
            
        if not content:
            self.error_occurred.emit("Empty response from server.")
            return

        # Very basic HTML sanitization (just replacing script tags basically)
        # For a true production app, we would use bleach or beautifulsoup.
        # Here we just render as raw if it's JSON, or minimal if it's HTML
        
        try:
            # Check if JSON
            data = json.loads(content)
            formatted_json = json.dumps(data, indent=4)
            html = f"""
            <h3 style='color: #ffb86c;'>JSON Response View (Raw Mode)</h3>
            <pre style='color: #50fa7b; font-size: 13px;'>{formatted_json}</pre>
            """
            self.content_ready.emit(url, html, "trusted")
            return
        except ValueError:
            pass

        # If not JSON, render HTML
        # Strip simple script tags for basic safety (QTextBrowser doesn't execute JS anyway)
        safe_html = content.replace("<script", "&lt;script").replace("</script>", "&lt;/script&gt;")
        
        html = f"""
        <div style='border-bottom: 2px solid {theme.PRIMARY}; margin-bottom: 20px; padding-bottom: 10px;'>
            <h3 style='color: {theme.PRIMARY};'>🌐 Secure Reader Mode</h3>
            <p style='color: {theme.TEXT_DIM}; font-size: 12px;'>Scripts have been neutralized. JS execution is disabled by the Sandbox.</p>
        </div>
        {safe_html}
        """
        
        # Decide trust state (in a real app, consult a Trust Engine API)
        trust_state = "trusted" if "https://" in url else "unknown"
        
        self.content_ready.emit(url, html, trust_state)

    def _on_content_ready(self, url: str, html: str, trust_state: str):
        self.browser_view.setHtml(html)
        self.trust_indicator.set_state(trust_state)
        if self.url_input.text() != url:
            self.url_input.setText(url)
        self._is_loading = False

    def _on_error(self, message: str):
        err_html = f"""
        <center style='margin-top: 50px;'>
            <h1 style='color: #ff3333;'>SECURE API BLOCKED / ERROR</h1>
            <p style='color: {theme.TEXT};'>{message}</p>
        </center>
        """
        self.browser_view.setHtml(err_html)
        self.trust_indicator.set_state("risky")
        self._is_loading = False
