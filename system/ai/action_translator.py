# =============================================================
#  system/ai/action_translator.py — Q-Vault OS
#
#  AI Action Dispatcher. Converts logical AI decisions into
#  standardized SystemEvent requests.
# =============================================================

import logging
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

class ActionTranslator:
    """
    Decouples AI reasoning from EventBus syntax.
    """
    @staticmethod
    def execute_action(action_type: str, params: dict = None):
        """
        Translates a logical action (e.g. 'launch') into 
        a system request (e.g. REQ_APP_LAUNCH).
        """
        params = params or {}
        logger.info(f"[AI_ACTION] Translating: {action_type} with {params}")
        
        if action_type == "launch":
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": params.get("app")}, source="AI_Action_Translator")
        
        elif action_type == "close":
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE, {"id": params.get("id")}, source="AI_Action_Translator")
            
        elif action_type == "notify":
            EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, {
                "title": params.get("title", "AI Assistant"),
                "message": params.get("message", ""),
                "level": params.get("level", "info")
            }, source="AI_Action_Translator")
            
        elif action_type == "focus":
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_FOCUS, {"id": params.get("id")}, source="AI_Action_Translator")
        
        elif action_type == "workflow":
            from system.automation.workflow_engine import WORKFLOW_ENGINE
            WORKFLOW_ENGINE.execute_workflow(params.get("name"))
        
        else:
            logger.warning(f"[AI_ACTION] Unknown action type: {action_type}")
