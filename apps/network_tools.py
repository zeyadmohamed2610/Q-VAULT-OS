# =============================================================
#  network_tools.py — Q-Vault OS  |  Network Tools Panel
#
#  Tabs:
#    Ping      — ICMP ping simulation (or real via subprocess)
#    Port Scan — TCP connect scan on a target host
#    IP Info   — Show local IP info + ARP table simulation
#    Monitor   — Live packet rate counter (simulated)
#
#  All network operations run in QThread workers so the UI
#  never freezes.
# =============================================================

import socket
import subprocess
import platform
import random
import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QSpinBox
)
from PyQt5.QtCore  import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui   import QColor

from assets import theme


# ── Shared style ──────────────────────────────────────────────
STYLE = f"""
    QWidget#NetworkTools {{ background: {theme.BG_WINDOW}; }}
    QTabWidget::pane {{
        background: {theme.BG_WINDOW};
        border: 1px solid {theme.BORDER_DIM};
        border-top: none;
    }}
    QTabBar::tab {{
        background: {theme.BG_PANEL};
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        padding: 6px 16px;
        border: 1px solid {theme.BORDER_DIM};
        border-bottom: none;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {theme.BG_WINDOW};
        color: {theme.ACCENT_CYAN};
        border-bottom: 1px solid {theme.BG_WINDOW};
    }}
    QTabBar::tab:hover {{ color: {theme.TEXT_PRIMARY}; }}
    QLineEdit#NetField {{
        background: {theme.BG_DARK};
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 13px;
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 4px;
        padding: 6px 10px;
    }}
    QLineEdit#NetField:focus {{ border: 1px solid {theme.BORDER_BRIGHT}; }}
    QPushButton#NetBtn {{
        background: {theme.ACCENT_CYAN};
        color: {theme.BG_DARK};
        border: none; border-radius: 4px;
        padding: 7px 20px;
        font-family: 'Consolas', monospace;
        font-size: 12px; font-weight: bold;
    }}
    QPushButton#NetBtn:hover {{ background: #33ddff; }}
    QPushButton#NetBtn:disabled {{
        background: {theme.BORDER_DIM};
        color: {theme.TEXT_DIM};
    }}
    QPushButton#StopBtn {{
        background: {theme.ACCENT_RED};
        color: white;
        border: none; border-radius: 4px;
        padding: 7px 20px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
    }}
    QPushButton#StopBtn:hover {{ background: #ff6666; }}
    QTextEdit#NetOutput {{
        background: #080c10;
        color: {theme.ACCENT_GREEN};
        font-family: 'Consolas', monospace;
        font-size: 12px;
        border: none; padding: 8px;
    }}
    QTableWidget {{
        background: {theme.BG_DARK};
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        gridline-color: {theme.BORDER_DIM};
        border: none;
    }}
    QHeaderView::section {{
        background: {theme.BG_PANEL};
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 11px; font-weight: bold;
        border: none;
        border-bottom: 1px solid {theme.BORDER_DIM};
        padding: 4px 8px;
    }}
    QLabel#NetInfo {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 11px;
    }}
"""


# ── Worker threads ────────────────────────────────────────────

class PingWorker(QThread):
    result = pyqtSignal(str, str)   # (text, color)
    done   = pyqtSignal()

    def __init__(self, host: str, count: int):
        super().__init__()
        self._host  = host
        self._count = count
        self._stop  = False

    def run(self):
        host = self._host.strip()
        if not host:
            self.result.emit("Error: No host specified.", theme.ACCENT_RED)
            self.done.emit(); return

        self.result.emit(f"PING {host}: {self._count} packets", theme.ACCENT_CYAN)

        sent = 0; recv = 0; times = []

        for seq in range(1, self._count + 1):
            if self._stop:
                break
            try:
                start = time.time()
                # Try real ICMP via OS ping (1 packet, 1 s timeout)
                if platform.system() == "Windows":
                    cmd = ["ping", "-n", "1", "-w", "1000", host]
                else:
                    cmd = ["ping", "-c", "1", "-W", "1", host]
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3
                )
                elapsed_ms = (time.time() - start) * 1000
                sent += 1
                if proc.returncode == 0:
                    recv += 1
                    times.append(elapsed_ms)
                    self.result.emit(
                        f"  {seq}: {host}  time={elapsed_ms:.1f}ms  TTL=64",
                        theme.ACCENT_GREEN
                    )
                else:
                    self.result.emit(
                        f"  {seq}: Request timeout for {host}",
                        theme.ACCENT_RED
                    )
            except Exception:
                # Simulated ping if subprocess fails
                sent += 1
                t = round(random.uniform(8.0, 42.0), 1)
                times.append(t)
                recv += 1
                self.result.emit(
                    f"  {seq}: {host}  time={t}ms  TTL=64  (simulated)",
                    theme.TEXT_DIM
                )
            self.msleep(500)

        loss = 0 if not sent else int((1 - recv / sent) * 100)
        avg  = sum(times) / len(times) if times else 0
        mn   = min(times) if times else 0
        mx   = max(times) if times else 0
        self.result.emit("", "")
        self.result.emit(
            f"--- {host} ping statistics ---",
            theme.ACCENT_CYAN
        )
        self.result.emit(
            f"  {sent} packets transmitted, {recv} received, {loss}% packet loss",
            theme.TEXT_DIM
        )
        if times:
            self.result.emit(
                f"  round-trip min/avg/max = {mn:.1f}/{avg:.1f}/{mx:.1f} ms",
                theme.TEXT_DIM
            )
        self.done.emit()

    def stop(self): self._stop = True


