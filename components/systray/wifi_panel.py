from __future__ import annotations
import subprocess
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter

logger = logging.getLogger(__name__)


# ── Background scanner ────────────────────────────────────────

class WifiScanner(QThread):
    networks_found = pyqtSignal(list)

    def run(self):
        import platform
        sys_name = platform.system()
        nets = []
        if sys_name == "Linux":
            nets = self._scan_linux()
        elif sys_name == "Windows":
            nets = self._scan_windows()
        
        if not nets:
            nets = self._fallback()
        self.networks_found.emit(nets)

    def _scan_linux(self) -> list[dict]:
        try:
            r = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
                capture_output=True, text=True, timeout=5
            )
            nets = []
            for line in r.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 2 and parts[0].strip():
                    sig = int(parts[1]) if parts[1].strip().isdigit() else 50
                    sec = len(parts) > 2 and parts[2].strip() not in ("", "--")
                    nets.append({"ssid": parts[0].strip(), "signal": sig, "secured": sec})
            return nets
        except Exception as exc:
            logger.debug("Linux WiFi scan failed: %s", exc)
            return []

    def _scan_windows(self) -> list[dict]:
        try:
            r = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, timeout=5
            )
            nets = []; cur: dict = {}
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    if cur: nets.append(cur)
                    cur = {"ssid": line.split(":", 1)[-1].strip(), "signal": 50, "secured": True}
                elif "Signal" in line:
                    try: cur["signal"] = int(line.split(":", 1)[-1].strip().rstrip("%"))
                    except Exception: pass
                elif "Authentication" in line:
                    cur["secured"] = "Open" not in line
            if cur: nets.append(cur)
            return [n for n in nets if n.get("ssid")]
        except Exception as exc:
            logger.debug("Windows WiFi scan failed: %s", exc)
            return []

    def _fallback(self) -> list[dict]:
        return [
            {"ssid": "Q-Vault-Secure",  "signal": 95, "secured": True},
            {"ssid": "HomeNetwork_5G",  "signal": 78, "secured": True},
            {"ssid": "Office_WiFi",     "signal": 62, "secured": True},
            {"ssid": "AndroidHotspot",  "signal": 45, "secured": False},
            {"ssid": "DIRECT-TV-Box",   "signal": 30, "secured": True},
        ]


def _bars(strength: int) -> str:
    if strength >= 80: return "▂▄▆█"
    if strength >= 60: return "▂▄▆░"
    if strength >= 40: return "▂▄░░"
    if strength >= 20: return "▂░░░"
    return "░░░░"


# ── Network row ───────────────────────────────────────────────

class NetworkRow(QWidget):
    def __init__(self, ssid: str, signal: int, secured: bool, connected: bool = False):
        super().__init__()
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self._hov = False
        self.setStyleSheet("NetworkRow { background: transparent; border-radius: 6px; }")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        lock = QLabel("🔒" if secured else "🔓")
        lock.setFixedWidth(18)
        lock.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(lock)

        name = QLabel(ssid)
        name.setFont(QFont("Segoe UI", 10))
        col = "#54b1c6" if connected else "#d4e8f0"
        name.setStyleSheet(f"color:{col}; background:transparent;")
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(name, 1)

        if connected:
            badge = QLabel("Connected")
            badge.setStyleSheet(
                "color:#3fb950; font-size:9px;"
                "background:rgba(63,185,80,0.15);"
                "border-radius:4px; padding:1px 5px;"
            )
            lay.addWidget(badge)

        bars = QLabel(_bars(signal))
        bars.setStyleSheet("color:#54b1c6; font-size:11px; background:transparent;")
        bars.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(bars)

    def enterEvent(self, e): self._hov = True;  self.update()
    def leaveEvent(self, e): self._hov = False; self.update()
    def paintEvent(self, event):
        if self._hov:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(84, 177, 198, 25))
            p.drawRoundedRect(self.rect(), 8, 8)
            p.end()
        super().paintEvent(event)


# ── WiFi Panel popup ──────────────────────────────────────────

class WifiPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedWidth(300)
        self._build_ui()
        self._scan()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("PanelCard")
        self._card.setStyleSheet("""
            QFrame#PanelCard {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 rgba(15, 30, 55, 240),
                                                  stop:1 rgba(4, 15, 34, 250));
                border: 1px solid rgba(84,177,198,0.4);
                border-radius: 16px;
            }
            QWidget { background: transparent; color: #d4e8f0; }
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #0b162d; width: 4px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #2f6183; border-radius: 2px; min-height: 20px;
            }
        """)
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(0, 12, 0, 12)
        cl.setSpacing(0)

        # Header row
        hrow = QHBoxLayout()
        hrow.setContentsMargins(16, 0, 16, 8)
        title = QLabel("📶  Wi-Fi")
        title.setFont(QFont("Segoe UI Semibold", 11))
        title.setStyleSheet("color:#d4e8f0; background:transparent;")
        hrow.addWidget(title)
        hrow.addStretch()

        self._tog = QPushButton("On")
        self._tog.setCheckable(True)
        self._tog.setChecked(True)
        self._tog.setFixedSize(42, 22)
        self._tog.setStyleSheet(
            "QPushButton{background:#54b1c6;color:#01020e;"
            "border:none;border-radius:11px;font-size:10px;font-weight:bold;}"
            "QPushButton:!checked{background:#243558;color:#4a6880;}"
        )
        self._tog.clicked.connect(self._toggle)
        hrow.addWidget(self._tog)
        cl.addLayout(hrow)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:rgba(84,177,198,0.1);")
        div.setFixedHeight(1)
        cl.addWidget(div)
        cl.addSpacing(4)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFixedHeight(220)

        self._nets_w = QWidget()
        self._nets_l = QVBoxLayout(self._nets_w)
        self._nets_l.setContentsMargins(0, 0, 0, 0)
        self._nets_l.setSpacing(0)
        scroll.setWidget(self._nets_w)
        cl.addWidget(scroll)

        self._loading = QLabel("Scanning networks…")
        self._loading.setAlignment(Qt.AlignCenter)
        self._loading.setStyleSheet("color:#4a6880;font-size:10px;background:transparent;")
        self._nets_l.addWidget(self._loading)

        outer.addWidget(self._card)

    def _scan(self):
        self._scanner = WifiScanner()
        self._scanner.networks_found.connect(self._show_networks)
        self._scanner.start()

    def _show_networks(self, nets: list):
        while self._nets_l.count():
            item = self._nets_l.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not nets:
            lbl = QLabel("No networks found")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#4a6880; background:transparent;")
            self._nets_l.addWidget(lbl)
            return
        for i, net in enumerate(nets):
            row = NetworkRow(net["ssid"], net["signal"], net["secured"], connected=(i == 0))
            self._nets_l.addWidget(row)
        self._nets_l.addStretch()

    def _toggle(self, checked: bool):
        self._tog.setText("On" if checked else "Off")
        for i in range(self._nets_l.count()):
            w = self._nets_l.itemAt(i).widget()
            if w:
                w.setEnabled(checked)

    def popup_near(self, pos: QPoint):
        self.adjustSize()
        self.move(pos.x() - self.width() // 2,
                  pos.y() - self.height() - 8)
        self.show()
