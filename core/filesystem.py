import logging
logger = logging.getLogger(__name__)
# =============================================================
#  filesystem.py — Q-Vault OS  |  Virtual Filesystem v3
#
#  Refactored: God Object split into three focused components.
#  Public API is 100% unchanged — all callers continue to work.
#
#  Architecture (post-refactor)
#  ─────────────────────────────
#  Before: one 460-line class with 23 methods mixing path
#          resolution, permission checks, file I/O, /proc, and
#          lock-down logic.
#
#  After:  three single-responsibility components + thin Facade.
#
#    ┌──────────────────────────────────────────────────────┐
#    │  VirtualFS  (this file — Facade / Command layer)     │
#    │                                                      │
#    │  ┌────────────────┐  ┌──────────────────────────┐   │
#    │  │  PathResolver  │  │   PermissionChecker      │   │
#    │  │  (pure/static) │  │  + /etc write-gap fix    │   │
#    │  └────────────────┘  └──────────────────────────┘   │
#    │                                                      │
#    │  ┌──────────────────────────────────────────────┐   │
#    │  │  ProcFSHandler  (dynamic /proc generation)   │   │
#    │  └──────────────────────────────────────────────┘   │
#    └──────────────────────────────────────────────────────┘
#
#  Changes vs v2
#  ──────────────
#  1. Path resolution  → PathResolver
#  2. Permission checks → PermissionChecker
#  3. /proc is now a living subsystem via ProcFSHandler
#  4. BUG FIX: write_file / touch / mkdir now enforce
#     SYSTEM_WRITE_PROTECTED — non-root users can no longer
#     write to /etc, /bin, /var, /proc, /dev.
#  5. /root access blocked at path level (check_root_dir_access)
#     so it cannot be circumvented by _meta manipulation.
#
#  External contract (unchanged — zero breaking changes)
#  ──────────────────────────────────────────────────────
#  • from core.filesystem import FS, VirtualFS, Meta
#  • VirtualFS.SUDO_PASSWORD
#  • fresh_fs._cwd   (direct attribute, list[str])
#  • fresh_fs._tree  (direct attribute, dict)
#  • fresh_fs._resolve(path)    → list[str]
#  • fresh_fs._node_at(parts)   → dict | Meta | None
#  • fresh_fs._cwd_node()       → dict
#  • fresh_fs._check_readable(node, is_root, path)
#  • All 17 public methods: same signatures, same exceptions,
#    same return types.
# =============================================================

import time
from core.event_bus import EVENT_BUS, SystemEvent
from core._path_resolver    import PathResolver
from core._permission_checker import PermissionChecker
from core._proc_fs_handler    import ProcFSHandler


# ── Meta ──────────────────────────────────────────────────────────────────
# Defined here (not in a sub-module) so that `from core.filesystem import Meta`
# continues to work for every external caller and for the sub-modules that
# do a local `from core.filesystem import Meta` to avoid circular imports.

