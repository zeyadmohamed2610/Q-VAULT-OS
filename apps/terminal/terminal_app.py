import logging
import os
import time
import psutil
from pathlib import Path
from collections import deque

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QScrollBar, QFrame, QLabel
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QTextCursor, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QTimer

from system.config import get_qvault_home
from core.event_bus import EVENT_BUS, SystemEvent
from .nano_editor import NanoEditor
from apps.notepad.notepad_app import NotepadApp

logger = logging.getLogger(__name__)

# Design Tokens (Legacy compat)
C_BG = "#0d1117"; C_TEXT = "#c9d1d9"; C_PROMPT = "#3fb950"
C_ERROR = "#f85149"; C_PATH = "#e3b341"; C_CMD = "#58a6ff"; C_MUTED = "#8b949e"


def _best_mono_font(size: int = 11) -> QFont:
    """
    Find the best monospace font that renders box-drawing characters correctly.
    Priority: Cascadia Code (best) → Fira Code → JetBrains Mono → Courier New.
    Falls back to system monospace if none of the preferred fonts are installed.
    """
    from PyQt5.QtGui import QFontDatabase
    preferred = [
        "Cascadia Code", "Cascadia Mono",
        "Fira Code", "JetBrains Mono",
        "Lucida Console", "Courier New",
    ]
    available = set(QFontDatabase().families())
    for name in preferred:
        if name in available:
            f = QFont(name, size)
            f.setStyleHint(QFont.Monospace)
            return f
    # Ultimate fallback — let Qt pick the best monospace
    f = QFont()
    f.setStyleHint(QFont.Monospace)
    f.setFixedPitch(True)
    f.setPointSize(size)
    return f

class _Highlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        from PyQt5.QtCore import QRegExp
        self._rules = []
        
        # Rules: (Pattern, Color, Bold?)
        
        # 1. Prompt Structure
        self._add(r"┌──", "#58a6ff", True)
        self._add(r"──", "#58a6ff", True)
        self._add(r"└─", "#3fb950", True)
        
        # 2. User & Machine
        self._add(r"\[ROOT\]", "#f85149", True) # Red badge for ROOT
        self._add(r"\(.*㉿.*\)", "#3fb950", True) # (user㉿qvault)
        
        # 3. Path
        self._add(r"\[.*\]", "#58a6ff", False) # [path]
        
        # 4. Prompt Symbols
        self._add(r"\$", "#3fb950", True)
        self._add(r"\#", "#f85149", True)

        # 5. Known Commands (Vibrant Green - only when typed as commands)
        cmds = "|".join([
            "ls", "cd", "pwd", "mkdir", "touch", "cat", "echo", "rm", "rmdir", 
            "stat", "whoami", "clear", "help", "history", "qsu", "sudo", 
            "lock", "ask", "status", "verify_audit", "nano", "chmod", "bash"
        ])
        # Match command at the start of the line after $ or #
        self._add(rf"(?<=[$#] )\b({cmds})\b", "#55ff55", True) 
        # Fallback for any instance of these commands (less bold)
        self._add(rf"\b({cmds})\b", "#3fb950", False)
        
        # 6. Status/Security Messages
        self._add(r"\[SECURITY\].*", "#f85149")
        self._add(r"\[ERROR\].*", "#f85149")
        self._add(r"\[Success\].*", "#3fb950")
        self._add(r"\[cd\].*", "#8b949e")
        
        # 7. File Paths (Cyan for Dirs, Amber for Files)
        self._add(r"/[a-zA-Z0-9_./-]+", "#58a6ff", True) # Directories (Cyan)
        self._add(r"\b[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+\b", "#c9d1d9") # Files (White/Grey)
        
        # 8. Flags & Arguments
        self._add(r" -[a-zA-Z]+", "#58a6ff") # Flags
        self._add(r" --[a-zA-Z-]+", "#58a6ff") # Long flags
        self._add(r"\".*\"", "#e3b341") # Strings (Amber)
        self._add(r"'.*'", "#e3b341")
        
        # 9. ASCII Art Logo Gradient (Q-VAULT banner)
        self._add(r"[@!]{2,}", "#00e6ff", False)   # Main blocks (Cyan)
        self._add(r"[:!]{2,}", "#00b3cc", False)   # Accent blocks (Teal)
        self._add(r"[:.]{2,}", "#008099", False)   # Dim blocks (Dark Cyan)

    def _add(self, pat, col, bold=False):
        from PyQt5.QtCore import QRegExp
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(col))
        # Ensure we use the exact same font metrics as the base document
        fmt.setFont(self.document().defaultFont())
        if bold: fmt.setFontWeight(QFont.Bold)
        self._rules.append((QRegExp(pat), fmt))

    def highlightBlock(self, text):
        for rx, fmt in self._rules:
            i = rx.indexIn(text)
            while i >= 0:
                self.setFormat(i, rx.matchedLength(), fmt)
                i = rx.indexIn(text, i + rx.matchedLength())

