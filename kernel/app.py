from __future__ import annotations

import math
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import logging
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal

logger = logging.getLogger(__name__)
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFrame, QSizePolicy,
    QSplitter,
)

from assets import theme
from assets.theme import THEME
from core.event_bus import EVENT_BUS, EventPayload, SystemEvent
from system.sandbox.base_app import BaseApp
from system.sandbox.secure_api import SecureAPI

# ── Theme aliases (matches system_monitor convention) ────────────
_T = THEME
C_BG       = _T["bg_black"]
C_SURFACE  = _T["surface_dark"]
C_PANEL    = _T["bg_dark"]
C_BORDER   = _T["border_color"]
C_BORDER_S = _T["border_subtle"]
C_CYAN     = _T["primary_glow"]
C_CYAN_DIM = _T["primary_deep"]
C_TEXT     = _T["text_main"]
C_DIM      = _T["text_dim"]
C_MUTED    = _T["text_muted"]
C_GREEN    = _T["success"]
C_ORANGE   = _T["warning"]
C_RED      = _T["accent_error"]
C_PURPLE   = _T["accent_purple"]
MONO       = theme.FONT_MONO

# Process color palette (cycles through 8 vivid hues)
_PROC_PALETTE = [
    "#00e6ff", "#00ff88", "#9c27ff", "#ffaa00",
    "#ff2fd1", "#66f2ff", "#ff6644", "#4fc3f7",
]
_IDLE_COLOR   = "#1a2540"
_FREE_COLOR   = "#1a2540"
_USED_COLOR   = "#00e6ff"
_DL_COLOR     = "#ff3366"


def _proc_color(pid: Optional[int]) -> str:
    if pid is None:
        return _IDLE_COLOR
    return _PROC_PALETTE[pid % len(_PROC_PALETTE)]


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {C_MUTED}; font-family: {MONO}; font-size: 9px; "
        f"font-weight: bold; letter-spacing: 1.5px; padding: 0;"
    )
    return lbl


def _panel(title: str, widget: QWidget, fixed_height: int = 0) -> QWidget:
    """Wrap widget in a titled dark panel card."""
    card = QWidget()
    card.setStyleSheet(
        f"QWidget {{ background: {C_SURFACE}; "
        f"border: 1px solid {C_BORDER_S}; border-radius: 8px; }}"
    )
    lay = QVBoxLayout(card)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(6)
    lay.addWidget(_section_label(title))
    lay.addWidget(widget)
    if fixed_height:
        card.setFixedHeight(fixed_height)
    return card


# ═══════════════════════════════════════════════════════════════
# 1. CPU TIMELINE WIDGET
# ═══════════════════════════════════════════════════════════════

class CPUTimelineWidget(QWidget):
    """
    Horizontal strip per core showing recent process activity.
    Each cell = one tick; colours are per-process, grey = IDLE.
    Updated on every PROC_SCHEDULED / PROC_CONTEXT_SWITCHED event.
    """

    MAX_TICKS = 60          # cells to keep visible
    CELL_W    = 10          # px per tick cell
    ROW_H     = 22          # px per core row
    GAP       =  4          # px gap between rows

    def __init__(self, core_count: int = 4, parent=None):
        super().__init__(parent)
        self._core_count = core_count
        # history[core_id] = deque of (pid_or_None, label)
        self._history: Dict[int, deque] = {
            i: deque(maxlen=self.MAX_TICKS) for i in range(core_count)
        }
        self._current: Dict[int, Optional[int]] = {i: None for i in range(core_count)}

        total_h = core_count * (self.ROW_H + self.GAP) + 20
        self.setMinimumHeight(total_h)
        self.setMinimumWidth(self.MAX_TICKS * self.CELL_W + 60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Subscribe
        EVENT_BUS.subscribe(SystemEvent.PROC_SCHEDULED,       self._on_scheduled)
        EVENT_BUS.subscribe(SystemEvent.PROC_CONTEXT_SWITCHED, self._on_ctx_switch)
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK,            self._on_tick)

    def set_core_count(self, n: int) -> None:
        self._core_count = n
        for i in range(n):
            if i not in self._history:
                self._history[i] = deque(maxlen=self.MAX_TICKS)
                self._current[i] = None
        self.update()

    def _on_scheduled(self, payload: EventPayload) -> None:
        d = payload.data
        pid     = d.get("pid")
        core_id = d.get("core_id", 0)
        if core_id < self._core_count:
            self._current[core_id] = pid

    def _on_ctx_switch(self, payload: EventPayload) -> None:
        d = payload.data
        core_id = d.get("cpu_id", 0)
        pid     = d.get("to_pid")
        if core_id < self._core_count:
            self._current[core_id] = pid

    def _on_tick(self, payload: EventPayload) -> None:
        try:
            # Check if C++ object still exists to avoid "RuntimeError: wrapped C/C++ object deleted"
            # This happens if the widget is closed but the handler is still subscribed
            if self.parent() is None and not self.isVisible():
                return
                
            for core_id in range(self._core_count):
                pid = self._current.get(core_id)
                label = f"P{pid}" if pid is not None else "IDLE"
                self._history[core_id].append((pid, label))
            self.update()
        except RuntimeError:
            # Safely ignore if the object was deleted mid-execution
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        fnt = QFont(MONO, 7)
        painter.setFont(fnt)

        label_w = 48
        cell_w  = self.CELL_W

        for core_id in range(self._core_count):
            y = core_id * (self.ROW_H + self.GAP)

            # Core label
            painter.setPen(QColor(C_DIM))
            painter.drawText(0, y, label_w - 4, self.ROW_H,
                             Qt.AlignVCenter | Qt.AlignRight,
                             f"CORE {core_id}")

            hist = list(self._history[core_id])
            # Pad with IDLE on the left if shorter
            pad = self.MAX_TICKS - len(hist)
            hist = [(None, "IDLE")] * pad + hist

            for i, (pid, lbl) in enumerate(hist):
                x = label_w + i * cell_w
                color = QColor(_proc_color(pid))
                painter.fillRect(x, y, cell_w - 1, self.ROW_H, color)

                # Label only if wide enough and not IDLE
                if pid is not None and cell_w >= 10:
                    painter.setPen(QColor(0, 0, 0, 180))
                    painter.drawText(x, y, cell_w, self.ROW_H,
                                     Qt.AlignCenter, str(pid))

        painter.end()


