# =============================================================
#  core/user_manager.py — COMPATIBILITY SHIM
#
#  The real implementation lives in system/session_manager.py.
#  This file re-exports the symbols that other modules import
#  so nothing breaks:
#
#    from core.user_manager import UM   ← still works
# =============================================================

from system.session_manager import SESSION, SessionUser as User, UM_SHIM as UM

__all__ = ["UM", "User", "SESSION"]
