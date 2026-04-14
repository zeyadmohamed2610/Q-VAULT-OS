# =============================================================
#  terminal.py — Q-Vault OS  |  Real Shell Engine v1
#
#  Real execution of host OS commands via subprocess
#  No simulation - direct system interaction
# =============================================================

import os
import sys
import platform
import subprocess
import shutil
import pathlib
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QHBoxLayout,
    QLabel,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeyEvent

from assets import theme
from system.session_manager import SESSION
from system.permission_system import PERM_MGR
from system.package_system import PKG_MGR
from system.security_input import (
    SANITIZER,
    sanitize_input,
    validate_path,
    check_root_command,
)


HOST_OS = platform.system()
IS_WINDOWS = HOST_OS == "Windows"

USER_HOME = pathlib.Path.home()
USER_NAME = os.getenv("USERNAME", os.getenv("USER", "user"))


def _e(t: str) -> str:
    """Escape HTML entities."""
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class RealTerminal(QWidget):
    """Real shell that executes commands on the host OS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Terminal")
        self.setStyleSheet(theme.TERMINAL_STYLE)

        # Current user session
        # Use logged-in session user, fall back to "user"
        _su = SESSION.current_user
        self._current_user = _su if _su else SESSION.get_user("user")
        self._effective_user = self._current_user
        self._is_root = False

        self._cwd = str(USER_HOME)
        self._history = []
        self._hist_idx = -1
        self._last_exit = 0
        self._current_process = None

        self._setup_ui()
        self._show_banner()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._output = QTextEdit()
        self._output.setObjectName("TermOutput")
        self._output.setReadOnly(True)
        self._output.setFontFamily("Consolas")
        self._output.setStyleSheet(
            f"QTextEdit#TermOutput {{ background: #060a10; color: {theme.ACCENT_GREEN}; border: none; padding: 8px; }}"
        )
        root.addWidget(self._output, stretch=1)

        self._prompt = QLabel()
        self._prompt.setStyleSheet(
            f"color: {theme.ACCENT_GREEN}; font-family: Consolas; font-size: 13px; background: #060a10; padding-left: 8px;"
        )
        self._prompt.setFixedHeight(28)

        self._input = QLineEdit()
        self._input.setStyleSheet(
            f"background: #060a10; color: {theme.ACCENT_GREEN}; border: none; font-family: Consolas; font-size: 13px; padding-left: 4px;"
        )
        self._input.returnPressed.connect(self._on_enter)
        self._input.installEventFilter(self)

        input_container = QWidget()
        input_container.setStyleSheet(
            f"background: #060a10; border-top: 1px solid {theme.BORDER_DIM};"
        )
        row = QHBoxLayout(input_container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._prompt)
        row.addWidget(self._input)
        root.addWidget(input_container)

        self._update_prompt()

    def _update_prompt(self):
        cwd = os.path.basename(self._cwd) or self._cwd
        user = self._effective_user.username if self._effective_user else "user"
        host = HOST_OS.lower()
        suffix = "# " if self._is_root else "$ "
        self._prompt.setText(f"{user}@{host}:{_e(cwd)}{suffix}")

    def _show_banner(self):
        self._out(f"Q-VAULT OS Real Shell v1.0 (Multi-User)")
        self._out(f"Host: {HOST_OS} {platform.release()}")
        self._out(
            f"User: {self._current_user.username if self._current_user else 'user'}"
        )
        self._out(f"Home: {USER_HOME}")
        self._out(f"Type 'help' for available commands.")
        self._out("")

    def _out(self, text: str):
        self._output.append(_e(text))
        self._scroll_down()

    def _err(self, text: str):
        self._output.append(
            f'<span style="color: {theme.ACCENT_RED};">{_e(text)}</span>'
        )
        self._scroll_down()

    def _scroll_down(self):
        sb = self._output.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_enter(self):
        cmd = self._input.text()
        self._input.clear()

        if not cmd.strip():
            return

        # Sanitize input before execution
        is_safe, sanitized, reason = sanitize_input(cmd)
        if not is_safe:
            self._err(f"Command blocked: {reason}")
            self._last_exit = 1
            return

        self._out(f"{USER_NAME}@{HOST_OS.lower()}:{os.path.basename(self._cwd)}$ {cmd}")

        self._history.append(cmd)
        self._hist_idx = len(self._history)

        parts = sanitized.split()
        if not parts:
            return

        self._execute(parts)

    def _execute(self, tokens: list):
        cmd = tokens[0]
        args = tokens[1:]

        if cmd == "help":
            self._show_help()
            return

        if cmd == "clear":
            self._output.clear()
            return

        if cmd == "cd":
            self._cmd_cd(args)
            return

        if cmd == "exit":
            self._out("Use Alt+F4 to close the terminal window.")
            return

        if cmd == "pwd":
            self._out(self._cwd)
            return

        if cmd == "whoami":
            self._out(USER_NAME)
            return

        if cmd == "hostname":
            self._out(platform.node())
            return

        if cmd == "date":
            self._out(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
            return

        if cmd == "echo":
            self._out(" ".join(args))
            return

        if cmd == "ls":
            self._cmd_ls(args)
            return

        if cmd == "dir":
            self._cmd_ls(["-l"] + args)
            return

        if cmd == "cat":
            self._cmd_cat(args)
            return

        if cmd == "type" or cmd == "which":
            self._cmd_which(args)
            return

        if cmd == "tree":
            self._cmd_tree(args)
            return

        if cmd == "mkdir":
            self._cmd_mkdir(args)
            return

        if cmd == "touch":
            self._cmd_touch(args)
            return

        if cmd == "rm":
            self._cmd_rm(args)
            return

        if cmd == "cp":
            self._cmd_cp(args)
            return

        if cmd == "mv":
            self._cmd_mv(args)
            return

        if cmd == "df":
            self._cmd_df(args)
            return

        if cmd == "free":
            self._cmd_free(args)
            return

        if cmd == "ps":
            self._cmd_ps(args)
            return

        if cmd == "tasklist":
            self._cmd_tasklist(args)
            return

        if cmd == "systeminfo":
            self._cmd_systeminfo(args)
            return

        if cmd == "uname":
            self._cmd_uname(args)
            return

        if cmd == "ver":
            self._out(f"{HOST_OS} {platform.release()}")
            return

        # User management commands
        if cmd == "su":
            self._cmd_su(args)
            return

        if cmd == "sudo":
            self._cmd_sudo(args)
            return

        if cmd == "useradd":
            self._cmd_useradd(args)
            return

        if cmd == "passwd":
            self._cmd_passwd(args)
            return

        if cmd == "users":
            self._cmd_users()
            return

        if cmd == "id":
            self._cmd_id()
            return

        if cmd == "groups":
            self._cmd_groups(args)
            return

        # Package management commands
        if cmd == "apt":
            self._cmd_apt(args)
            return

        # Permission commands
        if cmd == "chmod":
            self._cmd_chmod(args)
            return

        if cmd == "chown":
            self._cmd_chown(args)
            return

        self._run_subprocess(cmd, args)

    def _run_subprocess(self, cmd: str, args: list):
        # Check root command permission
        allowed, reason = check_root_command(
            cmd,
            self._current_user.username if self._current_user else "unknown",
            self._is_root,
        )
        if not allowed:
            self._err(f"Permission denied: {reason}")
            self._last_exit = 1
            return

        full_cmd = [cmd] + args

        try:
            # Always use shell=False for security
            # On Windows, use shell=True only for cmd.exe builtins
            use_shell = False
            if IS_WINDOWS and cmd.lower() in [
                "cmd",
                "dir",
                "type",
                "echo",
                "set",
                "cd",
                "mkdir",
                "del",
                "copy",
                "move",
            ]:
                use_shell = True

            result = subprocess.run(
                full_cmd,
                cwd=self._cwd,
                capture_output=True,
                text=True,
                timeout=5,  # 5 second timeout max
                shell=use_shell,
            )
            self._last_exit = result.returncode
            if result.stdout:
                for line in result.stdout.rstrip("\n").split("\n"):
                    self._out(line)
            if result.stderr:
                for line in result.stderr.rstrip("\n").split("\n"):
                    self._err(line)
        except FileNotFoundError:
            self._err(f"{cmd}: command not found")
            self._last_exit = 127
        except subprocess.TimeoutExpired:
            self._err(f"{cmd}: command timed out (5s limit)")
            self._last_exit = 124
        except PermissionError:
            self._err(f"{cmd}: permission denied")
            self._last_exit = 126
        except Exception as e:
            self._err(f"{cmd}: {str(e)}")
            self._last_exit = 1

    def _show_help(self):
        cmds = [
            ("cd [dir]", "Change directory"),
            ("ls [-la]", "List files"),
            ("cat <file>", "Display file contents"),
            ("pwd", "Print working directory"),
            ("whoami", "Current user"),
            ("hostname", "System name"),
            ("date", "Current date/time"),
            ("mkdir <dir>", "Create directory"),
            ("touch <file>", "Create empty file"),
            ("rm <file>", "Delete file"),
            ("cp <src> <dst>", "Copy file"),
            ("mv <src> <dst>", "Move file"),
            ("tree", "Directory tree"),
            ("df", "Disk usage"),
            ("free", "Memory usage"),
            ("ps", "Running processes"),
            ("systeminfo", "System information"),
            ("clear", "Clear screen"),
            ("exit", "Exit terminal"),
            ("--- USER MANAGEMENT ---", ""),
            ("su <user>", "Switch user"),
            ("sudo <cmd>", "Execute as root"),
            ("useradd <name>", "Create user (root)"),
            ("passwd [user]", "Change password"),
            ("users", "List all users"),
            ("id", "Display user ID"),
            ("groups [user]", "Display user groups"),
            ("--- PACKAGES ---", ""),
            ("apt install <pkg>", "Install package"),
            ("apt remove <pkg>", "Remove package"),
            ("apt list", "List packages"),
            ("apt search <query>", "Search packages"),
            ("--- PERMISSIONS ---", ""),
            ("chmod <mode> <file>", "Change permissions"),
            ("chown <user> <file>", "Change owner (root)"),
        ]
        for c, d in cmds:
            if d:
                self._out(f"  {c:24s} - {d}")
            else:
                self._out(f"\n{c}")

    def _cmd_cd(self, args):
        if not args:
            target = str(USER_HOME)
        else:
            target = args[0]

        if target == "~":
            target = str(USER_HOME)
        elif target == "-":
            return

        if os.path.isabs(target):
            new_cwd = target
        else:
            new_cwd = os.path.normpath(os.path.join(self._cwd, target))

        # Validate path to prevent traversal
        is_safe, resolved = validate_path(new_cwd)
        if not is_safe:
            self._err(f"cd: {target}: Invalid path (traversal blocked)")
            return

        if os.path.isdir(resolved):
            self._cwd = resolved
            self._update_prompt()
        else:
            self._err(f"cd: {target}: No such directory")

    def _cmd_ls(self, args):
        path = self._cwd
        long = "-l" in args or "-la" in args or "-al" in args
        all_files = "-a" in args or "-la" in args or "-al" in args

        for arg in args:
            if not arg.startswith("-") and os.path.exists(os.path.join(self._cwd, arg)):
                path = os.path.join(self._cwd, arg)
                break

        try:
            entries = sorted(os.scandir(path), key=lambda e: e.name)
            if not all_files:
                entries = [e for e in entries if not e.name.startswith(".")]

            if long:
                for e in entries:
                    stat = e.stat()
                    mode = "d" if e.is_dir() else "-"
                    size = stat.st_size
                    name = e.name
                    if e.is_dir():
                        name += "/"
                    self._out(f"{mode}  {size:>10}  {name}")
            else:
                cols = []
                for e in entries:
                    name = e.name + "/" if e.is_dir() else e.name
                    col = theme.ACCENT_CYAN if e.is_dir() else theme.TEXT_PRIMARY
                    cols.append(f'<span style="color: {col};">{_e(name)}</span>')
                self._out("  ".join(cols))
        except PermissionError:
            self._err(f"ls: cannot access '{path}': Permission denied")
        except Exception as e:
            self._err(f"ls: {str(e)}")

    def _cmd_cat(self, args):
        if not args:
            self._err("cat: missing file operand")
            return

        for f in args:
            path = os.path.join(self._cwd, f)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    self._out(fp.read())
            except FileNotFoundError:
                self._err(f"cat: {f}: No such file")
            except IsADirectoryError:
                self._err(f"cat: {f}: Is a directory")
            except PermissionError:
                self._err(f"cat: {f}: Permission denied")
            except Exception as e:
                self._err(f"cat: {f}: {str(e)}")

    def _cmd_which(self, args):
        if not args:
            return
        for arg in args:
            path = shutil.which(arg)
            if path:
                self._out(path)
            else:
                self._err(f"{arg}: not found")

    def _cmd_tree(self, args):
        def walk(dir_path, prefix=""):
            try:
                entries = sorted(os.scandir(dir_path), key=lambda e: e.name)
            except PermissionError:
                return
            for i, e in enumerate(entries):
                is_last = i == len(entries) - 1
                self._out(f"{prefix}{'└── ' if is_last else '├── '}{e.name}")
                if e.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    walk(e.path, next_prefix)

        walk(self._cwd)

    def _cmd_mkdir(self, args):
        if not args:
            self._err("mkdir: missing operand")
            return
        for d in args:
            path = os.path.join(self._cwd, d)
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                self._err(f"mkdir: cannot create directory '{d}': {str(e)}")

    def _cmd_touch(self, args):
        if not args:
            self._err("touch: missing file operand")
            return
        for f in args:
            path = os.path.join(self._cwd, f)
            try:
                pathlib.Path(path).touch()
            except Exception as e:
                self._err(f"touch: {str(e)}")

    def _cmd_rm(self, args):
        if not args:
            self._err("rm: missing operand")
            return
        force = "-f" in args
        recursive = "-r" in args or "-R" in args

        files = [a for a in args if not a.startswith("-")]
        for f in files:
            path = os.path.join(self._cwd, f)
            try:
                if os.path.isdir(path):
                    if recursive:
                        shutil.rmtree(path)
                    else:
                        self._err(f"rm: {f}: is a directory")
                else:
                    os.remove(path)
            except FileNotFoundError:
                if not force:
                    self._err(f"rm: {f}: No such file")
            except PermissionError:
                self._err(f"rm: {f}: Permission denied")
            except Exception as e:
                self._err(f"rm: {str(e)}")

    def _cmd_cp(self, args):
        if len(args) < 2:
            self._err("cp: missing file operand")
            return
        src = os.path.join(self._cwd, args[0])
        dst = os.path.join(self._cwd, args[1])
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            self._err(f"cp: {str(e)}")

    def _cmd_mv(self, args):
        if len(args) < 2:
            self._err("mv: missing file operand")
            return
        src = os.path.join(self._cwd, args[0])
        dst = os.path.join(self._cwd, args[1])
        try:
            shutil.move(src, dst)
        except Exception as e:
            self._err(f"mv: {str(e)}")

    def _cmd_df(self, args):
        if IS_WINDOWS:
            try:
                result = subprocess.run(
                    ["wmic", "logicaldisk", "get", "Size,FreeSpace,DeviceID"],
                    capture_output=True,
                    text=True,
                )
                self._out("Filesystem     Size    Used    Free    Use%")
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            drive = parts[0]
                            free = int(parts[1]) // (1024 * 1024) if parts[1] else 0
                            size = (
                                int(parts[2]) // (1024 * 1024)
                                if len(parts) > 2 and parts[2]
                                else 0
                            )
                            used = size - free
                            pct = int(used * 100 / size) if size else 0
                            self._out(
                                f"{drive}          {size}MB  {used}MB  {free}MB  {pct}%"
                            )
            except Exception as e:
                self._err(str(e))
        else:
            result = subprocess.run(["df", "-h"], capture_output=True, text=True)
            self._out(result.stdout)

    def _cmd_free(self, args):
        if IS_WINDOWS:
            try:
                result = subprocess.run(
                    ["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize"],
                    capture_output=True,
                    text=True,
                )
                for line in result.stdout.strip().split("\n")[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            free = int(parts[0]) // 1024
                            total = int(parts[1]) // 1024
                            used = total - free
                            self._out(
                                f"              total    used    free    shared  buff/cache   available"
                            )
                            self._out(f"Mem:        {total:>7}  {used:>7}  {free:>7}")
            except Exception as e:
                self._err(str(e))
        else:
            result = subprocess.run(["free", "-h"], capture_output=True, text=True)
            self._out(result.stdout)

    def _cmd_ps(self, args):
        if IS_WINDOWS:
            self._cmd_tasklist([])
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            self._out(result.stdout)

    def _cmd_tasklist(self, args):
        try:
            result = subprocess.run(["tasklist"], capture_output=True, text=True)
            self._out(result.stdout)
        except Exception as e:
            self._err(str(e))

    def _cmd_systeminfo(self, args):
        try:
            if IS_WINDOWS:
                result = subprocess.run(["systeminfo"], capture_output=True, text=True)
                self._out(result.stdout)
            else:
                result = subprocess.run(["uname", "-a"], capture_output=True, text=True)
                self._out(result.stdout)
        except Exception as e:
            self._err(str(e))

    def _cmd_uname(self, args):
        if "-a" in args:
            self._out(f"{HOST_OS} {platform.release()} {platform.machine()}")
        elif "-r" in args:
            self._out(platform.release())
        elif "-m" in args:
            self._out(platform.machine())
        else:
            self._out(HOST_OS)

    def _cmd_su(self, args):
        """Switch user."""
        if not args:
            target = "root"
        else:
            target = args[0]

        user = SESSION.get_user(target)
        if not user:
            self._err(f"su: user '{target}' not found")
            return

        # Simple password check (in real system would use PAM)
        if len(args) > 1:
            if not SESSION.verify_password(target, args[1]):
                self._err(f"su: authentication failure")
                return
        else:
            # No password provided — only allow if already root
            if not self._is_root:
                self._err("su: password required (use: su <user> <password>)")
                self._last_exit = 1
                return

        self._effective_user = user
        self._is_root = user.is_root
        # Drop sudo cache when switching users
        if not user.is_root:
            SESSION.sudo_drop()
        self._update_prompt()
        self._out(f"Switched to user: {user.username}")

    def _cmd_sudo(self, args):
        """Execute command as root — requires password (cached 5 min)."""
        if not args:
            self._err("sudo: no command specified")
            return

        cmd_str = " ".join(args)

        # Already elevated?
        if not SESSION.sudo_granted:
            from components.sudo_dialog import ask_sudo
            granted = ask_sudo(command=cmd_str, parent=self)
            if not granted:
                self._err("sudo: authentication failure")
                self._last_exit = 1
                return

        rem = SESSION.sudo_remaining()
        self._out(f"[sudo] Access granted ({rem}s remaining)")
        old_root = self._is_root
        self._is_root = True
        self._execute(args)
        self._is_root = old_root
        self._update_prompt()

    def _cmd_useradd(self, args):
        """Create new user."""
        if not self._is_root:
            self._err("useradd: permission denied (need root)")
            return

        name = args[0] if args else None
        if not name:
            self._err("useradd: missing username")
            return

        user = SESSION.create_user(name)
        if user:
            self._out(f"User '{name}' created with uid={user.uid}")
        else:
            self._err(f"useradd: user '{name}' already exists")

    def _cmd_passwd(self, args):
        """Change user password."""
        if not args:
            target = self._current_user.username if self._current_user else "user"
        else:
            target = args[0]

        # Check permission
        if not self._is_root and target != (
            self._current_user.username if self._current_user else "user"
        ):
            self._err("passwd: permission denied")
            return

        # Simple implementation - just accept any new password for demo
        new_pass = args[1] if len(args) > 1 else "password"
        if SESSION.change_password(target, new_pass):
            self._out(f"Password changed for user '{target}'")
        else:
            self._err(f"passwd: user '{target}' not found")

    def _cmd_users(self):
        """List all users."""
        users = SESSION.all_users()
        for u in users:
            self._out(u.username)

    def _cmd_id(self):
        """Display user identity."""
        if self._effective_user:
            u = self._effective_user
            groups = SESSION.groups_for(u.username)
            group_ids = [str(g) for g in groups]
            self._out(
                f"uid={u.uid}({u.username}) gid={u.gid}({u.username}) groups={','.join(group_ids)}"
            )
        else:
            self._out("uid=1000(user) gid=1000(user) groups=user")

    def _cmd_groups(self, args):
        """Display user groups."""
        target = (
            args[0]
            if args
            else (self._current_user.username if self._current_user else "user")
        )
        groups = SESSION.groups_for(target)
        if groups:
            self._out(" ".join(groups))
        else:
            self._out(target)

    def _cmd_apt(self, args):
        """APT package manager."""
        if not args:
            self._err("apt: no operation specified")
            return

        op = args[0]

        if op == "install":
            if not self._is_root:
                self._err("apt: permission denied (need root)")
                return
            for pkg in args[1:]:
                if PKG_MGR.install(pkg):
                    self._out(f"Installing {pkg}...")
                    self._out(f"{pkg} installed successfully")
                else:
                    self._err(f"apt: package {pkg} not found")

        elif op == "remove":
            if not self._is_root:
                self._err("apt: permission denied (need root)")
                return
            for pkg in args[1:]:
                if PKG_MGR.remove(pkg):
                    self._out(f"Removing {pkg}...")
                    self._out(f"{pkg} removed")
                else:
                    self._err(f"apt: package {pkg} not installed")

        elif op == "list":
            self._out("Available packages:")
            for p in PKG_MGR.list_all():
                status = "[installed]" if p["status"] == "installed" else ""
                self._out(f"  {p['name']} {p['version']} {status}")

        elif op == "search":
            query = args[1] if len(args) > 1 else ""
            results = PKG_MGR.search(query)
            self._out(f"Searching for '{query}'...")
            for p in results:
                self._out(f"  {p['name']} - {p['description']}")

        elif op == "show":
            pkg = args[1] if len(args) > 1 else None
            if pkg:
                p = PKG_MGR.get_package(pkg)
                if p:
                    self._out(f"Package: {p.name}")
                    self._out(f"Version: {p.version}")
                    self._out(f"Description: {p.description}")
                    self._out(f"Commands: {', '.join(p.commands)}")
                else:
                    self._err(f"apt: package {pkg} not found")

        else:
            self._err(f"apt: unknown operation '{op}'")

    def _cmd_chmod(self, args):
        """Change file permissions."""
        if not args:
            self._err("chmod: missing operand")
            return

        mode = args[0]
        files = args[1:] if len(args) > 1 else ["."]

        for f in files:
            path = os.path.join(self._cwd, f)
            try:
                PERM_MGR.set_mode(path, mode)
                self._out(f"Changed mode of {f} to {mode}")
            except Exception as e:
                self._err(f"chmod: {str(e)}")

    def _cmd_chown(self, args):
        """Change file ownership."""
        if not self._is_root:
            self._err("chown: permission denied (need root)")
            return

        if not args or len(args) < 2:
            self._err("chmod: missing operand")
            return

        owner = args[0]
        files = args[1:]

        user = SESSION.get_user(owner)
        if not user:
            self._err(f"chown: user '{owner}' not found")
            return

        for f in files:
            path = os.path.join(self._cwd, f)
            try:
                PERM_MGR.set_owner(path, user.uid, user.gid)
                self._out(f"Changed owner of {f} to {owner}")
            except Exception as e:
                self._err(f"chown: {str(e)}")

    def eventFilter(self, obj, event):
        if obj is self._input and isinstance(event, QKeyEvent):
            if event.type() == QKeyEvent.KeyPress:
                if event.key() == Qt.Key_Up:
                    self._nav_history(-1)
                    return True
                if event.key() == Qt.Key_Down:
                    self._nav_history(1)
                    return True
                if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
                    self._out("^C")
                    return True
                if event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
                    self._output.clear()
                    return True
        return super().eventFilter(obj, event)

    def _nav_history(self, direction: int):
        if not self._history:
            return
        if direction == -1:
            self._hist_idx = max(0, self._hist_idx - 1)
        else:
            self._hist_idx = min(len(self._history), self._hist_idx + 1)
        if self._hist_idx < len(self._history):
            self._input.setText(self._history[self._hist_idx])
        else:
            self._input.clear()


# ── Class alias expected by app_registry ────────────────────
Terminal = RealTerminal