# ═══════════════════════════════════════════════════════════════
# 2. MEMORY MAP WIDGET
# ═══════════════════════════════════════════════════════════════

class MemoryMapWidget(QWidget):
    """
    Visual representation of simulated RAM.
    Cyan blocks = allocated; dark = free.
    """

    BAR_H = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks: List[dict] = []
        self._frag:   float = 0.0
        self._used:   int   = 0
        self._free:   int   = 0
        self._total:  int   = 1024

        self.setMinimumHeight(self.BAR_H + 40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        EVENT_BUS.subscribe(SystemEvent.MEMORY_ALLOCATED, self._on_mem_change)
        EVENT_BUS.subscribe(SystemEvent.MEMORY_FREED,     self._on_mem_change)

    def _on_mem_change(self, payload: EventPayload) -> None:
        self._refresh_from_manager()

    def _refresh_from_manager(self) -> None:
        try:
            from kernel.memory_manager import MEMORY_MANAGER as MM
            self._blocks = MM.get_memory_map()
            self._frag   = MM.get_fragmentation_ratio()
            self._used   = MM.total_used()
            self._free   = MM.total_free()
            self._total  = MM.total_size
        except Exception:
            pass
        self.update()

    def refresh(self) -> None:
        self._refresh_from_manager()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        bar_y = 20
        fnt   = QFont(MONO, 8)
        painter.setFont(fnt)

        total = max(self._total, 1)

        if not self._blocks:
            painter.setPen(QColor(C_MUTED))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "— No memory data —")
            painter.end()
            return

        x_off = 0
        for blk in self._blocks:
            bw = int((blk["size"] / total) * w)
            bw = max(bw, 1)
            color = QColor(_proc_color(blk["pid"])) if not blk["free"] else QColor(_FREE_COLOR)

            # Draw block
            rect = QRectF(x_off, bar_y, bw - 1, self.BAR_H)
            painter.fillRect(rect, color)

            # PID label if wide enough
            if not blk["free"] and bw > 20:
                painter.setPen(QColor(0, 0, 0, 220))
                painter.drawText(int(rect.x()), int(rect.y()),
                                 int(rect.width()), int(rect.height()),
                                 Qt.AlignCenter, f"P{blk['pid']}")
            x_off += bw

        # Stats line below bar
        util_pct  = int(self._used / total * 100)
        frag_pct  = int(self._frag * 100)
        painter.setPen(QColor(C_DIM))
        painter.drawText(
            0, bar_y + self.BAR_H + 4, w, 16,
            Qt.AlignLeft,
            f"USED {self._used}/{total}u  ({util_pct}%)    "
            f"FRAG {frag_pct}%    FREE {self._free}u"
        )
        painter.end()


# ═══════════════════════════════════════════════════════════════
# 3. READY QUEUE WIDGET
# ═══════════════════════════════════════════════════════════════

