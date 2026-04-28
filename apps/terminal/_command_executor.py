"""
apps.terminal._command_executor
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Terminal Command Executor

Single Responsibility: execute every built-in command and manage the
subprocess thread for whitelisted OS commands.

What lives here
---------------
- All _handle_* filesystem commands: ls, cd, pwd, cat, rm, echo
- All _handle_* system commands:     help, status, ask, whoami, passwd,
                                     clear, verify_audit
- TerminalWorker and _run_subprocess

What does NOT live here
-----------------------
- EngineState transitions (sudo, lock)    → TerminalEngine
- Sudo session cache                      → SudoManager
- Behavioral analysis / threat scoring    → TerminalEngine
- String formatting                       → OutputFormatter

Design notes
------------
CommandExecutor owns ``self.cwd`` (the mutable working directory).
TerminalEngine reads it back via the ``cwd`` property so that the
subprocess layer always uses the current directory.

Output is delivered via three callables injected at construction time:
  emit_output(str)       →  fires TerminalEngine.output_ready
  emit_prompt()          →  fires TerminalEngine.prompt_update
  emit_password_mode(b)  →  fires TerminalEngine.password_mode

Using callables (instead of signals) means CommandExecutor has zero
dependency on the outer QObject and is trivially unit-testable with
a plain lambda.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from ._command_parser import CommandParser, SUBPROCESS_WHITELIST
from ._output_formatter import OutputFormatter


# ── Subprocess worker ─────────────────────────────────────────────────────

class TerminalWorker(QObject):
    """
    Background worker that runs a whitelisted OS subprocess.

    Unchanged from the original TerminalEngine.TerminalWorker — preserved
    here so the class remains in the terminal package and QThread lifecycle
    is not disturbed.
    """

    output_ready = pyqtSignal(str)
    finished     = pyqtSignal()

    def __init__(self, parts: list[str], cwd: str, guard) -> None:
        super().__init__()
        self.parts = parts
        self.cwd   = cwd
        self.guard = guard

    def run(self) -> None:
        try:
            base = self.parts[0].lower()
            if base not in SUBPROCESS_WHITELIST:
                self.output_ready.emit(OutputFormatter.security_blocked(base))
                return
            proc = self.guard.Popen(
                self.parts,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            out, _ = proc.communicate(timeout=10)
            if out:
                self.output_ready.emit(out)
        except Exception as exc:
            self.output_ready.emit(OutputFormatter.subprocess_error(exc))
        finally:
            self.finished.emit()


# ── Executor ──────────────────────────────────────────────────────────────

class CommandExecutor(QObject):
    """
    Executes built-in terminal commands and manages the subprocess thread.

    Parameters
    ----------
    base_dir : Path
        The workspace root (get_qvault_home()).  Used as the ``~`` home and
        as the security boundary for path operations.
    process_guard : ProcessGuard
        Guard instance that wraps subprocess.Popen.
    fs_guard : FileSystemGuard
        Guard instance for filesystem operations (reserved for future use).
    emit_output : Callable[[str], None]
        Callback to emit a string to the terminal display.
    emit_prompt : Callable[[], None]
        Callback to trigger a prompt redraw (called after cd, auth flows, etc.)
    api : object | None
        The secure_api object forwarded from TerminalApp.  Used by the AI
        commands (status, ask).  May be None.
    role_getter : Callable[[], str]
        Returns the current role string ("admin" or "guest").
        CommandExecutor reads the role at dispatch time — it does not cache it,
        because sudo can elevate/revoke the role between commands.
    """

    def __init__(
        self,
        base_dir: Path,
        process_guard,
        fs_guard,
        emit_output: Callable[[str], None],
        emit_prompt: Callable[[], None],
        api,
        role_getter: Callable[[], str],
    ) -> None:
        super().__init__()
        self._base_dir      = base_dir
        self._process_guard = process_guard
        self._fs_guard      = fs_guard
        self._emit_output   = emit_output
        self._emit_prompt   = emit_prompt
        self._api           = api
        self._role_getter   = role_getter

        # Mutable working directory — owned by this class
        self.cwd: Path = base_dir

        # Subprocess thread management
        self._thread: QThread | None = None
        self._worker: TerminalWorker | None = None

    # ── Dispatch ──────────────────────────────────────────────────────────

    # Commands that require admin role to execute destructively
    _ADMIN_COMMANDS: frozenset[str] = frozenset({"rm"})

    def dispatch(self, base: str, parts: list[str]) -> bool:
        """
        Route ``base`` to the correct _handle_* method.

        Returns True if the command was handled (callers can branch on this
        to know whether to fall through to _run_subprocess).
        Returns False for unrecognised commands — TerminalEngine will then
        call run_subprocess().

        Note: "sudo" and "lock" are intentionally absent — they live in
        TerminalEngine because they require EngineState transitions.
        """
        table: dict[str, Callable] = {
            "ls":           self._handle_ls,
            "cd":           self._handle_cd,
            "pwd":          self._handle_pwd,
            "cat":          self._handle_cat,
            "rm":           self._handle_rm,
            "echo":         self._handle_echo,
            "clear":        self._handle_clear,
            "help":         self._handle_help,
            "status":       self._handle_status,
            "ask":          self._handle_ask,
            "whoami":       self._handle_whoami,
            "passwd":       self._handle_passwd,
            "verify_audit": self._handle_verify_audit,
        }
        handler = table.get(base)
        if handler is None:
            return False
        handler(parts)
        return True

    # ── Filesystem commands ───────────────────────────────────────────────

    def _handle_ls(self, parts: list[str]) -> None:
        target = (self.cwd / parts[1]).resolve() if len(parts) > 1 else self.cwd
        if not str(target).startswith(str(self._base_dir)):
            self._emit_output(OutputFormatter.permission_denied(str(target)))
            return
        try:
            entries = sorted(
                target.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )
            self._emit_output(OutputFormatter.ls_output(entries))
        except Exception:
            self._emit_output(OutputFormatter.ls_error())

    def _handle_cd(self, parts: list[str]) -> None:
        raw = parts[1] if len(parts) > 1 else "~"
        if raw == "~":
            self.cwd = self._base_dir
            self._emit_prompt()
            return
        try:
            candidate = (self.cwd / raw).resolve()
            if (
                str(candidate).startswith(str(self._base_dir))
                and candidate.is_dir()
            ):
                self.cwd = candidate
                self._emit_prompt()
            else:
                self._emit_output(OutputFormatter.cd_invalid_path())
        except Exception:
            self._emit_output(OutputFormatter.cd_error())

    def _handle_pwd(self, _parts: list[str]) -> None:
        self._emit_output(str(self.cwd) + "\n")

    def _handle_cat(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._emit_output("cat: missing filename\n")
            return
        target = (self.cwd / parts[1]).resolve()
        if not str(target).startswith(str(self._base_dir)):
            self._emit_output(OutputFormatter.permission_denied(str(target)))
            return
        try:
            self._emit_output(target.read_text(errors="replace") + "\n")
        except FileNotFoundError:
            self._emit_output(f"cat: {parts[1]}: No such file or directory\n")
        except IsADirectoryError:
            self._emit_output(f"cat: {parts[1]}: Is a directory\n")
        except Exception as exc:
            self._emit_output(OutputFormatter.subprocess_error(exc))

    def _handle_echo(self, parts: list[str]) -> None:
        self._emit_output(" ".join(parts[1:]) + "\n")

    def _handle_rm(self, parts: list[str]) -> None:
        if len(parts) < 2:
            return

        name = parts[1]

        # Guard: protected system paths (threat reporting stays in TerminalEngine)
        if CommandParser.is_system_path_target(name):
            self._emit_output(OutputFormatter.policy_restricted("rm", name))
            # Signal to TerminalEngine that a threat event occurred
            self._on_rm_policy_violation(name)
            return

        # Guard: admin role required for rm
        if self._role_getter() != "admin":
            self._emit_output(OutputFormatter.admin_required("rm"))
            return

        target = (self.cwd / name).resolve()
        if not str(target).startswith(str(self._base_dir)):
            self._emit_output(OutputFormatter.permission_denied(name))
            return

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            self._emit_output(OutputFormatter.rm_success(name))
        except Exception:
            pass  # silently ignored — mirrors original behaviour

    # Policy violation hook — overridden by TerminalEngine to feed threat score
    def _on_rm_policy_violation(self, name: str) -> None:
        """
        Called when rm targets a protected path.
        Default: no-op.  TerminalEngine overrides this to call _increase_threat().
        """

    # ── System commands ───────────────────────────────────────────────────

    def _handle_clear(self, _parts: list[str]) -> None:
        # \x0c is the form-feed / clear sentinel consumed by TerminalWidget
        self._emit_output("\x0c")

    def _handle_help(self, _parts: list[str]) -> None:
        self._emit_output(OutputFormatter.help_text())

    def _handle_whoami(self, _parts: list[str]) -> None:
        # Role is read from TerminalEngine via the getter — always current
        role = self._role_getter()
        # We don't have the username directly, but it's embedded in the prompt.
        # TerminalEngine overrides whoami to pass user+role explicitly.
        self._emit_output(OutputFormatter.whoami(role, role))

    def _handle_passwd(self, _parts: list[str]) -> None:
        self._emit_output(OutputFormatter.passwd_policy())

    def _handle_status(self, _parts: list[str]) -> None:
        if self._api:
            res = self._api.intel.get_system_status()
            self._emit_output(OutputFormatter.status_line(
                res["reasoning"],
                0,          # threat_score is in TerminalEngine; passed via override
            ))
        else:
            self._emit_output(OutputFormatter.status_unavailable())

    def _handle_ask(self, parts: list[str]) -> None:
        question = " ".join(parts[1:])
        if not question:
            self._emit_output(OutputFormatter.ask_empty())
            return
        if self._api:
            result = self._api.intel.analyze_text(f"Explain {question}")
            self._emit_output(OutputFormatter.ask_response(result.get("reason", "")))

    def _handle_verify_audit(self, _parts: list[str]) -> None:
        # Delegate to SudoManager via override hook
        self._on_verify_audit()

    def _on_verify_audit(self) -> None:
        """
        Overridden by TerminalEngine to call sudo_manager.verify_audit_log()
        and emit the result.  Default: no-op.
        """

    # ── Subprocess ────────────────────────────────────────────────────────

    def run_subprocess(self, parts: list[str]) -> None:
        """Launch a whitelisted OS command in a background QThread."""
        if self._thread and self._thread.isRunning():
            return
        self._thread = QThread()
        self._worker = TerminalWorker(parts, str(self.cwd), self._process_guard)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.output_ready.connect(self._emit_output)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()
