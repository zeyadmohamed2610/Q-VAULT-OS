"""
apps.terminal._command_parser
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Terminal Command Parser

Single Responsibility: turn a raw input string into structured parts and
classify the command — nothing else.

No Qt, no file I/O, no state mutation.  Every method is pure: given the
same input it always returns the same output.

Previously these concerns were inline inside TerminalEngine.execute_command
and scattered across the _run_subprocess path.  Extracting them here means:

  - The parsing contract is independently testable (no mocking needed).
  - The subprocess whitelist is a single, auditable constant.
  - execute_command() becomes a thin routing decision, not a parser + router.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import shlex
from typing import NamedTuple


# ── Subprocess Whitelist ──────────────────────────────────────────────────
#
# Only commands in this dict may be forwarded to the real OS via
# ProcessGuard.Popen().  The value lists the permitted sub-arguments;
# ["*"] means any arguments are allowed.
#
# Previously: _SUBPROCESS_WHITELIST  (module-level in terminal_engine.py)
# Now         : CommandParser.SUBPROCESS_WHITELIST (canonical location)
# Re-exported : _SUBPROCESS_WHITELIST  (compat alias in terminal_engine.py)

SUBPROCESS_WHITELIST: dict[str, list[str]] = {
    "ping":     ["*"],
    "git":      ["status", "log", "branch", "diff"],
    "pip":      ["list", "show"],
    "echo":     ["*"],
    "hostname": [],
    "ver":      [],
}


# ── Built-in command registry ─────────────────────────────────────────────
#
# Commands that are handled internally by CommandExecutor or TerminalEngine
# and must NOT be forwarded to the OS subprocess layer.

BUILTIN_COMMANDS: frozenset[str] = frozenset({
    "ls", "cd", "pwd", "rm", "cat", "echo",
    "clear", "help", "status", "sudo", "passwd",
    "lock", "ask", "verify_audit", "whoami",
})


# ── Result type ───────────────────────────────────────────────────────────

class ParsedCommand(NamedTuple):
    """
    Immutable result of CommandParser.parse().

    Attributes
    ----------
    parts : list[str]
        The tokenised argv, e.g. ["ls", "-la", "/home"].
        Empty list if the raw input was blank.
    base : str
        Lower-cased argv[0], e.g. "ls".  Empty string if parts is empty.
    is_builtin : bool
        True when base is handled by the internal command dispatcher.
    is_whitelisted : bool
        True when base may be forwarded to the OS via ProcessGuard.Popen().
    """
    parts:          list[str]
    base:           str
    is_builtin:     bool
    is_whitelisted: bool


# ── Parser ────────────────────────────────────────────────────────────────

class CommandParser:
    """
    Stateless command parser for the Q-Vault terminal shell.

    Usage
    -----
    ::

        parsed = CommandParser.parse("ls -la /home")
        # ParsedCommand(parts=['ls', '-la', '/home'],
        #               base='ls',
        #               is_builtin=True,
        #               is_whitelisted=False)
    """

    SUBPROCESS_WHITELIST: dict[str, list[str]] = SUBPROCESS_WHITELIST
    BUILTIN_COMMANDS: frozenset[str] = BUILTIN_COMMANDS

    @classmethod
    def parse(cls, raw: str) -> ParsedCommand:
        """
        Tokenise `raw` and classify the leading command.

        Mirrors the original logic in TerminalEngine.execute_command:
          - On POSIX: use shlex.split()
          - On Windows: fall back to str.split()  (shlex chokes on
            backslash paths that are common on Windows)

        Parameters
        ----------
        raw : str
            The stripped command line from the terminal widget.

        Returns
        -------
        ParsedCommand
            If `raw` is blank, returns an empty ParsedCommand where
            parts=[], base="", is_builtin=False, is_whitelisted=False.
        """
        raw = raw.strip()
        if not raw:
            return ParsedCommand([], "", False, False)

        parts = shlex.split(raw) if os.name != "nt" else raw.split()
        if not parts:
            return ParsedCommand([], "", False, False)

        base = parts[0].lower()
        return ParsedCommand(
            parts=parts,
            base=base,
            is_builtin=base in cls.BUILTIN_COMMANDS,
            is_whitelisted=base in cls.SUBPROCESS_WHITELIST,
        )

    @classmethod
    def is_system_path_target(cls, name: str) -> bool:
        """
        Return True if `name` refers to a protected system directory.

        Used by CommandExecutor._handle_rm to gate destructive operations
        before touching the filesystem.
        """
        PROTECTED = {".", "..", "/", "system", "core", "apps"}
        return name in PROTECTED
