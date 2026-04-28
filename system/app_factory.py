# =============================================================
#  system/app_factory.py — Q-VAULT OS  |  Application Factory
#
#  Responsible for creating application instances with the 
#  correct security wrappers and isolation proxies.
# =============================================================

import importlib
import logging
from typing import Optional, TYPE_CHECKING
from core.app_registry import AppDefinition, REGISTRY, AppStatus

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)

def create_app_instance(
    app_def: AppDefinition,
    parent: Optional["QWidget"] = None
) -> Optional["QWidget"]:
    """
    Dynamically load and instantiate an app widget with security context.
    Ensures 100% UX Consistency by using IsolatedAppWidget proxy for process apps.
    """
    # 1. Resolve Module and Class
    # If module starts with 'components.' or 'apps.', use it as is.
    # Otherwise, default to 'apps.' for backward compatibility.
    module_path = app_def.module
    if not (module_path.startswith("apps.") or module_path.startswith("components.")):
        module_path = f"apps.{module_path}"

    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, app_def.class_name)
    except Exception as e:
        REGISTRY.quarantine(app_def.name, f"Import Error: {e}")
        return None

    # Defer imports to avoid circular dependencies
    from system.sandbox.secure_api import SecureAPI
    from system.runtime.isolated_widget import IsolatedAppWidget

    # 2. Check if the class is already an IsolatedAppWidget subclass
    is_already_isolated = issubclass(cls, IsolatedAppWidget)

    # 3. Handle Process Isolation
    if app_def.isolation_mode == "process" and not is_already_isolated:
        try:
            secure_api = SecureAPI(app_id=app_def.name)
            logger.debug(f"AppFactory: Wrapping {app_def.name} in IsolatedAppWidget")
            widget = IsolatedAppWidget(
                app_id=app_def.name,
                module_path=module_path,
                class_name=app_def.class_name,
                secure_api=secure_api,
                parent=parent
            )
            REGISTRY.set_status(app_def.name, AppStatus.AVAILABLE)
            return widget
        except Exception as e:
            REGISTRY.quarantine(app_def.name, f"Proxy Wrap Error: {e}")
            return None

    # 4. Direct Instantiation (Already isolated or requested direct/thread mode)
    try:
        secure_api = SecureAPI(app_id=app_def.name)
        try:
            widget = cls(secure_api=secure_api, parent=parent)
        except TypeError:
            # Fallback for apps not yet updated to accept secure_api in __init__
            widget = cls(parent=parent)
            if secure_api and not hasattr(widget, "secure_api"):
                widget.secure_api = secure_api

        REGISTRY.set_status(app_def.name, AppStatus.AVAILABLE)
        logger.info("AppFactory: Launched '%s' (Isolation: %s)", app_def.name, app_def.isolation_mode)
        return widget
    except Exception as exc:
        REGISTRY.quarantine(app_def.name, f"Instantiation error: {exc}")
        return None

def create_app_by_name(
    name: str,
    parent: Optional["QWidget"] = None
) -> Optional["QWidget"]:
    """Look up app by name and create instance."""
    app_def = REGISTRY.get_by_name(name)
    if app_def is None:
        logger.warning(f"AppFactory: App '{name}' not found in manifest")
        return None
    return create_app_instance(app_def, parent=parent)
