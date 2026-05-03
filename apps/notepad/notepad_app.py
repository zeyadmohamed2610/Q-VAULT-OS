import logging
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLabel, QFileDialog, QMenuBar, QMenu, QAction, 
    QMessageBox, QStatusBar, QToolBar, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat

logger = logging.getLogger(__name__)

class NotepadApp(QWidget):
    """
    A professional, realistic Notepad application for Q-Vault OS.
    Features: Open, Save, Save As, New, Basic Editing, Status Bar.
    """
    closed = pyqtSignal()

    def __init__(self, secure_api=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.secure_api = secure_api
        self.current_file = None
        self._setup_ui()
        
    def _setup_ui(self):
        # Professional Dark Theme Styling
        self.setStyleSheet("""
            QWidget { 
                background: #0d1117; 
                color: #c9d1d9; 
                font-family: 'Segoe UI', sans-serif;
            }
            QTextEdit { 
                background: #0d1117; 
                border: none; 
                border-top: 1px solid #30363d;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                padding: 15px;
                color: #c9d1d9;
            }
            QMenuBar { 
                background: #161b22; 
                border-bottom: 1px solid #30363d; 
                color: #8b949e;
                padding: 2px;
            }
            QMenuBar::item:selected { background: #21262d; color: #58a6ff; }
            QMenu { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; }
            QMenu::item:selected { background: #21262d; color: #58a6ff; }
            QStatusBar { background: #161b22; color: #8b949e; border-top: 1px solid #30363d; font-size: 11px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Menu Bar
        self.menu_bar = QMenuBar(self)
        
        # File Menu
        file_menu = self.menu_bar.addMenu("File")
        new_act = QAction("New", self)
        new_act.setShortcut("Ctrl+N")
        new_act.triggered.connect(self._new_file)
        file_menu.addAction(new_act)
        
        open_act = QAction("Open...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)
        
        save_act = QAction("Save", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_file)
        file_menu.addAction(save_act)
        
        save_as_act = QAction("Save As...", self)
        save_as_act.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_act)
        
        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)
        
        # Edit Menu
        edit_menu = self.menu_bar.addMenu("Edit")
        undo_act = QAction("Undo", self)
        undo_act.setShortcut("Ctrl+Z")
        undo_act.triggered.connect(lambda: self.editor.undo())
        edit_menu.addAction(undo_act)
        
        redo_act = QAction("Redo", self)
        redo_act.setShortcut("Ctrl+Y")
        redo_act.triggered.connect(lambda: self.editor.redo())
        edit_menu.addAction(redo_act)
        
        edit_menu.addSeparator()
        cut_act = QAction("Cut", self)
        cut_act.setShortcut("Ctrl+X")
        cut_act.triggered.connect(lambda: self.editor.cut())
        edit_menu.addAction(cut_act)
        
        copy_act = QAction("Copy", self)
        copy_act.setShortcut("Ctrl+C")
        copy_act.triggered.connect(lambda: self.editor.copy())
        edit_menu.addAction(copy_act)
        
        paste_act = QAction("Paste", self)
        paste_act.setShortcut("Ctrl+V")
        paste_act.triggered.connect(lambda: self.editor.paste())
        edit_menu.addAction(paste_act)
        
        layout.addWidget(self.menu_bar)
        
        # Main Editor
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")
        self.lbl_cursor = QLabel("Ln 1, Col 1")
        self.status_bar.addPermanentWidget(self.lbl_cursor)
        layout.addWidget(self.status_bar)
        
        self.editor.cursorPositionChanged.connect(self._update_cursor_status)
        
        self._is_dirty = False
        self._update_title()

    def _update_cursor_status(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.lbl_cursor.setText(f"Ln {line}, Col {col}")

    def _update_title(self):
        name = Path(self.current_file).name if self.current_file else "Untitled"
        dirty = "*" if self._is_dirty else ""
        title = f"{name}{dirty} — Q-Vault Notepad"
        # Since this is a widget, we can't set window title directly if it's inside a shell.
        # But we can emit a signal or let the window manager handle it.
        if hasattr(self, "setWindowTitle"):
            self.setWindowTitle(title)
        
        # If wrapped in OSWindow, update its title
        if self.parent() and hasattr(self.parent(), "setWindowTitle"):
            self.parent().setWindowTitle(title)

    def _on_text_changed(self):
        if not self._is_dirty:
            self._is_dirty = True
            self._update_title()

    def _new_file(self):
        if self._is_dirty:
            res = QMessageBox.question(self, "Unsaved Changes", "Save changes to current file?", 
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if res == QMessageBox.Cancel: return
            if res == QMessageBox.Yes: self._save_file()
            
        self.editor.clear()
        self.current_file = None
        self._is_dirty = False
        self._update_title()
        self.status_bar.showMessage("New file created", 3000)

    def _open_file(self, path=None):
        if not path:
            from system.config import get_qvault_home
            path, _ = QFileDialog.getOpenFileName(self, "Open File", get_qvault_home(), "All Files (*)")
        
        if path:
            try:
                p = Path(path)
                content = p.read_text(encoding='utf-8', errors='replace')
                self.editor.setPlainText(content)
                self.current_file = path
                self._is_dirty = False
                self._update_title()
                self.status_bar.showMessage(f"Opened {p.name}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def _save_file(self):
        if self.current_file:
            try:
                Path(self.current_file).write_text(self.editor.toPlainText(), encoding='utf-8')
                self._is_dirty = False
                self._update_title()
                self.status_bar.showMessage("Saved successfully", 3000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")
                return False
        else:
            return self._save_file_as()

    def _save_file_as(self):
        from system.config import get_qvault_home
        path, _ = QFileDialog.getSaveFileName(self, "Save File As", get_qvault_home(), "Text Files (*.txt);;All Files (*)")
        if path:
            self.current_file = path
            return self._save_file()
        return False

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)