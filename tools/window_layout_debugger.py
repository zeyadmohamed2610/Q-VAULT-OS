import sys
import os
import time

# Add workspace to path
sys.path.append(os.getcwd())

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPalette

def dump_widget_tree(widget, indent=0, report_lines=None):
    if report_lines is None:
        report_lines = []
    
    geom = widget.geometry()
    size = widget.size()
    visible = widget.isVisible()
    is_hidden = widget.isHidden()
    # Handle cases where classes override .layout() method with an attribute
    layout_obj = getattr(widget, "layout", None)
    if callable(layout_obj):
        try:
            layout = layout_obj()
        except TypeError:
            layout = None # It was a layout object itself that raised TypeError when called
    else:
        layout = layout_obj

    if layout is None:
        # Fallback to get children layouts or internal
        pass
        
    layout_info = type(layout).__name__ if layout else "No Layout"
    margins = "None"
    if layout and hasattr(layout, "contentsMargins"):
        try:
            m = layout.contentsMargins()
            margins = f"({m.left()},{m.top()},{m.right()},{m.bottom()})"
        except: pass
    
    name = widget.objectName() or "Unnamed"
    cls = type(widget).__name__
    
    status = ""
    if size.width() == 0 or size.height() == 0:
        status += "[ZERO_SIZE] "
    if is_hidden:
        status += "[HIDDEN] "
    if not layout and widget.children():
        status += "[ORPHAN_CHILDREN?] "

    line = f"{'  ' * indent}- {cls} ({name}) | Rect: {geom.x()},{geom.y()} {size.width()}x{size.height()} | {layout_info} Margins: {margins} | {status}"
    report_lines.append(line)
    
    for child in widget.children():
        if isinstance(child, QWidget):
            dump_widget_tree(child, indent + 1, report_lines)
            
    return report_lines

def attach_diagnostic_borders(window):
    """Adds colored borders for visual diagnosis."""
    try:
        # OSWindow - Magenta
        window.setStyleSheet(window.styleSheet() + "; border: 2px solid magenta;")
        
        # Title Bar - Green
        if hasattr(window, 'title_bar') and window.title_bar:
            window.title_bar.setStyleSheet(window.title_bar.styleSheet() + "; border: 2px solid green;")
            
        # WindowContent - Cyan
        for child in window.children():
            if isinstance(child, QWidget) and child.objectName() == "WindowContent":
                child.setStyleSheet(child.styleSheet() + "; border: 2px solid cyan;")
                
        # App Root Widget - Yellow
        if hasattr(window, 'content_widget') and window.content_widget:
            window.content_widget.setStyleSheet(window.content_widget.styleSheet() + "; border: 2px solid yellow;")
            
    except Exception as e:
        print(f"Error styling: {e}")
