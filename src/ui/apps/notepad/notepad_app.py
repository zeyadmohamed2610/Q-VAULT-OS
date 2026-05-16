import logging
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit,
    QLabel, QFileDialog, QMenuBar, QMenu, QAction, 
    QMessageBox, QStatusBar, QToolBar, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QEvent
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat, QPainter, QTextFormat
from .highlighter import PythonHighlighter
from resources.theme import THEME

logger = logging.getLogger(__name__)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        
        self.highlighter = PythonHighlighter(self.document())

    def line_number_area_width(self):
        digits = 1
        max_v = max(1, self.blockCount())
        while max_v >= 10:
            max_v //= 10
            digits += 1
        space = 20 + self.fontMetrics().width('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(THEME['primary_glow']).lighter(160)
            line_color.setAlpha(20)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(THEME['bg_black']))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(THEME['text_muted']))
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

class NotepadApp(QWidget):
    """
    A professional, realistic Notepad application for Q-Vault OS.
    Features: Open, Save, Save As, New, Basic Editing, Status Bar.
    """
    closed = pyqtSignal()

    def __init__(self, secure_api=None, parent=None, file_path=None, **kwargs):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.secure_api = secure_api
        self.current_file = None
        self._setup_ui()
        
        if file_path:
            # Delay slightly to ensure UI is ready
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._open_file(file_path))
        
    def _setup_ui(self):
        # Professional Dark Theme Styling
        from resources import theme
        self.setStyleSheet(f"""
            QWidget {{ 
                background: {theme.THEME['bg_dark']}; 
                color: {theme.THEME['text_main']}; 
                font-family: {theme.FONT['family']};
            }}
            QTextEdit {{ 
                background: {theme.THEME['bg_black']}; 
                border: none; 
                border-top: 1px solid {theme.THEME['border_subtle']};
                font-family: {theme.FONT_MONO};
                font-size: 14px;
                padding: 15px;
                color: {theme.THEME['text_main']};
            }}
            QMenuBar {{ 
                background: {theme.THEME['bg_black']}; 
                border-bottom: 1px solid {theme.THEME['border_subtle']}; 
                color: {theme.THEME['text_dim']};
                padding: 2px;
            }}
            QMenuBar::item:selected {{ background: {theme.THEME['hover_glow']}; color: {theme.THEME['primary_glow']}; }}
            QMenu {{ background: {theme.THEME['bg_dark']}; border: 1px solid {theme.THEME['border_color']}; color: {theme.THEME['text_main']}; }}
            QMenu::item:selected {{ background: {theme.THEME['hover_glow']}; color: {theme.THEME['primary_glow']}; }}
            QStatusBar {{ background: {theme.THEME['bg_black']}; color: {theme.THEME['text_muted']}; border-top: 1px solid {theme.THEME['border_subtle']}; font-size: 11px; }}
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
        self.editor = CodeEditor()
        self.editor.setAcceptDrops(True)
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