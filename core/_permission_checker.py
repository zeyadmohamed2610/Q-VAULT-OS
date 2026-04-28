"""
core._permission_checker
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Virtual Filesystem  |  Permission Checker

Single Responsibility: every access-control decision for the VirtualFS.

Security gap fixed here
───────────────────────
Previously write_file, touch, and mkdir would write to system directories
(/etc, /bin, /var, /proc, /dev) for any non-root user because the only
check was Meta.readable_by_user on the *file* node, not the *destination
directory*.

Fix: check_writable(cwd_parts, is_root) — called at the top of every
write-path method in VirtualFS — raises PermissionError when a non-root
user attempts to write into a system-owned directory.

Linux convention preserved
──────────────────────────
- /tmp, /home  → world-writable (excluded from SYSTEM_WRITE_PROTECTED)
- /proc        → read-only for everyone (kernel virtual FS)
- /etc, /bin, /var, /dev → root-only writes
- /root        → root-only directory (ls/cd blocked for non-root)
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

# ── Security policy constants ─────────────────────────────────────────────

# Top-level directories that require root privilege to write into.
# /tmp and /home are intentionally excluded (world-writable in real Linux).
SYSTEM_WRITE_PROTECTED: frozenset[str] = frozenset({
    "etc", "bin", "dev", "proc", "var",
})

# Top-level directories that are entirely off-limits to non-root users
# for both reading AND listing.
ROOT_ONLY_DIRS: frozenset[str] = frozenset({"root"})


class PermissionChecker:
    """
    Stateless access-control checker for the Q-Vault virtual filesystem.

    All methods are classmethods — no instantiation needed.
    Every method either returns cleanly (access granted) or raises the
    appropriate Unix-convention exception (access denied).
    """

    # ── Read-path checks ─────────────────────────────────────────────────

    @classmethod
    def check_readable(cls, node, is_root: bool, path: str = "") -> None:
        """
        Raise PermissionError if node is not readable by the current user.
        Mirrors original VirtualFS._check_readable() logic exactly.

        Delegates to node's Meta.readable_by_user flag.  Root always passes.
        """
        if is_root:
            return
        meta = cls._meta_of(node)
        if meta is not None and not meta.readable_by_user:
            raise PermissionError(f"Permission denied: {path or 'this path'}")

    @classmethod
    def check_root_dir_access(cls, parts: list[str], is_root: bool) -> None:
        """
        Raise PermissionError if a non-root user attempts to access /root.

        Called by ls() and cd() before checking Meta.readable_by_user, so
        that the /root directory is blocked at the path level regardless of
        whether _meta.readable_by_user is set correctly on the node.

        Linux convention: /root is the root user's home directory and is
        mode 550 — inaccessible to ordinary users.

        Parameters
        ----------
        parts : list[str]
            Resolved path segments (e.g. ["root"] for /root,
            ["root", ".secret"] for /root/.secret).
        is_root : bool
            True when the calling session has sudo/root privilege.

        Raises
        ------
        PermissionError
            When parts[0] is a root-only directory and is_root is False.
        """
        if is_root:
            return
        if parts and parts[0] in ROOT_ONLY_DIRS:
            raise PermissionError(
                f"Permission denied: /{parts[0]}"
            )

    @classmethod
    def check_entry_readable(cls, meta, is_root: bool, name: str = "") -> None:
        """
        Raise PermissionError if a single entry's Meta is not readable.
        Used inside ls() to silently skip root-only files in listings.
        """
        if is_root:
            return
        if not meta.readable_by_user:
            raise PermissionError(f"Permission denied: {name}")

    # ── Write-path checks (NEW — fixes /etc write security gap) ──────────

    @classmethod
    def check_writable(
        cls,
        cwd_parts: list[str],
        is_root: bool,
        op: str = "write",
    ) -> None:
        """
        Raise PermissionError if a non-root user attempts to write into a
        system-protected directory.

        **This method fixes the /etc write security gap identified in the
        QA audit.**  Previously, write_file / touch / mkdir checked only the
        file's own Meta.readable_by_user flag, never the destination
        directory.  A non-root user could therefore place arbitrary files
        in /etc, /bin, /var, etc.

        /proc is never writable, even for root — it is a kernel virtual FS.
        /tmp and /home remain world-writable (not in SYSTEM_WRITE_PROTECTED).

        Parameters
        ----------
        cwd_parts : list[str]
            Current working directory as a segment list (e.g. ["etc"]).
        is_root : bool
            True when the calling session has sudo/root privilege.
        op : str
            Operation name used in the error message ("touch", "mkdir", …).

        Raises
        ------
        PermissionError
        """
        if not cwd_parts:
            return  # filesystem root — individual node checks handle this

        top = cwd_parts[0]

        # /proc: read-only for everyone, including root.
        if top == "proc":
            raise PermissionError(
                f"{op}: /proc is a read-only virtual filesystem"
            )

        if not is_root and top in SYSTEM_WRITE_PROTECTED:
            raise PermissionError(
                f"{op}: /{top}: "
                "non-root users cannot write to system directories"
            )

    @classmethod
    def check_removable(cls, node, name: str, is_root: bool) -> None:
        """
        Raise PermissionError if a non-root user attempts to remove a
        root-only entry.

        Parameters
        ----------
        node : dict | Meta
            The tree node to be removed.
        name : str
            Entry name — used in the error message.
        is_root : bool
            True when the calling session has sudo/root privilege.

        Raises
        ------
        PermissionError
        """
        if is_root:
            return
        meta = cls._meta_of(node)
        if meta is not None and not meta.readable_by_user:
            raise PermissionError(
                f"rm: cannot remove '{name}': Permission denied"
            )

    # ── Lock-down (Emergency) ─────────────────────────────────────────────

    @classmethod
    def lock_all_home(cls, home_node: dict) -> None:
        """
        Emergency lockdown: recursively mark every node in the /home
        subtree as readable_by_user=False.

        Called by VirtualFS.lock_all() when the Security subsystem detects
        a critical threat.  Root access (is_root=True) is unaffected because
        check_readable() short-circuits for root before inspecting the flag.

        Parameters
        ----------
        home_node : dict
            The ``_tree["home"]`` dict node — mutated in-place.
        """
        from core.filesystem import Meta as MetaCls  # local import: avoids circular dep

        def _revoke(node) -> None:
            if isinstance(node, MetaCls):
                node.readable_by_user = False
                return
            if isinstance(node, dict):
                meta = node.get("_meta")
                if isinstance(meta, MetaCls):
                    meta.readable_by_user = False
                for k, v in node.items():
                    if k != "_meta":
                        _revoke(v)

        _revoke(home_node)

    # ── Internal helper ───────────────────────────────────────────────────

    @staticmethod
    def _meta_of(node):
        """
        Extract the Meta object from a directory dict or a raw Meta node.
        Returns None if no Meta can be found.
        Uses a local import to avoid a circular dependency at module load time.
        """
        from core.filesystem import Meta as MetaCls
        if isinstance(node, MetaCls):
            return node
        if isinstance(node, dict):
            meta = node.get("_meta")
            if isinstance(meta, MetaCls):
                return meta
        return None
