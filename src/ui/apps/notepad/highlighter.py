from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import QRegExp

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6")) # Pink
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True",
            "try", "while", "with", "yield", "self"
        ]
        for word in keywords:
            pattern = QRegExp(r"\b" + word + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

        # Class format
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#50fa7b")) # Green
        class_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\bQ[A-Za-z]+\b"), class_format))

        # Function format
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#50fa7b")) # Green
        self.highlighting_rules.append((QRegExp(r"\b[A-Za-z0-9_]+(?=\()"), function_format))

        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c")) # Yellow
        self.highlighting_rules.append((QRegExp(r"\".*\""), string_format))
        self.highlighting_rules.append((QRegExp(r"'.*'"), string_format))

        # Comment format
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4")) # Gray/Blue
        self.highlighting_rules.append((QRegExp(r"#[^\n]*"), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
