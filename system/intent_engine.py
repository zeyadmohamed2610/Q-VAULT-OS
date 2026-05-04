import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
from system.notification_service import NOTIFICATION_SERVICE, NotificationLevel
from system.orchestration_engine import OrchestrationPlan, ORCHESTRATION_ENGINE
from system.plan_registry import PLAN_REGISTRY
from system.automation_engine import AUTOMATION_ENGINE, AutomationMode

logger = logging.getLogger(__name__)

@dataclass
class PatternMetadata:
    """v1.0 Judgment Metadata with Recency & Preference."""
    count: int = 0
    accept_count: int = 0
    reject_count: int = 0
    last_suggested: float = 0
    last_used_at: float = 0
    preference_weight: float = 1.0 # v1.0 User Preference learning
    cooldown_until: float = 0 # v1.0 Penalty Logic
    is_pinned: bool = False
    is_ignored: bool = False
    stability_score: float = 0.0

class IntentEngine:
    """
    v1.0 Personality-Aware Decision Engine.
    Features: Stability Dampening (Hysteresis), Continuity Boost, Personality Scaling.
    """
    def __init__(self):
        self._session_graph: List[EventPayload] = []
        self._max_graph_size = 30
        self._patterns: Dict[str, PatternMetadata] = {}
        self._active_suggestions: Dict[str, Dict] = {}
        self._last_winner_id: Optional[str] = None # v1.0 Hysteresis anchor
        
        # Calibration Parameters (Base)
        self.HALF_LIFE_RECENCY = 6 * 3600
        self.UNDO_PENALTY_BASE = 0.4
        self.COOLDOWN_DURATION = 30 * 60
        
        # Friction Gates
        self.LEVEL_SILENT  = 0.6
        self.LEVEL_SUGGEST = 0.8
        
        self._cooldown_period = 600
        EVENT_BUS.event_emitted.connect(self._on_any_event)
        
    def _on_any_event(self, payload: EventPayload):
        self._session_graph.append(payload)
        if len(self._session_graph) > self._max_graph_size: self._session_graph.pop(0)
            
        if payload.type == SystemEvent.SESSION_LOCKED:
            self._session_graph = []
            self._last_winner_id = None # Session soft reset
            return
            
        if payload.type in [SystemEvent.APP_LAUNCHED, SystemEvent.WINDOW_FOCUSED]:
            self._analyze_intent()
            
        if payload.type == SystemEvent.ACTION_CLICKED:
            self._handle_action_feedback(payload)

        # v1.0/2.3 Penalty Loop
        if payload.type == SystemEvent.UNDO_REQUESTED:
            self._apply_undo_penalty()

    def _analyze_intent(self):
        recent_apps = [p.data.get("app_id") for p in self._session_graph if p.type == SystemEvent.APP_LAUNCHED]
        if not recent_apps: return
        
        candidates = []

        if "terminal" in recent_apps and "files" not in recent_apps:
            candidates.append(("dev_workspace_plan", PLAN_REGISTRY.get_template("dev_setup")))
        
        if len(self._session_graph) > 15:
            candidates.append(("focus_trigger", PLAN_REGISTRY.get_template("focus_mode")))

        if not candidates: return

        # 1. Ranking Competition (v1.0)
        ranked = []
        for p_id, plan in candidates:
            if not plan: continue
            score, breakdown = self._rank_candidate(p_id, plan)
            ranked.append({"id": p_id, "plan": plan, "score": score, "breakdown": breakdown})

        ranked.sort(key=lambda x: x["score"], reverse=True)
        if not ranked: return

        # 2. Stability Dampening (Hysteresis 0.05)
        top = ranked[0]
        if self._last_winner_id and self._last_winner_id != top["id"]:
            prev_winner = next((r for r in ranked if r["id"] == self._last_winner_id), None)
            if prev_winner and (top["score"] - prev_winner["score"] < 0.05):
                top = prev_winner # Dampen flickering
        
        self._last_winner_id = top["id"]

        # Global floor check
        if top["score"] < 0.65: return 

        # 3. Selection Strategy
        others = [r for r in ranked[1:] if abs(top["score"] - r["score"]) < 0.03]
        self._process_selection(top, others[0] if others else None)

    def _rank_candidate(self, p_id: str, plan: OrchestrationPlan) -> (float, str):
        if p_id not in self._patterns: self._patterns[p_id] = PatternMetadata()
        p = self._patterns[p_id]
        
        from system.personality_manager import PERSONALITY_MANAGER
        from system.context_engine import CONTEXT_ENGINE
        from system.sequence_engine import SEQUENCE_ENGINE
        
        conf_score, conf_br = self._calculate_confidence(p_id)
        health = ORCHESTRATION_ENGINE.get_plan_health(plan.plan_id)
        
        stats = ORCHESTRATION_ENGINE._stats.get(plan.plan_id, {})
        last_used = stats.get("last_executed_at", 0)
        elapsed = time.time() - last_used if last_used > 0 else (10 * self.HALF_LIFE_RECENCY)
        recency = 0.5 ** (elapsed / self.HALF_LIFE_RECENCY)
        
        pref = p.preference_weight
        
        # v1.0/2.5 Situational Context Factor (20%)
        ctx_score, ctx_br, is_learned = CONTEXT_ENGINE.get_context_score(p_id, plan.category)
        
        # v1.0 Preemptive Intelligence (Sequence Boost)
        pred_boost = 0.0
        is_predicted = False
        # Gate: Only predict if STABLE and not in transition
        if CONTEXT_ENGINE.pending_intent is None:
            pred_id, pred_conf, pred_status = SEQUENCE_ENGINE.get_prediction()
            if pred_id == p_id and pred_status == "READY":
                pred_boost = 0.15
                is_predicted = True
                # Notify made (only once per window)
                if time.time() - SEQUENCE_ENGINE.last_suggestion_time > 30:
                    SEQUENCE_ENGINE.notify_suggestion_made(p_id)
        
        # v1.0 Dynamic Continuity Boost
        boost = PERSONALITY_MANAGER.get_continuity_boost(p_id, plan.category)
        
        # v1.0 Master Formula (Base + Context + Sequence + Personality)
        score = (conf_score * 0.3) + (health * 0.25) + (recency * 0.15) + (pref * 0.1) + (ctx_score * 0.2) + boost + pred_boost
        
        if time.time() < p.cooldown_until: score *= 0.1

        learned_pre = "⭐ LEARNED: " if is_learned else ""
        pred_pre = "🔮 PREDICTED: " if is_predicted else ""
        br = f"Conf: {conf_score:.2f} | Health: {health:.2f} | Rec: {recency:.2f} | Context: {ctx_score:.2f} | Pred: +{pred_boost:.2f} | Boost: +{boost:.2f}\nSits: {learned_pre}{pred_pre}{ctx_br}"
        return score, br

    def _process_selection(self, top: dict, second: Optional[dict]):
        p_id = top["id"]
        plan = top["plan"]
        score = top["score"]
        
        from system.personality_manager import PERSONALITY_MANAGER
        
        # v1.0 Personality-Driven Thresholds
        auto_threshold = PERSONALITY_MANAGER.get_thresholds(plan.category)

        if score >= auto_threshold and AUTOMATION_ENGINE.mode == AutomationMode.AUTONOMOUS:
            self._execute_plan_auto(plan)
            return

        # Notification cooldown
        if time.time() - self._patterns[p_id].last_suggested >= self._cooldown_period:
            msg = f"Personality: {PERSONALITY_MANAGER.mode.value.upper()} | {top['breakdown']}"
            if second: msg += f"\nAlt Possible: '{second['plan'].title}' (Score: {second['score']:.2f})"
            self._suggest_plan(p_id, plan, score, msg)

    def _apply_undo_penalty(self):
        from system.personality_manager import PERSONALITY_MANAGER
        now = time.time()
        # Scale penalty by personality mode
        penalty_val = self.UNDO_PENALTY_BASE * PERSONALITY_MANAGER.get_penalty_mod()
        
        for p_id, p_meta in self._patterns.items():
            if now - p_meta.last_suggested < 60:
                logger.warning(f"Undo penalty (scalar {penalty_val:.2f}) applied to {p_id}")
                p_meta.preference_weight = max(0.0, p_meta.preference_weight - penalty_val)
                p_meta.cooldown_until = now + self.COOLDOWN_DURATION
                break

    def _suggest_plan(self, pattern_id: str, plan: OrchestrationPlan, confidence: float, breakdown: str):
        suggestion_id = str(uuid.uuid4())
        self._active_suggestions[suggestion_id] = {"pattern_id": pattern_id, "timestamp": time.time(), "plan": plan}
        
        p = self._patterns[pattern_id]
        p.last_suggested = time.time()
        p.count += 1
        
        steps_summary = "\n".join([f"• {s.description}" for s in plan.steps])
        narrative = f"{plan.goal}\n\n{steps_summary}\n\n📊 Judgment Score: {int(confidence*100)}%"
        
        NOTIFICATION_SERVICE.notify(
            narrative,
            f"Smart Workflow: {plan.title}",
            level=NotificationLevel.INFO,
            actions=[
                {"label": "Execute", "command": f"@execute_plan {suggestion_id}"},
                {"label": "Ignore", "command": f"@ignore_pattern {pattern_id}"}
            ]
        )
        EVENT_BUS.emit(SystemEvent.PLAN_STATS_UPDATED, {"id": pattern_id, "judgment": breakdown}, source="IntentEngine")

    def _handle_action_feedback(self, payload):
        sid = payload.data.get("suggestion_id")
        if sid in self._active_suggestions:
            self._handle_feedback(sid, accepted=True)

    def _calculate_confidence(self, pattern_id: str):
        p = self._patterns.get(pattern_id, PatternMetadata())
        f_weight = min(1.0, p.count / 5.0)
        s_weight = 1.0 
        total_feedback = p.accept_count + p.reject_count
        a_weight = (p.accept_count / total_feedback) if total_feedback > 0 else 0.5
        confidence = (0.5 * f_weight) + (0.3 * s_weight) + (0.2 * a_weight)
        return confidence, f"Freq: {f_weight:.1f}, Context: {s_weight:.1f}, Trust: {a_weight:.1f}"

    def _execute_plan_auto(self, plan: OrchestrationPlan):
        ORCHESTRATION_ENGINE.execute_plan(plan)

    def _handle_feedback(self, suggestion_id: str, accepted: bool):
        data = self._active_suggestions.pop(suggestion_id, None)
        if not data: return
        p = self._patterns[data["pattern_id"]]
        if accepted:
            p.accept_count += 1
            p.preference_weight = min(2.0, p.preference_weight + 0.1)
        else:
            p.reject_count += 1
            p.preference_weight = max(0.0, p.preference_weight - 0.1)

    def ignore_pattern(self, pattern_id: str):
        if pattern_id in self._patterns:
            self._patterns[pattern_id].is_ignored = True

# Singleton
INTENT_ENGINE = IntentEngine()
