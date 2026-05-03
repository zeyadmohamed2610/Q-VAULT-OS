import logging
import time
from typing import Dict, Any, List, Optional
from core.event_bus import EVENT_BUS, SystemEvent
from .context_builder import ContextBuilder
from .action_translator import ActionTranslator
from .validator import AIActionValidator
from .reasoning_engine import ReasoningEngine
from .memory_store import MemoryStore
from .llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

class AIController:
    """
    Advanced AI Orchestrator.
    Handles complex planning, memory retrieval, and sequential execution.
    """
    def __init__(self):
        self.context = ContextBuilder()
        self.validator = AIActionValidator()
        self.translator = ActionTranslator()
        self.reasoner = ReasoningEngine()
        self.memory = MemoryStore()
        self.llm = LLMAdapter()
        
        self._action_queue: List[Dict[str, Any]] = []
        
        # ── Subscriptions ──
        EVENT_BUS.subscribe(SystemEvent.REQ_USER_INPUT, self._process_request)
        EVENT_BUS.subscribe(SystemEvent.EVT_ERROR, self._handle_anomaly)
        EVENT_BUS.subscribe(SystemEvent.APP_LAUNCHED, lambda p: self.memory.record_app_launch(p.data.get("module", "unknown")))
        
        logger.info("[AI_CONTROLLER] Intelligence Engine v3.0 (Multi-Step) Active.")

    def _process_request(self, payload):
        """Main entry point for AI reasoning."""
        prompt = payload.data.get("text", "").strip().lower()
        if not prompt: return

        self.memory.record_intent(prompt)
        logger.info(f"[AI_CONTROLLER] Reasoning about: '{prompt}'")

        # ── 1. Plan Generation (Reasoning Step) ──
        # Try LLM first, fallback to Reasoner, fallback to simple intent
        plan = self.llm.process(prompt, self.context.get_full_context())
        
        if not plan:
            plan = self.reasoner.plan(prompt)
        
        EVENT_BUS.emit(SystemEvent.EVT_AI_THINKING_START, {"prompt": prompt}, source="AI_Controller")

        try:
            # ── 1. Plan Generation (Reasoning Step) ──
            plan = self.llm.process(prompt, self.context.get_full_context())
            if not plan:
                plan = self.reasoner.plan(prompt)
            if not plan:
                simple_intent = self._parse_simple_intent(prompt)
                plan = [simple_intent] if simple_intent else []

            if not plan:
                logger.info(f"[AI_CONTROLLER] No plan generated for: '{prompt}'")
                EVENT_BUS.emit(SystemEvent.EVT_AI_UNKNOWN_INTENT, {"prompt": prompt}, source="AI_Controller")
                return

            # ── 2. Sequential Execution ──
            self._execute_plan(plan, prompt)
        finally:
            EVENT_BUS.emit(SystemEvent.EVT_AI_THINKING_STOP, source="AI_Controller")

    def _execute_plan(self, plan: List[Dict[str, Any]], original_prompt: str):
        """Executes a chain of actions with safety checks."""
        logger.info(f"[AI_CONTROLLER] Executing plan with {len(plan)} steps.")
        
        for i, step in enumerate(plan):
            action = step.get("action")
            params = step.get("params", {})
            
            # Validation (with chain context for loop prevention)
            is_safe, reasoning = self.validator.validate(action, params, is_chain=(i > 0))
            
            if not is_safe:
                logger.warning(f"[AI_CONTROLLER] Step {i} rejected: {reasoning}")
                EVENT_BUS.emit(SystemEvent.EVT_AI_REJECTED_ACTION, {
                    "step": i,
                    "action": action,
                    "reasoning": reasoning
                }, source="AI_Controller")
                break # Stop execution on failure
            
            # Execute
            EVENT_BUS.emit(SystemEvent.EVT_AI_DECISION, {
                "step": i,
                "action": action,
                "params": params,
                "total_steps": len(plan)
            }, source="AI_Controller")
            
            self.translator.execute_action(action, params)
            
            # Artificial delay between steps for visual feedback and rate limiting
            if i < len(plan) - 1:
                time.sleep(0.3)

    def _parse_simple_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Legacy deterministic matching for single actions."""
        if text.startswith("open "):
            app = text.replace("open ", "").strip().title()
            return {"action": "launch", "params": {"app": app}}
            
        if text in ["close", "exit", "close window"]:
            active_id = self.context.get_active_window()
            return {"action": "close", "params": {"id": active_id}}
            
        if "status" in text or "health" in text:
            summary = self.context.get_context_summary()
            return {"action": "notify", "params": {"message": summary, "title": "System Health"}}

        # Workflow execution intent (Phase 7)
        if text.startswith("run workflow ") or text.startswith("execute "):
            wf_name = text.replace("run workflow ", "").replace("execute ", "").strip().lower().replace(" ", "_")
            return {"action": "workflow", "params": {"name": wf_name}}

        return None

    def _handle_anomaly(self, payload):
        """Proactive response to system errors."""
        err_data = payload.data
        if err_data.get("type") == "handler_exception":
            self.translator.execute_action("notify", {
                "title": "Stability Alert",
                "message": f"I've detected a system anomaly. Monitoring for recurrences.",
                "level": "error"
            })
