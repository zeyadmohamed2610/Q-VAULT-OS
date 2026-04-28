# =============================================================
#  system/ai/reasoning_engine.py — Q-Vault OS
#
#  AI Planning & Multi-step Reasoning.
#  Converts complex intents into sequential action chains.
# =============================================================

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """
    Decomposes high-level requests into atomic execution steps.
    Supports complex workflows like 'Prepare workspace'.
    """
    
    # Predefined Workflow Templates (Rule-based reasoning v1)
    WORKFLOWS = {
        "prepare workspace": [
            {"action": "launch", "params": {"app": "Files"}},
            {"action": "launch", "params": {"app": "Terminal"}},
            {"action": "notify", "params": {"message": "Workspace is ready.", "title": "AI Assistant"}}
        ],
        "panic": [
            {"action": "notify", "params": {"message": "Stabilizing system...", "level": "warning"}},
            {"action": "close", "params": {"id": "all"}}, # Placeholder for mass close
            {"action": "notify", "params": {"message": "All non-essential windows closed."}}
        ],
        "cleanup": [
             {"action": "notify", "params": {"message": "Starting cleanup sequence..."}},
             {"action": "close", "params": {"id": "active"}} # Placeholder for focused
        ]
    }

    def plan(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyzes text and returns a sequence of structured actions.
        """
        text = text.lower().strip()
        
        # 1. Direct Workflow Match
        for trigger, steps in self.WORKFLOWS.items():
            if trigger in text:
                logger.info(f"[REASONING] Workflow matched: '{trigger}'")
                return steps

        # 2. Heuristic Decomposition (Simple chaining)
        # Example: "Open Files and then open Terminal"
        actions = []
        if " and " in text or " then " in text:
            parts = text.replace("then", "and").split("and")
            for part in parts:
                # We reuse the basic intent parsing logic here or defer to controller
                # For now, let's just mark it as multi-step
                pass
                
        return [] # Return empty if no complex plan is found
