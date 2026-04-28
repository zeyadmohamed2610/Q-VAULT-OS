from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QCompleter
from PyQt5.QtGui import QFont, QColor, QTextCursor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtCore import Qt, QRegExp, QStringListModel

from system.runtime.isolated_widget import IsolatedAppWidget
from assets.theme import THEME

class TerminalHighlighter(QSyntaxHighlighter):
    """Syntax Highlighter for Kali-level visual feedback."""
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        # 1. Prompt (Green username, Blue path)
        prompt_user_fmt = QTextCharFormat()
        prompt_user_fmt.setForeground(QColor("#50fa7b"))
        prompt_user_fmt.setFontWeight(QFont.Bold)
        self.rules.append((QRegExp(r"^vault@node"), prompt_user_fmt))

        # 2. Commands (Cyan)
        cmd_fmt = QTextCharFormat()
        cmd_fmt.setForeground(QColor("#8be9fd"))
        self.rules.append((QRegExp(r"\b(ls|cd|pwd|analyze|shadow|audit|help|clear|cat|echo|rm|mkdir|touch|ping|qsu)\b"), cmd_fmt))

        # 3. Success / OK (Green)
        success_fmt = QTextCharFormat()
        success_fmt.setForeground(QColor("#50fa7b"))
        self.rules.append((QRegExp(r"\b(Success|OK|Done|Ready|Verified|Authenticated)\b"), success_fmt))

        # 4. Errors / Failures (Red)
        error_fmt = QTextCharFormat()
        error_fmt.setForeground(QColor("#ff5555"))
        self.rules.append((QRegExp(r"\b(Error|Failed|Exception|Blocked|Denied|Critical|Risk)\b"), error_fmt))

        # 5. Paths (Yellow/Orange)
        path_fmt = QTextCharFormat()
        path_fmt.setForeground(QColor("#f1fa8c"))
        self.rules.append((QRegExp(r"/[a-zA-Z0-9\._\-/]+"), path_fmt))

        # 6. AI Impact Tags (Purple)
        impact_fmt = QTextCharFormat()
        impact_fmt.setForeground(QColor("#bd93f9"))
        self.rules.append((QRegExp(r"\[(Impact|AI Analysis|Sandbox)\]"), impact_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

class TerminalWidget(QPlainTextEdit):
    """Integrated Interactive Emulator with Bash-style Autocomplete and Highlighting."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setObjectName("TerminalEmulator")
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet(f"""
            background-color: {THEME['bg_dark']}; 
            color: {THEME['text_main']}; 
            border: none; 
            selection-background-color: {THEME['border_muted']};
        """)
        
        self.prompt = "vault@node:~$ "
        self.history = []
        self.history_idx = -1
        self.password_mode = False
        self._pass_buffer = ""
        
        # 1. Highlighter
        self.highlighter = TerminalHighlighter(self.document())
        
        # 2. Completer (Bash-style)
        self.commands = [
            "ls", "cd", "pwd", "analyze", "shadow", "audit", 
            "help", "clear", "cat", "echo", "rm", "mkdir", "touch", "ping", "qsu"
        ]
        self.completer = QCompleter(self.commands, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self._insert_completion)

        self._write_prompt()
        self._set_command_start()

    def _write_prompt(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.insertPlainText(self.prompt)
        self._set_command_start()

    def _set_command_start(self):
        self.command_start_pos = self.textCursor().position()

    def _insert_completion(self, completion):
        cursor = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        cursor.movePosition(QTextCursor.Left)
        cursor.movePosition(QTextCursor.EndOfWord)
        cursor.insertText(completion[-extra:])
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        # 1. Tab Autocomplete (Disable in Password Mode)
        if event.key() == Qt.Key_Tab and not self.password_mode:
            if self.completer.popup().isVisible():
                event.ignore()
                return
            
            cursor = self.textCursor()
            cursor.select(QTextCursor.WordUnderCursor)
            prefix = cursor.selectedText()
            
            if prefix:
                self.completer.setCompletionPrefix(prefix)
                rect = self.cursorRect()
                rect.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(rect)
            return

        cursor = self.textCursor()
        
        # 2. Backspace Protection
        if event.key() == Qt.Key_Backspace:
            if cursor.position() <= self.command_start_pos:
                return
            if self.password_mode:
                self._pass_buffer = self._pass_buffer[:-1]

        # 3. Command Execution
        elif event.key() == Qt.Key_Return:
            text = self.toPlainText()
            command = self._pass_buffer if self.password_mode else text[self.command_start_pos:].strip()
            
            self._pass_buffer = "" # Clear buffer
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
            self.insertPlainText("\n")
            
            if command or self.password_mode:
                if not self.password_mode:
                    self.history.append(command)
                    self.history_idx = len(self.history)
                self.parent_app.call_remote("execute_command", command)
            else:
                self._write_prompt()
            return

        # 4. History (Up/Down)
        elif event.key() == Qt.Key_Up and not self.password_mode:
            if self.history and self.history_idx > 0:
                self.history_idx -= 1
                self._replace_command(self.history[self.history_idx])
            return
        elif event.key() == Qt.Key_Down and not self.password_mode:
            if self.history and self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self._replace_command(self.history[self.history_idx])
            elif self.history_idx == len(self.history) - 1:
                self.history_idx = len(self.history)
                self._replace_command("")
            return

        # 5. Prevent editing old lines
        if cursor.position() < self.command_start_pos:
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)

        # 6. Password Masking
        if self.password_mode and event.text() and event.key() not in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Backspace):
            self._pass_buffer += event.text()
            self.insertPlainText("*") # Show asterisk
            return

        super().keyPressEvent(event)

    def set_password_mode(self, enabled):
        """Toggle masking for password inputs."""
        self.password_mode = enabled
        self._pass_buffer = ""

    def _replace_command(self, new_cmd):
        cursor = self.textCursor()
        cursor.setPosition(self.command_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertPlainText(new_cmd)
        self.setTextCursor(cursor)

    def append_output(self, text):
        if "\x0c" in text:
            self.clear()
            self._write_prompt()
            return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        if text.strip() or text == "\n":
            self.insertPlainText(text)
        
        if text.endswith("\n") or text == "":
            self._write_prompt()

    def update_prompt(self, new_prompt):
        """Updates the prompt string and redraws it if at the end."""
        self.prompt = new_prompt
        # If we just finished a command, the next _write_prompt will use the new one.

class TerminalApp(IsolatedAppWidget):
    """
    Process-Isolated Terminal Frontend (v4.5 Kali Alignment).
    Featuring Interactive Emulator, Bash-style Autocomplete, and Syntax Highlighting.
    """
    APP_ID = "terminal"

    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id=self.APP_ID,
            module_path="apps.terminal.terminal_engine",
            class_name="TerminalEngine",
            secure_api=secure_api,
            parent=parent
        )

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("AppContainer")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.terminal = TerminalWidget(self)
        layout.addWidget(self.terminal)

    def handle_event(self, event, data):
        """Asynchronous events from the isolated engine."""
        if event == "output_ready":
            self.terminal.append_output(data)
        elif event == "prompt_update":
            self.terminal.update_prompt(data)
        elif event == "password_mode":
            self.terminal.set_password_mode(data)

    def on_start(self):
        self.terminal.setFocus()
        self.call_remote("boot_terminal")

    def get_permissions(self):
        return ["file_access:workspace", "system_calls:governed"]