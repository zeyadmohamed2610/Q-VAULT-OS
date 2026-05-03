class QVaultError(Exception):
    """Base class for all Q-Vault OS errors."""


class SecurityError(QVaultError):
    """
    Raised when a security boundary is violated.

    Examples:
      - A module calls a capability-gated method without the token
      - An operation is attempted in LOCKDOWN mode
      - A role check fails
    """


class PermissionDenied(SecurityError):
    """Raised when a role or permission check fails."""


class AuthenticationError(SecurityError):
    """Raised when credentials are invalid or the account is locked."""


class CapabilityViolation(SecurityError):
    """
    Raised when a protected method is called without the correct
    capability token.  The only authorized caller is SecurityAPI.
    """


# ── Standardized message strings ─────────────────────────────
#
#  ALL modules must use these constants instead of free-form strings.
#  This ensures consistent wording in logs, UI, and tests.

MSG_NOT_AUTHENTICATED = "permission denied: not authenticated"
MSG_NOT_PERMITTED     = "operation not permitted"
MSG_NO_SUCH_USER      = "no such user"
MSG_AUTH_FAILURE      = "authentication failure"
MSG_ACCOUNT_LOCKED    = "account locked"
MSG_INVALID_ROLE      = "invalid role"
MSG_LOCKDOWN          = "operation blocked: system is in LOCKDOWN mode"
MSG_DIRECT_ACCESS     = (
    "direct access is forbidden — use system.security_api.SecurityAPI"
)
