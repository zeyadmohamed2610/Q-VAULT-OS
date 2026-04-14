# =============================================================
#  vault_tool.py — Q-Vault OS  |  Encrypted File Vault (Finalized)
#
#  Finalization fix:
#    ✓ NOTIFY.send() after successful encrypt and decrypt
#    ✓ NOTIFY.send() after vault lock/unlock
#    ✓ closeEvent unsubscribes FS observer
# =============================================================

import hashlib
import time

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFrame,
)
from PyQt5.QtCore import Qt

from core.filesystem import FS
from core.system_state import STATE
from assets import theme


# ── Cipher (XOR simulation of AES-256) ───────────────────────


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _derive_key(passphrase: str) -> bytes:
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def _to_hex(data: bytes, width: int = 32) -> str:
    lines = []
    for i in range(0, min(len(data), 128), width):
        chunk = data[i : i + width]
        lines.append(f"  {i:04x}  " + " ".join(f"{b:02x}" for b in chunk))
    if len(data) > 128:
        lines.append(f"  … ({len(data)} bytes total)")
    return "\n".join(lines)


def _notify(title: str, body: str, level: str = "info"):
    """Fire a toast notification if NOTIFY is available."""
    try:
        from system.notification_system import NOTIFY

        NOTIFY.send(title, body, level=level)
    except Exception:
        pass


STYLE = f"""
    QWidget#VaultTool {{ background: {theme.BG_WINDOW}; }}
    QLabel#VaultTitle {{
        color: {theme.ACCENT_CYAN};
        font-family: 'Consolas', monospace;
        font-size: 13px; font-weight: bold;
        padding: 10px 12px 6px 12px; background: transparent;
    }}
    QLabel#VaultStatus {{
        font-family: 'Consolas', monospace;
        font-size: 11px; padding: 2px 12px;
    }}
    QListWidget#VaultList {{
        background: #0a0e14; color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace; font-size: 12px;
        border: none; border-right: 1px solid {theme.BORDER_DIM};
    }}
    QListWidget#VaultList::item {{ padding: 5px 8px; }}
    QListWidget#VaultList::item:selected {{
        background: {theme.BG_SELECTED}; color: {theme.ACCENT_CYAN};
    }}
    QLineEdit#VaultField {{
        background: {theme.BG_DARK}; color: {theme.TEXT_PRIMARY};
        font-family: 'Consolas', monospace; font-size: 13px;
        border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; padding: 6px 10px;
    }}
    QLineEdit#VaultField:focus {{ border: 1px solid {theme.BORDER_BRIGHT}; }}
    QTextEdit#VaultOutput {{
        background: #080c10; color: {theme.ACCENT_GREEN};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px; border: none; padding: 8px;
    }}
    QPushButton#VaultBtn {{
        background: {theme.ACCENT_CYAN}; color: {theme.BG_DARK};
        border: none; border-radius: 4px; padding: 6px 16px;
        font-family: 'Consolas', monospace; font-size: 12px; font-weight: bold;
    }}
    QPushButton#VaultBtn:hover {{ background: #33ddff; }}
    QPushButton#VaultDanger {{
        background: transparent; color: {theme.ACCENT_RED};
        border: 1px solid {theme.ACCENT_RED}; border-radius: 4px; padding: 6px 16px;
        font-family: 'Consolas', monospace; font-size: 12px;
    }}
    QPushButton#VaultDanger:hover {{
        background: {theme.ACCENT_RED}; color: white;
    }}
    QPushButton#VaultSec {{
        background: transparent; color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER_DIM}; border-radius: 4px; padding: 6px 16px;
        font-family: 'Consolas', monospace; font-size: 12px;
    }}
    QPushButton#VaultSec:hover {{
        background: {theme.BG_HOVER}; color: {theme.TEXT_PRIMARY};
    }}
"""


