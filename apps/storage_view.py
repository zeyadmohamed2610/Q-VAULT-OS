# =============================================================
#  storage_view.py — Q-Vault OS  |  Storage View ("This PC")
#
#  Shows:
#    • Drive list with usage bars (simulated sizes)
#    • Current vault mount status
#    • Virtual FS tree with file permission display
#    • Quick-launch buttons to related apps
# =============================================================

import time
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QScrollArea,
    QSplitter,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.filesystem import FS
from core.system_state import STATE
from assets import theme


STYLE = f"""
    QWidget#StorageView {{ background: {theme.BG_WINDOW}; }}

    QLabel#StorTitle {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 13px; font-weight: bold;
        padding: 10px 14px 6px 14px;
        background: transparent;
    }}
    QLabel#DriveLabel {{
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 12px;
        background: transparent;
    }}
    QLabel#DriveSub {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 10px;
        background: transparent;
    }}
    QFrame#DriveCard {{
        background: {theme.BG_PANEL};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 6px;
    }}
    QFrame#DriveCard[mounted="true"] {{
        border: 1px solid {theme.ACCENT_CYAN};
    }}
    QProgressBar#DiskBar {{
        background: {theme.BG_DARK};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 3px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar#DiskBar::chunk {{
        background: {theme.ACCENT_CYAN};
        border-radius: 3px;
    }}
    QProgressBar#DiskBar[critical="true"]::chunk {{
        background: {theme.ACCENT_RED};
    }}
    QProgressBar#DiskBar[warn="true"]::chunk {{
        background: {theme.ACCENT_AMBER};
    }}
    QTreeWidget#FsTree {{
        background: {theme.BG_DARK};
        color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace;
        font-size: 11px;
        border: none;
    }}
    QTreeWidget#FsTree::item {{
        padding: 2px 0;
    }}
    QTreeWidget#FsTree::item:selected {{
        background: {theme.BG_SELECTED};
        color: {theme.ACCENT_CYAN};
    }}
    QHeaderView::section {{
        background: {theme.BG_PANEL};
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 10px; font-weight: bold;
        border: none;
        border-bottom: 1px solid {theme.BORDER_DIM};
        padding: 4px 6px;
    }}
    QPushButton#StorBtn {{
        background: transparent;
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM};
        border-radius: 4px;
        padding: 5px 14px;
        font-family: 'Consolas', monospace;
        font-size: 11px;
    }}
    QPushButton#StorBtn:hover {{
        background: {theme.BG_HOVER};
        color: {theme.TEXT_PRIMARY};
    }}
    QLabel#PermLabel {{
        font-family: 'Consolas', monospace;
        font-size: 11px;
        background: transparent;
    }}
    QLabel#StatusBar {{
        color: {theme.TEXT_DIM};
        font-family: 'Consolas', monospace;
        font-size: 10px;
        padding: 2px 8px;
    }}
"""

# ── Simulated drive definitions ───────────────────────────────
# (label, total_gb, used_gb, icon, drive_type)
_DRIVES = [
    ("System  /", 32.0, 18.4, "🖥", "system"),
    ("Home    /home", 8.0, 3.1, "🏠", "home"),
    ("Temp    /tmp", 2.0, 0.2, "🗑", "temp"),
    ("Vault   /mnt/vault", 4.0, 0.0, "🔐", "vault"),
]


def _fmt_gb(gb: float) -> str:
    if gb < 1.0:
        return f"{gb * 1024:.0f} MB"
    return f"{gb:.1f} GB"


def _perm_str(is_dir: bool, owner: str, readable: bool) -> str:
    """Format a Unix-style permission string."""
    kind = "d" if is_dir else "-"
    user = "rwx" if owner == "root" else "rw-"
    grp = "r-x" if is_dir else "r--"
    oth = "r-x" if (is_dir and readable) else ("r--" if readable else "---")
    return f"{kind}{user}{grp}{oth}"


