"""
core._path_resolver
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Virtual Filesystem  |  Path Resolver

Single Responsibility: turn strings into tree coordinates and walk the tree.

Rules
─────
- No state. Every method is a pure function or classmethod.
- No permission checks (those belong in PermissionChecker).
- No tree mutation (that belongs in VirtualFS command methods).
- No Qt, no EventBus, no I/O.

Why extracted
─────────────
Previously, path resolution logic was interleaved with permission checks and
command logic throughout VirtualFS. Extracting it here means:

  - Path resolution is independently testable with zero mocking.
  - VirtualFS._resolve / _node_at / _cwd_node delegate here, so the
    existing call sites (and tests that call fresh_fs._resolve directly)
    continue to work unchanged.
  - ProcFSHandler and PermissionChecker can share PathResolver without
    creating circular imports.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Any


class PathResolver:
    """
    Stateless path resolution utilities for the Q-Vault virtual filesystem.

    All methods are classmethods — instantiation is never needed.
    """

    # The conventional home directory for the unprivileged user.
    HOME_PARTS: tuple[str, ...] = ("home", "user")

    @classmethod
    def resolve(cls, path: str, cwd: list[str]) -> list[str]:
        """
        Turn an absolute or relative path string into a list of clean segments.

        Mirrors the original VirtualFS._resolve() logic exactly:
          - Absolute paths (start with '/') are resolved from root.
          - Relative paths are resolved from cwd.
          - '..' pops the last segment (clamped at []).
          - '.' and empty segments are ignored.
          - '~' is treated as /home/user.
          - Double slashes are collapsed (empty segments ignored).

        Returns
        -------
        list[str]
            Clean segment list, never None.  Empty list means filesystem root.

        Examples
        --------
        >>> PathResolver.resolve("/home/user/docs", [])
        ['home', 'user', 'docs']
        >>> PathResolver.resolve("..", ["home", "user", "docs"])
        ['home', 'user']
        >>> PathResolver.resolve("~", ["tmp"])
        ['home', 'user']
        >>> PathResolver.resolve("../../..", ["home", "user", "docs"])
        []
        """
        if path == "~":
            return list(cls.HOME_PARTS)

        if path.startswith("/"):
            # Absolute: start from root, ignore cwd
            parts: list[str] = []
            segments = path.split("/")
        else:
            # Relative: start from current directory
            parts = list(cwd)
            segments = path.split("/")

        for seg in segments:
            if not seg or seg == ".":
                continue
            if seg == "..":
                if parts:
                    parts.pop()
                # At root already: clamp (no escape)
            else:
                parts.append(seg)

        return parts

    @classmethod
    def node_at(cls, tree: dict, parts: list[str]) -> Any:
        """
        Walk ``tree`` following ``parts`` and return the node found, or None.

        Mirrors the original VirtualFS._node_at() logic exactly.

        Parameters
        ----------
        tree : dict
            The root of the virtual filesystem tree.
        parts : list[str]
            Segment list produced by resolve().

        Returns
        -------
        dict | Meta | None
            dict  — directory node
            Meta  — file node
            None  — path does not exist
        """
        node: Any = tree
        for seg in parts:
            if not isinstance(node, dict) or seg not in node:
                return None
            node = node[seg]
        return node

    @classmethod
    def cwd_node(cls, tree: dict, cwd: list[str]) -> dict | None:
        """
        Return the dict node for the current working directory.

        Mirrors the original VirtualFS._cwd_node() logic exactly.
        Returns None if the cwd points to a non-existent or non-directory node.
        """
        node = cls.node_at(tree, cwd)
        return node if isinstance(node, dict) else None

    @classmethod
    def pwd(cls, cwd: list[str]) -> str:
        """
        Format ``cwd`` as a POSIX absolute path string.

        Mirrors the original VirtualFS.pwd() logic exactly.

        >>> PathResolver.pwd(["home", "user"])
        '/home/user'
        >>> PathResolver.pwd([])
        '/'
        """
        return ("/" + "/".join(cwd)) if cwd else "/"

    @classmethod
    def cwd_display(cls, cwd: list[str]) -> str:
        """
        Return a tilde-abbreviated path for shell prompt display.

        Mirrors the original VirtualFS.cwd_display() logic exactly.

        >>> PathResolver.cwd_display(["home", "user"])
        '~'
        >>> PathResolver.cwd_display(["home", "user", "Documents"])
        '~/Documents'
        >>> PathResolver.cwd_display(["tmp"])
        '/tmp'
        """
        full = cls.pwd(cwd)
        home = "/home/user"
        if full == home:
            return "~"
        if full.startswith(home + "/"):
            return "~" + full[len(home):]
        return full
