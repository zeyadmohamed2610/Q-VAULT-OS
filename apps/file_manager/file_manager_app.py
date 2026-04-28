import os
import subprocess
import shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QFileSystemModel,
    QPushButton, QLineEdit, QMenu, QFileIconProvider
)
from PyQt5.QtCore import QDir, Qt, QSize

class FileManagerApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setStyleSheet(f"""
            QPushButton {{ background-color: {THEME['surface_raised']}; color: white; border: none; padding: 4px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {THEME['text_disabled']}; }}
            QLineEdit {{ background-color: {THEME['surface_dark']}; color: white; border: 1px solid {THEME['text_disabled']}; padding: 2px; }}
        """)

        # 🔷 Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(5, 5, 5, 5)

        self.btn_back = QPushButton("←")
        self.btn_up = QPushButton("↑")
        self.path_bar = QLineEdit()

        toolbar.addWidget(self.btn_back)
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.path_bar)

        main_layout.addLayout(toolbar)

        # 🔷 File System Model
        from system.config import get_qvault_home
        base_dir = get_qvault_home()
        os.makedirs(base_dir, exist_ok=True)

        self.model = QFileSystemModel()
        self.model.setRootPath(base_dir)
        
        self.icon_provider = QFileIconProvider()
        self.model.setIconProvider(self.icon_provider)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIndex(self.model.index(base_dir))
        self.view.setStyleSheet(f"background-color: {THEME['surface_dark']}; color: #fff; border: none;")
        self.view.setIconSize(QSize(24, 24))

        # Drag & Drop & Edits
        self.view.setEditTriggers(self.view.EditKeyPressed | self.view.SelectedClicked)
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)
        self.view.setDropIndicatorShown(True)
        self.view.setDefaultDropAction(Qt.MoveAction)
        self.view.setDragDropMode(self.view.InternalMove)

        # Context Menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._menu)

        main_layout.addWidget(self.view)

        # State
        self.history = []
        self.current_path = base_dir
        self.path_bar.setText(self.current_path)
        
        self._clipboard_path = None
        self._cut_mode = False

        self._connect()

    def _connect(self):
        self.view.doubleClicked.connect(self._open)
        self.btn_up.clicked.connect(self._go_up)
        self.btn_back.clicked.connect(self._go_back)
        self.path_bar.returnPressed.connect(self._go_path)

    def _open(self, index):
        path = self.model.filePath(index)
        if self.model.isDir(index):
            self.history.append(self.current_path)
            self.current_path = path
            self.view.setRootIndex(self.model.index(path))
            self.path_bar.setText(path)
        else:
            try:
                import os
                if hasattr(os, 'startfile'):
                    os.startfile(path)
                else:
                    subprocess.Popen(['xdg-open', path])
            except Exception as e:
                print("Failed to open file:", e)

    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        from system.config import get_qvault_home
        base_dir = get_qvault_home()
        if parent.startswith(base_dir):
            self.history.append(self.current_path)
            self.current_path = parent
            self.view.setRootIndex(self.model.index(parent))
            self.path_bar.setText(parent)

    def _go_back(self):
        if self.history:
            path = self.history.pop()
            self.current_path = path
            self.view.setRootIndex(self.model.index(path))
            self.path_bar.setText(path)

    def _go_path(self):
        path = self.path_bar.text()
        from system.config import get_qvault_home
        base_dir = get_qvault_home()
        if path.startswith(base_dir) and os.path.isdir(path):
            self.history.append(self.current_path)
            self.current_path = path
            self.view.setRootIndex(self.model.index(path))
            
    def _menu(self, pos):
        from system.trash_manager import move_to_trash

        index = self.view.indexAt(pos)
        
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {THEME['surface_mid']}; color: white; border: 1px solid {THEME['text_disabled']}; }}
            QMenu::item:selected {{ background-color: {THEME['primary_soft']}; }}
        """)
        
        path = None
        if index.isValid():
            path = self.model.filePath(index)
            rename = menu.addAction("Rename")
            menu.addSeparator()
            copy = menu.addAction("Copy")
            cut = menu.addAction("Cut")
            
        if self._clipboard_path:
            paste = menu.addAction("Paste")
            
        if index.isValid():
            menu.addSeparator()
            delete = menu.addAction("Move to Trash")

        action = menu.exec_(self.view.viewport().mapToGlobal(pos))
        
        if not action:
            return

        if action.text() == "Move to Trash" and path:
            move_to_trash(path)
        elif action.text() == "Rename" and index.isValid():
            self.view.edit(index)
        elif action.text() == "Copy" and path:
            self._clipboard_path = path
            self._cut_mode = False
        elif action.text() == "Cut" and path:
            self._clipboard_path = path
            self._cut_mode = True
        elif action.text() == "Paste":
            self._paste()

    def _paste(self):
        if not self._clipboard_path:
            return

        src = self._clipboard_path
        name = os.path.basename(src)
        dest = os.path.join(self.current_path, name)
        
        from system.config import get_qvault_home
        from assets.theme import THEME
        base_dir = get_qvault_home()
        if not os.path.abspath(dest).startswith(base_dir):
            return

        try:
            if self._cut_mode:
                shutil.move(src, dest)
            else:
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
        except Exception as e:
            print("Paste error:", e)

        if self._cut_mode:
            self._clipboard_path = None
            self._cut_mode = False
