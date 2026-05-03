import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, 
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
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#161b22"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#8b949e"))
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        selection = QPlainTextEdit.ExtraSelection()
        line_color = QColor("#1c2128")
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
        self.setStyleSheet("""
            QWidget { background: #0b162d; color: #d4e8f0; }
            AdvancedTextEdit { 
                background: #0d1117; 
                border: 1px solid #30363d; 
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                color: #c9d1d9;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(30)
        self.header.setStyleSheet("background: #161b22; border-bottom: 1px solid #30363d;")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel(f"GNU Nano 7.2 — {self.file_path.name}")
        title.setStyleSheet("color: #c9d1d9; font-weight: bold;")
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        self.status = QLabel("")
        self.status.setStyleSheet("color: #3fb950; font-size: 10px;")
        h_layout.addWidget(self.status)
        layout.addWidget(self.header)
        
        # Editor
        self._editor = AdvancedTextEdit(self)
        layout.addWidget(self._editor)
        
        # Footer
        self.footer = QFrame()
        self.footer.setFixedHeight(50)
        self.footer.setStyleSheet("background: #161b22; border-top: 1px solid #30363d;")
        f_layout = QVBoxLayout(self.footer)
        f_layout.setContentsMargins(15, 5, 15, 5)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("\033[7m^G\033[0m Get Help  \033[7m^O\033[0m Write Out  \033[7m^W\033[0m Where Is   \033[7m^K\033[0m Cut Text"))
        row1.addStretch()
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("\033[7m^X\033[0m Exit      \033[7m^R\033[0m Read File  \033[7m^\\\033[0m Replace    \033[7m^U\033[0m Uncut Text"))
        row2.addStretch()
        
        for r in [row1, row2]:
            for i in range(r.count()):
                w = r.itemAt(i).widget()
                if w: w.setStyleSheet("color: #8b949e; font-family: monospace; font-size: 10px;")
        
        f_layout.addLayout(row1)
        f_layout.addLayout(row2)
        layout.addWidget(self.footer)

    def _save(self):
        try:
            content = self._editor.toPlainText()
            self.file_path.write_text(content, encoding='utf-8')
            self.status.setText("[ Saved Successfully ]")
            QTimer.singleShot(2000, lambda: self.status.setText(""))
            self.saved.emit(content)
        except Exception as e:
            self.status.setText(f"[ ERROR: {str(e)} ]")
            self.status.setStyleSheet("color: #f85149;")

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

    def _exit(self):
        self.closed.emit()
        self.deleteLater()
