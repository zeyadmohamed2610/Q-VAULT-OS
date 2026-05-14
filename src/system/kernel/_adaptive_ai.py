from __future__ import annotations
import json
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .adaptive_scheduler import AdaptiveScheduler
    from ._adaptive_metrics import MetricsSnapshot

logger = logging.getLogger(__name__)

class AdaptiveAIEngine:
    """
    Handles LLM consultation and response parsing for intelligent scheduling.
    """

    @staticmethod
    def consult(scheduler: 'AdaptiveScheduler', snapshot: 'MetricsSnapshot') -> Optional[str]:
        if snapshot.llm_available:
            return AdaptiveAIEngine._ask_llm(scheduler, snapshot)
        return AdaptiveAIEngine._deterministic_fallback(scheduler, snapshot)

    @staticmethod
    def _ask_llm(scheduler: 'AdaptiveScheduler', snapshot: 'MetricsSnapshot') -> Optional[str]:
        try:
            from system.ai.llm_adapter import LLMAdapter
            adapter = LLMAdapter()
            
            prompt = AdaptiveAIEngine._build_prompt(snapshot)
            context = {"domain": "kernel_scheduling", "metrics": snapshot.as_dict()}
            
            response = adapter.process(prompt, context)
            if not response: return None
            
            return AdaptiveAIEngine._parse_response(response, snapshot.algorithm)
        except Exception as e:
            logger.error(f"[ADAPTIVE] LLM Consultation failed: {e}")
            return None

    @staticmethod
    def _deterministic_fallback(scheduler: 'AdaptiveScheduler', snapshot: 'MetricsSnapshot') -> Optional[str]:
        if snapshot.starved_pids: return "FCFS"
        if snapshot.avg_waiting_time > 40: return "SJF"
        return "RR"

    @staticmethod
    def _build_prompt(snapshot: 'MetricsSnapshot') -> str:
        return (
            f"Advisory for Q-Vault OS Kernel. State: {snapshot.as_dict()}\n"
            "Pick best algo (FCFS, SJF, RR, PRIO). Return JSON: {\"algorithm\":\"...\", \"confidence\":0.0-1.0}"
        )

    @staticmethod
    def _parse_response(response: any, current_algo: str) -> Optional[str]:
        try:
            if isinstance(response, str):
                cleaned = response.strip().lstrip("```json").rstrip("```").strip()
                data = json.loads(cleaned)
            else:
                data = response
            
            algo = str(data.get("algorithm", "")).upper()
            if algo in {"FCFS", "SJF", "RR", "PRIO"} and algo != current_algo:
                if float(data.get("confidence", 0.0)) >= 0.5:
                    return algo
            return None
        except:
            return None
