"""
apps.terminal._command_parser — Q-Vault OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terminal Command Parser  |  Upgrade v4

Changes from v3
───────────────
- BUILTIN_COMMANDS expanded with every new command
- SUBPROCESS_WHITELIST: added curl, wget (simulated; executor intercepts first)
- Alias expansion: resolve aliases before parsing
- Pipeline stub: detect | character and split (future use)
- Improved shlex fallback for Windows compat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import os
import shlex
from typing import NamedTuple


# ── Subprocess Whitelist ──────────────────────────────────────────────────────
# Commands that may be forwarded to the real OS via ProcessGuard.Popen().
# curl/wget are listed here but CommandExecutor intercepts them as builtins
# first, so they never reach the real OS — whitelist entry is a safety net.

SUBPROCESS_WHITELIST: dict[str, list[str]] = {
    "ping":     ["*"],
    "git":      ["status", "log", "branch", "diff"],
    "pip":      ["list", "show"],
    "echo":     ["*"],
    "hostname": [],
    "ver":      [],
    "curl":     ["*"],
    "wget":     ["*"],
}


# ── Built-in command registry ──────────────────────────────────────────────────
# Every command handled internally MUST be listed here to prevent OS forwarding.

BUILTIN_COMMANDS: frozenset[str] = frozenset({
    # File & Directory
    "ls", "cd", "pwd", "mkdir", "touch", "rmdir", "rm", "mv", "cp", "ln", "tree",
    # Viewing & Editing
    "cat", "less", "more", "head", "tail", "nano", "vim", "vi",
    # Permissions
    "chmod", "chown",
    # Search
    "grep", "egrep", "fgrep", "find",
    # Text processing
    "echo", "wc", "sort", "uniq", "diff",
    # System info
    "stat", "ps", "top", "htop", "df", "du", "free",
    "uname", "date", "uptime", "id", "whoami", "which", "type",
    # Network (intercepted before subprocess)
    "ping", "curl", "wget", "ssh",
    # Documentation
    "man", "history",
    # Environment & Session
    "env", "export", "unset", "alias", "exit", "logout",
    # Shell / Security / AI
    "clear", "help", "status", "sudo", "passwd",
    "lock", "ask", "verify_audit",
    "qsu", "bash", "sh",
    # Stress tools
    "stress", "fullstress",
})


# ── Result type ────────────────────────────────────────────────────────────────

class ParsedCommand(NamedTuple):
    """
    Immutable result of CommandParser.parse().

    Attributes
    ----------
    parts          : list[str]  – tokenised argv
    base           : str        – lower-cased argv[0]
    flags          : set[str]   – extracted flags (single chars and long flags)
    args           : list[str]  – positional arguments (no leading -)
    is_builtin     : bool       – handled internally
    is_whitelisted : bool       – may go to real OS via ProcessGuard
    is_local_exec  : bool       – starts with ./ or .\
    redirect_file  : str | None – target file for > or >>
    redirect_append: bool       – True if >>
    raw            : str        – original raw input string (for history)
    """
    parts:           list[str]
    base:            str
    flags:           set[str]
    args:            list[str]
    is_builtin:      bool
    is_whitelisted:  bool
    is_local_exec:   bool
    redirect_file:   str | None = None
    redirect_append: bool = False
    raw:             str = ""


# ── Parser ─────────────────────────────────────────────────────────────────────

class CommandParser:
    """Stateless command parser for the Q-Vault terminal shell."""

    SUBPROCESS_WHITELIST: dict[str, list[str]] = SUBPROCESS_WHITELIST
    BUILTIN_COMMANDS:     frozenset[str]        = BUILTIN_COMMANDS

    # System paths protected from destructive operations
    _PROTECTED: frozenset[str] = frozenset({
        ".", "..", "/", "system", "core", "apps", "kernel",
    })

    @classmethod
    def parse(cls, raw: str, aliases: dict[str, str] | None = None) -> ParsedCommand:
        """
        Tokenise raw input into a ParsedCommand.

        Alias expansion
        ───────────────
        If the leading token matches a defined alias, the alias value is
        prepended and the rest of the line is appended before re-parsing.
        Alias cycles are prevented (max one expansion level).

        Parameters
        ----------
        raw     : str
            Raw shell input line.
        aliases : dict[str, str] | None
            Current alias table.  Pass None to skip alias expansion.
        """
        raw = raw.strip()
        if not raw:
            return ParsedCommand([], "", set(), [], False, False, False, "")

        # ── Alias expansion ────────────────────────────────────────────────
        if aliases:
            first_token = raw.split()[0].lower()
            if first_token in aliases:
                remainder = raw[len(first_token):].strip()
                expanded  = aliases[first_token]
                if remainder:
                    expanded += " " + remainder
                raw = expanded

        # ── Tokenise ──────────────────────────────────────────────────────
        try:
            parts = shlex.split(raw, posix=(os.name != "nt"))
        except ValueError:
            # Unmatched quote — fall back to simple split
            parts = raw.split()

        if not parts:
            return ParsedCommand([], "", set(), [], False, False, False, raw)

        base          = parts[0].lower()
        is_local_exec = base.startswith("./") or base.startswith(".\\")

        # ── Flag & argument extraction ─────────────────────────────────────
        flags: set[str] = set()
        args:  list[str] = []

        skip_next = False
        for idx, token in enumerate(parts[1:], start=1):
            if skip_next:
                skip_next = False
                continue
            if token == "--":
                # Everything after -- is positional
                args.extend(parts[idx + 1:])
                break
            if token.startswith("--") and len(token) > 2:
                flag_name = token[2:]
                # Handle --flag=value
                if "=" in flag_name:
                    k, v = flag_name.split("=", 1)
                    flags.add(k)
                    args.append(v)
                else:
                    flags.add(flag_name)
            elif token.startswith("-") and len(token) > 1 and not token[1:].replace(".", "").isdigit():
                for ch in token[1:]:
                    flags.add(ch)
            else:
                args.append(token)

        # ── Redirection extraction ─────────────────────────────────────────
        redirect_file = None
        redirect_append = False
        
        # Check for > or >> in the parts
        for i in range(len(parts)):
            if parts[i] in (">", ">>"):
                if i + 1 < len(parts):
                    redirect_file = parts[i + 1]
                    redirect_append = (parts[i] == ">>")
                    # Remove the redirect operators and filename from the parts for internal logic
                    # We only modify a copy for dispatching, but keep original for raw
                    parts = parts[:i] + parts[i+2:]
                    # Re-extract args without redirect parts
                    args = [a for a in args if a != redirect_file]
                break

        return ParsedCommand(
            parts          = parts,
            base           = base,
            flags          = flags,
            args           = args,
            is_builtin     = base in cls.BUILTIN_COMMANDS,
            is_whitelisted = base in cls.SUBPROCESS_WHITELIST,
            is_local_exec  = is_local_exec,
            redirect_file  = redirect_file,
            redirect_append = redirect_append,
            raw            = raw,
        )

    @classmethod
    def is_system_path_target(cls, name: str) -> bool:
        """Return True if `name` refers to a protected system path."""
        return name.strip("/") in cls._PROTECTED
