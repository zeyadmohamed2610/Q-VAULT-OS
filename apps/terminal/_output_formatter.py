"""
apps.terminal._output_formatter — Q-Vault OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terminal Output Formatter  |  Upgrade v4

Changes from v3
───────────────
- help_text() rewritten: complete command reference with categories
- ls_output() supports colour hints (dirs cyan, executables green)
- prompt() now shows [ROOT] badge when role == admin
- New: unknown_command() with did-you-mean suggestions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import difflib
from pathlib import Path


class OutputFormatter:
    """Stateless factory for every string the terminal outputs."""

    # ── Boot & Setup ─────────────────────────────────────────────────────────

    @staticmethod
    def boot_banner() -> str:
        """
        Q-VAULT ASCII art — pure ASCII, works in every monospace font.
        """
        lines = [
            "",
            "  @@@@@@               @@@  @@@   @@@@@@   @@@  @@@  @@@       @@@@@@@  ",
            " @@@@@@@@              @@@  @@@  @@@@@@@@  @@@  @@@  @@@       @@@@@@@  ",
            " @@!  @@@              @@!  @@@  @@!  @@@  @@!  @@@  @@!         @@!    ",
            " !@!  @!@              !@!  @!@  !@!  @!@  !@!  @!@  !@!         !@!    ",
            " @!@  !@!   @!@!@!@!@  @!@  !@!  @!@!@!@!  @!@  !@!  @!!         @!!    ",
            " !@!  !!!   !!!@!@!!!  !@!  !!!  !!!@!!!!  !@!  !!!  !!!         !!!    ",
            " !!:!!:!:              :!:  !!:  !!:  !!!  !!:  !!!  !!:         !!:    ",
            " :!: :!:                ::!!:!   :!:  !:!  :!:  !:!   :!:        :!:    ",
            " ::::: :!                ::::    ::   :::  ::::: ::   :: ::::     ::    ",
            "  : :  :::                :       :   : :   : :  :   : :: : :     :     ",
            ""
        ]
        logo = "\n".join(lines)
        return (
            "\n" + logo + "\n"
            "  -------------------------------------------------\n"
            "  Secure AI-Powered OS Terminal  |  Q-Vault v1.0.0\n"
            "  Rust Security Core Active  |  Session Encrypted  \n"
            "  -------------------------------------------------\n"
            "\n"
            "  Type 'help' for a command list, 'man <cmd>' for details.\n"
            "\n"
        )

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

    # ── Authentication & Session ──────────────────────────────────────────────

    @staticmethod
    def sudo_prompt() -> str:
        return "[sudo] password for user: "

    @staticmethod
    def sudo_granted() -> str:
        return "\n"

    @staticmethod
    def sudo_denied() -> str:
        return "\nsudo: Authentication failure\n"

    @staticmethod
    def lock_screen() -> str:
        return "\x0c\n[LOCKED] Session locked.\nUnlock Password: "

    @staticmethod
    def unlock_success() -> str:
        return "\n[Restored] Session unlocked.\n"

    @staticmethod
    def unlock_failed() -> str:
        return "\nIncorrect password. Unlock Password: "

    @staticmethod
    def passwd_policy() -> str:
        return "Use 'lock' then reset via GUI (Hardened Policy).\n"

    # ── Threat & Lockdown ─────────────────────────────────────────────────────

    @staticmethod
    def threat_lockdown() -> str:
        return "\n\n[CRITICAL] SYSTEM LOCKDOWN: High-risk anomaly detected.\n"

    @staticmethod
    def security_blocked(cmd: str) -> str:
        return f"[Security] '{cmd}' is not permitted in this environment.\n"

    @staticmethod
    def policy_restricted(cmd: str, name: str) -> str:
        return f"{cmd}: operation on '{name}' is policy-restricted.\n"

    @staticmethod
    def admin_required(cmd: str) -> str:
        return f"{cmd}: requires administrator privileges. Use 'sudo {cmd} ...'.\n"

    @staticmethod
    def permission_denied(path: str = "") -> str:
        suffix = f": {path}" if path else ""
        return f"Permission denied{suffix}.\n"

    # ── Filesystem ───────────────────────────────────────────────────────────

    @staticmethod
    def ls_output(entries: list[Path], base_path: Path | None = None) -> str:
        """
        Format a sequence of Path objects as ls output.
        Directories are shown with trailing / and a colour hint marker.
        """
        sorted_entries = sorted(
            entries, key=lambda x: (not x.is_dir(), x.name.lower())
        )

        parts: list[str] = []
        for x in sorted_entries:
            try:
                name = str(x.relative_to(base_path)) if base_path else x.name
            except ValueError:
                name = x.name
            if x.is_dir():
                parts.append(f"[DIR] {name}/")
            elif x.suffix in (".sh", ".py", ".exe", ".bin"):
                parts.append(f"[EXE] {name}*")
            else:
                parts.append(f"      {name}")

        return "\n".join(parts) + "\n" if parts else "\n"

    @staticmethod
    def ls_error() -> str:
        return "ls: cannot list directory.\n"

    @staticmethod
    def cd_invalid_path() -> str:
        return "cd: No such file or directory.\n"

    @staticmethod
    def cd_error() -> str:
        return "cd: error.\n"

    @staticmethod
    def rm_success(name: str) -> str:
        return f"Removed {name}\n"

    @staticmethod
    def subprocess_error(exc: Exception) -> str:
        return f"Error: {exc}\n"

    # ── Unknown command ───────────────────────────────────────────────────────

    @staticmethod
    def unknown_command(cmd: str, known: list[str]) -> str:
        """Print a helpful 'command not found' with did-you-mean suggestions."""
        msg = f"bash: {cmd}: command not found\n"
        suggestions = difflib.get_close_matches(cmd, known, n=3, cutoff=0.6)
        if suggestions:
            msg += f"Did you mean: {', '.join(suggestions)}?\n"
        return msg

    # ── AI / System ───────────────────────────────────────────────────────────

    @staticmethod
    def status_line(reasoning: str, threat_score: int) -> str:
        bar = "█" * (threat_score // 10) + "░" * (10 - threat_score // 10)
        return (
            f"[System Status]\n"
            f"  Health     : {reasoning}\n"
            f"  Threat     : [{bar}] {threat_score}%\n"
            f"  Integrity  : CHECKED\n"
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
        tag = "[OK]  " if valid else "[FAIL]"
        return f"Audit Integrity Check: {tag} {msg}\n"

    # ── Whoami & Help ─────────────────────────────────────────────────────────

    @staticmethod
    def whoami(user: str, role: str) -> str:
        return f"{user}\n"

    @staticmethod
    def help_text() -> str:
        return (
            "\n"
            " ╔══════════════════════════════════════════════════════╗\n"
            " ║          Q-Vault OS — Command Reference v4           ║\n"
            " ╚══════════════════════════════════════════════════════╝\n"
            "\n"
            " [ FILE & DIRECTORY MANAGEMENT ]\n"
            "  ls [-lahR]         list directory contents\n"
            "  cd [DIR]           change directory  (~, -, ..)\n"
            "  pwd                print working directory\n"
            "  mkdir [-p] DIR     create directory\n"
            "  rm [-rf] FILE      remove file or directory\n"
            "  cp [-r] SRC DST    copy files\n"
            "  mv SRC DST         move / rename\n"
            "  touch FILE         create empty file / update mtime\n"
            "  ln [-s] TGT LINK   create link (simulated)\n"
            "  tree [DIR]         directory tree view\n"
            "\n"
            " [ VIEWING & EDITING ]\n"
            "  cat [-n] FILE      display file contents\n"
            "  less FILE          paginated view (first 40 lines)\n"
            "  head [-N] FILE     first N lines (default 10)\n"
            "  tail [-N] FILE     last N lines (default 10)\n"
            "  nano / vim FILE    open graphical editor\n"
            "\n"
            " [ SEARCH & TEXT PROCESSING ]\n"
            "  grep [-inrvcwl] PAT FILE   search for pattern\n"
            "  find [PATH] [-name PAT]    find files\n"
            "  wc [-lwc] FILE             word/line/char count\n"
            "  sort [-rnu] FILE           sort lines\n"
            "  uniq [-c] FILE             remove duplicate lines\n"
            "  diff FILE1 FILE2           compare two files\n"
            "\n"
            " [ PERMISSIONS & OWNERSHIP ]\n"
            "  chmod [-R] MODE FILE       change permissions\n"
            "  chown [-R] OWNER FILE      change owner (root)\n"
            "  sudo COMMAND               run as administrator\n"
            "\n"
            " [ SYSTEM INFORMATION ]\n"
            "  ps [aux]           process list\n"
            "  top / htop         live resource monitor\n"
            "  df [-h]            disk space\n"
            "  du [-hs] PATH      directory size\n"
            "  free [-h]          memory usage\n"
            "  uname [-a]         system/kernel info\n"
            "  uptime             system uptime\n"
            "  date               current date/time\n"
            "  id / whoami        user identity\n"
            "  stat FILE          detailed file info\n"
            "\n"
            " [ NETWORK ]\n"
            "  ping [-c N] HOST   test connectivity\n"
            "  curl URL           HTTP request\n"
            "  wget URL           download file\n"
            "  ssh [user@]HOST    remote shell (simulated)\n"
            "\n"
            " [ DOCUMENTATION & HISTORY ]\n"
            "  man COMMAND        manual page\n"
            "  history [N]        command history\n"
            "  which COMMAND      locate command\n"
            "  type COMMAND       describe command type\n"
            "\n"
            " [ ENVIRONMENT & SESSION ]\n"
            "  env                print environment\n"
            "  export K=V         set variable\n"
            "  alias [k='v']      define / list aliases\n"
            "  echo [-n] TEXT     print text\n"
            "  clear              clear screen\n"
            "  exit / logout      end session\n"
            "\n"
            " [ SECURITY & AI ]\n"
            "  whoami             print current user\n"
            "  passwd             password policy\n"
            "  lock               lock session\n"
            "  qsu                Q-Vault sudo setup\n"
            "  ask QUESTION       AI assistant\n"
            "  status             system status\n"
            "  verify_audit       audit log integrity\n"
            "\n"
            " [ ADMIN (Right-click → Run as Administrator) ]\n"
            "  sudo COMMAND       execute with root rights\n"
            "  stress [N]         spawn N dummy processes\n"
            "  fullstress         full OS stress test\n"
            "\n"
        )

    # ── Prompt ────────────────────────────────────────────────────────────────

    @staticmethod
    def prompt(user: str, role: str, cwd: Path, base_dir: Path) -> str:
        """
        Build the shell prompt.  Root sessions get a # symbol and [ROOT] badge.
        """
        is_root = (role == "admin")
        sym     = "#" if is_root else "$"
        badge   = "[ROOT] " if is_root else ""

        try:
            rel      = cwd.relative_to(base_dir)
            path_str = f"~/{rel}" if str(rel) != "." else "~"
        except ValueError:
            path_str = str(cwd)

        path_str = path_str.replace("\\", "/")
        return f"┌──({badge}{user}㉿qvault)──[{path_str}]\n└─{sym} "
