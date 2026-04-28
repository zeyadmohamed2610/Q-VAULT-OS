# =============================================================
#  system/automation/workflow_engine.py — Q-Vault OS
#
#  System Automation & Workflow Orchestrator.
#  Executes complex action sequences triggered by system events.
# =============================================================

import logging
import time
from typing import Dict, Any, List
from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    State-aware Automation Engine.
    Listens for triggers and orchestrates multi-step responses.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkflowEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
        
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._active_executions: List[str] = []
        
        # Internal registry for triggers
        self._event_triggers: Dict[str, List[str]] = {}
        
        EVENT_BUS.subscribe(SystemEvent.REQ_WORKFLOW_LIST, self._list_workflows)
        EVENT_BUS.subscribe(SystemEvent.REQ_WORKFLOW_EXECUTE, lambda p: self.execute_workflow(p.data.get("name")))
        
        logger.info("[WORKFLOW_ENGINE] Automation Layer Active.")

    def _list_workflows(self, payload):
        """Broadcasts all available workflow names."""
        names = list(self._workflows.keys())
        EVENT_BUS.emit(SystemEvent.EVT_WORKFLOW_LIST, {"workflows": names}, source="WorkflowEngine")

    def register_workflow(self, workflow: Dict[str, Any]):
        """
        Registers a JSON-based workflow definition.
        Example:
        {
            "name": "on_error_notify",
            "trigger": "sys.error",
            "actions": [
                {"action": "notify", "params": {"message": "An error occurred!", "level": "error"}}
            ]
        }
        """
        name = workflow.get("name")
        trigger = workflow.get("trigger")
        
        if not name or not trigger:
            logger.error(f"[WORKFLOW_ENGINE] Invalid workflow definition: {name}")
            return
            
        self._workflows[name] = workflow
        
        # Hook trigger to EventBus
        if trigger not in self._event_triggers:
            self._event_triggers[trigger] = []
            # We subscribe once per unique trigger type
            EVENT_BUS.subscribe(trigger, lambda p: self._on_trigger_event(trigger, p))
            
        self._event_triggers[trigger].append(name)
        logger.info(f"[WORKFLOW_ENGINE] Registered workflow '{name}' on trigger '{trigger}'")

    def _on_trigger_event(self, trigger_name: str, payload: Any):
        """Reaction to observed system events."""
        workflows_to_run = self._event_triggers.get(trigger_name, [])
        for w_name in workflows_to_run:
            self.execute_workflow(w_name, context=payload.data)

    def execute_workflow(self, name: str, context: Dict[str, Any] = None):
        """Sequential execution of a workflow."""
        if name not in self._workflows:
            logger.error(f"[WORKFLOW_ENGINE] Workflow '{name}' not found.")
            return

        workflow = self._workflows[name]
        actions = workflow.get("actions", [])
        
        logger.info(f"[WORKFLOW_ENGINE] Starting workflow: {name}")
        EVENT_BUS.emit(SystemEvent.EVT_WORKFLOW_STARTED, {"name": name}, source="WorkflowEngine")
        
        for i, step in enumerate(actions):
            action_type = step.get("action")
            params = step.get("params", {}).copy()
            
            # Context Injection (e.g. inject error message from trigger into notification)
            if context:
                # Simple placeholder replacement logic can go here
                pass
                
            logger.debug(f"[WORKFLOW_ENGINE] [{name}] Step {i}: {action_type}")
            EVENT_BUS.emit(SystemEvent.EVT_WORKFLOW_STEP, {
                "workflow": name,
                "step": i,
                "action": action_type
            }, source="WorkflowEngine")
            
            # Emit Request to the system
            # We don't call managers; we just BROADCAST the intent.
            # The AI Controller or System Managers will handle it.
            # For automation, we usually map to REQ events.
            self._dispatch_action(action_type, params)
            
            # Delay between steps for stability
            time.sleep(0.1)
            
        EVENT_BUS.emit(SystemEvent.EVT_WORKFLOW_COMPLETED, {"name": name}, source="WorkflowEngine")
        logger.info(f"[WORKFLOW_ENGINE] Workflow '{name}' completed successfully.")

    def _dispatch_action(self, action_type: str, params: Dict[str, Any]):
        """Converts logical action to EventBus emission."""
        # This mirrors ActionTranslator logic but for automation layer
        # In a real system, they might share a common 'SystemIntentAPI'
        if action_type == "launch":
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": params.get("app")}, source="WorkflowEngine")
        elif action_type == "notify":
            EVENT_BUS.emit(SystemEvent.NOTIFICATION_SENT, params, source="WorkflowEngine")
        elif action_type == "close":
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_CLOSE, params, source="WorkflowEngine")
        else:
             # Generic emission support for raw REQ events
             EVENT_BUS.emit(action_type, params, source="WorkflowEngine")

# Global Instance
WORKFLOW_ENGINE = WorkflowEngine()
