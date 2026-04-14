# =============================================================
#  filesystem.py — Q-Vault OS  |  Virtual Filesystem v2
#
#  What's new vs v1:
#    • File metadata: size, created_at, modified_at, owner
#    • Permission model: owner / readable_by_user booleans
#    • /root is restricted to root only
#    • mkdir -p  (create parent dirs recursively)
#    • rm -r     (recursive directory removal)
#    • Observer pattern: any widget can subscribe to changes
#      so Terminal and File Explorer stay in sync automatically
# =============================================================

import time
from typing import Callable


# ── Node structure ────────────────────────────────────────────
# Every entry in the tree is either:
#   dict  → directory  { "_meta": Meta, child_name: node, … }
#   Meta  → regular file
#
# Using a dedicated Meta class keeps file data clean.

class Meta:
    """Holds file content + metadata (size, times, owner, perms)."""
    def __init__(self, content: str = "", owner: str = "user",
                 readable_by_user: bool = True):
        self.content          = content
        self.owner            = owner
        self.readable_by_user = readable_by_user   # False = root-only
        self.created_at       = time.time()
        self.modified_at      = time.time()

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))

    def write(self, content: str):
        self.content     = content
        self.modified_at = time.time()

    def fmt_time(self, ts: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

    def __repr__(self):
        return f"<File owner={self.owner} size={self.size}>"


# Helper to create a directory node (always a plain dict)
def _dir(owner: str = "user") -> dict:
    return {"_meta": Meta("", owner=owner)}


class VirtualFS:
    """
    In-memory Unix-like filesystem.
    All state lives here; both Terminal and FileExplorer read/write
    through this singleton so they are always in sync.

    Observer pattern
    ────────────────
    Call  fs.subscribe(callback)  to register a zero-argument function.
    Every mutation (mkdir, touch, rm …) calls _notify() which fires
    all registered callbacks.  FileExplorer subscribes in __init__ so
    its view refreshes automatically.
    """

    SUDO_PASSWORD = "root"   # password required for `sudo` in the terminal

    def __init__(self):
        # ── Tree ──────────────────────────────────────────────
        self._tree: dict = {
            "_meta": Meta("", owner="root"),
            "home": {
                "_meta": Meta("", owner="root"),
                "user": {
                    "_meta": Meta("", owner="user"),
                    "Desktop": {
                        "_meta": Meta("", owner="user"),
                    },
                    "Documents": {
                        "_meta": Meta("", owner="user"),
                        "readme.txt": Meta(
                            "Welcome to Q-Vault OS.\n"
                            "This is a simulated Linux environment.\n"
                            "Version 2.0  —  Phase 2 complete.",
                            owner="user"
                        ),
                        "notes.md": Meta(
                            "# Q-Vault Notes\n\n"
                            "- Terminal is now fully stateful\n"
                            "- FileExplorer syncs automatically\n"
                            "- Permissions enforced\n",
                            owner="user"
                        ),
                    },
                    "Downloads": {
                        "_meta": Meta("", owner="user"),
                        "archive.zip": Meta("[binary data — 2.4 MB]", owner="user"),
                    },
                    ".bashrc": Meta(
                        "# Q-Vault shell config\n"
                        "export PS1='user@q-vault:~$ '\n"
                        "alias ll='ls -l'\n"
                        "alias la='ls -a'\n",
                        owner="user"
                    ),
                    ".ssh": {
                        "_meta": Meta("", owner="user"),
                        "id_rsa": Meta(
                            "-----BEGIN RSA PRIVATE KEY-----\n[SIMULATED]\n"
                            "-----END RSA PRIVATE KEY-----",
                            owner="user", readable_by_user=True
                        ),
                    },
                },
            },
            "root": {
                "_meta": Meta("", owner="root", readable_by_user=False),
                ".secret":    Meta("Q-VAULT ROOT ACCESS GRANTED\nClearance: LEVEL 5", owner="root", readable_by_user=False),
                ".bash_history": Meta("sudo su\nls /\ncat /etc/passwd", owner="root", readable_by_user=False),
            },
            "etc": {
                "_meta": Meta("", owner="root"),
                "passwd":     Meta("root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000::/home/user:/bin/bash", owner="root"),
                "shadow":     Meta("root:$6$SIMULATED:19000:0:99999:7:::", owner="root", readable_by_user=False),
                "hosts":      Meta("127.0.0.1   localhost\n127.0.1.1   q-vault", owner="root"),
                "hostname":   Meta("q-vault", owner="root"),
                "os-release": Meta(
                    'NAME="Q-Vault OS"\nVERSION="2.0"\n'
                    'ID=qvault\nPRETTY_NAME="Q-Vault OS 2.0"',
                    owner="root"
                ),
                "sudoers":    Meta("root    ALL=(ALL:ALL) ALL\nuser    ALL=(ALL) ALL", owner="root", readable_by_user=False),
            },
            "tmp": {
                "_meta": Meta("", owner="root"),
            },
            "var": {
                "_meta": Meta("", owner="root"),
                "log": {
                    "_meta": Meta("", owner="root"),
                    "syslog":   Meta("[boot]  Q-Vault OS 2.0 initialized\n[info]  All systems nominal\n[info]  Terminal v2 loaded", owner="root"),
                    "auth.log": Meta("[auth]  user logged in\n[auth]  sudo session opened", owner="root"),
                },
            },
            "bin":  {"_meta": Meta("", owner="root")},
            "dev":  {"_meta": Meta("", owner="root")},
            "proc": {"_meta": Meta("", owner="root")},
        }

        # Current working directory as path segments (no leading slash)
        self._cwd: list[str] = ["home", "user"]

        # Registered observer callbacks
        self._observers: list[Callable] = []

    # ── Observer / sync API ───────────────────────────────────

    def subscribe(self, callback: Callable):
        """Register a zero-argument function called on every mutation."""
        if callback not in self._observers:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable):
        self._observers = [o for o in self._observers if o is not callback]

    def _notify(self):
        """Fire all registered observer callbacks."""
        for cb in self._observers:
            try:
                cb()
            except Exception:
                pass   # never let an observer crash the filesystem

    # ── Path helpers ──────────────────────────────────────────

    def pwd(self) -> str:
        return ("/" + "/".join(self._cwd)) if self._cwd else "/"

    def cwd_display(self) -> str:
        """Tilde-abbreviated path for the shell prompt."""
        full = self.pwd()
        home = "/home/user"
        if full == home:
            return "~"
        if full.startswith(home + "/"):
            return "~" + full[len(home):]
        return full

    def _resolve(self, path: str) -> list[str] | None:
        """
        Turn an absolute or relative path string into a list of
        clean path segments. Returns None on bad input.
        """
        if path.startswith("/"):
            parts = [p for p in path.split("/") if p]
        else:
            parts = self._cwd[:]
            for seg in path.split("/"):
                if not seg or seg == ".":
                    continue
                if seg == "..":
                    if parts:
                        parts.pop()
                else:
                    parts.append(seg)
        return parts

    def _node_at(self, parts: list[str]):
        """Walk the tree and return the node, or None if not found."""
        node = self._tree
        for seg in parts:
            if not isinstance(node, dict) or seg not in node:
                return None
            node = node[seg]
        return node

    def _cwd_node(self) -> dict:
        return self._node_at(self._cwd)

    def _check_readable(self, node, is_root: bool, path: str = ""):
        """Raise PermissionError if user can't read this node."""
        meta = node.get("_meta") if isinstance(node, dict) else node
        if isinstance(meta, Meta) and not meta.readable_by_user and not is_root:
            raise PermissionError(
                f"Permission denied: {path or 'this path'}"
            )

    # ── Public commands ───────────────────────────────────────

    def pwd_str(self) -> str:
        return self.pwd()

    def ls(self, path: str = ".", flags: set = None,
           is_root: bool = False) -> list[dict]:
        """
        Return a list of entry dicts for display.
        Each dict has: name, is_dir, size, owner, modified, hidden
        flags: 'l' = long format, 'a' = show hidden
        """
        flags = flags or set()
        parts = self._resolve(path)
        node  = self._node_at(parts) if parts is not None else None

        if parts is None or node is None:
            raise FileNotFoundError(
                f"ls: cannot access '{path}': No such file or directory"
            )
        if not isinstance(node, dict):
            raise NotADirectoryError(f"ls: {path}: Not a directory")

        self._check_readable(node, is_root, path)

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

            # Skip root-owned files when not root (permission check)
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

        return sorted(entries, key=lambda e: (not e["is_dir"], e["name"].lower()))

    def cd(self, path: str, is_root: bool = False) -> None:
        if path in ("", "~"):
            self._cwd = ["home", "user"] if not is_root else ["root"]
            return
        parts = self._resolve(path)
        node  = self._node_at(parts) if parts is not None else None
        if parts is None or node is None:
            raise FileNotFoundError(f"cd: {path}: No such file or directory")
        if not isinstance(node, dict):
            raise NotADirectoryError(f"cd: {path}: Not a directory")
        self._check_readable(node, is_root, path)
        self._cwd = parts

    def mkdir(self, name: str, parents: bool = False,
              is_root: bool = False) -> None:
        """Create directory. If parents=True, create intermediate dirs."""
        parts = self._resolve(name)
        if parts is None:
            raise ValueError(f"mkdir: invalid path: {name}")

        if parents:
            # Walk and create each missing segment
            node = self._tree
            for seg in parts:
                if seg not in node:
                    node[seg] = {"_meta": Meta("", owner="root" if is_root else "user")}
                node = node[seg]
        else:
            parent_node = self._node_at(self._cwd)
            seg = parts[-1] if len(parts) == 1 else None
            if seg is None:
                raise ValueError("mkdir: use -p for nested paths")
            if seg in parent_node:
                raise FileExistsError(
                    f"mkdir: cannot create directory '{name}': File exists"
                )
            parent_node[seg] = {
                "_meta": Meta("", owner="root" if is_root else "user")
            }
        self._notify()

    def rmdir(self, name: str, is_root: bool = False) -> None:
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
        # Empty = only "_meta" key
        real_children = [k for k in target if k != "_meta"]
        if real_children:
            raise OSError(
                f"rmdir: failed to remove '{name}': Directory not empty"
            )
        del node[name]
        self._notify()

    def rm(self, name: str, recursive: bool = False,
           is_root: bool = False) -> None:
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
        # Permission check
        meta = target.get("_meta") if isinstance(target, dict) else target
        if isinstance(meta, Meta) and not meta.readable_by_user and not is_root:
            raise PermissionError(f"rm: cannot remove '{name}': Permission denied")
        del node[name]
        self._notify()

    def touch(self, name: str, is_root: bool = False) -> None:
        node = self._cwd_node()
        if name not in node:
            node[name] = Meta(
                "", owner="root" if is_root else "user"
            )
        else:
            # Update modification time
            existing = node[name]
            if isinstance(existing, Meta):
                existing.modified_at = time.time()
        self._notify()

    def cat(self, name: str, is_root: bool = False) -> str:
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

    def write_file(self, name: str, content: str,
                   is_root: bool = False) -> None:
        node = self._cwd_node()
        if name in node and isinstance(node[name], dict):
            raise IsADirectoryError(f"Cannot write to '{name}': Is a directory")
        if name in node:
            node[name].write(content)
        else:
            node[name] = Meta(
                content, owner="root" if is_root else "user"
            )
        self._notify()

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

    # ── Helpers for FileExplorer ──────────────────────────────

    def exists(self, path: str) -> bool:
        parts = self._resolve(path)
        return parts is not None and self._node_at(parts) is not None

    def is_dir(self, path: str) -> bool:
        parts = self._resolve(path)
        if parts is None:
            return False
        return isinstance(self._node_at(parts), dict)

    def list_for_explorer(self, abs_path: str,
                          is_root: bool = False) -> tuple[list, list]:
        """Return (dir_names, file_names) for the FileExplorer panel."""
        parts = [p for p in abs_path.strip("/").split("/") if p]
        node  = self._node_at(parts)
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

    def get_meta_for_explorer(self, abs_path: str,
                              name: str) -> Meta | None:
        """Return metadata for a single entry in a directory."""
        parts = [p for p in abs_path.strip("/").split("/") if p]
        node  = self._node_at(parts)
        if not isinstance(node, dict) or name not in node:
            return None
        entry = node[name]
        if isinstance(entry, dict):
            return entry.get("_meta")
        return entry if isinstance(entry, Meta) else None

    def lock_all(self):
        """Emergency lockdown: revokes all user access to /home."""
        try:
            home = self._tree["home"]
            for name, node in home.items():
                if name == "_meta": continue
                meta = node if isinstance(node, Meta) else node.get("_meta")
                if meta:
                    meta.readable_by_user = False
            self._notify()
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────
FS = VirtualFS()