class ReadyQueueWidget(QWidget):
    """
    List of processes waiting in the scheduler's ready queue.
    Shows burst_time and priority as inline bars.
    Updated on PROC_SCHEDULED / PROC_PREEMPTED / CLOCK_TICK.
    """

    ROW_H    = 26
    MAX_ROWS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: List[dict] = []   # list of process as_dict()

        h = self.MAX_ROWS * (self.ROW_H + 2) + 24
        self.setMinimumHeight(h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        EVENT_BUS.subscribe(SystemEvent.PROC_SCHEDULED,       self._on_sched_event)
        EVENT_BUS.subscribe(SystemEvent.PROC_PREEMPTED,       self._on_sched_event)
        EVENT_BUS.subscribe(SystemEvent.PROC_QUANTUM_EXPIRED, self._on_sched_event)

    def _on_sched_event(self, payload: EventPayload) -> None:
        try:
            self._refresh_from_scheduler()
        except RuntimeError:
            pass

    def _refresh_from_scheduler(self) -> None:
        try:
            from kernel.scheduler import SCHEDULER
            self._queue = [p.as_dict() for p in SCHEDULER.ready_queue]
        except Exception:
            pass
        self.update()

    def refresh(self) -> None:
        self._refresh_from_scheduler()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        fnt = QFont(MONO, 9)
        painter.setFont(fnt)

        if not self._queue:
            painter.setPen(QColor(C_MUTED))
            painter.drawText(0, 0, w, self.height(),
                             Qt.AlignCenter, "— Queue empty —")
            painter.end()
            return

        col_pid   = 0
        col_name  = 36
        col_burst = 130
        col_prio  = 220
        col_bar   = 280

        # Header
        painter.setPen(QColor(C_MUTED))
        painter.drawText(col_pid,   2, 36,  16, Qt.AlignLeft, "PID")
        painter.drawText(col_name,  2, 90,  16, Qt.AlignLeft, "NAME")
        painter.drawText(col_burst, 2, 80,  16, Qt.AlignLeft, "BURST")
        painter.drawText(col_prio,  2, 60,  16, Qt.AlignLeft, "PRIO")
        painter.drawText(col_bar,   2, w - col_bar, 16, Qt.AlignLeft, "REMAINING")

        max_burst = max((p.get("burst_time", 1) for p in self._queue), default=1) or 1

        for idx, proc in enumerate(self._queue[:self.MAX_ROWS]):
            y = 20 + idx * (self.ROW_H + 2)

            # Row background
            bg = QColor(20, 30, 50, 160) if idx % 2 == 0 else QColor(10, 18, 32, 120)
            painter.fillRect(0, y, w, self.ROW_H, bg)

            pid   = proc.get("pid", "?")
            name  = proc.get("name", "?")[:12]
            burst = proc.get("burst_time", 0)
            rem   = proc.get("remaining_time", 0)
            prio  = proc.get("priority", 5)

            c = QColor(_proc_color(pid))
            painter.setPen(c)
            painter.drawText(col_pid,  y, 36, self.ROW_H, Qt.AlignVCenter, str(pid))

            painter.setPen(QColor(C_TEXT))
            painter.drawText(col_name,  y, 90, self.ROW_H, Qt.AlignVCenter, name)
            painter.drawText(col_burst, y, 80, self.ROW_H, Qt.AlignVCenter, str(burst))

            # Priority badge
            prio_color = (C_RED if prio >= 8 else C_ORANGE if prio >= 5 else C_DIM)
            painter.setPen(QColor(prio_color))
            painter.drawText(col_prio, y, 60, self.ROW_H, Qt.AlignVCenter, str(prio))

            # Remaining-time mini bar
            bar_w   = w - col_bar - 4
            bar_h   = 8
            bar_y   = y + (self.ROW_H - bar_h) // 2
            fill_w  = int(bar_w * (rem / max_burst)) if max_burst else 0

            painter.fillRect(col_bar, bar_y, bar_w, bar_h, QColor(30, 40, 60))
            if fill_w > 0:
                painter.fillRect(col_bar, bar_y, fill_w, bar_h, QColor(C_CYAN))

        painter.end()


# ═══════════════════════════════════════════════════════════════
# 4. DEADLOCK GRAPH WIDGET
# ═══════════════════════════════════════════════════════════════

class DeadlockGraphWidget(QWidget):
    """
    Visualises the Resource Allocation Graph (RAG).
      • Process nodes  — cyan circles
      • Resource nodes — white rectangles
      • Edges          — arrows (held=green, request=orange)
      • Cycle nodes    — highlighted red
    Updated on DEADLOCK_DETECTED / DEADLOCK_RESOLVED events.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rag: dict  = {"nodes": [], "edges": []}
        self._cycles: List[List[int]] = []
        self._deadlocked_pids = set()

        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        EVENT_BUS.subscribe(SystemEvent.DEADLOCK_DETECTED, self._on_detected)
        EVENT_BUS.subscribe(SystemEvent.DEADLOCK_RESOLVED, self._on_resolved)

    def _on_detected(self, payload: EventPayload) -> None:
        d = payload.data
        self._rag  = d.get("rag", {"nodes": [], "edges": []})
        cycle      = d.get("cycle", [])
        self._deadlocked_pids = set(cycle)
        self.update()

    def _on_resolved(self, payload: EventPayload) -> None:
        try:
            victim = payload.data.get("victim")
            self._deadlocked_pids.discard(victim)
            self.update()
        except RuntimeError:
            pass

    def refresh(self) -> None:
        try:
            from kernel.deadlock_manager import DEADLOCK_MANAGER as DM
            self._rag = DM.get_rag()
        except Exception:
            pass
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        nodes = self._rag.get("nodes", [])
        edges = self._rag.get("edges", [])

        if not nodes:
            painter.setPen(QColor(C_MUTED))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "— No RAG data —")
            painter.end()
            return

        # ── Layout: distribute nodes in a circle ─────────────────
        cx, cy = w / 2, h / 2
        r_layout = min(cx, cy) * 0.75
        n = len(nodes)
        positions: Dict[str, Tuple[float, float]] = {}

        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i / n) - math.pi / 2
            nx = cx + r_layout * math.cos(angle)
            ny = cy + r_layout * math.sin(angle)
            positions[node["id"]] = (nx, ny)

        NODE_R  = 18
        RECT_W  = 36
        RECT_H  = 18

        # ── Draw edges ────────────────────────────────────────────
        for edge in edges:
            src_pos = positions.get(edge["from"])
            dst_pos = positions.get(edge["to"])
            if not src_pos or not dst_pos:
                continue

            color = QColor(C_GREEN) if edge["type"] == "held" else QColor(C_ORANGE)
            pen = QPen(color, 1.5)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            sx, sy = src_pos
            dx, dy = dst_pos

            # Arrow line
            painter.drawLine(int(sx), int(sy), int(dx), int(dy))

            # Arrowhead
            angle = math.atan2(dy - sy, dx - sx)
            aw = 8
            ax1 = dx - aw * math.cos(angle - 0.4)
            ay1 = dy - aw * math.sin(angle - 0.4)
            ax2 = dx - aw * math.cos(angle + 0.4)
            ay2 = dy - aw * math.sin(angle + 0.4)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(
                QPointF(dx, dy), QPointF(ax1, ay1), QPointF(ax2, ay2)
            )

        # ── Draw nodes ────────────────────────────────────────────
        fnt = QFont(MONO, 8)
        painter.setFont(fnt)

        for node in nodes:
            nx, ny = positions[node["id"]]
            ntype  = node["type"]
            nid    = node["id"]

            if ntype == "process":
                pid = node.get("pid")
                in_cycle = pid in self._deadlocked_pids
                fill  = QColor(C_RED)    if in_cycle else QColor(C_CYAN)
                text  = QColor(0, 0, 0)

                painter.setBrush(fill)
                painter.setPen(QPen(fill.lighter(130), 1.5))
                painter.drawEllipse(
                    QPointF(nx, ny), NODE_R, NODE_R
                )
                painter.setPen(text)
                painter.drawText(
                    int(nx - NODE_R), int(ny - NODE_R),
                    NODE_R * 2, NODE_R * 2,
                    Qt.AlignCenter, f"P{pid}"
                )

            else:  # resource
                fill = QColor(50, 60, 90)
                painter.setBrush(fill)
                painter.setPen(QPen(QColor(C_BORDER), 1.5))
                painter.drawRoundedRect(
                    QRectF(nx - RECT_W / 2, ny - RECT_H / 2, RECT_W, RECT_H),
                    4, 4
                )
                painter.setPen(QColor(C_TEXT))
                lbl = node.get("label", node.get("rid", "?"))[:6]
                painter.drawText(
                    int(nx - RECT_W / 2), int(ny - RECT_H / 2),
                    RECT_W, RECT_H, Qt.AlignCenter, lbl
                )

        # Legend
        painter.setPen(QColor(C_MUTED))
        painter.setFont(QFont(MONO, 7))
        painter.drawText(4, h - 30, 200, 12, Qt.AlignLeft, "● process  ■ resource")
        painter.setPen(QColor(C_GREEN))
        painter.drawText(4, h - 16, 90, 12, Qt.AlignLeft, "→ holds")
        painter.setPen(QColor(C_ORANGE))
        painter.drawText(60, h - 16, 90, 12, Qt.AlignLeft, "→ waits")
        painter.setPen(QColor(C_RED))
        painter.drawText(120, h - 16, 120, 12, Qt.AlignLeft, "● deadlocked")

        painter.end()


# ═══════════════════════════════════════════════════════════════
# 5. CORE MONITOR WIDGET
# ═══════════════════════════════════════════════════════════════

class CoreMonitorWidget(QWidget):
    """
    Vertical utilization bars, one per core.
    EWMA utilization from MulticoreEngine, updated every second.
    """

    BAR_W  = 40
    BAR_H  = 90
    GAP    = 14

    def __init__(self, core_count: int = 4, parent=None):
        super().__init__(parent)
        self._cores: List[dict] = []
        self._core_count = core_count

        total_w = core_count * (self.BAR_W + self.GAP) + self.GAP + 10
        self.setMinimumSize(total_w, self.BAR_H + 40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        EVENT_BUS.subscribe(SystemEvent.CORE_ASSIGNED,    self._on_core_event)
        EVENT_BUS.subscribe(SystemEvent.PROCESS_MIGRATED, self._on_core_event)

    def _on_core_event(self, payload: EventPayload) -> None:
        try:
            self._refresh()
        except RuntimeError:
            pass

    def _refresh(self) -> None:
        try:
            from kernel.multicore_engine import MULTICORE_ENGINE as MCE
            self._cores = [c.as_dict() for c in MCE.cores]
            self._core_count = len(self._cores)
        except Exception:
            pass
        self.update()

    def refresh(self) -> None:
        self._refresh()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        fnt = QFont(MONO, 8)
        painter.setFont(fnt)

        bar_h   = self.BAR_H
        bar_top = 16
        n       = max(self._core_count, len(self._cores))
        total_w = n * (self.BAR_W + self.GAP)
        x_off   = max((self.width() - total_w) // 2, 0)

        for i, core in enumerate(self._cores):
            x   = x_off + i * (self.BAR_W + self.GAP)
            util = core.get("utilization", 0.0)
            pid  = core.get("current_pid")

            # ── Trough ──────────────────────────────────────────
            painter.fillRect(x, bar_top, self.BAR_W, bar_h, QColor(20, 28, 48))

            # ── Fill bar (gradient cyan→green based on util) ────
            fill_h = max(int(bar_h * util), 1)
            fill_y = bar_top + bar_h - fill_h

            grad = QLinearGradient(x, fill_y, x, bar_top + bar_h)
            if util > 0.8:
                top_c, bot_c = QColor(C_RED), QColor(C_ORANGE)
            elif util > 0.5:
                top_c, bot_c = QColor(C_ORANGE), QColor(C_CYAN)
            else:
                top_c, bot_c = QColor(C_CYAN), QColor(C_CYAN_DIM)
            grad.setColorAt(0.0, top_c)
            grad.setColorAt(1.0, bot_c)

            painter.fillRect(x, fill_y, self.BAR_W, fill_h, QBrush(grad))

            # ── Border ──────────────────────────────────────────
            painter.setPen(QPen(QColor(C_BORDER_S), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(x, bar_top, self.BAR_W, bar_h)

            # ── Core label ──────────────────────────────────────
            painter.setPen(QColor(C_DIM))
            painter.drawText(x, bar_top - 14, self.BAR_W, 14,
                             Qt.AlignCenter, f"C{i}")

            # ── Util % ──────────────────────────────────────────
            pct_str = f"{int(util * 100)}%"
            painter.setPen(QColor(C_TEXT) if util > 0.1 else QColor(C_MUTED))
            painter.drawText(x, bar_top + bar_h + 2, self.BAR_W, 14,
                             Qt.AlignCenter, pct_str)

            # ── Current PID ─────────────────────────────────────
            if pid is not None:
                painter.setPen(QColor(_proc_color(pid)))
                painter.drawText(x, bar_top + bar_h + 16, self.BAR_W, 12,
                                 Qt.AlignCenter, f"P{pid}")

        painter.end()


# ═══════════════════════════════════════════════════════════════
# 6. INTERRUPT LOG WIDGET  (bonus lightweight panel)
# ═══════════════════════════════════════════════════════════════

class InterruptLogWidget(QWidget):
    """Scrolling log of recent INTERRUPT_RAISED events."""

    MAX_ENTRIES = 40
    new_row_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: deque = deque(maxlen=self.MAX_ENTRIES)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QScrollArea()
        self._list.setWidgetResizable(True)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
        )

        self._inner = QWidget()
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(0, 0, 0, 0)
        self._inner_lay.setSpacing(1)
        self._inner_lay.addStretch()

        self._list.setWidget(self._inner)
        layout.addWidget(self._list)

        self.setMinimumHeight(100)

        self.new_row_signal.connect(self._add_row_safe)

        EVENT_BUS.subscribe(SystemEvent.INTERRUPT_RAISED,  self._on_irq)
        EVENT_BUS.subscribe(SystemEvent.INTERRUPT_HANDLED, self._on_irq_handled)

    def _on_irq(self, payload: EventPayload) -> None:
        try:
            irq  = payload.data.get("interrupt", {})
            itype = irq.get("type", "?")
            pid   = irq.get("source_pid")
            tick  = irq.get("tick", 0)
            prio  = irq.get("priority", 5)
            self._add_row(
                f"tick={tick:>4}  [{itype.upper():12s}]  prio={prio}  pid={pid}",
                color=C_ORANGE
            )
        except RuntimeError:
            pass

    def _on_irq_handled(self, payload: EventPayload) -> None:
        try:
            irq  = payload.data.get("interrupt", {})
            itype = irq.get("type", "?")
            tick  = payload.data.get("handled_at_tick", 0)
            self._add_row(
                f"tick={tick:>4}  handled  {itype}",
                color=C_GREEN
            )
        except RuntimeError:
            pass

    def _add_row(self, text: str, color: str = C_DIM) -> None:
        self.new_row_signal.emit(text, color)

    def _add_row_safe(self, text: str, color: str) -> None:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-family: {MONO}; font-size: 9px; "
            f"padding: 1px 4px;"
        )
        # Insert before stretch
        self._inner_lay.insertWidget(self._inner_lay.count() - 1, lbl)

        # Prune old entries
        if self._inner_lay.count() - 1 > self.MAX_ENTRIES:
            item = self._inner_lay.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Auto-scroll
        QTimer.singleShot(50, lambda: self._list.verticalScrollBar().setValue(
            self._list.verticalScrollBar().maximum()
        ))


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

class KernelMonitorApp(BaseApp, QWidget):
    """
    Q-Vault OS — Kernel Monitor Dashboard.
    Real-time visualization of CPU scheduling, memory, deadlocks, and cores.
    """

    APP_ID = "kernel_monitor"
    tick_header_signal = pyqtSignal(int, str, int)
    deadlock_detected_signal = pyqtSignal(list)
    deadlock_resolved_signal = pyqtSignal(object)

    def __init__(self, secure_api: SecureAPI = None, parent=None):
        BaseApp.__init__(self, secure_api)
        QWidget.__init__(self, parent)

        self.tick_header_signal.connect(self._on_tick_header_safe)
        self.deadlock_detected_signal.connect(self._on_deadlock_header_safe)
        self.deadlock_resolved_signal.connect(self._on_resolved_header_safe)

        self.setObjectName("AppContainer")
        self.setMinimumSize(860, 620)
        self.setStyleSheet(f"QWidget#AppContainer {{ background: {C_BG}; }}")

        self._refresh_timer: Optional[QTimer] = None
        self._tick_count = 0

        # ── Build all widgets ────────────────────────────────────
        self.cpu_timeline   = CPUTimelineWidget(core_count=4)
        self.memory_map     = MemoryMapWidget()
        self.ready_queue    = ReadyQueueWidget()
        self.deadlock_graph = DeadlockGraphWidget()
        self.core_monitor   = CoreMonitorWidget(core_count=4)
        self.irq_log        = InterruptLogWidget()

        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        # ── Main content area ────────────────────────────────────
        content = QWidget()
        content.setStyleSheet(f"background: {C_BG};")
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(10, 10, 10, 10)
        content_lay.setSpacing(8)

        # Row 1: CPU Timeline (full width)
        tl_panel = _panel("CPU TIMELINE  (each cell = 1 tick)", self.cpu_timeline)
        content_lay.addWidget(tl_panel)

        # Row 2: Memory map (full width)
        mem_panel = _panel("RAM MAP  ■ allocated  □ free", self.memory_map, fixed_height=110)
        content_lay.addWidget(mem_panel)

        # Row 3: three panels side-by-side
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)

        rq_panel = _panel("READY QUEUE", self.ready_queue)
        mid_row.addWidget(rq_panel, stretch=2)

        dl_panel = _panel("DEADLOCK GRAPH  (RAG)", self.deadlock_graph)
        mid_row.addWidget(dl_panel, stretch=2)

        irq_panel = _panel("INTERRUPT LOG", self.irq_log)
        mid_row.addWidget(irq_panel, stretch=1)

        content_lay.addLayout(mid_row, stretch=1)

        # Row 4: Core Monitor (full width)
        core_panel = _panel("CORE UTILIZATION  (EWMA)", self.core_monitor, fixed_height=160)
        content_lay.addWidget(core_panel)

        root.addWidget(content, stretch=1)
        root.addWidget(self._make_footer())

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(
            f"background: {C_PANEL}; "
            f"border-bottom: 1px solid {C_BORDER};"
        )
        row = QHBoxLayout(header)
        row.setContentsMargins(16, 0, 16, 0)

        title = QLabel("⬡ KERNEL MONITOR")
        title.setStyleSheet(
            f"color: {C_CYAN}; font-family: {MONO}; "
            f"font-size: 14px; font-weight: bold; letter-spacing: 3px;"
        )

        self._tick_lbl = QLabel("TICK: 0")
        self._tick_lbl.setStyleSheet(
            f"color: {C_DIM}; font-family: {MONO}; font-size: 11px;"
        )
        self._algo_lbl = QLabel("ALGO: —")
        self._algo_lbl.setStyleSheet(
            f"color: {C_DIM}; font-family: {MONO}; font-size: 11px;"
        )
        self._mem_lbl = QLabel("MEM: —")
        self._mem_lbl.setStyleSheet(
            f"color: {C_DIM}; font-family: {MONO}; font-size: 11px;"
        )
        self._dl_lbl = QLabel("DEADLOCK: OK")
        self._dl_lbl.setStyleSheet(
            f"color: {C_GREEN}; font-family: {MONO}; font-size: 11px; font-weight: bold;"
        )

        from PyQt5.QtWidgets import QPushButton
        self._stress_btn = QPushButton("STRESS")
        self._stress_btn.setFixedWidth(60)
        self._stress_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1a2333; color: {C_ORANGE}; border: 1px solid {C_ORANGE};
                font-family: {MONO}; font-size: 10px; font-weight: bold; border-radius: 2px;
            }}
            QPushButton:hover {{ background: {C_ORANGE}; color: black; }}
            QPushButton:pressed {{ background: #ffcc00; }}
        """)
        self._stress_btn.clicked.connect(self._run_internal_stress)

        row.addWidget(title)
        row.addStretch()
        row.addWidget(self._stress_btn)
        row.addWidget(_vsep())
        row.addWidget(self._tick_lbl)
        row.addWidget(_vsep())
        row.addWidget(self._algo_lbl)
        row.addWidget(_vsep())
        row.addWidget(self._mem_lbl)
        row.addWidget(_vsep())
        row.addWidget(self._dl_lbl)

        # Subscribe header to tick + deadlock events
        EVENT_BUS.subscribe(SystemEvent.CLOCK_TICK,       self._on_tick_header)
        EVENT_BUS.subscribe(SystemEvent.DEADLOCK_DETECTED, self._on_deadlock)
        EVENT_BUS.subscribe(SystemEvent.DEADLOCK_RESOLVED, self._on_resolved_header)

        return header

    def _make_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(24)
        footer.setStyleSheet(
            f"background: {C_PANEL}; border-top: 1px solid {C_BORDER_S};"
        )
        row = QHBoxLayout(footer)
        row.setContentsMargins(12, 0, 12, 0)

        self._footer_lbl = QLabel(
            "● CLOCK_TICK  ● PROC_SCHEDULED  ● MEMORY_ALLOCATED  "
            "● DEADLOCK_DETECTED  ● CORE_ASSIGNED  ● INTERRUPT_RAISED"
        )
        self._footer_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-family: {MONO}; font-size: 8px;"
        )
        row.addWidget(self._footer_lbl)
        return footer

    # ── Header event handlers ─────────────────────────────────────

    def _on_tick_header(self, payload: EventPayload) -> None:
        try:
            tick = payload.data.get("tick", 0)
            algo = "?"
            mem_pct = 0
            try:
                from kernel.scheduler import SCHEDULER
                algo = SCHEDULER.algorithm
            except Exception:
                pass
            try:
                from kernel.memory_manager import MEMORY_MANAGER as MM
                mem_pct = int(MM.total_used() / max(MM.total_size, 1) * 100)
            except Exception:
                pass
            self.tick_header_signal.emit(tick, algo, mem_pct)
        except RuntimeError:
            pass

    def _on_tick_header_safe(self, tick: int, algo: str, mem_pct: int) -> None:
        self._tick_lbl.setText(f"TICK: {tick}")
        if algo != "?":
            self._algo_lbl.setText(f"ALGO: {algo}")
        if mem_pct != 0:
            self._mem_lbl.setText(f"MEM: {mem_pct}%")

    def _on_deadlock(self, payload: EventPayload) -> None:
        try:
            cycle = payload.data.get("cycle", [])
            self.deadlock_detected_signal.emit(cycle)
        except RuntimeError:
            pass

    def _on_deadlock_header_safe(self, cycle: list) -> None:
        self._dl_lbl.setText(f"DEADLOCK: {cycle}")
        self._dl_lbl.setStyleSheet(
            f"color: {C_RED}; font-family: {MONO}; font-size: 11px; font-weight: bold;"
        )

    def _on_resolved_header(self, payload: EventPayload) -> None:
        try:
            victim = payload.data.get("victim")
            self.deadlock_resolved_signal.emit(victim)
        except RuntimeError:
            pass

    def _on_resolved_header_safe(self, victim) -> None:
        self._dl_lbl.setText(f"RESOLVED (v={victim})")
        self._dl_lbl.setStyleSheet(
            f"color: {C_ORANGE}; font-family: {MONO}; font-size: 11px; font-weight: bold;"
        )
        QTimer.singleShot(3000, self._reset_dl_label)

    def _reset_dl_label(self) -> None:
        self._dl_lbl.setText("DEADLOCK: OK")
        self._dl_lbl.setStyleSheet(
            f"color: {C_GREEN}; font-family: {MONO}; font-size: 11px; font-weight: bold;"
        )

    def _run_internal_stress(self) -> None:
        """Internal stress trigger for monitoring validation."""
        try:
            from kernel.memory_manager import MEMORY_MANAGER
            import random
            
            count = 20
            # First, clean up any previous stress pids
            for i in range(count):
                MEMORY_MANAGER.deallocate(pid=2000 + i)

            for i in range(count):
                pid = 2000 + i
                # 1. Create process
                EVENT_BUS.emit(SystemEvent.PROC_SPAWNED, {"pid": pid, "name": f"stress_task_{i}"}, source="StressInternal")
                
                # 2. Actually allocate memory (this emits MEMORY_ALLOCATED internally)
                size = random.randint(15, 60)
                MEMORY_MANAGER.allocate(pid=pid, size=size, label=f"stress_{i}")
                
                # 3. Assign to cores
                core_id = i % 4
                EVENT_BUS.emit(SystemEvent.CORE_ASSIGNED, {"pid": pid, "core_id": core_id}, source="StressInternal")
                
                # 4. Schedule it
                EVENT_BUS.emit(SystemEvent.PROC_SCHEDULED, {"pid": pid, "core_id": core_id}, source="StressInternal")
                
                # 5. Interrupts
                if i % 4 == 0:
                    EVENT_BUS.emit(SystemEvent.INTERRUPT_RAISED, {
                        "interrupt": {"type": "stress_pulse", "priority": 4, "source_pid": pid, "tick": 0}
                    }, source="StressInternal")

            logger.info("[STRESS] Completed: %d processes spawned and allocated.", count)
        except Exception as e:
            logger.error("[STRESS] Error during stress test: %s", e, exc_info=True)

    # ── BaseApp lifecycle ─────────────────────────────────────────

    # ── Lazy simulation start ─────────────────────────────────────

    def showEvent(self, event) -> None:
        """Start simulation clock only when widget becomes visible."""
        super().showEvent(event)
        self._start_simulation()

    def hideEvent(self, event) -> None:
        """Pause simulation clock when widget is hidden to save CPU."""
        super().hideEvent(event)
        self._pause_simulation()

    def _start_simulation(self) -> None:
        from kernel.simulation_clock import SIMULATION_CLOCK
        if not SIMULATION_CLOCK.is_running:
            SIMULATION_CLOCK.start()
            logger.info("[KernelMonitorApp] Simulation clock started (lazy, on show)")

    def _pause_simulation(self) -> None:
        from kernel.simulation_clock import SIMULATION_CLOCK
        if SIMULATION_CLOCK.is_running and not SIMULATION_CLOCK.is_paused:
            SIMULATION_CLOCK.pause()
            logger.info("[KernelMonitorApp] Simulation clock paused (on hide)")

    def on_start(self) -> None:
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._periodic_refresh)
        self._refresh_timer.start(1000)   # 1 second
        # Initial data pull
        self._periodic_refresh()

    def on_stop(self) -> None:
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
        # Unsubscribe header events
        for ev, cb in [
            (SystemEvent.CLOCK_TICK,        self._on_tick_header),
            (SystemEvent.DEADLOCK_DETECTED, self._on_deadlock_header),
            (SystemEvent.DEADLOCK_RESOLVED, self._on_resolved_header),
        ]:
            try:
                EVENT_BUS.unsubscribe(ev, cb)
            except Exception:
                pass

    def get_permissions(self) -> list:
        return ["file_access:virtual_only", "network_access:DENIED"]

    # ── Periodic refresh (1 s) ────────────────────────────────────

    def _periodic_refresh(self) -> None:
        """Pull latest state into all stat-based widgets."""
        self.memory_map.refresh()
        self.ready_queue.refresh()
        self.deadlock_graph.refresh()
        self.core_monitor.refresh()


# ── Helpers ───────────────────────────────────────────────────────

def _vsep() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet(f"background: {C_BORDER_S};")
    return sep
