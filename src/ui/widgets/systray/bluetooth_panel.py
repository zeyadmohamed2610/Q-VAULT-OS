from __future__ import annotations
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QFontMetrics

logger = logging.getLogger(__name__)


from system.system_helper import SystemControlHelper

class BtScanner(QThread):
    devices_found = pyqtSignal(list)

    def run(self):
        devs = SystemControlHelper.get_bluetooth_devices()
        self.devices_found.emit(devs)


class DeviceRow(QWidget):
    def __init__(self, dev: dict):
        super().__init__()
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._hov = False
        self.setStyleSheet("DeviceRow { background: transparent; border-radius: 6px; }")

        rl = QHBoxLayout(self)
        rl.setContentsMargins(16, 0, 16, 0)
        rl.setSpacing(8)

        ncol = QVBoxLayout()
        ncol.setSpacing(1)
        
        # Elide long names
        font = QFont("Segoe UI", 10)
        metrics = QFontMetrics(font)
        elided_name = metrics.elidedText(dev["name"], Qt.ElideRight, 180)
        
        n = QLabel(elided_name)
        n.setToolTip(dev["name"])
        n.setFont(font)
        n.setStyleSheet("color:#d4e8f0; background:transparent;")
        
        t = QLabel(dev.get("type", "Device"))
        t.setFont(QFont("Segoe UI", 8))
        t.setStyleSheet("color:#4a6880; background:transparent;")
        ncol.addWidget(n); ncol.addWidget(t)
        rl.addLayout(ncol)
        rl.addStretch()

        if dev["connected"]:
            badge = QLabel("● Connected")
            badge.setStyleSheet("color:#3fb950; font-size:9px; background:transparent;")
            rl.addWidget(badge)
        else:
            btn = QPushButton("Connect")
            btn.setStyleSheet(
                "QPushButton{background:rgba(84,177,198,0.10);color:#54b1c6;"
                "border:1px solid rgba(84,177,198,0.30);border-radius:6px;"
                "padding:2px 8px;font-size:9px;}"
                "QPushButton:hover{background:rgba(84,177,198,0.22);}"
            )
            rl.addWidget(btn)

    def enterEvent(self, e): self._hov = True;  self.update()
    def leaveEvent(self, e): self._hov = False; self.update()
    def paintEvent(self, event):
        if self._hov:
            from PyQt5.QtGui import QPainter, QColor
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(84, 177, 198, 25))
            p.drawRoundedRect(self.rect(), 8, 8)
            p.end()
        super().paintEvent(event)


class BluetoothPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedWidth(350)
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

        # Header
        hrow = QHBoxLayout()
        hrow.setContentsMargins(16, 0, 16, 8)
        title = QLabel("🔵  Bluetooth")
        title.setFont(QFont("Segoe UI Semibold", 11))
        title.setStyleSheet("color:#d4e8f0; background:transparent;")
        hrow.addWidget(title)
        hrow.addStretch()

        from ui.widgets.common.toggle_switch import ToggleSwitch
        self._tog = ToggleSwitch()
        self._tog.set_checked(True)
        self._tog.toggled.connect(self._toggle)
        hrow.addWidget(self._tog)
        cl.addLayout(hrow)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:rgba(84,177,198,0.1);")
        div.setFixedHeight(1)
        cl.addWidget(div)
        cl.addSpacing(4)

        # Device list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFixedHeight(200)

        self._devs_w = QWidget()
        self._devs_l = QVBoxLayout(self._devs_w)
        self._devs_l.setContentsMargins(0, 0, 0, 0)
        self._devs_l.setSpacing(0)
        scroll.setWidget(self._devs_w)
        cl.addWidget(scroll)
        outer.addWidget(self._card)

    def _scan(self):
        self._scanner = BtScanner()
        self._scanner.devices_found.connect(self._show_devices)
        self._scanner.start()

    def _show_devices(self, devs: list):
        while self._devs_l.count():
            item = self._devs_l.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for dev in devs:
            row = DeviceRow(dev)
            self._devs_l.addWidget(row)

        self._devs_l.addStretch()

    def _toggle(self, checked: bool):
        self._tog.setText("On" if checked else "Off")

    def popup_near(self, pos: QPoint):
        self.adjustSize()
        self.move(pos.x() - self.width() // 2,
                  pos.y() - self.height() - 8)
        self.show()
