import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QTextEdit,
    QLabel, QPushButton, QFrame, QShortcut, QLineEdit, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QTimer
from PyQt5.QtGui import QFont, QKeySequence, QColor, QTextFormat, QPainter

logger = logging.getLogger(__name__)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class AdvancedTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        from resources.theme import THEME
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(THEME['bg_black']))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(THEME['text_muted']))
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        from resources.theme import THEME
        selection = QTextEdit.ExtraSelection()
        line_color = QColor(THEME['hover_glow'])
        selection.format.setBackground(line_color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_S or event.key() == Qt.Key_O:
                self.parent()._save()
                return
            if event.key() == Qt.Key_X:
                self.parent()._exit()
                return
            if event.key() == Qt.Key_W:
                self.parent()._show_search()
                return
        super().keyPressEvent(event)

class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.setFixedWidth(300)
        self.setStyleSheet("background: #161b22; color: #c9d1d9; border: 1px solid #30363d;")
        layout = QVBoxLayout(self)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search for...")
        self.input.setStyleSheet("background: #0d1117; padding: 5px;")
        layout.addWidget(self.input)
        
        btns = QHBoxLayout()
        find_btn = QPushButton("Find Next")
        find_btn.setStyleSheet("background: #238636; border-radius: 4px; padding: 5px;")
        find_btn.clicked.connect(self.accept)
        btns.addWidget(find_btn)
        layout.addLayout(btns)
        
    def get_text(self):
        return self.input.text()

class NanoEditor(QWidget):
    closed = pyqtSignal()
    saved = pyqtSignal(str)

    def __init__(self, file_path: Path, content: str = "", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._setup_ui()
        self._editor.setPlainText(content)
        self._editor.setFocus()

    def _setup_ui(self):
        from resources.theme import THEME
        self.setStyleSheet(f"""
            QWidget {{ background: {THEME['bg_dark']}; color: {THEME['text_main']}; }}
            AdvancedTextEdit {{ 
                background: {THEME['bg_black']}; 
                border: 1px solid {THEME['border_subtle']}; 
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                color: {THEME['text_main']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(30)
        self.header.setStyleSheet(f"background: {THEME['bg_black']}; border-bottom: 1px solid {THEME['border_subtle']};")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("NANO - " + self.file_path.name)
        title.setStyleSheet(f"color: {THEME['primary_glow']}; font-family: 'Segoe UI Semibold', sans-serif; font-size: 11px;")
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        self.status = QLabel("Line 1, Col 1")
        self.status.setStyleSheet(f"color: {THEME['success']}; font-size: 10px;")
        h_layout.addWidget(self.status)
        layout.addWidget(self.header)
        
        # Editor
        self._editor = AdvancedTextEdit(self)
        layout.addWidget(self._editor)
        
        # Footer
        self.footer = QFrame()
        self.footer.setFixedHeight(50)
        self.footer.setStyleSheet(f"background: {THEME['bg_black']}; border-top: 1px solid {THEME['border_subtle']};")
        f_layout = QVBoxLayout(self.footer)
        f_layout.setContentsMargins(15, 5, 15, 5)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(" [ ∆ ] Help    [ ∇ ] Save    [ ⌕ ] Find    [ ⊖ ] Cut"))
        row1.addStretch()
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(" [ ⊗ ] Exit    [ ∐ ] Load    [ ⇄ ] Swap    [ ⊕ ] Paste"))
        row2.addStretch()
        
        for r in [row1, row2]:
            for i in range(r.count()):
               for w in [self._btn_save, self._btn_exit, self._btn_find]:
                if w: w.setStyleSheet(f"color: {THEME['primary_glow']}; font-family: 'Cascadia Code', monospace; font-size: 11px;")
        
        f_layout.addLayout(row1)
        f_layout.addLayout(row2)
        layout.addWidget(self.footer)

    def _save(self):
        from resources.theme import THEME
        try:
            content = self._editor.toPlainText()
            self.file_path.write_text(content, encoding='utf-8')
            self.status.setText("[ Saved Successfully ]")
            # Use context-aware singleShot to avoid "wrapped object deleted" error
            QTimer.singleShot(2000, self, lambda: self._clear_status())
            self.saved.emit(content)
        except Exception as e:
            self.status.setText(f"[ ERROR: {str(e)} ]")
            self.status.setStyleSheet(f"color: {THEME['accent_error']};")

    def _show_search(self):
        dlg = SearchDialog(self)
        if dlg.exec_():
            text = dlg.get_text()
            if not self._editor.find(text):
                # Wrap around
                cursor = self._editor.textCursor()
                cursor.movePosition(QPainter.Begin)
                self._editor.setTextCursor(cursor)
                self._editor.find(text)

    def _clear_status(self):
        try:
            if hasattr(self, 'status') and self.status:
                self.status.setText("")
        except RuntimeError:
            pass

    def _exit(self):
        self.closed.emit()
        self.deleteLater()
