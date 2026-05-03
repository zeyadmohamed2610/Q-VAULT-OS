"""
apps.terminal.terminal_engine — Q-Vault OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terminal Engine  |  Upgrade v4

Changes from v3
───────────────
1. History tracking   – every executed command stored in CommandContext._history
2. Alias expansion    – passes alias table to CommandParser.parse()
3. Unknown command    – shows did-you-mean via OutputFormatter.unknown_command()
4. Right-click admin  – run_as_administrator() public method sets ROOT state
5. Arrow-key history  – history_prev() / history_next() for UI to call
6. Pipe detection     – single-level pipe (cmd1 | cmd2) handled gracefully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import time
from collections import deque
from enum import Enum
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from system.sandbox.process_guard import ProcessGuard
from system.sandbox.fs_guard import FileSystemGuard
from system.security.auth_manager import AuthManager

from ._command_parser import CommandParser, SUBPROCESS_WHITELIST
from ._command_executor import CommandExecutor, TerminalWorker
from ._commands import CommandContext
from ._sudo_manager import (
    SudoManager,
    THREAT_FAILED_SUDO,
    THREAT_FAILED_UNLOCK,
    THREAT_COMMAND_BURST,
    THREAT_PATTERN_CORRELATE,
)
from ._output_formatter import OutputFormatter

# Backward-compat re-exports
_SUBPROCESS_WHITELIST = SUBPROCESS_WHITELIST
__all__ = [
    "TerminalEngine",
    "EngineState",
    "TerminalWorker",
    "_SUBPROCESS_WHITELIST",
]


class EngineState(Enum):
    NORMAL       = 0
    AUTH_REQUEST = 1
    AUTH_CONFIRM = 2
    AUTH_SUDO    = 3
    LOCKED       = 4
    TERMINATED   = 5
    ROOT         = 6


class TerminalEngine(QObject):
    """
    Facade that coordinates four single-responsibility components.

    New in v4
    ─────────
    - Command history stored in CommandContext._history (shared class-level list)
    - Alias table shared via CommandContext._aliases
    - Arrow-key navigation: history_prev() / history_next()
    - run_as_administrator() — called by right-click context menu
    - Single-level pipe support: 'cmd1 | cmd2' routes output of cmd1 as
      input file argument to cmd2 (limited simulation)
    - Unknown commands produce did-you-mean suggestions
    """

    output_ready  = pyqtSignal(str)
    prompt_update = pyqtSignal(str, str)
    password_mode = pyqtSignal(str, bool)
    state_changed = pyqtSignal(object) # Emits EngineState

    def __init__(self, secure_api=None, start_path: Path | None = None) -> None:
        super().__init__()
        from system.config import get_qvault_home

        self.api      = secure_api
        self.base_dir = Path(get_qvault_home()).resolve()

        self._auth_manager = AuthManager()
        self.sudo_manager  = SudoManager(self._auth_manager)

        self.current_user = "user"
        self.current_role = "user"

        self._state         = EngineState.NORMAL
        self._pending_pass = ""
        self._pending_cmd  = ""

        self.threat_score      = 0
        self._cmd_history: deque = deque(maxlen=15)
        self._suspicious_flags = 0
    
    @property
    def state(self) -> EngineState:
        return self._state

    @state.setter
    def state(self, new_state: EngineState):
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)

        self._process_guard = ProcessGuard("Terminal", api=secure_api)
        self._fs_guard      = FileSystemGuard("Terminal", api=secure_api)

        # Arrow-key history navigation cursor
        self._hist_cursor: int = -1   # -1 = not navigating

        self._executor = self._build_executor()
        if start_path:
            self._executor.cwd = start_path

    # ── Component wiring ──────────────────────────────────────────────────────

    def _build_executor(self) -> CommandExecutor:
        executor = CommandExecutor(
            base_dir=self.base_dir,
            process_guard=self._process_guard,
            fs_guard=self._fs_guard,
            emit_output=self.output_ready.emit,
            emit_prompt=self._emit_prompt,
            api=self.api,
            role_getter=lambda: self.current_role,
        )

        # Hook: rm on protected path → threat score
        def _rm_policy_violation(name: str) -> None:
            self._increase_threat(40, f"Attempted system deletion: {name}")
        executor._on_rm_policy_violation = _rm_policy_violation

        # Hook: verify_audit → SudoManager
        def _verify_audit() -> None:
            valid, msg = self.sudo_manager.verify_audit_log()
            self.output_ready.emit(OutputFormatter.audit_result(valid, msg))
        executor._on_verify_audit = _verify_audit

        # Hook: whoami needs current_user
        def _handle_whoami(_parts) -> None:
            self.output_ready.emit(
                OutputFormatter.whoami(self.current_user, self.current_role)
            )
        executor._handle_whoami = _handle_whoami

        # Hook: status needs live threat_score
        def _handle_status(_parts) -> None:
            if self.api:
                res = self.api.intel.get_system_status()
                self.output_ready.emit(
                    OutputFormatter.status_line(res["reasoning"], self.threat_score)
                )
            else:
                self.output_ready.emit(OutputFormatter.status_unavailable())
        executor._handle_status = _handle_status

        return executor

    # ── Public API ────────────────────────────────────────────────────────────

    def boot_terminal(self) -> None:
        self.output_ready.emit(OutputFormatter.boot_banner())
        self._emit_prompt()

    def execute_command(self, cmd_line: str) -> None:
        if not hasattr(self, "_last_cmd_time"):
            self._last_cmd_time = 0.0

        now = time.time()
        if now - self._last_cmd_time < 0.05:
            return
        self._last_cmd_time = now

        if self.state == EngineState.TERMINATED:
            self.output_ready.emit("[BLOCKED] Security integrity violation.\n")
            return

        cmd = cmd_line.strip()

        # Handle non-NORMAL states (password input, locked, etc.)
        if self.state not in (EngineState.NORMAL, EngineState.ROOT):
            self._handle_state_input(cmd)
            return

        if not cmd:
            self.output_ready.emit("")
            return

        # ── Store in history ──────────────────────────────────────────────
        if cmd and (not CommandContext._history or CommandContext._history[-1] != cmd):
            CommandContext._history.append(cmd)
        self._hist_cursor = -1  # reset navigation cursor

        self._analyze_behavior(cmd)
        if self.state == EngineState.TERMINATED:
            return

        # ── Pipe detection ────────────────────────────────────────────────
        if "|" in cmd:
            self._handle_pipe(cmd)
            return

        # ── Parse (with alias expansion) ──────────────────────────────────
        parsed = CommandParser.parse(cmd, aliases=CommandContext._aliases)
        if not parsed.parts:
            self._emit_prompt()
            return

        # ── Route ─────────────────────────────────────────────────────────
        if parsed.base == "qsu":
            self._handle_qsu()
        elif parsed.base == "sudo":
            self._handle_sudo(parsed.parts)
        elif parsed.base == "lock":
            self._handle_lock(parsed.parts)
        elif self._executor.dispatch(parsed):
            self._emit_prompt()
        elif parsed.is_whitelisted:
            self._executor.run_subprocess(parsed.parts)
        else:
            # Unknown command — suggest alternatives
            known = list(CommandParser.BUILTIN_COMMANDS) + list(CommandParser.SUBPROCESS_WHITELIST.keys())
            self.output_ready.emit(OutputFormatter.unknown_command(parsed.base, known))
            self._emit_prompt()

    # ── Right-click "Run as Administrator" ───────────────────────────────────

    def run_as_administrator(self) -> None:
        """
        Called by the terminal's right-click context menu 'Run as Administrator'.
        Elevates to ROOT state if the sudo password is already cached,
        otherwise triggers the sudo authentication flow.
        """
        if self.state == EngineState.ROOT:
            self.output_ready.emit("[Info] Already running as administrator.\n")
            self._emit_prompt()
            return

        if self.sudo_manager.is_sudo_cached:
            self._elevate_to_root()
            return

        if not self.sudo_manager.is_setup_complete:
            self._pending_cmd = "__admin__"
            self.state = EngineState.AUTH_REQUEST
            self.output_ready.emit(
                "[Administrator] Set up a master password to enable root access.\n"
                + OutputFormatter.setup_prompt_initial()
            )
            self.password_mode.emit("password_mode", True)
        else:
            self._pending_cmd = "__admin__"
            self.state = EngineState.AUTH_SUDO
            self.password_mode.emit("password_mode", True)
            self.output_ready.emit(
                "[Administrator] Authentication required.\n"
                + OutputFormatter.sudo_prompt()
            )

    def _elevate_to_root(self) -> None:
        self.sudo_manager.grant()
        self.state        = EngineState.ROOT
        self.current_user = "root"
        self.current_role = "admin"
        self.output_ready.emit("\033[41m[ROOT]\033[0m Administrator session active.\n")
        self._emit_prompt()

    # ── Arrow-key history navigation ─────────────────────────────────────────

    def history_prev(self) -> str:
        """Return previous command (↑ arrow). Empty string if none."""
        hist = CommandContext._history
        if not hist:
            return ""
        if self._hist_cursor == -1:
            self._hist_cursor = len(hist) - 1
        elif self._hist_cursor > 0:
            self._hist_cursor -= 1
        return hist[self._hist_cursor]

    def history_next(self) -> str:
        """Return next command (↓ arrow). Empty string if at end."""
        hist = CommandContext._history
        if self._hist_cursor == -1:
            return ""
        self._hist_cursor += 1
        if self._hist_cursor >= len(hist):
            self._hist_cursor = -1
            return ""
        return hist[self._hist_cursor]

    # ── Pipe handling ─────────────────────────────────────────────────────────

    def _handle_pipe(self, cmd: str) -> None:
        """
        Simple single-level pipe simulation.
        cmd1 | cmd2  →  run cmd1, collect output, pass as last arg to cmd2.
        """
        segments = [s.strip() for s in cmd.split("|", 1)]
        if len(segments) != 2:
            self.execute_command(cmd.replace("|", ""))
            return

        # Capture cmd1 output in a buffer
        buffer: list[str] = []
        orig_emit = self._executor._emit_output

        def _capture(text: str) -> None:
            buffer.append(text)

        self._executor._emit_output = _capture
        try:
            parsed1 = CommandParser.parse(segments[0], aliases=CommandContext._aliases)
            if parsed1.parts:
                self._executor.dispatch(parsed1)
        finally:
            self._executor._emit_output = orig_emit

        captured = "".join(buffer)

        # Write captured output to a temp file so cmd2 can read it
        import tempfile, os
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pipe", delete=False,
                dir=str(self._executor.cwd), encoding="utf-8"
            ) as f:
                f.write(captured)
                tmp = f.name

            pipe_arg = os.path.basename(tmp)
            cmd2_raw = segments[1] + " " + pipe_arg
            parsed2  = CommandParser.parse(cmd2_raw, aliases=CommandContext._aliases)
            if parsed2.parts:
                if self._executor.dispatch(parsed2):
                    pass
                elif parsed2.is_whitelisted:
                    self._executor.run_subprocess(parsed2.parts)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

        self._emit_prompt()

    # ── State machine ─────────────────────────────────────────────────────────

    def _handle_state_input(self, text: str) -> None:
        if self.state == EngineState.AUTH_REQUEST:
            self._state_setup_pass(text)
        elif self.state == EngineState.AUTH_CONFIRM:
            self._state_setup_confirm(text)
        elif self.state == EngineState.AUTH_SUDO:
            self._state_auth_sudo(text)
        elif self.state == EngineState.LOCKED:
            self._state_locked(text)

    def _handle_qsu(self) -> None:
        if not self.sudo_manager.is_setup_complete:
            self.state = EngineState.AUTH_REQUEST
            self.output_ready.emit(OutputFormatter.setup_prompt_initial())
            self.password_mode.emit("password_mode", True)
        else:
            self._pending_cmd = "qsu"
            self.state = EngineState.AUTH_SUDO
            self.password_mode.emit("password_mode", True)
            self.output_ready.emit(OutputFormatter.sudo_prompt())

    def _state_setup_pass(self, text: str) -> None:
        if len(text) < 8:
            self.output_ready.emit(OutputFormatter.setup_min_length_error())
            return
        self._pending_pass = text
        self.state = EngineState.AUTH_CONFIRM
        self.output_ready.emit(OutputFormatter.setup_confirm_prompt())

    def _state_setup_confirm(self, text: str) -> None:
        self.password_mode.emit("password_mode", False)
        if text == self._pending_pass:
            self.sudo_manager.set_password(text)
            if self._pending_cmd == "__admin__":
                self._elevate_to_root()
            else:
                self.state        = EngineState.ROOT
                self.current_user = "root"
                self.current_role = "admin"
                self.output_ready.emit(OutputFormatter.setup_success())
                self._emit_prompt()
        else:
            self.state = EngineState.AUTH_REQUEST
            self.password_mode.emit("password_mode", True)
            self.output_ready.emit(OutputFormatter.setup_mismatch_error())
        self._pending_pass = ""

    def _state_auth_sudo(self, text: str) -> None:
        self.password_mode.emit("password_mode", False)
        import logging
        logger = logging.getLogger("terminal.sudo")
        logger.info(f"[SUDO_AUTH] len={len(text)}, setup={self.sudo_manager.is_setup_complete}")

        verified = self.sudo_manager.verify_password(text)
        logger.info(f"[SUDO_AUTH] result={verified}")

        if verified:
            self.sudo_manager.grant()
            if self._pending_cmd in ("qsu", "__admin__"):
                self._elevate_to_root()
            else:
                self.state = EngineState.NORMAL
                self.output_ready.emit(OutputFormatter.sudo_granted())
                saved_role        = self.current_role
                self.current_role = "admin"
                self.execute_command(self._pending_cmd)
                self.current_role = saved_role
        else:
            pts = self.sudo_manager.threat_points_for_failed_sudo()
            self._increase_threat(pts, "Failed sudo auth attempt")
            self.state = EngineState.NORMAL
            self.output_ready.emit(OutputFormatter.sudo_denied())
            self._emit_prompt()

    def _state_locked(self, text: str) -> None:
        if self.sudo_manager.verify_password(text):
            self.state = EngineState.NORMAL
            self.password_mode.emit("password_mode", False)
            self.output_ready.emit(OutputFormatter.unlock_success())
            self._emit_prompt()
        else:
            pts = self.sudo_manager.threat_points_for_failed_unlock()
            self._increase_threat(pts, "Failed session unlock")
            self.output_ready.emit(OutputFormatter.unlock_failed())

    def _handle_sudo(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self.output_ready.emit("usage: sudo command\n")
            self._emit_prompt()
            return
        self._pending_cmd = " ".join(parts[1:])
        if self.sudo_manager.is_sudo_cached:
            saved_role        = self.current_role
            self.current_role = "admin"
            self.execute_command(self._pending_cmd)
            self.current_role = saved_role
            return
        self.state = EngineState.AUTH_SUDO
        self.password_mode.emit("password_mode", True)
        self.output_ready.emit(OutputFormatter.sudo_prompt())

    def _handle_lock(self, _parts: list[str]) -> None:
        self.state = EngineState.LOCKED
        self.password_mode.emit("password_mode", True)
        self.output_ready.emit(OutputFormatter.lock_screen())

    # ── Behavioral analysis / IDS ─────────────────────────────────────────────

    def _analyze_behavior(self, cmd: str) -> None:
        now = time.time()
        self._cmd_history.append((now, cmd))

        burst_count = sum(1 for t, _ in self._cmd_history if now - t < 2.0)
        if burst_count > 8:
            self._increase_threat(
                THREAT_COMMAND_BURST,
                f"Command Burst Detected ({burst_count} in 2s)",
            )

    def _increase_threat(self, points: int, reason: str) -> None:
        self.threat_score += points
        self.sudo_manager.log_audit(
            "THREAT_DETECTED",
            f"Score: {self.threat_score} | {reason}",
        )
        if self.threat_score >= 100:
            self.state = EngineState.TERMINATED
            self.output_ready.emit(OutputFormatter.threat_lockdown())

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _emit_prompt(self) -> None:
        prompt_str = OutputFormatter.prompt(
            user=self.current_user,
            role=self.current_role,
            cwd=self._executor.cwd,
            base_dir=self.base_dir,
        )
        self.prompt_update.emit("prompt_update", prompt_str)

    @property
    def cwd(self) -> Path:
        return self._executor.cwd
