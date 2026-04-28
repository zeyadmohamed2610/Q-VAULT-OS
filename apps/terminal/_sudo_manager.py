"""
apps.terminal._sudo_manager
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Sudo / Authentication Session Manager

Single Responsibility: manage every authentication concern of the terminal.

  - sudo session cache (60-second TTL)
  - password setup state machine helpers  (SETUP_PASS → SETUP_CONFIRM)
  - failed-attempt threat weighting
  - audit log delegation

No Qt imports.  No output signals.  No knowledge of EngineState.
SudoManager tells you *facts* about auth state and *performs* auth
operations; it does not decide what to do with the results — that stays
in TerminalEngine (the Facade) where state transitions live.

Previously all of this was inlined across:
  TerminalEngine.__init__          (sudo_auth_until, _pending_pass)
  TerminalEngine._handle_sudo      (cache check, role elevation)
  TerminalEngine._handle_state_input (setup + lock auth flows)
  TerminalEngine._increase_threat   (partially)
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import time


# ── Threat contribution weights ───────────────────────────────────────────
#
# These were previously bare integer literals inside _increase_threat().
# Naming them makes the security policy auditable without reading logic.

THREAT_FAILED_SUDO      = 25   # wrong sudo password
THREAT_FAILED_UNLOCK    = 15   # wrong lock-screen password
THREAT_COMMAND_BURST    = 20   # rapid-fire command flood  (per burst)
THREAT_PATTERN_CORRELATE = 50  # failed-auth → sensitive file access


class SudoManager:
    """
    Manages the sudo session cache and all authentication helpers for the
    Q-Vault terminal.

    Parameters
    ----------
    auth : AuthManager
        The real AuthManager instance from system.security.auth_manager.
        SudoManager wraps it — never owns the user database itself.
    sudo_ttl : int
        Seconds a successful sudo verification stays valid.
        Default: 60  (matches the original hard-coded value).
    """

    def __init__(self, auth, sudo_ttl: int = 60) -> None:
        self._auth = auth
        self._sudo_ttl = sudo_ttl
        self._sudo_auth_until: float = 0.0   # epoch timestamp

    # ── Public read-only properties ───────────────────────────────────────

    @property
    def is_setup_complete(self) -> bool:
        """True when the master password has already been configured."""
        return self._auth.is_setup_complete()

    @property
    def is_sudo_cached(self) -> bool:
        """
        True when a successful sudo verification is still within its TTL.
        Mirrors the original: ``time.time() < self.sudo_auth_until``
        """
        return time.time() < self._sudo_auth_until

    # ── Session operations ────────────────────────────────────────────────

    def grant(self) -> None:
        """
        Record a successful sudo verification.
        The session is valid for ``sudo_ttl`` seconds from now.
        """
        self._sudo_auth_until = time.time() + self._sudo_ttl

    def revoke(self) -> None:
        """Immediately invalidate the sudo session cache."""
        self._sudo_auth_until = 0.0

    # ── Verification ─────────────────────────────────────────────────────

    def verify_password(self, text: str) -> bool:
        """Delegate to AuthManager.verify_password()."""
        return self._auth.verify_password(text)

    def set_password(self, text: str) -> None:
        """Delegate to AuthManager.set_password() (initial setup only)."""
        self._auth.set_password(text)

    # ── Audit / Threat ────────────────────────────────────────────────────

    def log_audit(self, event: str, detail: str) -> None:
        """Delegate to AuthManager.log_audit()."""
        self._auth.log_audit(event, detail)

    def verify_audit_log(self) -> tuple[bool, str]:
        """Delegate to AuthManager.verify_audit_log()."""
        return self._auth.verify_audit_log()

    def threat_points_for_failed_sudo(self) -> int:
        """
        Return the threat score contribution for a failed sudo attempt
        and record the event in the audit log.
        Caller adds the returned value to the engine's running threat_score.
        """
        self._auth.log_audit(
            "THREAT_DETECTED",
            f"Failed sudo auth attempt (+{THREAT_FAILED_SUDO}pts)",
        )
        return THREAT_FAILED_SUDO

    def threat_points_for_failed_unlock(self) -> int:
        """
        Return the threat score contribution for a failed lock-screen attempt
        and record the event in the audit log.
        """
        self._auth.log_audit(
            "THREAT_DETECTED",
            f"Failed session unlock (+{THREAT_FAILED_UNLOCK}pts)",
        )
        return THREAT_FAILED_UNLOCK
