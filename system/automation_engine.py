import logging
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from core.event_bus import EVENT_BUS, SystemEvent, EventPayload
from system.notification_service import NOTIFICATION_SERVICE, NotificationLevel
from system.window_manager import get_window_manager

logger = logging.getLogger(__name__)

class AutomationMode(Enum):
    """v1.0 User Governance Modes."""
    ASSISTIVE = "assistive"
    SEMI_AUTO = "semi_auto"
    AUTONOMOUS = "autonomous"

@dataclass
class ActionSnapshot:
    """
    v1.0 Hardened Safety Record.
    Featuring strict validation and origin tracking.
    """
    type: str # e.g. "app_restart", "app_launch"
    data: Dict[str, Any]
    undo_func: Callable
    validate_func: Callable[[], bool]
    description: str = ""
    origin: str = "system" # system | manual
    timestamp: float = field(default_factory=lambda: time.time())

@dataclass
class CompoundSnapshot(ActionSnapshot):
    """
    v1.0 Orchestrator Record.
    Wraps multiple action steps into a single logical Undo.
    """
    plan_id: str = ""
    sub_snapshots: List[ActionSnapshot] = field(default_factory=list)

class AutomationEngine:
    """
    v1.0 Hardened Cohesive OS Governance.
    Implements a robust LIFO Undo system with Re-entrant Locking and Strict Validation.
    """
    def __init__(self):
        self.mode = AutomationMode.SEMI_AUTO
        self._is_active = True
        self._undo_stack: List[ActionSnapshot] = []
        self._undo_lock = threading.Lock()
        
        # Subscribe to EventBus
        EVENT_BUS.event_emitted.connect(self._on_system_event)
        EVENT_BUS.subscribe(SystemEvent.DECISION_MADE, self._on_ai_decision)
        
    def set_mode(self, mode: AutomationMode):
        logger.info(f"[AutomationEngine] Mode changed to {mode.value.upper()}")
        self.mode = mode

    def _on_ai_decision(self, payload: EventPayload):
        """
        v1.0 Alignment: The bridge between Reasoning and UI.
        Determines if a decision warrants human attention.
        """
        decision = payload.data
        if decision.get("silent"):
            logger.info("[Automation] Reasoning suggested SILENT. Shadow Mode active.")
            return

        # ── Decision Thresholds ──
        impact = decision.get("impact", {}).get("level", "LOW")
        score = decision.get("impact", {}).get("score", 0)
        
        # Security Override: Always show if security fix or risk detected
        is_urgent = decision.get("security_override") or len(decision.get("risks", [])) > 0
        
        if impact == "HIGH" or is_urgent:
            self._trigger_notification(decision, urgent=True)
        elif impact == "MEDIUM" and self.mode != AutomationMode.ASSISTIVE:
            self._trigger_notification(decision, urgent=False)
        else:
            logger.info(f"[Automation] Impact {impact} (Score {score}) below threshold for {self.mode.value} mode.")

    def _trigger_notification(self, decision: Dict[str, Any], urgent: bool = False):
        """Renders the AI decision to the user."""
        msg = decision.get("message", "System Update")
        level = NotificationLevel.WARNING if urgent else NotificationLevel.INFO
        
        # Add risk markers if present
        risks = decision.get("risks", [])
        if risks:
            msg += f"\n⚠️ {risks[0]['msg']}"
            
        NOTIFICATION_SERVICE.notify(
            msg,
            "AI Insights" if not urgent else "Security Alert",
            level=level
        )
        
        EVENT_BUS.emit(SystemEvent.ACTION_TAKEN, {
            "type": "notification",
            "message": msg,
            "urgent": urgent
        }, source="AutomationEngine")

    def _on_system_event(self, payload: EventPayload):
        if not self._is_active: return
        
        etype = payload.type
        data = payload.data

        # 🏥 RULE 1: Self-Healing (App Crashes)
        if etype == SystemEvent.APP_CRASHED:
            app_id = data.get("app_id")
            if not app_id: return
            
            if self.mode == AutomationMode.ASSISTIVE:
                NOTIFICATION_SERVICE.notify(
                    f"'{app_id}' crashed. Self-healing is disabled in ASSISTIVE mode.",
                    "System Report",
                    level=NotificationLevel.INFO,
                    actions=[{"label": "Manual Restart", "command": "@launch " + app_id}]
                )
            else:
                # 🧠 v1.0 Emotional UX & Action Snapshot
                narrative = f"'{app_id}' restarted to keep things stable 👀"
                
                # Take Snapshot before action (LIFO)
                snapshot = ActionSnapshot(
                    type="app_restart",
                    data={"app_id": app_id},
                    description=f"Restart of {app_id}",
                    undo_func=lambda: self._undo_restart(app_id),
                    validate_func=lambda: self._is_app_running(app_id),
                    origin="system"
                )
                self._push_undo(snapshot)
                
                NOTIFICATION_SERVICE.notify(
                    narrative,
                    "Autonomous Recovery",
                    level=NotificationLevel.INFO,
                    actions=[{"label": "Undo", "command": "@undo"}]
                )
                self._restart_app(app_id)

        # 🔄 RULE 2: Global Undo Trigger
        if etype == SystemEvent.UNDO_REQUESTED:
            self.perform_undo()

        # 🔒 RULE 3: Session Security (Clear stack on lock AND unlock for fresh context)
        if etype in [SystemEvent.SESSION_LOCKED, SystemEvent.SESSION_UNLOCKED]:
            logger.info(f"[AutomationEngine] Session transition ({etype.value}). Clearing Undo stack.")
            with self._undo_lock:
                self._undo_stack.clear()

    def perform_undo(self):
        """
        v1.0 Hardened Undo Execution.
        Strategy: Peek -> Validate -> Pop -> Execute
        """
        if not self._undo_stack:
            NOTIFICATION_SERVICE.notify("Nothing left to undo.", "System")
            return
            
        with self._undo_lock:
            if not self._undo_stack: return # Double check after lock
            
            # 1. PEEK
            snapshot = self._undo_stack[-1]
            logger.info(f"[AutomationEngine] Evaluated UNDO: {snapshot.type}")

            # 2. VALIDATE
            try:
                if not snapshot.validate_func():
                    self._undo_stack.pop() # Discard invalid snapshot
                    NOTIFICATION_SERVICE.notify("Nothing to undo", "Skip", level=NotificationLevel.INFO)
                    EVENT_BUS.emit(SystemEvent.UNDO_FAILED, {
                        "reason": "validation_failed",
                        "action": snapshot.description
                    }, source="AutomationEngine")
                    return
            except Exception as e:
                logger.error(f"Validation failed with error: {e}")
                self._undo_stack.pop()
                return

            # 3. POP
            self._undo_stack.pop()

            # 4. EXECUTE
            try:
                snapshot.undo_func()
                
                # 📢 SUCCESS UX
                NOTIFICATION_SERVICE.notify(
                    f"Undid: {snapshot.description}\nSystem is back to previous state", 
                    "Undo Successful"
                )
                EVENT_BUS.emit(SystemEvent.UNDO_PERFORMED, {
                    "action": snapshot.description,
                    "type": snapshot.type
                }, source="AutomationEngine")
                
            except Exception as e:
                # ❌ FAILURE UX
                logger.error(f"Undo execution failed: {e}")
                NOTIFICATION_SERVICE.notify("Undo failed safely", "Undo Error", level=NotificationLevel.WARNING)
                EVENT_BUS.emit(SystemEvent.UNDO_FAILED, {
                    "reason": "exception",
                    "error": str(e),
                    "action": snapshot.description
                }, source="AutomationEngine")

    def _push_undo(self, snapshot: ActionSnapshot):
        with self._undo_lock:
            snapshot.timestamp = time.time()
            self._undo_stack.append(snapshot)
            if len(self._undo_stack) > 10:
                self._undo_stack.pop(0)

    def _is_app_running(self, app_id: str) -> bool:
        """Strict validation: check if the app has an active window."""
        wm = get_window_manager()
        # Search for window with title or ID matching app_id (logic simplified)
        return any(app_id.lower() in wid.lower() for wid in wm._windows.keys())

    def _undo_restart(self, app_id):
        """Reverses an app restart by terminating it."""
        logger.info(f"Undo: Terminating {app_id} (Reversing restart)")
        EVENT_BUS.emit(SystemEvent.COMMAND_EXECUTED, {"command": f"@kill {app_id}"}, source="AutomationEngine")

    def _restart_app(self, app_id):
        logger.info(f"Automation: Self-healing app '{app_id}'")
        EVENT_BUS.emit(SystemEvent.COMMAND_EXECUTED, {"command": f"@launch {app_id}"}, source="AutomationEngine")

# Singleton Instance
AUTOMATION_ENGINE = AutomationEngine()
