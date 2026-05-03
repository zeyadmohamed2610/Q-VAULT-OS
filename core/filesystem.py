"""
core/filesystem.py — Q-Vault OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Virtual Filesystem (VFS)  |  Upgrade v4

Architecture unchanged (Facade + three sub-components).
External API contract: 100% backward-compatible.

New capabilities in v4
──────────────────────
- Meta: full permission bits (rwxrwxrwx), group, symlink target
- VirtualFS.cp()   – copy file or directory subtree
- VirtualFS.mv()   – move / rename entry within the VFS
- VirtualFS.ln()   – create symbolic link (stored in Meta.symlink)
- VirtualFS.du()   – recursive disk-usage count (bytes)
- VirtualFS.find() – search VFS tree by name pattern and type
- VirtualFS.grep() – search file contents in VFS for a pattern
- VirtualFS.chmod()– update permission bits on a Meta node
- VirtualFS.chown()– update owner on a Meta node (root only)
- VirtualFS.ls()   – now includes symlink entries and perm string
- Richer /home tree: Pictures, Music, Videos, .config, .local
- /usr, /sbin virtual nodes added
- /var/log enriched with more realistic log entries
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import fnmatch
import logging
import time
from copy import deepcopy
from typing import Generator

from core.event_bus import EVENT_BUS, SystemEvent
from core._path_resolver     import PathResolver
from core._permission_checker import PermissionChecker
from core._proc_fs_handler    import ProcFSHandler

logger = logging.getLogger(__name__)


# ── Meta ──────────────────────────────────────────────────────────────────────

class Meta:
    """
    Holds file content and metadata for a VFS node.

    New in v4
    ─────────
    - mode      : int  — Unix permission bits  (default 0o644 for files)
    - group     : str  — owning group          (default "user")
    - symlink   : str | None — symlink target path (None = real file)
    - nlink     : int  — hard link count
    """

    def __init__(
        self,
        content: str = "",
        owner: str = "user",
        readable_by_user: bool = True,
        mode: int = 0o644,
        group: str = "user",
        symlink: str | None = None,
    ) -> None:
        self.content          = content
        self.owner            = owner
        self.readable_by_user = readable_by_user
        self.mode             = mode
        self.group            = group
        self.symlink          = symlink      # None = regular file; str = symlink target
        self.nlink            = 1
        self.created_at       = time.time()
        self.modified_at      = time.time()

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))

    @property
    def is_symlink(self) -> bool:
        return self.symlink is not None

    @property
    def perm_string(self) -> str:
        """Return rwxrwxrwx permission string (e.g. '-rw-r--r--')."""
        kind = "l" if self.is_symlink else "-"
        return kind + self._bits(self.mode)

    @staticmethod
    def _bits(mode: int) -> str:
        chars = ""
        for shift in (6, 3, 0):
            t = (mode >> shift) & 0o7
            chars += ("r" if t & 4 else "-")
            chars += ("w" if t & 2 else "-")
            chars += ("x" if t & 1 else "-")
        return chars

    # ── Mutation ────────────────────────────────────────────────────────────

    def write(self, content: str) -> None:
        self.content     = content
        self.modified_at = time.time()

    def fmt_time(self, ts: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

    def __repr__(self) -> str:
        return f"<File owner={self.owner} size={self.size} mode={oct(self.mode)}>"


# ── Tree helpers ──────────────────────────────────────────────────────────────

def _dir(owner: str = "root", mode: int = 0o755) -> dict:
    """Create a bare directory node."""
    m = Meta("", owner=owner, mode=mode)
    m.nlink = 2
    return {"_meta": m}


def _file(content: str, owner: str = "user",
          readable_by_user: bool = True, mode: int = 0o644) -> Meta:
    """Convenience factory for a file Meta node."""
    return Meta(content, owner=owner, readable_by_user=readable_by_user, mode=mode)


# ── VirtualFS ─────────────────────────────────────────────────────────────────

class VirtualFS:
    """
    In-memory Unix-like filesystem — Facade over three subsystems.

    Public API (unchanged from v3 + new v4 methods)
    ────────────────────────────────────────────────
    Original : ls, cd, mkdir, rmdir, rm, touch, cat, write_file,
               stat, exists, is_dir, list_for_explorer,
               get_meta_for_explorer, lock_all, pwd, cwd_display, pwd_str
    New v4   : cp, mv, ln, du, find, grep, chmod, chown
    """

    SUDO_PASSWORD: str = "root"

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._tree: dict = self._build_tree()
        self._cwd:  list[str] = ["home", "user"]

    @staticmethod
    def _build_tree() -> dict:
        """Build and return the initial filesystem tree."""
        return {
            "_meta": _file("", owner="root", mode=0o755),

            # ── /home ────────────────────────────────────────────────────
            "home": {
                "_meta": _file("", owner="root", mode=0o755),
                "user": {
                    "_meta": _file("", owner="user", mode=0o755),
                    "Desktop":   _dir("user"),
                    "Documents": {
                        "_meta": _file("", owner="user", mode=0o755),
                        "readme.txt": _file(
                            "Welcome to Q-Vault OS.\n"
                            "This is a simulated Linux environment.\n"
                            "Version 4.0  —  Full Linux command parity.",
                        ),
                        "notes.md": _file(
                            "# Q-Vault Notes\n\n"
                            "- Terminal v4: full Linux command set\n"
                            "- mv, cp, grep, find, du, df, ps, top, htop\n"
                            "- man pages, history, alias, env, export\n"
                            "- ping (real), curl/wget/ssh (simulated)\n"
                            "- Right-click → Run as Administrator = sudo\n",
                        ),
                        "todo.txt": _file(
                            "[ ] Review security dashboard\n"
                            "[ ] Run stress test\n"
                            "[x] Install Q-Vault OS\n",
                        ),
                    },
                    "Downloads": {
                        "_meta": _file("", owner="user", mode=0o755),
                        "archive.zip":    _file("[binary — 2.4 MB]"),
                        "installer.sh":   _file(
                            "#!/bin/bash\necho 'Q-Vault Installer v4'\n",
                            mode=0o755,
                        ),
                    },
                    "Pictures": _dir("user"),
                    "Music":    _dir("user"),
                    "Videos":   _dir("user"),
                    ".config": {
                        "_meta": _file("", owner="user", mode=0o700),
                        "qvault.conf": _file(
                            "[general]\ntheme=dark\nlanguage=en\n"
                            "[terminal]\nfont_size=13\nhistory_size=500\n",
                        ),
                    },
                    ".local": {
                        "_meta": _file("", owner="user", mode=0o755),
                        "share": _dir("user"),
                    },
                    ".bashrc": _file(
                        "# Q-Vault shell config\n"
                        "export PS1='user@q-vault:~$ '\n"
                        "alias ll='ls -la'\n"
                        "alias la='ls -a'\n"
                        "alias l='ls -CF'\n"
                        "alias grep='grep --color=auto'\n",
                    ),
                    ".bash_history": _file(
                        "ls -la\ncd Documents\ncat readme.txt\n"
                        "sudo apt update\nps aux\ndf -h\n",
                    ),
                    ".ssh": {
                        "_meta": _file("", owner="user", mode=0o700),
                        "id_rsa": _file(
                            "-----BEGIN RSA PRIVATE KEY-----\n[SIMULATED]\n"
                            "-----END RSA PRIVATE KEY-----",
                            mode=0o600,
                        ),
                        "id_rsa.pub": _file(
                            "ssh-rsa AAAAB3NzaC1yc2E[SIMULATED] user@q-vault",
                            mode=0o644,
                        ),
                        "known_hosts": _file("# SSH known hosts\n"),
                        "authorized_keys": _file("# Authorized keys\n"),
                    },
                },
            },

            # ── /root ────────────────────────────────────────────────────
            "root": {
                "_meta": _file("", owner="root", readable_by_user=False, mode=0o550),
                ".secret": _file(
                    "Q-VAULT ROOT ACCESS GRANTED\nClearance: LEVEL 5",
                    owner="root", readable_by_user=False,
                ),
                ".bash_history": _file(
                    "sudo su\nls /\ncat /etc/passwd\nchmod 600 /etc/shadow",
                    owner="root", readable_by_user=False,
                ),
                ".bashrc": _file(
                    "# Root shell config\nexport PS1='root@q-vault:~# '\n",
                    owner="root", readable_by_user=False,
                ),
            },

            # ── /etc ─────────────────────────────────────────────────────
            "etc": {
                "_meta": _file("", owner="root", mode=0o755),
                "passwd": _file(
                    "root:x:0:0:root:/root:/bin/bash\n"
                    "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                    "user:x:1000:1000:Q-Vault User:/home/user:/bin/bash\n",
                    owner="root",
                ),
                "shadow": _file(
                    "root:$6$SIMULATED$HASH:19000:0:99999:7:::\n"
                    "user:$6$SIMULATED$HASH:19000:0:99999:7:::\n",
                    owner="root", readable_by_user=False, mode=0o640,
                ),
                "group": _file(
                    "root:x:0:\ndaemon:x:1:\nsudo:x:27:user\n"
                    "user:x:1000:\n",
                    owner="root",
                ),
                "hosts": _file(
                    "127.0.0.1   localhost\n"
                    "127.0.1.1   q-vault\n"
                    "::1         localhost ip6-localhost\n",
                    owner="root",
                ),
                "hostname": _file("q-vault\n", owner="root"),
                "fstab": _file(
                    "# /etc/fstab\n"
                    "UUID=xxxx-xxxx  /         ext4  errors=remount-ro  0 1\n"
                    "UUID=yyyy-yyyy  /boot/efi  vfat  umask=0077         0 1\n",
                    owner="root",
                ),
                "os-release": _file(
                    'NAME="Q-Vault OS"\nVERSION="4.0"\n'
                    'ID=qvault\nID_LIKE=ubuntu\n'
                    'PRETTY_NAME="Q-Vault OS 4.0"\n'
                    'HOME_URL="https://qvault.os"\n',
                    owner="root",
                ),
                "sudoers": _file(
                    "# /etc/sudoers\nroot    ALL=(ALL:ALL) ALL\n"
                    "user    ALL=(ALL) NOPASSWD: ALL\n"
                    "%sudo   ALL=(ALL:ALL) ALL\n",
                    owner="root", readable_by_user=False, mode=0o440,
                ),
                "crontab": _file(
                    "# /etc/crontab\n"
                    "0 * * * *  root  /usr/sbin/qvault-health-check\n",
                    owner="root",
                ),
                "network": {
                    "_meta": _file("", owner="root", mode=0o755),
                    "interfaces": _file(
                        "auto lo\niface lo inet loopback\nauto eth0\n"
                        "iface eth0 inet dhcp\n",
                        owner="root",
                    ),
                },
            },

            # ── /tmp ─────────────────────────────────────────────────────
            "tmp": _dir("root", mode=0o1777),   # sticky bit

            # ── /var ─────────────────────────────────────────────────────
            "var": {
                "_meta": _file("", owner="root", mode=0o755),
                "log": {
                    "_meta": _file("", owner="root", mode=0o755),
                    "syslog": _file(
                        "[boot]   Q-Vault OS 4.0 initialised\n"
                        "[kernel] Loaded security modules: qvault-sec v4\n"
                        "[info]   All subsystems nominal\n"
                        "[info]   Terminal v4 loaded — full Linux parity\n"
                        "[info]   VFS mounted at /\n",
                        owner="root",
                    ),
                    "auth.log": _file(
                        "[auth]  user logged in via lock screen\n"
                        "[auth]  sudo session opened by user\n"
                        "[auth]  sudo session closed\n",
                        owner="root",
                    ),
                    "kern.log": _file(
                        "[0.000000] Booting Q-Vault kernel 5.15.0\n"
                        "[0.123456] Memory: 4096MB available\n"
                        "[1.234567] QVAULT security core active\n",
                        owner="root",
                    ),
                    "dpkg.log": _file(
                        "2025-01-01 00:00:01 startup archives unpack\n"
                        "2025-01-01 00:00:02 install qvault-os 4.0\n",
                        owner="root",
                    ),
                },
                "tmp":   _dir("root", mode=0o1777),
                "cache": _dir("root", mode=0o755),
                "run":   _dir("root", mode=0o755),
            },

            # ── /bin  /sbin  /usr ────────────────────────────────────────
            "bin":  _dir("root", mode=0o755),
            "sbin": _dir("root", mode=0o755),
            "usr": {
                "_meta": _file("", owner="root", mode=0o755),
                "bin":  _dir("root", mode=0o755),
                "sbin": _dir("root", mode=0o755),
                "lib":  _dir("root", mode=0o755),
                "share": {
                    "_meta": _file("", owner="root", mode=0o755),
                    "doc": _dir("root"),
                    "man": _dir("root"),
                },
                "local": {
                    "_meta": _file("", owner="root", mode=0o755),
                    "bin": _dir("root"),
                    "lib": _dir("root"),
                },
            },

            # ── /dev ─────────────────────────────────────────────────────
            "dev": {
                "_meta": _file("", owner="root", mode=0o755),
                "null":    _file("", owner="root", mode=0o666),
                "zero":    _file("", owner="root", mode=0o666),
                "random":  _file("[character device]", owner="root", mode=0o666),
                "urandom": _file("[character device]", owner="root", mode=0o666),
                "tty":     _file("[character device]", owner="root", mode=0o666),
                "pts": _dir("root"),
            },

            # ── /proc ────────────────────────────────────────────────────
            "proc": ProcFSHandler.build_proc_tree(pm=None),

            # ── /sys ─────────────────────────────────────────────────────
            "sys": {
                "_meta": _file("", owner="root", mode=0o555),
                "kernel": {
                    "_meta": _file("", owner="root", mode=0o555),
                    "hostname":  _file("q-vault\n", owner="root"),
                    "ostype":    _file("Q-VaultOS\n", owner="root"),
                    "osrelease": _file("5.15.0-qvault\n", owner="root"),
                },
                "class": _dir("root", mode=0o555),
                "bus":   _dir("root", mode=0o555),
            },

            # ── /opt ─────────────────────────────────────────────────────
            "opt": _dir("root", mode=0o755),

            # ── /srv ─────────────────────────────────────────────────────
            "srv": _dir("root", mode=0o755),
        }

    # ── EventBus ──────────────────────────────────────────────────────────────

    def _notify(self) -> None:
        EVENT_BUS.emit(SystemEvent.FS_CHANGED, source="filesystem")

    # ── /proc refresh ─────────────────────────────────────────────────────────

    def _refresh_proc(self, pm=None) -> None:
        self._tree["proc"] = ProcFSHandler.build_proc_tree(pm=pm)

    # ── Backward-compat shims ─────────────────────────────────────────────────

    def _resolve(self, path: str) -> list[str]:
        return PathResolver.resolve(path, self._cwd)

    def _node_at(self, parts: list[str]):
        return PathResolver.node_at(self._tree, parts)

    def _cwd_node(self) -> dict:
        return PathResolver.cwd_node(self._tree, self._cwd)

    def _check_readable(self, node, is_root: bool, path: str = "") -> None:
        PermissionChecker.check_readable(node, is_root, path)

    # ── Path helpers ──────────────────────────────────────────────────────────

    def pwd(self) -> str:
        return PathResolver.pwd(self._cwd)

    def pwd_str(self) -> str:
        return self.pwd()

    def cwd_display(self) -> str:
        return PathResolver.cwd_display(self._cwd)

    # ── Directory listing ─────────────────────────────────────────────────────

    def ls(
        self,
        path: str = ".",
        flags: set = None,
        is_root: bool = False,
    ) -> list[dict]:
        """
        List directory contents.

        Returns list of dicts:
            {name, is_dir, is_symlink, size, owner, group, mode, modified, hidden, perm}
        """
        flags = flags or set()
        parts = PathResolver.resolve(path, self._cwd)
        node  = PathResolver.node_at(self._tree, parts)

        if node is None:
            raise FileNotFoundError(
                f"ls: cannot access '{path}': No such file or directory"
            )
        if not isinstance(node, dict):
            raise NotADirectoryError(f"ls: {path}: Not a directory")

        PermissionChecker.check_root_dir_access(parts, is_root)
        PermissionChecker.check_readable(node, is_root, path)

        if parts and parts[0] == "proc":
            self._refresh_proc()
            node = PathResolver.node_at(self._tree, parts)

        entries = []
        for name, child in node.items():
            if name == "_meta":
                continue
            hidden = name.startswith(".")
            if hidden and "a" not in flags:
                continue

            if isinstance(child, dict):
                meta   = child.get("_meta") or Meta("", owner="root")
                is_dir = True
            else:
                meta   = child
                is_dir = False

            if not meta.readable_by_user and not is_root:
                continue

            entries.append({
                "name":       name,
                "is_dir":     is_dir,
                "is_symlink": meta.is_symlink,
                "size":       meta.size,
                "owner":      meta.owner,
                "group":      meta.group,
                "mode":       meta.mode,
                "perm":       ("d" if is_dir else "") + meta._bits(meta.mode),
                "modified":   meta.fmt_time(meta.modified_at),
                "hidden":     hidden,
            })

        return sorted(
            entries,
            key=lambda e: (not e["is_dir"], e["name"].lower()),
        )

    # ── Navigation ────────────────────────────────────────────────────────────

    def cd(self, path: str, is_root: bool = False) -> None:
        if path in ("", "~"):
            self._cwd = ["home", "user"] if not is_root else ["root"]
            return

        parts = PathResolver.resolve(path, self._cwd)
        node  = PathResolver.node_at(self._tree, parts)

        if node is None:
            raise FileNotFoundError(f"cd: {path}: No such file or directory")
        if not isinstance(node, dict):
            raise NotADirectoryError(f"cd: {path}: Not a directory")

        PermissionChecker.check_root_dir_access(parts, is_root)
        PermissionChecker.check_readable(node, is_root, path)
        self._cwd = parts

    # ── Directory mutation ────────────────────────────────────────────────────

    def mkdir(self, name: str, parents: bool = False, is_root: bool = False) -> None:
        parts = PathResolver.resolve(name, self._cwd)
        if not parts:
            raise ValueError(f"mkdir: invalid path: {name!r}")

        parent_parts = parts[:-1] if len(parts) > 1 else self._cwd
        PermissionChecker.check_writable(parent_parts, is_root, "mkdir")

        if parents:
            node = self._tree
            for seg in parts:
                if seg not in node:
                    node[seg] = {"_meta": Meta("", owner="root" if is_root else "user", mode=0o755)}
                node = node[seg]
        else:
            if "/" in name.strip("/"):
                raise ValueError(f"mkdir: {name!r}: No such file or directory (use -p)")
            seg         = name.strip("/")
            parent_node = self._cwd_node()
            if seg in parent_node:
                raise FileExistsError(f"mkdir: cannot create directory '{name}': File exists")
            parent_node[seg] = {"_meta": Meta("", owner="root" if is_root else "user", mode=0o755)}

        self._notify()

    def rmdir(self, name: str, is_root: bool = False) -> None:
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"rmdir: failed to remove '{name}': No such file or directory")
        target = node[name]
        if not isinstance(target, dict):
            raise NotADirectoryError(f"rmdir: failed to remove '{name}': Not a directory")
        if [k for k in target if k != "_meta"]:
            raise OSError(f"rmdir: failed to remove '{name}': Directory not empty")
        del node[name]
        self._notify()

    def rm(self, name: str, recursive: bool = False, is_root: bool = False) -> None:
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"rm: cannot remove '{name}': No such file or directory")
        target = node[name]
        if isinstance(target, dict) and not recursive:
            raise IsADirectoryError(f"rm: cannot remove '{name}': Is a directory  (use -r)")
        PermissionChecker.check_removable(target, name, is_root)
        del node[name]
        self._notify()

    # ── File mutation ─────────────────────────────────────────────────────────

    def touch(self, name: str, is_root: bool = False) -> None:
        PermissionChecker.check_writable(self._cwd, is_root, "touch")
        node = self._cwd_node()
        if name not in node:
            node[name] = Meta("", owner="root" if is_root else "user")
        else:
            existing = node[name]
            if isinstance(existing, Meta):
                existing.modified_at = time.time()
        self._notify()

    def cat(self, name: str, is_root: bool = False) -> str:
        if self._cwd and self._cwd[0] == "proc":
            self._refresh_proc()
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"cat: {name}: No such file or directory")
        entry = node[name]
        if isinstance(entry, dict):
            raise IsADirectoryError(f"cat: {name}: Is a directory")
        if not isinstance(entry, Meta):
            raise TypeError(f"cat: {name}: Unknown entry type")
        if not entry.readable_by_user and not is_root:
            raise PermissionError(f"cat: {name}: Permission denied")
        return entry.content

    def write_file(self, name: str, content: str, is_root: bool = False) -> None:
        PermissionChecker.check_writable(self._cwd, is_root, "write")
        node = self._cwd_node()
        if name in node and isinstance(node[name], dict):
            raise IsADirectoryError(f"write_file: '{name}': Is a directory")
        if name in node:
            node[name].write(content)
        else:
            node[name] = Meta(content, owner="root" if is_root else "user")
        self._notify()

    # ── New v4: cp / mv / ln ─────────────────────────────────────────────────

    def cp(
        self,
        src: str,
        dst: str,
        recursive: bool = False,
        is_root: bool = False,
    ) -> None:
        """
        Copy a file or directory within the VFS.

        Raises
        ------
        FileNotFoundError  – src does not exist
        IsADirectoryError  – src is a dir and recursive=False
        PermissionError    – write into protected directory
        """
        src_parts  = PathResolver.resolve(src, self._cwd)
        dst_parts  = PathResolver.resolve(dst, self._cwd)
        src_node   = PathResolver.node_at(self._tree, src_parts)

        if src_node is None:
            raise FileNotFoundError(f"cp: cannot stat '{src}': No such file or directory")
        if isinstance(src_node, dict) and not recursive:
            raise IsADirectoryError(f"cp: -r not specified; omitting directory '{src}'")

        # Determine real destination
        dst_node = PathResolver.node_at(self._tree, dst_parts)
        if isinstance(dst_node, dict):
            # dst is an existing directory — place src inside it
            dst_parts = dst_parts + [src_parts[-1]]
        
        dst_parent = dst_parts[:-1]
        PermissionChecker.check_writable(dst_parent if dst_parent else self._cwd, is_root, "cp")

        # Deep copy the subtree
        self._set_node(dst_parts, deepcopy(src_node))
        self._notify()

    def mv(
        self,
        src: str,
        dst: str,
        is_root: bool = False,
    ) -> None:
        """
        Move / rename an entry within the VFS.

        Raises
        ------
        FileNotFoundError – src does not exist
        PermissionError   – write into protected directory
        """
        src_parts = PathResolver.resolve(src, self._cwd)
        dst_parts = PathResolver.resolve(dst, self._cwd)
        src_node  = PathResolver.node_at(self._tree, src_parts)

        if src_node is None:
            raise FileNotFoundError(f"mv: cannot stat '{src}': No such file or directory")

        # If dst is an existing directory, place src inside it
        dst_node = PathResolver.node_at(self._tree, dst_parts)
        if isinstance(dst_node, dict):
            dst_parts = dst_parts + [src_parts[-1]]

        dst_parent = dst_parts[:-1]
        PermissionChecker.check_writable(dst_parent if dst_parent else self._cwd, is_root, "mv")

        self._set_node(dst_parts, src_node)
        self._del_node(src_parts)
        self._notify()

    def ln(
        self,
        target: str,
        link_name: str,
        symbolic: bool = True,
        is_root: bool = False,
    ) -> None:
        """
        Create a (symbolic) link within the VFS.
        Hard links are simulated as copies.
        """
        PermissionChecker.check_writable(self._cwd, is_root, "ln")
        node = self._cwd_node()
        if symbolic:
            node[link_name] = Meta("", owner="root" if is_root else "user", symlink=target)
        else:
            src_parts = PathResolver.resolve(target, self._cwd)
            src_node  = PathResolver.node_at(self._tree, src_parts)
            if src_node is None:
                raise FileNotFoundError(f"ln: {target}: No such file or directory")
            node[link_name] = deepcopy(src_node)
        self._notify()

    # ── New v4: chmod / chown ────────────────────────────────────────────────

    def chmod(
        self,
        name: str,
        mode: int,
        recursive: bool = False,
        is_root: bool = False,
    ) -> None:
        """Change permission bits on a VFS node."""
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"chmod: cannot access '{name}': No such file or directory")
        entry = node[name]

        def _apply(n) -> None:
            meta = n.get("_meta") if isinstance(n, dict) else n
            if isinstance(meta, Meta):
                meta.mode = mode
            if recursive and isinstance(n, dict):
                for k, v in n.items():
                    if k != "_meta":
                        _apply(v)

        _apply(entry)
        self._notify()

    def chown(
        self,
        name: str,
        owner: str,
        group: str | None = None,
        recursive: bool = False,
        is_root: bool = True,
    ) -> None:
        """Change owner (root-only)."""
        if not is_root:
            raise PermissionError("chown: operation not permitted")
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"chown: cannot access '{name}': No such file or directory")
        entry = node[name]

        def _apply(n) -> None:
            meta = n.get("_meta") if isinstance(n, dict) else n
            if isinstance(meta, Meta):
                meta.owner = owner
                if group:
                    meta.group = group
            if recursive and isinstance(n, dict):
                for k, v in n.items():
                    if k != "_meta":
                        _apply(v)

        _apply(entry)
        self._notify()

    # ── New v4: du / find / grep ─────────────────────────────────────────────

    def du(self, path: str = ".", is_root: bool = False) -> int:
        """Return total byte size of a VFS subtree."""
        parts = PathResolver.resolve(path, self._cwd)
        node  = PathResolver.node_at(self._tree, parts)
        if node is None:
            raise FileNotFoundError(f"du: {path}: No such file or directory")
        return self._subtree_size(node)

    @staticmethod
    def _subtree_size(node) -> int:
        if isinstance(node, Meta):
            return node.size
        if isinstance(node, dict):
            return sum(
                VirtualFS._subtree_size(v)
                for k, v in node.items()
                if k != "_meta"
            )
        return 0

    def find(
        self,
        path: str = ".",
        name_pat: str | None = None,
        type_filter: str | None = None,
        is_root: bool = False,
    ) -> list[str]:
        """
        Search VFS tree for entries matching criteria.

        Parameters
        ----------
        path        : starting directory
        name_pat    : shell glob pattern (e.g. "*.txt")
        type_filter : "f" for files, "d" for directories, None for both
        """
        parts   = PathResolver.resolve(path, self._cwd)
        node    = PathResolver.node_at(self._tree, parts)
        results: list[str] = []

        def _walk(n, current_parts: list[str]) -> None:
            if not isinstance(n, dict):
                return
            for name, child in n.items():
                if name == "_meta":
                    continue
                child_parts = current_parts + [name]
                is_dir      = isinstance(child, dict)
                meta        = child.get("_meta") if is_dir else child
                if isinstance(meta, Meta) and not meta.readable_by_user and not is_root:
                    continue

                if name_pat and not fnmatch.fnmatch(name, name_pat):
                    pass
                elif type_filter == "f" and is_dir:
                    pass
                elif type_filter == "d" and not is_dir:
                    pass
                else:
                    results.append("/" + "/".join(child_parts))

                if is_dir:
                    _walk(child, child_parts)

        _walk(node, parts)
        return results

    def grep(
        self,
        pattern: str,
        path: str = ".",
        recursive: bool = False,
        ignore_case: bool = False,
        is_root: bool = False,
    ) -> list[tuple[str, int, str]]:
        """
        Search file contents in VFS.

        Returns
        -------
        list of (filepath, line_number, line_text)
        """
        import re
        flags   = re.IGNORECASE if ignore_case else 0
        regex   = re.compile(re.escape(pattern), flags)
        results = []

        def _search_file(file_path: str, meta: Meta) -> None:
            if not meta.readable_by_user and not is_root:
                return
            for i, line in enumerate(meta.content.splitlines(), 1):
                if regex.search(line):
                    results.append((file_path, i, line))

        parts = PathResolver.resolve(path, self._cwd)
        node  = PathResolver.node_at(self._tree, parts)

        if isinstance(node, Meta):
            _search_file("/" + "/".join(parts), node)
            return results

        def _walk(n, current_parts: list[str]) -> None:
            if not isinstance(n, dict):
                return
            for name, child in n.items():
                if name == "_meta":
                    continue
                child_parts = current_parts + [name]
                fp = "/" + "/".join(child_parts)
                if isinstance(child, Meta):
                    _search_file(fp, child)
                elif recursive and isinstance(child, dict):
                    _walk(child, child_parts)

        _walk(node, parts)
        return results

    # ── Tree mutation helpers ─────────────────────────────────────────────────

    def _set_node(self, parts: list[str], value) -> None:
        """Write `value` at `parts` in the tree, creating intermediate dicts."""
        node = self._tree
        for seg in parts[:-1]:
            if seg not in node or not isinstance(node[seg], dict):
                node[seg] = {"_meta": Meta("", owner="root", mode=0o755)}
            node = node[seg]
        node[parts[-1]] = value

    def _del_node(self, parts: list[str]) -> None:
        """Delete the node at `parts`."""
        node = self._tree
        for seg in parts[:-1]:
            if not isinstance(node, dict) or seg not in node:
                return
            node = node[seg]
        if isinstance(node, dict) and parts[-1] in node:
            del node[parts[-1]]

    # ── File metadata ─────────────────────────────────────────────────────────

    def stat(self, name: str, is_root: bool = False) -> Meta:
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(f"stat: {name}: No such file or directory")
        entry = node[name]
        meta  = entry.get("_meta") if isinstance(entry, dict) else entry
        if not isinstance(meta, Meta):
            raise TypeError(f"stat: {name}: bad node")
        if not meta.readable_by_user and not is_root:
            raise PermissionError(f"stat: {name}: Permission denied")
        return meta

    # ── Existence / type helpers ──────────────────────────────────────────────

    def exists(self, path: str) -> bool:
        parts = PathResolver.resolve(path, self._cwd)
        return PathResolver.node_at(self._tree, parts) is not None

    def is_dir(self, path: str) -> bool:
        parts = PathResolver.resolve(path, self._cwd)
        return isinstance(PathResolver.node_at(self._tree, parts), dict)

    # ── FileExplorer helpers ──────────────────────────────────────────────────

    def list_for_explorer(
        self, abs_path: str, is_root: bool = False
    ) -> tuple[list, list]:
        parts = [p for p in abs_path.strip("/").split("/") if p]
        node  = PathResolver.node_at(self._tree, parts)
        if not isinstance(node, dict):
            return [], []

        dirs, files = [], []
        for k, v in node.items():
            if k == "_meta":
                continue
            meta = v.get("_meta") if isinstance(v, dict) else v
            if isinstance(meta, Meta) and not meta.readable_by_user and not is_root:
                continue
            if isinstance(v, dict):
                dirs.append(k)
            else:
                files.append(k)

        return sorted(dirs), sorted(files)

    def get_meta_for_explorer(self, abs_path: str, name: str) -> "Meta | None":
        parts = [p for p in abs_path.strip("/").split("/") if p]
        node  = PathResolver.node_at(self._tree, parts)
        if not isinstance(node, dict) or name not in node:
            return None
        entry = node[name]
        if isinstance(entry, dict):
            return entry.get("_meta")
        return entry if isinstance(entry, Meta) else None

    # ── Emergency lockdown ────────────────────────────────────────────────────

    def lock_all(self) -> None:
        try:
            PermissionChecker.lock_all_home(self._tree["home"])
            self._notify()
        except Exception as exc:
            logger.debug("lock_all suppressed: %s", exc)


# ── Module-level singleton ─────────────────────────────────────────────────────
FS = VirtualFS()
