"""
apps.terminal.terminal_engine
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Terminal Engine  (Refactored — Facade pattern)

ARCHITECTURE (post-refactor)
─────────────────────────────
Before: one 260-line God Object with 20+ methods mixing parsing,
        execution, sudo, formatting, threat analysis, and output.

After:  four single-responsibility components + one thin Facade.

  ┌──────────────────────────────────────────────────────────┐
  │  TerminalEngine  (this file — Facade / Coordinator)      │
  │                                                          │
  │  ┌──────────────────┐  ┌──────────────────┐             │
  │  │  CommandParser   │  │   SudoManager    │             │
  │  │  (pure, static)  │  │  (auth + cache)  │             │
  │  └──────────────────┘  └──────────────────┘             │
  │                                                          │
  │  ┌──────────────────┐  ┌──────────────────┐             │
  │  │ CommandExecutor  │  │  OutputFormatter │             │
  │  │ (fs + sys cmds)  │  │  (pure strings)  │             │
  │  └──────────────────┘  └──────────────────┘             │
  └──────────────────────────────────────────────────────────┘

EXTERNAL CONTRACT (unchanged — zero breaking changes)
──────────────────────────────────────────────────────
  Import path : apps.terminal.terminal_engine
  Class       : TerminalEngine
  Signals     : output_ready(str)
                prompt_update(str, str)   <- ("prompt_update", "<text>")
                password_mode(str, bool)  <- ("password_mode", True/False)
  Methods     : boot_terminal()
                execute_command(str)

Re-exported for backward compat:
  EngineState, TerminalWorker, _SUBPROCESS_WHITELIST
────────────────────────────────────────────────────────────────────────────
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
    NORMAL         = 0
    SETUP_PASS     = 1
    SETUP_CONFIRM  = 2
    AUTH_SUDO      = 3
    LOCKED         = 4
    TERMINATED     = 5


class TerminalEngine(QObject):
    """
    Facade that coordinates four single-responsibility components.
    The only things that remain here are:
      - Signal declarations (IsolatedAppWidget contract)
      - EngineState machine (sudo + lock transitions)
      - Threat / IDS logic (reads + writes self.state)
      - Component wiring
    """

    output_ready  = pyqtSignal(str)
    prompt_update = pyqtSignal(str, str)
    password_mode = pyqtSignal(str, bool)

    def __init__(self, secure_api=None) -> None:
        super().__init__()
        from system.config import get_qvault_home

        self.api      = secure_api
        self.base_dir = Path(get_qvault_home()).resolve()

        self._auth_manager = AuthManager()
        self.sudo_manager  = SudoManager(self._auth_manager)

        self.current_user = "guest"
        self.current_role = "guest"

        self.state         = EngineState.NORMAL
        self._pending_pass = ""
        self._pending_cmd  = ""

        self.threat_score      = 0
        self._cmd_history: deque = deque(maxlen=15)
        self._suspicious_flags = 0

        self._process_guard = ProcessGuard("Terminal", api=secure_api)
        self._fs_guard      = FileSystemGuard("Terminal", api=secure_api)

        self._executor = self._build_executor()

        if not self.sudo_manager.is_setup_complete:
            self.state = EngineState.SETUP_PASS

    # ------------------------------------------------------------------
    # Component wiring
    # ------------------------------------------------------------------

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

        # Hook: rm on protected path -> threat score
        def _rm_policy_violation(name: str) -> None:
            self._increase_threat(40, f"Attempted system deletion: {name}")
        executor._on_rm_policy_violation = _rm_policy_violation

        # Hook: verify_audit -> SudoManager
        def _verify_audit() -> None:
            valid, msg = self.sudo_manager.verify_audit_log()
            self.output_ready.emit(OutputFormatter.audit_result(valid, msg))
        executor._on_verify_audit = _verify_audit

        # Hook: whoami needs current_user (executor only has role getter)
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

    # ------------------------------------------------------------------
    # Public API  (called via IsolatedAppWidget.call_remote)
    # ------------------------------------------------------------------

    def boot_terminal(self) -> None:
        if self.state == EngineState.SETUP_PASS:
            self.output_ready.emit(OutputFormatter.setup_prompt_initial())
            self.password_mode.emit("password_mode", True)
        else:
            self.output_ready.emit(OutputFormatter.boot_banner())
            self._emit_prompt()

    def execute_command(self, cmd_line: str) -> None:
        if self.state == EngineState.TERMINATED:
            self.output_ready.emit("[BLOCKED] Security integrity violation.\n")
            return

        cmd = cmd_line.strip()

        if self.state != EngineState.NORMAL:
            self._handle_state_input(cmd)
            return

        if not cmd:
            self.output_ready.emit("")
            return

        self._analyze_behavior(cmd)
        if self.state == EngineState.TERMINATED:
            return

        parsed = CommandParser.parse(cmd)
        if not parsed.parts:
            return

        if parsed.base == "sudo":
            self._handle_sudo(parsed.parts)
        elif parsed.base == "lock":
            self._handle_lock(parsed.parts)
        elif self._executor.dispatch(parsed.base, parsed.parts):
            pass
        else:
            self._executor.run_subprocess(parsed.parts)

    # ------------------------------------------------------------------
    # State machine  (EngineState transitions — must stay in Facade)
    # ------------------------------------------------------------------

    def _handle_state_input(self, text: str) -> None:
        if self.state == EngineState.SETUP_PASS:
            self._state_setup_pass(text)
        elif self.state == EngineState.SETUP_CONFIRM:
            self._state_setup_confirm(text)
        elif self.state == EngineState.AUTH_SUDO:
            self._state_auth_sudo(text)
        elif self.state == EngineState.LOCKED:
            self._state_locked(text)

    def _state_setup_pass(self, text: str) -> None:
        if len(text) < 8:
            self.output_ready.emit(OutputFormatter.setup_min_length_error())
            return
        self._pending_pass = text
        self.state = EngineState.SETUP_CONFIRM
        self.output_ready.emit(OutputFormatter.setup_confirm_prompt())

    def _state_setup_confirm(self, text: str) -> None:
        self.password_mode.emit("password_mode", False)
        if text == self._pending_pass:
            self.sudo_manager.set_password(text)
            self.state        = EngineState.NORMAL
            self.current_user = "admin"
            self.current_role = "admin"
            self.output_ready.emit(OutputFormatter.setup_success())
            self._emit_prompt()
        else:
            self.state = EngineState.SETUP_PASS
            self.password_mode.emit("password_mode", True)
            self.output_ready.emit(OutputFormatter.setup_mismatch_error())
        self._pending_pass = ""

    def _state_auth_sudo(self, text: str) -> None:
        self.password_mode.emit("password_mode", False)
        if self.sudo_manager.verify_password(text):
            self.sudo_manager.grant()
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

    # ------------------------------------------------------------------
    # Behavioral analysis / IDS
    # ------------------------------------------------------------------

    def _analyze_behavior(self, cmd: str) -> None:
        now = time.time()
        self._cmd_history.append((now, cmd))

        burst_count = sum(1 for t, _ in self._cmd_history if now - t < 2.0)
        if burst_count > 8:
            self._increase_threat(
                THREAT_COMMAND_BURST,
                f"Command Burst Detected ({burst_count} in 2s)",
            )

        # Pattern correlation branch — preserved from original.
        # _last_event_type() was never implemented; branch is permanently
        # unreachable. Documented here for future implementer.
        last_evt = ""
        if "Failed" in last_evt:
            if any(p in cmd for p in ["system", "audit", "auth", "vault"]):
                self._increase_threat(
                    THREAT_PATTERN_CORRELATE,
                    "Pattern Correlation: Access attempt after auth failure.",
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

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

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
        """Forward executor.cwd — preserves any external read of engine.cwd."""
        return self._executor.cwd