class Meta:
    """Holds file content + metadata (size, timestamps, owner, permissions)."""

    def __init__(
        self,
        content: str = "",
        owner: str = "user",
        readable_by_user: bool = True,
    ):
        self.content          = content
        self.owner            = owner
        self.readable_by_user = readable_by_user   # False = root-only
        self.created_at       = time.time()
        self.modified_at      = time.time()

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))

    def write(self, content: str) -> None:
        self.content     = content
        self.modified_at = time.time()

    def fmt_time(self, ts: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

    def __repr__(self) -> str:
        return f"<File owner={self.owner} size={self.size}>"


# ── Tree helpers ──────────────────────────────────────────────────────────

def _dir(owner: str = "root") -> dict:
    """Create a bare directory node with a Meta entry."""
    return {"_meta": Meta("", owner=owner)}


# ── VirtualFS ─────────────────────────────────────────────────────────────

class VirtualFS:
    """
    In-memory Unix-like filesystem — Facade over three subsystems.

    Responsibilities kept here
    ──────────────────────────
    - __init__: tree construction, _cwd initialisation
    - All 17 public command methods (ls, cd, mkdir, rmdir, rm,
      touch, cat, write_file, stat, exists, is_dir,
      list_for_explorer, get_meta_for_explorer, lock_all,
      pwd, cwd_display, pwd_str)
    - _notify(): EventBus emission
    - _refresh_proc(): on-demand /proc regeneration

    Responsibilities delegated
    ──────────────────────────
    - Segment resolution         → PathResolver
    - Access-control decisions   → PermissionChecker
    - /proc content generation   → ProcFSHandler

    Backward-compat shim methods
    ─────────────────────────────
    The QA test suite calls these directly on fresh_fs:
      _resolve(path)              → PathResolver.resolve()
      _node_at(parts)             → PathResolver.node_at()
      _cwd_node()                 → PathResolver.cwd_node()
      _check_readable(node, …)   → PermissionChecker.check_readable()
    All four remain as instance methods with identical signatures.
    """

    SUDO_PASSWORD: str = "root"

    # ── Construction ──────────────────────────────────────────────────────

    def __init__(self) -> None:
        # ── Filesystem tree ───────────────────────────────────────────────
        self._tree: dict = {
            "_meta": Meta("", owner="root"),

            "home": {
                "_meta": Meta("", owner="root"),
                "user": {
                    "_meta": Meta("", owner="user"),
                    "Desktop":   _dir("user"),
                    "Documents": {
                        "_meta": Meta("", owner="user"),
                        "readme.txt": Meta(
                            "Welcome to Q-Vault OS.\n"
                            "This is a simulated Linux environment.\n"
                            "Version 2.0  —  Phase 2 complete.",
                            owner="user",
                        ),
                        "notes.md": Meta(
                            "# Q-Vault Notes\n\n"
                            "- Terminal is now fully stateful\n"
                            "- FileExplorer syncs automatically\n"
                            "- Permissions enforced\n",
                            owner="user",
                        ),
                    },
                    "Downloads": {
                        "_meta": Meta("", owner="user"),
                        "archive.zip": Meta(
                            "[binary data — 2.4 MB]", owner="user"
                        ),
                    },
                    ".bashrc": Meta(
                        "# Q-Vault shell config\n"
                        "export PS1='user@q-vault:~$ '\n"
                        "alias ll='ls -l'\n"
                        "alias la='ls -a'\n",
                        owner="user",
                    ),
                    ".ssh": {
                        "_meta": Meta("", owner="user"),
                        "id_rsa": Meta(
                            "-----BEGIN RSA PRIVATE KEY-----\n[SIMULATED]\n"
                            "-----END RSA PRIVATE KEY-----",
                            owner="user",
                            readable_by_user=True,
                        ),
                    },
                },
            },

            "root": {
                "_meta": Meta("", owner="root", readable_by_user=False),
                ".secret": Meta(
                    "Q-VAULT ROOT ACCESS GRANTED\nClearance: LEVEL 5",
                    owner="root", readable_by_user=False,
                ),
                ".bash_history": Meta(
                    "sudo su\nls /\ncat /etc/passwd",
                    owner="root", readable_by_user=False,
                ),
            },

            "etc": {
                "_meta": Meta("", owner="root"),
                "passwd": Meta(
                    "root:x:0:0:root:/root:/bin/bash\n"
                    "user:x:1000:1000::/home/user:/bin/bash",
                    owner="root",
                ),
                "shadow": Meta(
                    "root:$6$SIMULATED:19000:0:99999:7:::",
                    owner="root", readable_by_user=False,
                ),
                "hosts": Meta(
                    "127.0.0.1   localhost\n127.0.1.1   q-vault",
                    owner="root",
                ),
                "hostname": Meta("q-vault", owner="root"),
                "os-release": Meta(
                    'NAME="Q-Vault OS"\nVERSION="2.0"\n'
                    'ID=qvault\nPRETTY_NAME="Q-Vault OS 2.0"',
                    owner="root",
                ),
                "sudoers": Meta(
                    "root    ALL=(ALL:ALL) ALL\nuser    ALL=(ALL) ALL",
                    owner="root", readable_by_user=False,
                ),
            },

            "tmp": _dir("root"),

            "var": {
                "_meta": Meta("", owner="root"),
                "log": {
                    "_meta": Meta("", owner="root"),
                    "syslog": Meta(
                        "[boot]  Q-Vault OS 2.0 initialized\n"
                        "[info]  All systems nominal\n"
                        "[info]  Terminal v2 loaded",
                        owner="root",
                    ),
                    "auth.log": Meta(
                        "[auth]  user logged in\n"
                        "[auth]  sudo session opened",
                        owner="root",
                    ),
                },
            },

            "bin":  _dir("root"),
            "dev":  _dir("root"),

            # /proc: populated by ProcFSHandler; refreshed on every access.
            "proc": ProcFSHandler.build_proc_tree(pm=None),
        }

        # Current working directory — list of path segments (no leading /)
        self._cwd: list[str] = ["home", "user"]

    # ── EventBus ──────────────────────────────────────────────────────────

    def _notify(self) -> None:
        """Fire FS_CHANGED on the global EventBus after any mutation."""
        EVENT_BUS.emit(SystemEvent.FS_CHANGED, source="filesystem")

    # ── /proc refresh ─────────────────────────────────────────────────────

    def _refresh_proc(self, pm=None) -> None:
        """
        Regenerate the /proc subtree with live data.

        Called automatically at the top of ls() and cat() whenever the
        target path is under /proc, keeping kernel-virtual-file content
        always current.

        Parameters
        ----------
        pm : ProcessManager | None
            When provided, per-PID subdirectories are built from live data.
        """
        self._tree["proc"] = ProcFSHandler.build_proc_tree(pm=pm)

    # ── Backward-compat shim methods ──────────────────────────────────────
    # These keep the original call signatures that the QA test suite uses
    # directly (e.g. fresh_fs._resolve(".."), fresh_fs._node_at([…])).
    # They delegate to the appropriate component — no logic lives here.

    def _resolve(self, path: str) -> list[str]:
        """Resolve path string → segment list. Delegates to PathResolver."""
        return PathResolver.resolve(path, self._cwd)

    def _node_at(self, parts: list[str]):
        """Walk tree to parts. Delegates to PathResolver. Returns dict|Meta|None."""
        return PathResolver.node_at(self._tree, parts)

    def _cwd_node(self) -> dict:
        """Return the dict node for the current directory."""
        return PathResolver.cwd_node(self._tree, self._cwd)

    def _check_readable(self, node, is_root: bool, path: str = "") -> None:
        """Check read permission. Delegates to PermissionChecker."""
        PermissionChecker.check_readable(node, is_root, path)

    # ── Path helpers (public) ─────────────────────────────────────────────

    def pwd(self) -> str:
        """Return current directory as an absolute path string."""
        return PathResolver.pwd(self._cwd)

    def pwd_str(self) -> str:
        """Alias for pwd() — backward compatibility."""
        return self.pwd()

    def cwd_display(self) -> str:
        """Return tilde-abbreviated path for shell prompt display."""
        return PathResolver.cwd_display(self._cwd)

    # ── Directory listing ─────────────────────────────────────────────────

    def ls(
        self,
        path: str = ".",
        flags: set = None,
        is_root: bool = False,
    ) -> list[dict]:
        """
        List directory contents.

        Returns a list of entry dicts:
            {name, is_dir, size, owner, modified, hidden}
        Sorted: directories before files, alphabetically within each group.

        Parameters
        ----------
        path : str
            Absolute or relative path to list.
        flags : set | None
            "a" → include hidden (dot) files.
            "l" → long format (reserved for future use).
        is_root : bool
            True when the caller has sudo/root privilege.

        Raises
        ------
        FileNotFoundError   – path does not exist
        NotADirectoryError  – path is a file, not a directory
        PermissionError     – access denied
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

        # /root check at the path level (before Meta flag check)
        PermissionChecker.check_root_dir_access(parts, is_root)
        # Meta-level readable_by_user check for the directory itself
        PermissionChecker.check_readable(node, is_root, path)

        # Refresh /proc so virtual kernel files are always current
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

            # Silently skip root-only entries when not root
            if not meta.readable_by_user and not is_root:
                continue

            entries.append({
                "name":     name,
                "is_dir":   is_dir,
                "size":     meta.size,
                "owner":    meta.owner,
                "modified": meta.fmt_time(meta.modified_at),
                "hidden":   hidden,
            })

        return sorted(
            entries,
            key=lambda e: (not e["is_dir"], e["name"].lower()),
        )

    # ── Navigation ────────────────────────────────────────────────────────

    def cd(self, path: str, is_root: bool = False) -> None:
        """
        Change current directory.

        Raises
        ------
        FileNotFoundError   – path does not exist
        NotADirectoryError  – path is a file
        PermissionError     – access denied
        """
        if path in ("", "~"):
            self._cwd = ["home", "user"] if not is_root else ["root"]
            return

        parts = PathResolver.resolve(path, self._cwd)
        node  = PathResolver.node_at(self._tree, parts)

        if node is None:
            raise FileNotFoundError(
                f"cd: {path}: No such file or directory"
            )
        if not isinstance(node, dict):
            raise NotADirectoryError(f"cd: {path}: Not a directory")

        PermissionChecker.check_root_dir_access(parts, is_root)
        PermissionChecker.check_readable(node, is_root, path)
        self._cwd = parts

    # ── Directory mutation ────────────────────────────────────────────────

    def mkdir(
        self,
        name: str,
        parents: bool = False,
        is_root: bool = False,
    ) -> None:
        """
        Create a directory.

        parents=True mirrors mkdir -p: intermediate directories are created
        automatically and an existing final target is silently accepted.

        Raises
        ------
        FileExistsError – directory already exists (parents=False)
        ValueError      – invalid or slash-containing name (parents=False)
        PermissionError – write attempt into a system-protected directory
        """
        parts = PathResolver.resolve(name, self._cwd)
        if not parts:
            raise ValueError(f"mkdir: invalid path: {name!r}")

        # Determine the parent path for the write-permission check.
        # For a relative name ("newdir"), parent == self._cwd.
        # For an absolute path ("/etc/newdir"), parent == ["etc"].
        parent_parts = parts[:-1] if len(parts) > 1 else self._cwd
        PermissionChecker.check_writable(parent_parts, is_root, "mkdir")

        if parents:
            node = self._tree
            for seg in parts:
                if seg not in node:
                    node[seg] = {
                        "_meta": Meta("", owner="root" if is_root else "user")
                    }
                node = node[seg]
        else:
            if "/" in name.strip("/"):
                raise ValueError(
                    f"mkdir: {name!r}: No such file or directory "
                    "(use parents=True for nested paths)"
                )
            seg         = name.strip("/")
            parent_node = self._cwd_node()
            if seg in parent_node:
                raise FileExistsError(
                    f"mkdir: cannot create directory '{name}': File exists"
                )
            parent_node[seg] = {
                "_meta": Meta("", owner="root" if is_root else "user")
            }

        self._notify()

    def rmdir(self, name: str, is_root: bool = False) -> None:
        """
        Remove an empty directory.

        Raises
        ------
        FileNotFoundError  – entry does not exist
        NotADirectoryError – entry is a file
        OSError            – directory is not empty
        """
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(
                f"rmdir: failed to remove '{name}': No such file or directory"
            )
        target = node[name]
        if not isinstance(target, dict):
            raise NotADirectoryError(
                f"rmdir: failed to remove '{name}': Not a directory"
            )
        real_children = [k for k in target if k != "_meta"]
        if real_children:
            raise OSError(
                f"rmdir: failed to remove '{name}': Directory not empty"
            )
        del node[name]
        self._notify()

    def rm(
        self,
        name: str,
        recursive: bool = False,
        is_root: bool = False,
    ) -> None:
        """
        Remove a file or directory.

        Raises
        ------
        FileNotFoundError  – entry does not exist
        IsADirectoryError  – target is a directory and recursive=False
        PermissionError    – target is root-only and is_root=False
        """
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(
                f"rm: cannot remove '{name}': No such file or directory"
            )
        target = node[name]
        if isinstance(target, dict) and not recursive:
            raise IsADirectoryError(
                f"rm: cannot remove '{name}': Is a directory  (use -r)"
            )
        PermissionChecker.check_removable(target, name, is_root)
        del node[name]
        self._notify()

    # ── File mutation ─────────────────────────────────────────────────────

    def touch(self, name: str, is_root: bool = False) -> None:
        """
        Create an empty file or update mtime of an existing file.

        Raises
        ------
        PermissionError – write into a system-protected directory
        """
        # /etc write-gap fix: check destination directory first
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
        """
        Return file content as a string.

        Raises
        ------
        FileNotFoundError  – file does not exist
        IsADirectoryError  – name refers to a directory
        PermissionError    – file is root-only and is_root=False
        """
        # Refresh /proc so kernel virtual files are always current
        if self._cwd and self._cwd[0] == "proc":
            self._refresh_proc()

        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(
                f"cat: {name}: No such file or directory"
            )
        entry = node[name]
        if isinstance(entry, dict):
            raise IsADirectoryError(f"cat: {name}: Is a directory")
        if not isinstance(entry, Meta):
            raise TypeError(f"cat: {name}: Unknown entry type")
        if not entry.readable_by_user and not is_root:
            raise PermissionError(f"cat: {name}: Permission denied")
        return entry.content

    def write_file(
        self,
        name: str,
        content: str,
        is_root: bool = False,
    ) -> None:
        """
        Write content to a file, creating it if it does not exist.

        Raises
        ------
        IsADirectoryError  – name refers to a directory
        PermissionError    – write into a system-protected directory
        """
        # /etc write-gap fix: check destination directory first
        PermissionChecker.check_writable(self._cwd, is_root, "write")

        node = self._cwd_node()
        if name in node and isinstance(node[name], dict):
            raise IsADirectoryError(
                f"write_file: '{name}': Is a directory"
            )
        if name in node:
            node[name].write(content)
        else:
            node[name] = Meta(
                content, owner="root" if is_root else "user"
            )
        self._notify()

    # ── File metadata ─────────────────────────────────────────────────────

    def stat(self, name: str, is_root: bool = False) -> Meta:
        """
        Return the Meta object for a file or directory.

        Raises
        ------
        FileNotFoundError  – entry does not exist
        PermissionError    – root-only entry and is_root=False
        TypeError          – malformed node (internal error)
        """
        node = self._cwd_node()
        if name not in node:
            raise FileNotFoundError(
                f"stat: {name}: No such file or directory"
            )
        entry = node[name]
        meta  = entry.get("_meta") if isinstance(entry, dict) else entry
        if not isinstance(meta, Meta):
            raise TypeError(f"stat: {name}: bad node")
        if not meta.readable_by_user and not is_root:
            raise PermissionError(f"stat: {name}: Permission denied")
        return meta

    # ── Existence / type helpers ──────────────────────────────────────────

    def exists(self, path: str) -> bool:
        parts = PathResolver.resolve(path, self._cwd)
        return PathResolver.node_at(self._tree, parts) is not None

    def is_dir(self, path: str) -> bool:
        parts = PathResolver.resolve(path, self._cwd)
        return isinstance(PathResolver.node_at(self._tree, parts), dict)

    # ── FileExplorer helpers ──────────────────────────────────────────────

    def list_for_explorer(
        self,
        abs_path: str,
        is_root: bool = False,
    ) -> tuple[list, list]:
        """
        Return (dir_names, file_names) sorted alphabetically.
        Root-only entries are omitted when is_root=False.
        """
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

    def get_meta_for_explorer(
        self,
        abs_path: str,
        name: str,
    ) -> "Meta | None":
        """Return the Meta for a single named entry inside abs_path."""
        parts = [p for p in abs_path.strip("/").split("/") if p]
        node  = PathResolver.node_at(self._tree, parts)
        if not isinstance(node, dict) or name not in node:
            return None
        entry = node[name]
        if isinstance(entry, dict):
            return entry.get("_meta")
        return entry if isinstance(entry, Meta) else None

    # ── Emergency lockdown ────────────────────────────────────────────────

    def lock_all(self) -> None:
        """
        Emergency lockdown: revoke all non-root access to /home.
        Delegates recursion to PermissionChecker.lock_all_home().
        """
        try:
            PermissionChecker.lock_all_home(self._tree["home"])
            self._notify()
        except Exception as exc:
            logger.debug("lock_all suppressed: %s", exc)


# ── Module-level singleton ────────────────────────────────────────────────
FS = VirtualFS()
