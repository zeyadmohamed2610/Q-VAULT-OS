"""
apps.terminal._output_formatter
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Terminal Output Formatter

Single Responsibility: produce every string the terminal can emit.
No Qt, no state, no I/O — pure transformation functions.

All strings that were previously scattered as inline literals inside
TerminalEngine._handle_* methods now live here.  Callers simply do:

    self.output_ready.emit(OutputFormatter.denied("rm", "Admin required."))

This makes all terminal messaging auditable in one place and trivially
testable without a Qt event loop.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from pathlib import Path


class OutputFormatter:
    """
    Stateless factory for every string the terminal outputs.

    Convention
    ----------
    - Methods that format a *class* of message (error, denied, success)
      take the relevant data as arguments.
    - Methods that produce a fixed block (boot message, help text) take
      no arguments and are class-level constants wrapped as classmethods
      to keep the API consistent.
    """

    # ── Boot & Setup ─────────────────────────────────────────────────────

    @staticmethod
    def boot_banner() -> str:
        return "Q-Vault Terminal v4.9.5 [Flawless Alignment]\n"

    @staticmethod
    def setup_prompt_initial() -> str:
        return (
            "Q-Vault: Secure AI-Powered Terminal Environment\n"
            "[Security] Setup Master Key (Password): "
        )

    @staticmethod
    def setup_confirm_prompt() -> str:
        return "\nConfirm Password: "

    @staticmethod
    def setup_success() -> str:
        return "\n[Success] Secure Session Initialized.\n"

    @staticmethod
    def setup_min_length_error() -> str:
        return "Min 8 chars. Retry: "

    @staticmethod
    def setup_mismatch_error() -> str:
        return "\n[Error] Mismatch. Password: "

    # ── Authentication & Session ──────────────────────────────────────────

    @staticmethod
    def sudo_prompt() -> str:
        return "[sudo] password for admin: "

    @staticmethod
    def sudo_granted() -> str:
        return "\n"

    @staticmethod
    def sudo_denied() -> str:
        return "\n[Denied]\n"

    @staticmethod
    def lock_screen() -> str:
        # \x0c is the form-feed / clear signal consumed by TerminalWidget.append_output
        return "\x0c\n[LOCKED]\nUnlock Password: "

    @staticmethod
    def unlock_success() -> str:
        return "\n[Restored]\n"

    @staticmethod
    def unlock_failed() -> str:
        return "\n[Error] Password: "

    @staticmethod
    def passwd_policy() -> str:
        return "Use 'lock' then reset via GUI (Hardened Policy).\n"

    # ── Threat & Lockdown ─────────────────────────────────────────────────

    @staticmethod
    def threat_lockdown() -> str:
        return "\n\n[CRITICAL] SYSTEM LOCKDOWN: High-risk anomaly detected.\n"

    @staticmethod
    def security_blocked(cmd: str) -> str:
        return f"[Security] '{cmd}' blocked.\n"

    @staticmethod
    def policy_restricted(cmd: str, name: str) -> str:
        return f"{cmd}: Policy restricted.\n"

    @staticmethod
    def admin_required(cmd: str) -> str:
        return f"{cmd}: Admin required.\n"

    @staticmethod
    def permission_denied(path: str = "") -> str:
        suffix = f": {path}" if path else ""
        return f"Denied{suffix}.\n"

    # ── Filesystem ───────────────────────────────────────────────────────

    @staticmethod
    def ls_output(entries) -> str:
        """
        Format a sequence of Path objects as ls output.
        Directories are prefixed with '/'.
        """
        parts = [
            f"/{x.name}" if x.is_dir() else x.name
            for x in entries
        ]
        return "  ".join(parts) + "\n" if parts else "\n"

    @staticmethod
    def ls_error() -> str:
        return "ls: Error.\n"

    @staticmethod
    def cd_invalid_path() -> str:
        return "Invalid path.\n"

    @staticmethod
    def cd_error() -> str:
        return "cd: Error.\n"

    @staticmethod
    def rm_success(name: str) -> str:
        return f"Removed {name}\n"

    @staticmethod
    def subprocess_error(exc: Exception) -> str:
        return f"Error: {exc}\n"

    # ── AI / System ───────────────────────────────────────────────────────

    @staticmethod
    def status_line(reasoning: str, threat_score: int) -> str:
        return (
            f"[Env] Health={reasoning} | "
            f"Threat={threat_score}% | Integrity=CHECKED\n"
        )

    @staticmethod
    def ask_response(reason: str) -> str:
        return f"[AI] {reason}\n"

    @staticmethod
    def ask_empty() -> str:
        return "[AI] No question provided.\n"

    @staticmethod
    def status_unavailable() -> str:
        return "[Status] System intelligence not available.\n"

    @staticmethod
    def audit_result(valid: bool, msg: str) -> str:
        color = "[OK]" if valid else "[FAIL]"
        return f"Audit Integrity Check: {color} {msg}\n"

    # ── Whoami & Help ─────────────────────────────────────────────────────

    @staticmethod
    def whoami(user: str, role: str) -> str:
        return f"{user} ({role})\n"

    @staticmethod
    def help_text() -> str:
        return (
            "Q-Vault Environment Help\n"
            " FS:  ls, cd, pwd, cat, rm, mkdir, touch\n"
            " AI:  analyze, shadow, audit, ask, status\n"
            " SEC: login, logout, sudo, passwd, lock, verify_audit\n"
            " SYS: ping, git, pip, whoami\n"
        )

    # ── Prompt ────────────────────────────────────────────────────────────

    @staticmethod
    def prompt(user: str, role: str, cwd: Path, base_dir: Path) -> str:
        """
        Build the shell prompt string.
        Mirrors the original _emit_prompt() logic exactly.

        Example outputs:
            "admin@node:~# "
            "user@node:~/Documents$ "
            "user@node:/tmp$ "
        """
        char = "#" if role == "admin" else "$"
        try:
            rel = f"~/{cwd.relative_to(base_dir)}"
        except ValueError:
            rel = str(cwd)

        # Normalise "~/." and "." → "~"
        if rel in ("~/.", "."):
            rel = "~"

        return f"{user}@node:{rel}{char} "
