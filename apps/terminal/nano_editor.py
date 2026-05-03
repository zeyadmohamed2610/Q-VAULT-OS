from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLabel, QPushButton, QFrame, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence, QColor
from pathlib import Path

class NanoTextEdit(QTextEdit):
    """Subclass to handle specific nano shortcuts and prevent consumption."""
    def keyPressEvent(self, event):
        # Intercept Ctrl+S and Ctrl+X before QTextEdit handles them
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.parent()._save()
                return
            if event.key() == Qt.Key_X:
                self.parent()._exit()
                return
        super().keyPressEvent(event)

class NanoEditor(QWidget):
    """
    A simple overlay editor triggered by 'nano' in terminal.
    """
    closed = pyqtSignal()
    saved = pyqtSignal(str)

    def __init__(self, file_path: Path, content: str = "", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._setup_ui()
        self._editor.setPlainText(content)
        
        # Focus the editor immediately
        self._editor.setFocus()

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget { background: #0b162d; color: #d4e8f0; }
            QTextEdit { 
                background: #0d1117; 
                border: 1px solid #30363d; 
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                padding: 10px;
                color: #d4e8f0;
            }
            QLabel#Title { color: #54b1c6; font-weight: bold; }
            QLabel#Footer { color: #4a6880; font-size: 10px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        hdr = QHBoxLayout()
        title = QLabel(f"Nano — {self.file_path.name}")
        title.setObjectName("Title")
        hdr.addWidget(title)
        hdr.addStretch()
        
        self.status = QLabel("")
        self.status.setStyleSheet("color: #00ff88; font-size: 10px;")
        hdr.addWidget(self.status)
        layout.addLayout(hdr)
        
        # Editor (Using our subclass)
        self._editor = NanoTextEdit(self)
        self._editor.setAcceptRichText(False)
        layout.addWidget(self._editor)
        
        # Footer
        footer = QHBoxLayout()
        f_lbl = QLabel("^S Save  |  ^X Exit")
        f_lbl.setObjectName("Footer")
        footer.addWidget(f_lbl)
        layout.addLayout(footer)

    def _save(self):
        try:
            content = self._editor.toPlainText()
            self.file_path.write_text(content, encoding='utf-8')
            self.status.setText("SAVED")
            self.status.setStyleSheet("color: #00ff88; font-size: 10px;")
            self.saved.emit(content)
        except Exception as e:
            self.status.setText(f"ERROR: {str(e)}")
            self.status.setStyleSheet("color: #f85149; font-size: 10px;")

    def _exit(self):
        self.closed.emit()
        self.deleteLater()