class StorageView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StorageView")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._make_left_panel())
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([380, 260])
        root.addWidget(splitter, stretch=1)

        root.addWidget(self._make_statusbar())

        # Refresh FS tree every 3 seconds (lightweight — only runs if visible)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_fs_tree)
        self._refresh_timer.start(3000)

    def closeEvent(self, event):
        STATE.unsubscribe(self._on_state_change)
        self._refresh_timer.stop()
        super().closeEvent(event)

    # ── STATE observer ────────────────────────────────────────

    def _on_state_change(self, field: str, old, new):
        pass

    # ── Header ────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL};border-bottom:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 12, 0)
        row.setSpacing(8)

        title = QLabel("💾  Storage  /  This PC")
        title.setObjectName("StorTitle")
        row.addWidget(title)
        row.addStretch()

        btn_ref = QPushButton("⟳ Refresh")
        btn_ref.setObjectName("StorBtn")
        btn_ref.clicked.connect(self._rebuild_drives)
        row.addWidget(btn_ref)

        return bar

    # ── Left panel: drives ────────────────────────────────────

    def _make_left_panel(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(10)

        section_lbl = QLabel("DRIVES")
        section_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px; letter-spacing:1px;"
            f"font-family:'Consolas',monospace;"
        )
        col.addWidget(section_lbl)

        self._drive_container = col
        self._drive_cards = []
        self._build_drive_cards(col)

        col.addStretch()
        return w

    def _build_drive_cards(self, col: QVBoxLayout):
        for lbl, total, used, icon, dtype in _DRIVES:
            is_vault = dtype == "vault"
            is_mounted = True
            actual_used = used if is_mounted else 0.0
            card = self._drive_card(lbl, total, actual_used, icon, is_vault, is_mounted)
            col.addWidget(card)
            self._drive_cards.append(card)

    def _drive_card(
        self,
        label: str,
        total: float,
        used: float,
        icon: str,
        is_vault: bool,
        mounted: bool,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("DriveCard")
        card.setProperty("mounted", "true" if (is_vault and mounted) else "false")
        card.setStyleSheet(STYLE)

        col = QVBoxLayout(card)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(6)

        # Header row
        hdr = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:22px; background:transparent;")

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_lbl = QLabel(label)
        name_lbl.setObjectName("DriveLabel")

        status_txt = "Mounted" if mounted else "Not Mounted"
        if is_vault:
            status_txt = "🔓 Mounted" if mounted else "🔒 Locked"
        sub_lbl = QLabel(f"{_fmt_gb(used)} used of {_fmt_gb(total)}  |  {status_txt}")
        sub_lbl.setObjectName("DriveSub")

        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)

        hdr.addWidget(icon_lbl)
        hdr.addLayout(name_col)
        hdr.addStretch()

        # Free space
        free_lbl = QLabel(_fmt_gb(total - used))
        free_lbl.setStyleSheet(
            f"color:{theme.ACCENT_CYAN}; font-family:'Consolas',monospace;"
            f"font-size:11px; background:transparent;"
        )
        hdr.addWidget(free_lbl)
        col.addLayout(hdr)

        # Usage bar
        bar = QProgressBar()
        bar.setObjectName("DiskBar")
        bar.setRange(0, 100)
        pct = int(used / total * 100) if total > 0 and mounted else 0
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)

        if pct >= 90:
            bar.setProperty("critical", "true")
        elif pct >= 75:
            bar.setProperty("warn", "true")
        bar.setStyleSheet(STYLE)

        col.addWidget(bar)
        return card

    def _rebuild_drives(self):
        """Rebuild all drive cards (called on STATE change or refresh)."""
        # Remove existing cards
        for card in self._drive_cards:
            self._drive_container.removeWidget(card)
            card.deleteLater()
        self._drive_cards.clear()

        # Re-insert after the section label (index 1 onward)
        self._build_drive_cards(self._drive_container)

    # ── Right panel: filesystem tree ──────────────────────────

    def _make_right_panel(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        hdr = QLabel("File System  (with permissions)")
        hdr.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px; letter-spacing:1px;"
            f"font-family:'Consolas',monospace;"
            f"padding:6px 10px; background:{theme.BG_PANEL};"
            f"border-bottom:1px solid {theme.BORDER_DIM};"
        )
        col.addWidget(hdr)

        self._fs_tree = QTreeWidget()
        self._fs_tree.setObjectName("FsTree")
        self._fs_tree.setHeaderLabels(["Name", "Perms", "Owner", "Size"])
        self._fs_tree.setColumnWidth(0, 160)
        self._fs_tree.setColumnWidth(1, 90)
        self._fs_tree.setColumnWidth(2, 55)
        self._fs_tree.setColumnWidth(3, 60)
        col.addWidget(self._fs_tree, stretch=1)

        self._refresh_fs_tree()

        # Selection info bar
        self._sel_info = QLabel("Select a file to view details.")
        self._sel_info.setObjectName("StatusBar")
        col.addWidget(self._sel_info)

        self._fs_tree.itemClicked.connect(self._on_tree_item_clicked)
        return w

    def _refresh_fs_tree(self):
        """Rebuild the filesystem tree from the virtual FS."""
        if not self.isVisible():
            return  # skip rebuild when panel is hidden

        self._fs_tree.clear()
        is_root = STATE.is_root()

        # Walk the virtual FS tree starting from "/"
        root_item = QTreeWidgetItem(["/ (root)", "drwxr-xr-x", "root", "—"])
        root_item.setForeground(0, QColor(theme.ACCENT_CYAN))
        self._fs_tree.addTopLevelItem(root_item)

        self._walk_fs_node(FS._tree, root_item, depth=0, is_root_user=is_root)
        root_item.setExpanded(True)

    def _walk_fs_node(
        self, node: dict, parent_item: QTreeWidgetItem, depth: int, is_root_user: bool
    ):
        if depth > 3:  # cap recursion for performance
            return

        from core.filesystem import Meta

        for key, child in node.items():
            if key == "_meta":
                continue

            if isinstance(child, dict):
                # Directory
                meta = child.get("_meta")
                owner = meta.owner if isinstance(meta, Meta) else "root"
                readable = meta.readable_by_user if isinstance(meta, Meta) else True

                # Hide root-only dirs from non-root users
                if not readable and not is_root_user:
                    continue

                perm_str = _perm_str(True, owner, readable)
                item = QTreeWidgetItem([f"📁 {key}", perm_str, owner, "—"])
                item.setForeground(0, QColor(theme.ACCENT_CYAN))
                item.setForeground(
                    1, QColor(theme.ACCENT_RED if not readable else theme.TEXT_DIM)
                )
                parent_item.addChild(item)
                self._walk_fs_node(child, item, depth + 1, is_root_user)

            elif isinstance(child, Meta):
                if not child.readable_by_user and not is_root_user:
                    continue
                perm_str = _perm_str(False, child.owner, child.readable_by_user)
                size_str = _fmt_size(child.size)
                item = QTreeWidgetItem([f"📄 {key}", perm_str, child.owner, size_str])
                item.setForeground(
                    1,
                    QColor(
                        theme.ACCENT_RED
                        if not child.readable_by_user
                        else theme.TEXT_DIM
                    ),
                )
                item.setData(0, Qt.UserRole, child)  # store meta for click
                parent_item.addChild(item)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, col: int):
        from core.filesystem import Meta

        meta = item.data(0, Qt.UserRole)
        if isinstance(meta, Meta):
            self._sel_info.setText(
                f"{item.text(0).replace('📄 ', '')}  |  "
                f"{meta.size} bytes  |  "
                f"owner: {meta.owner}  |  "
                f"modified: {meta.fmt_time(meta.modified_at)}  |  "
                f"perms: {item.text(1)}"
            )
        else:
            name = item.text(0).replace("📁 ", "").replace("/ (root)", "/")
            self._sel_info.setText(f"Directory: {name}  |  perms: {item.text(1)}")

    # ── Status bar ────────────────────────────────────────────

    def _make_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(22)
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL};border-top:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel(f"Session: {STATE.username()} ({STATE.session_type})")
        self._status_lbl.setObjectName("StatusBar")
        row.addWidget(self._status_lbl)

        # Update status every 2 s
        timer = QTimer(self)
        timer.timeout.connect(self._tick_status)
        timer.start(2000)
        return bar

    def _tick_status(self):
        self._status_lbl.setText(f"Session: {STATE.username()} ({STATE.session_type})")


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"