class VaultTool(QWidget):
    VAULT_DIR = "/home/user/.vault"
    ENC_SUFFIX = ".qvenc"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VaultTool")
        self.setStyleSheet(STYLE)

        self._vault_key: bytes | None = None
        self._unlocked = False

        self._ensure_vault_dir()
        self._build_ui()

        # Refresh list when FS changes (e.g. new files from terminal)
        FS.subscribe(self._on_fs_change)

    def closeEvent(self, event):
        FS.unsubscribe(self._on_fs_change)
        super().closeEvent(event)

    def _on_fs_change(self):
        if self._unlocked:
            self._refresh_list()

    def _ensure_vault_dir(self):
        saved = FS.pwd()
        try:
            FS.cd("/home/user")
            if not FS.exists(self.VAULT_DIR):
                FS.mkdir(".vault")
        except Exception:
            pass
        finally:
            try:
                FS.cd(saved)
            except Exception:
                pass

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._make_file_list())
        splitter.addWidget(self._make_operations())
        splitter.setSizes([200, 440])
        root.addWidget(splitter, stretch=1)

        root.addWidget(self._make_statusbar())

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-bottom:1px solid {theme.BORDER_DIM};"
        )
        col = QVBoxLayout(bar)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        title = QLabel("🔐  Q-Vault Encrypted Storage")
        title.setObjectName("VaultTitle")
        col.addWidget(title)

        unlock_row = QHBoxLayout()
        unlock_row.setContentsMargins(12, 6, 12, 8)
        unlock_row.setSpacing(8)

        self._key_field = QLineEdit()
        self._key_field.setObjectName("VaultField")
        self._key_field.setPlaceholderText("Vault passphrase…")
        self._key_field.setEchoMode(QLineEdit.Password)
        self._key_field.returnPressed.connect(self._unlock_vault)

        self._unlock_btn = QPushButton("🔓 Unlock Vault")
        self._unlock_btn.setObjectName("VaultBtn")
        self._unlock_btn.clicked.connect(self._unlock_vault)

        self._lock_btn = QPushButton("🔒 Lock")
        self._lock_btn.setObjectName("VaultDanger")
        self._lock_btn.clicked.connect(self._lock_vault)
        self._lock_btn.setEnabled(False)

        self._gen_btn = QPushButton("⚡ Gen Key")
        self._gen_btn.setObjectName("VaultSec")
        self._gen_btn.clicked.connect(self._generate_key)

        unlock_row.addWidget(self._key_field, stretch=1)
        unlock_row.addWidget(self._unlock_btn)
        unlock_row.addWidget(self._lock_btn)
        unlock_row.addWidget(self._gen_btn)
        col.addLayout(unlock_row)

        self._vault_status = QLabel("🔒  Vault is LOCKED")
        self._vault_status.setObjectName("VaultStatus")
        self._vault_status.setStyleSheet(
            f"color:{theme.ACCENT_RED}; font-family:'Consolas',monospace;"
            f"font-size:11px; padding:2px 12px 6px 12px;"
        )
        col.addWidget(self._vault_status)
        return bar

    def _make_file_list(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        lbl = QLabel("Vault Contents")
        lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-family:'Consolas',monospace; font-size:10px;"
            f"padding:6px 8px; background:{theme.BG_PANEL};"
            f"border-bottom:1px solid {theme.BORDER_DIM};"
        )
        col.addWidget(lbl)

        self._file_list = QListWidget()
        self._file_list.setObjectName("VaultList")
        self._file_list.itemClicked.connect(self._on_file_selected)
        col.addWidget(self._file_list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(6, 6, 6, 6)
        btn_ref = QPushButton("⟳")
        btn_ref.setObjectName("VaultSec")
        btn_ref.setFixedWidth(36)
        btn_ref.clicked.connect(self._refresh_list)
        btn_row.addWidget(btn_ref)
        btn_row.addStretch()
        col.addLayout(btn_row)
        return w

    def _make_operations(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(8)

        col.addWidget(self._small("Source file (relative to /home/user):"))

        self._src_field = QLineEdit()
        self._src_field.setObjectName("VaultField")
        self._src_field.setPlaceholderText("e.g. Documents/readme.txt")
        col.addWidget(self._src_field)

        btn_row = QHBoxLayout()
        btn_enc = QPushButton("🔐 Encrypt File")
        btn_enc.setObjectName("VaultBtn")
        btn_enc.clicked.connect(self._encrypt_file)
        btn_dec = QPushButton("🔓 Decrypt Selected")
        btn_dec.setObjectName("VaultSec")
        btn_dec.clicked.connect(self._decrypt_selected)
        btn_row.addWidget(btn_enc)
        btn_row.addWidget(btn_dec)
        col.addLayout(btn_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(
            f"color:{theme.BORDER_DIM}; background:{theme.BORDER_DIM}; max-height:1px;"
        )
        col.addWidget(sep)

        col.addWidget(self._small("Output / hex dump:"))
        self._output = QTextEdit()
        self._output.setObjectName("VaultOutput")
        self._output.setReadOnly(True)
        col.addWidget(self._output, stretch=1)
        return w

    def _make_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(22)
        bar.setStyleSheet(
            f"background:{theme.BG_PANEL}; border-top:1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 0, 8, 0)
        self._status_lbl = QLabel("Vault locked. Enter passphrase to unlock.")
        self._status_lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-size:10px; font-family:'Consolas',monospace;"
        )
        row.addWidget(self._status_lbl)
        return bar

    @staticmethod
    def _small(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{theme.TEXT_DIM}; font-family:'Consolas',monospace; font-size:11px;"
        )
        return lbl

    # ── Vault lock / unlock ───────────────────────────────────

    def _unlock_vault(self):
        passphrase = self._key_field.text()
        if not passphrase:
            self._set_status("Enter a passphrase to unlock.")
            return
        self._vault_key = _derive_key(passphrase)
        self._unlocked = True

        self._vault_status.setText("🔓  Vault is UNLOCKED")
        self._vault_status.setStyleSheet(
            f"color:{theme.ACCENT_GREEN}; font-family:'Consolas',monospace;"
            f"font-size:11px; padding:2px 12px 6px 12px;"
        )
        self._unlock_btn.setEnabled(False)
        self._lock_btn.setEnabled(True)
        self._key_field.clear()
        self._set_status("Vault unlocked. You may encrypt and decrypt files.")
        self._refresh_list()
        self._log(
            f"Vault unlocked  {time.strftime('%H:%M:%S')}\n"
            f"Key fingerprint: {self._key_fingerprint()}"
        )
        _notify(
            "Vault Unlocked", "Encrypted storage is now accessible.", level="success"
        )

    def _lock_vault(self):
        self._vault_key = None
        self._unlocked = False

        self._vault_status.setText("🔒  Vault is LOCKED")
        self._vault_status.setStyleSheet(
            f"color:{theme.ACCENT_RED}; font-family:'Consolas',monospace;"
            f"font-size:11px; padding:2px 12px 6px 12px;"
        )
        self._unlock_btn.setEnabled(True)
        self._lock_btn.setEnabled(False)
        self._output.clear()
        self._set_status("Vault locked. All keys cleared from memory.")
        _notify("Vault Locked", "Keys cleared. Drive dismounted.", level="info")

    def _generate_key(self):
        import random, string

        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pw = "".join(random.choices(chars, k=24))
        self._key_field.setEchoMode(QLineEdit.Normal)
        self._key_field.setText(pw)
        self._log(f"Generated passphrase: {pw}\n(Copy this before clicking Unlock!)")

    def _key_fingerprint(self) -> str:
        if not self._vault_key:
            return "—"
        h = hashlib.sha256(self._vault_key).hexdigest()
        return ":".join(h[i : i + 4] for i in range(0, 16, 4))

    # ── Encrypt / Decrypt ─────────────────────────────────────

    def _encrypt_file(self):
        if not self._unlocked:
            self._set_status("⚠  Unlock the vault first.")
            return
        src = self._src_field.text().strip()
        if not src:
            self._set_status("⚠  Enter a source file path.")
            return

        saved = FS.pwd()
        try:
            FS.cd("/home/user")
            content = FS.cat(src)
            plaintext = content.encode("utf-8")
            ciphertext = _xor_cipher(plaintext, self._vault_key)

            enc_name = src.replace("/", "_") + self.ENC_SUFFIX
            FS.cd(self.VAULT_DIR)
            FS.write_file(enc_name, ciphertext.hex())

            self._log(
                f"Encrypted: {src}  →  .vault/{enc_name}\n"
                f"Original:  {len(plaintext)} bytes\n"
                f"Encrypted: {len(ciphertext)} bytes\n"
                f"Algorithm: XOR-256 (sim) / AES-256-GCM (production)\n"
                f"\nHex dump (first 128 bytes):\n{_to_hex(ciphertext)}"
            )
            self._set_status(f"✓  Encrypted → .vault/{enc_name}")
            self._refresh_list()
            # ── Notification ──────────────────────────────────
            _notify("File Encrypted", f"{enc_name} saved to vault.", level="success")

        except Exception as exc:
            self._set_status(f"⚠  {exc}")
        finally:
            try:
                FS.cd(saved)
            except Exception:
                pass

    def _decrypt_selected(self):
        if not self._unlocked:
            self._set_status("⚠  Unlock the vault first.")
            return
        items = self._file_list.selectedItems()
        if not items:
            self._set_status("Select a vault file to decrypt.")
            return

        enc_name = items[0].text().split("  ")[-1].strip()
        saved = FS.pwd()
        try:
            FS.cd(self.VAULT_DIR)
            hex_content = FS.cat(enc_name)
            ciphertext = bytes.fromhex(hex_content)
            plaintext = _xor_cipher(ciphertext, self._vault_key)
            decoded = plaintext.decode("utf-8", errors="replace")
            self._log(
                f"Decrypted: {enc_name}\n"
                f"Size: {len(ciphertext)} → {len(plaintext)} bytes\n"
                f"\n--- Content ---\n{decoded}"
            )
            self._set_status(f"✓  Decrypted {enc_name}")
            # ── Notification ──────────────────────────────────
            _notify(
                "File Decrypted", f"{enc_name} decrypted successfully.", level="info"
            )

        except Exception as exc:
            self._set_status(f"⚠  Decryption failed: {exc}")
        finally:
            try:
                FS.cd(saved)
            except Exception:
                pass

    # ── File list ─────────────────────────────────────────────

    def _refresh_list(self):
        self._file_list.clear()
        _, files = FS.list_for_explorer(self.VAULT_DIR)
        for f in files:
            meta = FS.get_meta_for_explorer(self.VAULT_DIR, f)
            size = f"{meta.size} B" if meta else "?"
            self._file_list.addItem(QListWidgetItem(f"🔐  {f}  ({size})"))

    def _on_file_selected(self, item: QListWidgetItem):
        name = item.text().split("  ")[1].strip()
        self._set_status(f"Selected: {name}")

    # ── Output helpers ────────────────────────────────────────

    def _log(self, text: str):
        self._output.append(
            f'<span style="color:{theme.ACCENT_GREEN};">{_e(text)}</span>'
        )

    def _set_status(self, text: str):
        self._status_lbl.setText(text)


def _e(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
