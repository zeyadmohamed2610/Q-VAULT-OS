import logging
import time
import threading
import uuid
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
from system.notification_service import NOTIFICATION_SERVICE, NotificationLevel
from system.config import get_qvault_home
from system.automation_engine import ActionSnapshot, CompoundSnapshot, AUTOMATION_ENGINE

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    command: str
    description: str
    is_visual: bool = True
    delay_ms: Optional[int] = None # If None, uses dynamic logic

@dataclass
class OrchestrationPlan:
    title: str
    steps: List[PlanStep]
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    category: str = "general" # dev | focus | system
    icon: str = "󰒓"
    enabled: bool = True
    pinned: bool = False

class OrchestrationEngine:
    """
    v1.0 System Orchestration Core.
    Featuring Plan Ecosystem management, Telemetry, and Health Scoring.
    """
    def __init__(self):
        self._active_plan: Optional[OrchestrationPlan] = None
        self._execution_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._completed_steps = [] # Track for rollback
        self._lock = threading.Lock()
        
        # Telemetry Persistence
        self._config_dir = Path(get_qvault_home()) / ".config" / "qvault"
        self._stats_path = self._config_dir / "plan_telemetry.json"
        self._stats: Dict[str, Dict] = {} # { plan_id: { success: N, rollback: N, total: N, health: F } }
        self._load_stats()
        
        # Monitor user events for Abort Logic
        EVENT_BUS.event_emitted.connect(self._on_system_event)

    def execute_plan(self, plan: OrchestrationPlan):
        """Entry point for executing a new plan."""
        with self._lock:
            if not plan.enabled:
                logger.warning(f"Plan '{plan.title}' is disabled. Ignoring execution request.")
                return

            if self._active_plan:
                logger.warning(f"Plan '{self._active_plan.title}' already running. Aborting previous.")
                self.abort_current_plan(reason="new_plan_started")

            self._active_plan = plan
            self._stop_event.clear()
            self._completed_steps = []
            
            logger.info(f"Starting Plan: {plan.title} (ID: {plan.plan_id})")
            EVENT_BUS.emit(SystemEvent.PLAN_STARTED, {
                "plan_id": plan.plan_id,
                "title": plan.title,
                "steps_total": len(plan.steps)
            }, source="OrchestrationEngine")
            
            self._execution_thread = threading.Thread(target=self._run_loop, args=(plan,))
            self._execution_thread.daemon = True
            self._execution_thread.start()

    def _run_loop(self, plan: OrchestrationPlan):
        compound_snapshot = CompoundSnapshot(
            type="orchestration_plan",
            data={"plan_id": plan.plan_id},
            description=plan.title,
            undo_func=lambda: self._execute_rollback(list(reversed(self._completed_steps))),
            validate_func=lambda: True,
            sub_snapshots=[],
            plan_id=plan.plan_id
        )

        for i, step in enumerate(plan.steps):
            if self._stop_event.is_set():
                self._record_outcome(plan.plan_id, "aborted")
                return

            # Dynamic Delay logic
            delay = step.delay_ms if step.delay_ms is not None else (400 if step.is_visual else 150)
            time.sleep(delay / 1000.0)

            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.command}")
            try:
                EVENT_BUS.emit(SystemEvent.COMMAND_EXECUTED, {"command": step.command}, source="OrchestrationEngine")
                self._completed_steps.append(step)
                
                EVENT_BUS.emit(SystemEvent.PLAN_STEP_COMPLETED, {
                    "plan_id": plan.plan_id,
                    "step_index": i,
                    "description": step.description
                }, source="OrchestrationEngine")
            except Exception as e:
                self._handle_failure(plan, e)
                return

        # Success Finalization
        AUTOMATION_ENGINE._push_undo(compound_snapshot)
        self._record_outcome(plan.plan_id, "success")
        EVENT_BUS.emit(SystemEvent.PLAN_COMPLETED, {"plan_id": plan.plan_id}, source="OrchestrationEngine")
        
        with self._lock:
            self._active_plan = None

    def _handle_failure(self, plan: OrchestrationPlan, error: Exception):
        logger.warning(f"Plan {plan.plan_id} failed. Atomic Rollback triggered.")
        self._record_outcome(plan.plan_id, f"failed: {str(error)}")
        
        EVENT_BUS.emit(SystemEvent.PLAN_FAILED, {
            "plan_id": plan.plan_id,
            "error": str(error)
        }, source="OrchestrationEngine")
        
        self._execute_rollback(list(reversed(self._completed_steps)))
        
        NOTIFICATION_SERVICE.notify(
            f"Plan '{plan.title}' interrupted — rolled back safely 🛡️",
            "Orchestration Safety",
            level=NotificationLevel.WARNING
        )
        with self._lock:
            self._active_plan = None

    def _execute_rollback(self, steps_to_undo: List[PlanStep]):
        for step in steps_to_undo:
            if "@launch" in step.command:
                app_id = step.command.split()[-1]
                EVENT_BUS.emit(SystemEvent.COMMAND_EXECUTED, {"command": f"@kill {app_id}"}, source="OrchestrationEngine")
            time.sleep(0.1)

    def _on_system_event(self, payload: EventPayload):
        if not self._active_plan: return
        if payload.type in [SystemEvent.WINDOW_CLOSED, SystemEvent.SESSION_LOCKED]:
            if payload.source != "OrchestrationEngine":
                self.abort_current_plan(reason="user_interruption")

    def abort_current_plan(self, reason: str = "aborted"):
        self._stop_event.set()
        if self._active_plan:
            self._record_outcome(self._active_plan.plan_id, f"aborted: {reason}")
            EVENT_BUS.emit(SystemEvent.PLAN_ABORTED, {
                "plan_id": self._active_plan.plan_id,
                "reason": reason
            }, source="OrchestrationEngine")
            self._execute_rollback(list(reversed(self._completed_steps)))
            with self._lock:
                self._active_plan = None

    def _record_outcome(self, plan_id: str, outcome: str):
        """Telemetric data collection."""
        if plan_id not in self._stats:
            self._stats[plan_id] = {"success": 0, "rollback": 0, "total": 0, "last_error": None, "last_executed_at": 0}
        
        s = self._stats[plan_id]
        s["total"] += 1
        s["last_executed_at"] = time.time()
        
        if outcome == "success":
            s["success"] += 1
        else:
            s["rollback"] += 1
            s["last_error"] = outcome

        # Calculate Health Score: success_rate - (rollback_rate * 0.5)
        success_rate = s["success"] / s["total"]
        rollback_rate = s["rollback"] / s["total"]
        s["health"] = round(success_rate - (rollback_rate * 0.5), 2)
        
        self._save_stats()
        EVENT_BUS.emit(SystemEvent.PLAN_STATS_UPDATED, {"plan_id": plan_id, "stats": s}, source="OrchestrationEngine")

    def _load_stats(self):
        if not self._stats_path.exists(): return
        try:
            with open(self._stats_path, "r") as f:
                self._stats = json.load(f)
        except Exception: pass

    def _save_stats(self):
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._stats_path, "w") as f:
                json.dump(self._stats, f, indent=2)
        except Exception as e:
            logger.error(f"Telemetry: Save failed: {e}")

    def get_plan_health(self, plan_id: str) -> float:
        return self._stats.get(plan_id, {}).get("health", 1.0)

# Singleton
ORCHESTRATION_ENGINE = OrchestrationEngine()