class PortScanWorker(QThread):
    result   = pyqtSignal(int, str, str)   # (port, service, status)
    progress = pyqtSignal(int)
    done     = pyqtSignal()

    # Common ports to scan
    PORTS = [
        21, 22, 23, 25, 53, 80, 110, 143, 443, 465,
        587, 993, 995, 1433, 3306, 3389, 5432, 5900,
        6379, 8080, 8443, 8888, 9000, 9200, 27017,
    ]

    SERVICES = {
        21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
        53: "dns", 80: "http", 110: "pop3", 143: "imap",
        443: "https", 465: "smtps", 587: "submission",
        993: "imaps", 995: "pop3s", 1433: "mssql",
        3306: "mysql", 3389: "rdp", 5432: "postgres",
        5900: "vnc", 6379: "redis", 8080: "http-alt",
        8443: "https-alt", 8888: "jupyter", 9000: "middleware",
        9200: "elasticsearch", 27017: "mongodb",
    }

    def __init__(self, host: str, timeout: float = 0.5):
        super().__init__()
        self._host    = host
        self._timeout = timeout
        self._stop    = False

    def run(self):
        total = len(self.PORTS)
        for i, port in enumerate(self.PORTS):
            if self._stop:
                break
            self.progress.emit(int((i + 1) / total * 100))
            svc = self.SERVICES.get(port, "unknown")
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self._timeout)
                code = s.connect_ex((self._host, port))
                s.close()
                status = "open" if code == 0 else "closed"
            except Exception:
                status = "filtered"
            self.result.emit(port, svc, status)
        self.done.emit()

    def stop(self): self._stop = True


# ── Main widget ───────────────────────────────────────────────

