# =============================================================
#  system/ui_adapter.py — Q-VAULT OS  |  UI Boundary Adapter
#
#  Responsibilities:
#  - Catch raw PyO3 exceptions from Rust boundary.
#  - Parse strict JSON formatted strings.
#  - Convert into safe Python dictionaries.
#  - GUARANTEE: NEVER crash the UI, NO manual security tracking.
# =============================================================

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _parse_rust_error(exception: Exception) -> Dict[str, Any]:
    """Parse JSON structured strings from Rust exceptions safely."""
    raw_error = str(exception)
    
    # Optional extraction in case PyO3 prefixes the exception class
    try:
        if raw_error.startswith("ValueError: ") or raw_error.startswith("RuntimeError: ") or raw_error.startswith("PermissionError: "):
            json_str = raw_error.split(": ", 1)[1]
        else:
            json_str = raw_error

        # Parse JSON
        parsed = json.loads(json_str)
        code = parsed.get("code", "UNKNOWN_ERROR")
        
        # Enforce global logout on invalid tokens
        if code in ("SESSION_EXPIRED", "INVALID_TOKEN"):
            try:
                from core.system_state import STATE
                STATE.current_user = None
            except Exception as e:
                logger.error(f"Failed to reset global system state: {e}")

        return {
            "type": "error",
            "code": code,
            "message": parsed.get("message", "Unexpected system error"),
            "retry_after": parsed.get("retry_after", 0)
        }
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse Rust Exception JSON: {raw_error}")
        return {
            "type": "error",
            "code": "UNKNOWN_ERROR",
            "message": "Unexpected system error. Raw: " + raw_error[:50],
            "retry_after": 0
        }
    except Exception as e:
        logger.warning(f"Crash fallback on Exception Parsing: {e}")
        return {
            "type": "error",
            "code": "UNKNOWN_ERROR",
            "message": "Unexpected system error",
            "retry_after": 0
        }

def safe_call(func, *args, **kwargs) -> Dict[str, Any]:
    """Safely executes Rust calls returning normalized UI-dict standard format."""
    try:
        val = func(*args, **kwargs)
        if hasattr(val, "keys"):
            pass # already dict?
        return {"success": True, "type": "success", "value": val}
    except Exception as e:
        err_dict = _parse_rust_error(e)
        err_dict["success"] = False
        return err_dict
