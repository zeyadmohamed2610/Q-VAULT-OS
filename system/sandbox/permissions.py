import logging
import json
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("sandbox.permissions")

# ─── ENFORCEMENT LEVEL ────────────────────────────────────────────────────────
# observation  -> log only, never block (Phase 5.5-A)
# controlled   -> log + replace with safe alternative; block ONLY if no safe alt (Phase 5.5-B)
# strict       -> log + hard block immediately (Phase 5.5-C, future)
ENFORCEMENT_LEVEL: str = "strict"


class PermissionViolation(Exception):
    """Raised when an app violates policy and no safe alternative exists."""
    pass


class PermissionManager:
    """
    The Gatekeeper: loads manifests and checks permissions for App IDs.
    Supports caching and default-deny architecture.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    # ── Manifest loading ──────────────────────────────────────────────────────

    def _load_manifest(self, app_id: str) -> Dict[str, Any]:
        if app_id in self._cache:
            return self._cache[app_id]

        manifest_path = Path(f"apps/{app_id}/manifest.json")
        if not manifest_path.exists():
            logger.debug(
                "[PermissionManager] No manifest for '%s'. Default DENY applied.", app_id
            )
            self._cache[app_id] = {"permissions": {}}
            return self._cache[app_id]

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            self._cache[app_id] = manifest
            return manifest
        except Exception as exc:
            logger.error("[PermissionManager] Bad manifest for '%s': %s", app_id, exc)
            self._cache[app_id] = {"permissions": {}}
            return self._cache[app_id]

    # ── Public check API ──────────────────────────────────────────────────────

    def check(self, app_id: str, action: str, resource: str = "*") -> bool:
        """
        Decide whether `app_id` may perform `action` on `resource`.

        Returns
        -------
        True  -> allowed (either by policy or by observation/controlled pass-through)
        False -> hard-denied (only in strict mode)
        Raises PermissionViolation in controlled mode when no safe alternative.
        """
        manifest = self._load_manifest(app_id)
        perms = manifest.get("permissions", {})

        is_allowed = self._evaluate(action, perms)

        if not is_allowed:
            self._on_violation(app_id, action, resource)

        return True   # controlled/observation always returns True; exception raised inside if needed

    def _evaluate(self, action: str, perms: Dict[str, Any]) -> bool:
        """Pure policy evaluation — no side effects."""
        mapping = {
            "file_access":    ("file_access",    ["virtual_only", "user_home", "allowed"]),
            "network_access": ("network_access",  ["local_only", "wan",        "allowed"]),
            "system_calls":   ("system_calls",    ["allowed"]),
        }
        if action not in mapping:
            return False
        key, allowed_vals = mapping[action]
        level = perms.get(key, "DENIED")
        return level in allowed_vals

    def _on_violation(self, app_id: str, action: str, resource: str) -> None:
        msg = (
            f"[SANDBOX VIOLATION] App='{app_id}' Action='{action}' Resource='{resource}'"
        )

        if ENFORCEMENT_LEVEL == "observation":
            logger.warning(msg + " -> OBSERVATION: passing through.")

        elif ENFORCEMENT_LEVEL == "controlled":
            logger.warning(msg + " -> CONTROLLED: passing to safe handler.")
            # Caller decides whether a safe alternative exists.
            # If not, caller must raise PermissionViolation itself.

        elif ENFORCEMENT_LEVEL == "strict":
            logger.critical(msg + " -> STRICT: HARD BLOCK.")
            raise PermissionViolation(msg)


# ── Singleton ─────────────────────────────────────────────────────────────────
PM_GUARD = PermissionManager()