class TerminalBuffer(QPlainTextEdit):
    """
    The heart of the 'integrated' experience. 
    Intercepts keys to simulate a real TTY.
    """
    command_entered = pyqtSignal(str)
    tab_pressed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prompt_pos = 0
        self._history = []
        self._hist_idx = -1
        self._is_password_mode = False
        
        # Terminal styling — use best available font for box-drawing char support
        self.setFont(_best_mono_font(11))
        # Override global stylesheet that might force variable-width fonts
        self.setStyleSheet(f"""
            background: #0d1117; 
            color: {C_TEXT}; 
            font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            border: none; 
            padding: 10px;
        """)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.document().setMaximumBlockCount(2000)
        self._suggestion = ""
        
        # Cursor blink timer for visual polish
        self.setCursorWidth(2)

    def set_password_mode(self, enabled: bool):
        self._is_password_mode = enabled
        if enabled:
            self._pass_buffer = ""

    def set_prompt_text(self, text):
        """Called when engine emits a prompt update."""
        self.append_output(text, newline=False)
        self._prompt_pos = self.textCursor().position()
        self.ensureCursorVisible()

    def append_output(self, text, newline=True):
        if "\x0c" in text:
            # Handle clear command
            self.setPlainText("")
            self._prompt_pos = 0
            # Remove the \x0c and proceed if there's more text
            text = text.replace("\x0c", "")
            if not text:
                return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        # If we are in password mode, we don't want to show the text? 
        # Actually, output from commands should show. Only user typing is hidden.
        self.insertPlainText(text + ("\n" if newline else ""))
        self.ensureCursorVisible()

    def _get_current_input(self):
        if self._is_password_mode and hasattr(self, "_pass_buffer"):
            res = self._pass_buffer
            self._pass_buffer = ""
            return res
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def _replace_current_input(self, text):
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.insertPlainText(text)
        self.setTextCursor(cursor)

    def cut(self):
        """Terminals NEVER allow cut. Always blocked."""
        return

    def paste(self):
        # Always paste at end, never into protected history
        self.moveCursor(QTextCursor.End)
        super().paste()

    def insertFromMimeData(self, source):
        # Always insert at end, never into protected history
        self.moveCursor(QTextCursor.End)
        super().insertFromMimeData(source)

    def _is_range_protected(self, cursor: QTextCursor) -> bool:
        if not cursor.hasSelection():
            return cursor.position() <= self._prompt_pos
        return cursor.selectionStart() < self._prompt_pos

    def contextMenuEvent(self, event):
        """Custom context menu with Admin elevation, Copy, and Select All."""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#0b162d;border:1px solid rgba(0,230,255,0.2);"
            "border-radius:8px;padding:4px;color:#e6f7ff;font-family:'Segoe UI';font-size:10pt;}"
            "QMenu::item{padding:6px 20px;border-radius:4px;margin:1px 4px;}"
            "QMenu::item:selected{background:rgba(0,230,255,0.15);color:#00e6ff;}"
            "QMenu::item:disabled{color:#555568;}"
        )
        
        act_admin = menu.addAction("🛡️  Run as Administrator")
        act_admin.triggered.connect(self._run_as_admin)
        menu.addSeparator()
        
        act_copy = menu.addAction("📋  Copy")
        act_copy.setEnabled(self.textCursor().hasSelection())
        act_copy.triggered.connect(self.copy)
        menu.addSeparator()
        
        act_all = menu.addAction("📄  Select All")
        act_all.triggered.connect(self.selectAll)
        
        menu.exec_(event.globalPos())

    def _run_as_admin(self):
        if hasattr(self, "_engine") and self._engine:
            self._engine.run_as_administrator()

    def paintEvent(self, event):
        """Draw ghost text suggestion behind the cursor."""
        super().paintEvent(event)
        if not self._suggestion or self._is_password_mode:
            return

        painter = QTextCursor(self.document())
        painter.movePosition(QTextCursor.End)
        rect = self.cursorRect(painter)
        
        from PyQt5.QtGui import QPainter
        p = QPainter(self.viewport())
        p.setPen(QColor("#666666")) # Muted grey
        p.setFont(self.font())
        
        # Offset slightly to the right of the cursor
        p.drawText(rect.right() + 2, rect.top(), 
                  self.viewport().width(), rect.height(),
                  Qt.AlignLeft | Qt.AlignVCenter, self._suggestion)
        p.end()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        
        # 0. Keyboard shortcuts
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+L: Clear terminal
            if event.key() == Qt.Key_L:
                self.setPlainText("")
                self._prompt_pos = 0
                self.command_entered.emit("clear") # Trigger prompt refresh
                return

            # Ctrl+C: Interrupt
            if event.key() == Qt.Key_C:
                if cursor.hasSelection():
                    self.copy()
                else:
                    curr = self._get_current_input()
                    self.append_output("^C")
                    self._replace_current_input("") # Clear current line buffer
                    self.command_entered.emit("") # Just trigger a new prompt
                return

            # Ctrl+V: Paste at end
            if event.key() == Qt.Key_V:
                self.paste()
                return

            # Ctrl+A: Move to beginning of input (after prompt)
            if event.key() == Qt.Key_A:
                cursor.setPosition(self._prompt_pos)
                self.setTextCursor(cursor)
                return

            # Ctrl+E: Move to end of input
            if event.key() == Qt.Key_E:
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)
                return

            # Ctrl+U: Clear line before cursor
            if event.key() == Qt.Key_U:
                cursor.setPosition(self._prompt_pos, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                return

            # Ctrl+K: Clear line after cursor
            if event.key() == Qt.Key_K:
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                return

            # Ctrl+W: Clear word before cursor
            if event.key() == Qt.Key_W:
                if cursor.position() > self._prompt_pos:
                    cursor.movePosition(QTextCursor.PreviousWord, QTextCursor.KeepAnchor)
                    if cursor.selectionStart() < self._prompt_pos:
                        cursor.setPosition(self._prompt_pos, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                return

        # 1. Special Keys (Home/End/Arrows)
        if event.key() == Qt.Key_Home:
            cursor.setPosition(self._prompt_pos)
            self.setTextCursor(cursor)
            return

        if event.key() == Qt.Key_Left:
            if cursor.position() <= self._prompt_pos:
                return # Block moving before prompt

        # 2. Enforce typing zone
        if cursor.position() < self._prompt_pos:
            if not (event.modifiers() & Qt.ControlModifier): # Allow copy/select
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)

        # 2. Intercept Enter
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cmd = self._get_current_input()
            self.append_output("") # New line for the user's enter
            if cmd.strip():
                if not self._history or self._history[-1] != cmd:
                    self._history.append(cmd)
            self._hist_idx = -1
            self.command_entered.emit(cmd)
            return

        # 3. Intercept Backspace / Delete
        if event.key() == Qt.Key_Backspace or event.key() == Qt.Key_Delete:
            if self._is_range_protected(cursor):
                return
            if self._is_password_mode and event.key() == Qt.Key_Backspace and hasattr(self, "_pass_buffer"):
                if self._pass_buffer:
                    self._pass_buffer = self._pass_buffer[:-1]
                return

        # 4. History
        if event.key() == Qt.Key_Up:
            if self._is_password_mode: return
            if self._history:
                if self._hist_idx == -1: self._hist_idx = len(self._history) - 1
                elif self._hist_idx > 0: self._hist_idx -= 1
                self._replace_current_input(self._history[self._hist_idx])
            return
        if event.key() == Qt.Key_Down:
            if self._is_password_mode: return
            if self._hist_idx != -1:
                self._hist_idx += 1
                if self._hist_idx >= len(self._history):
                    self._hist_idx = -1
                    self._replace_current_input("")
                else:
                    self._replace_current_input(self._history[self._hist_idx])
            return

        # 5. Tab Autocomplete
        if event.key() == Qt.Key_Tab:
            if self._is_password_mode: return
            self.tab_pressed.emit(self._get_current_input())
            return

        # 6. Password masking (No-echo)
        if self._is_password_mode:
            # We don't call super().keyPressEvent(event) for printable characters
            if event.text() and not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
                # Ignore control chars like \r \t \b
                if ord(event.text()[0]) >= 32:
                    if not hasattr(self, "_pass_buffer"): self._pass_buffer = ""
                    self._pass_buffer += event.text()
                return # Don't show anything

        # 7. Accept Suggestion (Right arrow)
        if event.key() == Qt.Key_Right:
            if self._suggestion and cursor.atEnd():
                self._replace_current_input(self._get_current_input() + self._suggestion)
                self._update_suggestion()
                return

        super().keyPressEvent(event)
        # Update suggestion after any text change
        self._update_suggestion()

    def _update_suggestion(self):
        curr_raw = self._get_current_input()
        curr = curr_raw.strip()
        if not curr or self._is_password_mode:
            self._suggestion = ""
            self.viewport().update()
            return
            
        # 1. Try history match first (if input doesn't have spaces, it's a command)
        match = ""
        if " " not in curr:
            for h in reversed(self._history):
                if h.startswith(curr) and h != curr:
                    match = h[len(curr):]
                    break
        
        # 2. Try path match if no history match or if we have spaces (args)
        if not match:
            parts = curr_raw.split()
            last_part = parts[-1] if not curr_raw.endswith(" ") else ""
            
            # Use engine's CWD to look up files
            try:
                # Safety check: ensure _executor exists before access
                if hasattr(self._engine, "_executor") and self._engine._executor:
                    cwd = self._engine._executor.cwd
                    # Simple prefix match in CWD
                    for p in cwd.iterdir():
                        if p.name.startswith(last_part) and p.name != last_part:
                            match = p.name[len(last_part):]
                            if p.is_dir():
                                match += "/"
                            break
            except:
                pass
        
        if match != self._suggestion:
            self._suggestion = match
            self.viewport().update()

class TerminalApp(QWidget):
    def __init__(self, secure_api=None, start_path: str = None, role_override: str = None, parent=None):
        super().__init__(parent)
        self.secure_api = secure_api
        self._base_dir = Path(get_qvault_home()).resolve()
        
        # v2.0 Refactor: Use TerminalEngine for core logic
        from .terminal_engine import TerminalEngine
        start_path_obj = Path(start_path).resolve() if start_path else None
        self._engine = TerminalEngine(secure_api=secure_api, start_path=start_path_obj)
        
        self._setup_ui()
        
        # Inject engine into buffer for context menu and suggestions
        self._buffer._engine = self._engine
        
        # Connect Engine -> Buffer
        self._engine.output_ready.connect(self._buffer.append_output)
        self._engine.prompt_update.connect(lambda _, p: self._buffer.set_prompt_text(p))
        self._engine.password_mode.connect(lambda _, m: self._buffer.set_password_mode(m))
        
        # Connect Buffer -> Engine
        self._buffer.command_entered.connect(self._engine.execute_command)
        self._buffer.tab_pressed.connect(self._handle_tab)
        
        # Connect State changes to UI
        self._engine.state_changed.connect(self._update_state_ui)
        
        # Hook nano/notepad requests
        self._engine._executor._on_nano_request = self._open_nano
        self._engine._executor._on_notepad_request = self._open_notepad
        
        self._engine.boot_terminal()
        if role_override == "admin":
            # Already authenticated by desktop context menu
            self._engine._elevate_to_root()
            
        # Scroll to bottom so prompt is visible
        QTimer.singleShot(100, self._buffer.ensureCursorVisible)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # ── Status Header ──
        self.header = QFrame()
        self.header.setFixedHeight(30)
        self.header.setObjectName("terminalHeader")
        self.header.setStyleSheet("""
            #terminalHeader {
                background: #0b162d;
                border-bottom: 1px solid rgba(0, 230, 255, 0.2);
            }
            QLabel {
                color: #8899aa;
                font-family: 'Segoe UI Semibold', sans-serif;
                font-size: 9pt;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        self.state_label = QLabel("● NORMAL")
        self.state_label.setStyleSheet("color: #00e6ff;") # Cyan
        header_layout.addWidget(self.state_label)
        
        header_layout.addStretch()
        
        self.metrics_label = QLabel("CPU: 0%  |  MEM: 0%")
        header_layout.addWidget(self.metrics_label)
        
        self.layout.addWidget(self.header)

        # ── Buffer ──
        self._buffer = TerminalBuffer()
        self._hl = _Highlighter(self._buffer.document())
        self.layout.addWidget(self._buffer)

        # Metrics update timer
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(2000)
    
    def _update_metrics(self):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            self.metrics_label.setText(f"CPU: {cpu}%  |  MEM: {mem}%  |  Q-VAULT v4.0")
        except Exception:
            pass

    def _set_dim(self, enabled: bool):
        """Toggle a semi-transparent dimming overlay for focus."""
        if not hasattr(self, "_dim_overlay"):
            self._dim_overlay = QFrame(self)
            self._dim_overlay.setStyleSheet("background: rgba(0, 0, 0, 160);")
            self._dim_overlay.hide()
            
        if enabled:
            # Match buffer geometry
            self._dim_overlay.setGeometry(self._buffer.geometry())
            self._dim_overlay.show()
            self._dim_overlay.raise_()
        else:
            self._dim_overlay.hide()

    def _update_state_ui(self, state):
        # Update header based on engine state
        from .terminal_engine import EngineState
        if state == EngineState.ROOT:
            self.state_label.setText("● ROOT")
            self.state_label.setStyleSheet("color: #ff3366;") # Red
        elif state in (EngineState.AUTH_REQUEST, EngineState.AUTH_SUDO):
            self.state_label.setText("● SUDO")
            self.state_label.setStyleSheet("color: #ffcc00;") # Gold
        elif state == EngineState.LOCKED:
            self.state_label.setText("● LOCKED")
            self.state_label.setStyleSheet("color: #555568;") # Grey
        else:
            self.state_label.setText("● NORMAL")
            self.state_label.setStyleSheet("color: #00e6ff;")

    def _handle_tab(self, current_input):
        if not current_input: return
        
        # Determine what we are completing
        # If there are no spaces, we complete commands.
        # If there are spaces, we complete files/dirs.
        parts = current_input.split()
        last_part = current_input.split()[-1] if not current_input.endswith(" ") else ""
        
        matches = []
        cwd = self._engine.cwd

        # 1. Path-based completion (contains / or starts after a command)
        if "/" in last_part or len(parts) > 1 or current_input.endswith(" "):
            # We are completing a path
            path_prefix = Path(last_part)
            search_dir = cwd
            name_prefix = last_part

            if "/" in last_part:
                # Split into directory to search and prefix of name
                if last_part.endswith("/"):
                    search_dir = (cwd / last_part).resolve()
                    name_prefix = ""
                else:
                    search_dir = (cwd / last_part).parent.resolve()
                    name_prefix = Path(last_part).name

            try:
                if search_dir.exists() and search_dir.is_dir():
                    for entry in search_dir.iterdir():
                        if entry.name.startswith(name_prefix):
                            suffix = "/" if entry.is_dir() else ""
                            # Reconstruct the full string to replace the last part
                            if "/" in last_part:
                                base = last_part.rsplit("/", 1)[0]
                                matches.append(base + "/" + entry.name + suffix)
                            else:
                                matches.append(entry.name + suffix)
            except Exception:
                pass
        
        # 2. Command completion (only if it's the first word and doesn't look like a path)
        if (len(parts) <= 1 and not current_input.endswith(" ")) and "/" not in last_part:
            from ._commands import COMMAND_REGISTRY
            matches += [c for c in COMMAND_REGISTRY.keys() if c.startswith(last_part)]

        matches = sorted(list(set(matches)))
        if not matches: return

        if len(matches) == 1:
            # Single match: insert it
            match = matches[0]
            # Replace last_part with match
            new_input = current_input[:current_input.rfind(last_part)] + match
            self._buffer._replace_current_input(new_input)
        elif len(matches) > 1:
            # Multiple matches: show them and stay on current line
            self._buffer.append_output("\n" + "  ".join(matches))
            # Re-emit the prompt and current input to keep typing
            self._engine._emit_prompt()
            self._buffer._replace_current_input(current_input)

    def _open_nano(self, file_path):
        """Opens the NanoEditor overlay."""
        self._set_dim(True)
        try:
            content = ""
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
            
            self.nano = NanoEditor(file_path, content, parent=self)
            self.nano.setGeometry(self.rect())
            self.nano.show()
            self.nano.closed.connect(self._on_nano_closed)
        except Exception as e:
            self._buffer.append_output(f"[ERROR] Nano failed: {e}")
            self._set_dim(False)

    def _on_nano_closed(self):
        self._set_dim(False)
        self._buffer.setFocus()
        # Trigger a prompt refresh from engine
        self._engine._emit_prompt()

    def _open_notepad(self, file_path=None):
        """Opens the NotepadApp overlay."""
        self._set_dim(True)
        try:
            self.notepad = NotepadApp(secure_api=self.secure_api, parent=self)
            if file_path and file_path.exists():
                self.notepad._open_file(str(file_path))
            
            self.notepad.setGeometry(self.rect())
            self.notepad.closed.connect(self._on_notepad_closed)
            self.notepad.show()
        except Exception as e:
            self._buffer.append_output(f"[ERROR] Notepad failed: {e}")
            self._set_dim(False)

    def _on_notepad_closed(self):
        self._set_dim(False)
        self._buffer.setFocus()
        self._engine._emit_prompt()

    def change_directory(self, path: str):
        """API for external callers to dynamically change directory."""
        t = Path(path).resolve()
        # Direct access to engine's executor to update CWD
        self._engine._executor.cwd = t
        self._engine._emit_prompt()

    def showEvent(self, event):
        super().showEvent(event)
        self._buffer.setFocus()