class NetworkTools(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NetworkTools")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(self._make_ping_tab(),    "📡 Ping")
        tabs.addTab(self._make_scan_tab(),    "🔍 Port Scan")
        tabs.addTab(self._make_info_tab(),    "🌐 IP Info")
        tabs.addTab(self._make_monitor_tab(), "📊 Monitor")
        root.addWidget(tabs)

        self._workers = []

    # ── Ping Tab ──────────────────────────────────────────────

    def _make_ping_tab(self) -> QWidget:
        page = QWidget()
        col  = QVBoxLayout(page)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(8)

        row = QHBoxLayout()
        self._ping_host  = QLineEdit("8.8.8.8")
        self._ping_host.setObjectName("NetField")
        self._ping_host.setPlaceholderText("Hostname or IP…")

        self._ping_count = QSpinBox()
        self._ping_count.setRange(1, 20)
        self._ping_count.setValue(4)
        self._ping_count.setStyleSheet(
            f"background:{theme.BG_DARK}; color:{theme.TEXT_PRIMARY};"
            f"font-family:'Consolas',monospace; border:1px solid {theme.BORDER_DIM};"
            f"border-radius:4px; padding:5px;"
        )
        self._ping_count.setPrefix("count: ")

        self._ping_btn = QPushButton("Ping")
        self._ping_btn.setObjectName("NetBtn")
        self._ping_btn.clicked.connect(self._run_ping)

        self._ping_stop = QPushButton("Stop")
        self._ping_stop.setObjectName("StopBtn")
        self._ping_stop.setEnabled(False)

        row.addWidget(self._ping_host, stretch=1)
        row.addWidget(self._ping_count)
        row.addWidget(self._ping_btn)
        row.addWidget(self._ping_stop)
        col.addLayout(row)

        self._ping_out = QTextEdit()
        self._ping_out.setObjectName("NetOutput")
        self._ping_out.setReadOnly(True)
        col.addWidget(self._ping_out, stretch=1)

        return page

    def _run_ping(self):
        self._ping_out.clear()
        host  = self._ping_host.text()
        count = self._ping_count.value()

        worker = PingWorker(host, count)
        worker.result.connect(self._ping_line)
        worker.done.connect(lambda: self._ping_btn.setEnabled(True))
        worker.done.connect(lambda: self._ping_stop.setEnabled(False))
        self._ping_stop.clicked.connect(worker.stop)
        self._ping_btn.setEnabled(False)
        self._ping_stop.setEnabled(True)
        worker.start()
        self._workers.append(worker)

    def _ping_line(self, text: str, color: str):
        if not text:
            self._ping_out.append("")
            return
        self._ping_out.append(
            f'<span style="color:{color};">{_e(text)}</span>'
        )
        self._ping_out.verticalScrollBar().setValue(
            self._ping_out.verticalScrollBar().maximum()
        )

    # ── Port Scan Tab ─────────────────────────────────────────

    def _make_scan_tab(self) -> QWidget:
        page = QWidget()
        col  = QVBoxLayout(page)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(8)

        row = QHBoxLayout()
        self._scan_host = QLineEdit("127.0.0.1")
        self._scan_host.setObjectName("NetField")
        self._scan_host.setPlaceholderText("Target IP or hostname…")

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setObjectName("NetBtn")
        self._scan_btn.clicked.connect(self._run_scan)

        self._scan_stop = QPushButton("Stop")
        self._scan_stop.setObjectName("StopBtn")
        self._scan_stop.setEnabled(False)

        row.addWidget(self._scan_host, stretch=1)
        row.addWidget(self._scan_btn)
        row.addWidget(self._scan_stop)
        col.addLayout(row)

        self._scan_prog = QProgressBar()
        self._scan_prog.setRange(0, 100)
        self._scan_prog.setValue(0)
        self._scan_prog.setTextVisible(True)
        self._scan_prog.setStyleSheet(f"""
            QProgressBar {{
                background:{theme.BG_DARK}; border:1px solid {theme.BORDER_DIM};
                border-radius:3px; height:8px; text-align:center;
                color:{theme.TEXT_DIM}; font-family:'Consolas',monospace; font-size:10px;
            }}
            QProgressBar::chunk {{ background:{theme.ACCENT_CYAN}; border-radius:3px; }}
        """)
        col.addWidget(self._scan_prog)

        self._scan_table = QTableWidget(0, 3)
        self._scan_table.setHorizontalHeaderLabels(["Port", "Service", "Status"])
        self._scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._scan_table.verticalHeader().setVisible(False)
        self._scan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        col.addWidget(self._scan_table, stretch=1)

        self._scan_status = QLabel("Ready.")
        self._scan_status.setObjectName("NetInfo")
        col.addWidget(self._scan_status)

        return page

    def _run_scan(self):
        self._scan_table.setRowCount(0)
        self._scan_prog.setValue(0)
        self._scan_status.setText(
            f"Scanning {self._scan_host.text()}…"
        )
        worker = PortScanWorker(self._scan_host.text())
        worker.result.connect(self._scan_row)
        worker.progress.connect(self._scan_prog.setValue)
        worker.done.connect(self._scan_done)
        self._scan_stop.clicked.connect(worker.stop)
        self._scan_btn.setEnabled(False)
        self._scan_stop.setEnabled(True)
        worker.start()
        self._workers.append(worker)

    def _scan_row(self, port: int, service: str, status: str):
        row = self._scan_table.rowCount()
        self._scan_table.insertRow(row)

        color = (theme.ACCENT_GREEN if status == "open"
                 else theme.ACCENT_RED if status == "filtered"
                 else theme.TEXT_DIM)

        for col, text in enumerate([str(port), service, status]):
            item = QTableWidgetItem(text)
            item.setForeground(QColor(color))
            self._scan_table.setItem(row, col, item)

    def _scan_done(self):
        self._scan_btn.setEnabled(True)
        self._scan_stop.setEnabled(False)
        open_ports = sum(
            1 for r in range(self._scan_table.rowCount())
            if self._scan_table.item(r, 2)
               and self._scan_table.item(r, 2).text() == "open"
        )
        self._scan_prog.setValue(100)
        self._scan_status.setText(
            f"Scan complete.  {open_ports} open port(s) found."
        )

    # ── IP Info Tab ───────────────────────────────────────────

    def _make_info_tab(self) -> QWidget:
        page = QWidget()
        col  = QVBoxLayout(page)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(6)

        out = QTextEdit()
        out.setObjectName("NetOutput")
        out.setReadOnly(True)
        col.addWidget(out)

        # Populate immediately
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "q-vault"
            local_ip = "127.0.0.1"

        lines = [
            ("Hostname",    hostname),
            ("Local IP",    local_ip),
            ("Gateway",     "192.168.1.1  (simulated)"),
            ("DNS Primary", "8.8.8.8"),
            ("DNS Secondary","8.8.4.4"),
            ("Interface",   "eth0 / wlan0"),
            ("MAC Address", "de:ad:be:ef:00:01  (simulated)"),
            ("MTU",         "1500"),
        ]
        for key, val in lines:
            out.append(
                f'<span style="color:{theme.ACCENT_CYAN};">{_e(key):18s}</span>'
                f'<span style="color:{theme.TEXT_PRIMARY};">{_e(val)}</span>'
            )

        out.append("")
        out.append(f'<span style="color:{theme.ACCENT_CYAN};">ARP Table (simulated)</span>')
        out.append(f'<span style="color:{theme.TEXT_DIM};">{"─" * 50}</span>')
        arp_entries = [
            ("192.168.1.1",   "aa:bb:cc:dd:ee:01", "eth0"),
            ("192.168.1.100", "aa:bb:cc:dd:ee:02", "eth0"),
            ("192.168.1.101", "aa:bb:cc:dd:ee:03", "wlan0"),
        ]
        for ip, mac, iface in arp_entries:
            out.append(
                f'<span style="color:{theme.TEXT_PRIMARY};">{ip:18s}</span>'
                f'<span style="color:{theme.TEXT_DIM};">{mac}  {iface}</span>'
            )

        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.setObjectName("NetBtn")
        col.addWidget(btn_refresh)

        return page

    # ── Monitor Tab ───────────────────────────────────────────

    def _make_monitor_tab(self) -> QWidget:
        page = QWidget()
        col  = QVBoxLayout(page)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(8)

        info_lbl = QLabel("Live simulated network traffic monitor.")
        info_lbl.setObjectName("NetInfo")
        col.addWidget(info_lbl)

        # Stats labels
        grid = QHBoxLayout()
        self._mon_rx  = self._stat_card("RX", "0 KB/s")
        self._mon_tx  = self._stat_card("TX", "0 KB/s")
        self._mon_pkt = self._stat_card("Packets", "0/s")
        self._mon_con = self._stat_card("Connections", "0")
        grid.addWidget(self._mon_rx)
        grid.addWidget(self._mon_tx)
        grid.addWidget(self._mon_pkt)
        grid.addWidget(self._mon_con)
        col.addLayout(grid)

        self._mon_log = QTextEdit()
        self._mon_log.setObjectName("NetOutput")
        self._mon_log.setReadOnly(True)
        col.addWidget(self._mon_log, stretch=1)

        # Simulate traffic every 2 seconds
        self._mon_timer = QTimer(self)
        self._mon_timer.timeout.connect(self._tick_monitor)
        self._mon_timer.start(2000)

        return page

    def _stat_card(self, label: str, value: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{theme.BG_PANEL}; border:1px solid {theme.BORDER_DIM};"
            f"border-radius:4px; padding:6px;"
        )
        c = QVBoxLayout(w)
        c.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-family:'Consolas',monospace; font-size:10px;"
        )
        val = QLabel(value)
        val.setStyleSheet(
            f"color:{theme.ACCENT_CYAN}; font-family:'Consolas',monospace; font-size:16px; font-weight:bold;"
        )
        val.setObjectName(f"mon_{label.replace(' ','_').lower()}")
        c.addWidget(lbl)
        c.addWidget(val)
        w._val_lbl = val
        return w

    def _tick_monitor(self):
        rx  = random.uniform(0.5, 120.0)
        tx  = random.uniform(0.1, 40.0)
        pkt = random.randint(10, 800)
        con = random.randint(3, 22)

        self._mon_rx._val_lbl.setText(f"{rx:.1f} KB/s")
        self._mon_tx._val_lbl.setText(f"{tx:.1f} KB/s")
        self._mon_pkt._val_lbl.setText(f"{pkt}/s")
        self._mon_con._val_lbl.setText(str(con))

        ts = time.strftime("%H:%M:%S")
        proto = random.choice(["TCP", "UDP", "ICMP", "DNS", "TLS"])
        src = f"192.168.1.{random.randint(2,254)}"
        dst = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        port = random.choice([80, 443, 53, 22, 8080, 9000])
        color = theme.ACCENT_AMBER if proto == "ICMP" else theme.TEXT_DIM

        self._mon_log.append(
            f'<span style="color:{theme.TEXT_DIM};">[{ts}]  </span>'
            f'<span style="color:{color};">{proto:5s}</span>'
            f'<span style="color:{theme.TEXT_DIM};">  {src} → {dst}:{port}'
            f'  {rx:.0f}B</span>'
        )
        sb = self._mon_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event):
        """Stop all background worker threads gracefully before closing."""
        for worker in list(self._workers):
            try:
                worker.stop()
                worker.quit()
                worker.wait(500)   # wait up to 500ms
            except Exception:
                pass
        self._workers.clear()
        if hasattr(self, "_mon_timer"):
            self._mon_timer.stop()
        super().closeEvent(event)



def _e(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
