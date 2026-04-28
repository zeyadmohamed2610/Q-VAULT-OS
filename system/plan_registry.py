import logging
from typing import List, Dict, Optional
from system.orchestration_engine import OrchestrationPlan, PlanStep

logger = logging.getLogger(__name__)

class PlanRegistry:
    """
    v2.1 Central Catalog for System Plans.
    Manages Plan Templates with category-based governance.
    """
    def __init__(self):
        self._templates: Dict[str, OrchestrationPlan] = {}
        self._load_defaults()

    def _load_defaults(self):
        # 💻 DEV CATEGORY (Threshold: 0.80)
        self.register(OrchestrationPlan(
            plan_id="dev_setup",
            title="Dev Workspace Setup",
            goal="Prepare environment for coding",
            category="dev",
            icon="󰅩",
            steps=[
                PlanStep(command="@launch files", description="Open File Explorer"),
                PlanStep(command="@launch browser", description="Open Documentation"),
                PlanStep(command="@tile_windows", description="Arrange Layout")
            ]
        ))

        self.register(OrchestrationPlan(
            plan_id="git_workflow",
            title="Git Workflow",
            goal="Sync changes with repository",
            category="dev",
            icon="󰊢",
            steps=[
                PlanStep(command="@launch terminal --arg 'git status'", description="Check Git Status"),
                PlanStep(command="@launch browser --arg 'github.com'", description="Visit GitHub")
            ]
        ))

        self.register(OrchestrationPlan(
            plan_id="debug_session",
            title="Debug Session",
            goal="Trace and fix system issues",
            category="dev",
            icon="󰃤",
            steps=[
                PlanStep(command="@launch terminal", description="Open Debug Logs", is_visual=True),
                PlanStep(command="@launch system_monitor", description="Monitor Resources", is_visual=True)
            ]
        ))

        # 🧠 FOCUS CATEGORY (Threshold: 0.85)
        self.register(OrchestrationPlan(
            plan_id="focus_mode",
            title="Focus Mode",
            goal="Minimize distractions",
            category="focus",
            icon="󰚌",
            steps=[
                PlanStep(command="@set_dnd on", description="Enable Do Not Disturb", is_visual=False),
                PlanStep(command="@kill browser", description="Close non-essential tabs")
            ]
        ))

        self.register(OrchestrationPlan(
            plan_id="deep_work",
            title="Deep Work Session",
            goal="Max concentration on single task",
            category="focus",
            icon="󰔟",
            steps=[
                PlanStep(command="@set_dnd on", description="Silence System", is_visual=False),
                PlanStep(command="@kill slack", description="Close communication apps"),
                PlanStep(command="@launch browser --arg 'music.youtube.com'", description="Play Lofi Beats")
            ]
        ))

        # 🛡️ SYSTEM CATEGORY (Threshold: 0.95)
        self.register(OrchestrationPlan(
            plan_id="cleanup_session",
            title="System Cleanup",
            goal="Free up leaked resources",
            category="system",
            icon="󰃢",
            steps=[
                PlanStep(command="@kill idle_apps", description="Close unused applications"),
                PlanStep(command="@restart ui_engine", description="Refresh GUI state", is_visual=False)
            ]
        ))

        self.register(OrchestrationPlan(
            plan_id="recovery_mode",
            title="Emergency Recovery",
            goal="Restore OS from inconsistent state",
            category="system",
            icon="󰁯",
            steps=[
                PlanStep(command="@undo", description="Reverse latest critical action"),
                PlanStep(command="@restart all", description="Re-initialize OS services", is_visual=False)
            ]
        ))

    def register(self, plan: OrchestrationPlan):
        self._templates[plan.plan_id] = plan
        logger.info(f"PlanRegistry: Registered {plan.title} [{plan.category}]")

    def get_template(self, plan_id: str) -> Optional[OrchestrationPlan]:
        return self._templates.get(plan_id)

    def get_all(self) -> List[OrchestrationPlan]:
        return list(self._templates.values())

    def get_by_category(self, category: str) -> List[OrchestrationPlan]:
        return [p for p in self._templates.values() if p.category == category]

# Singleton Instance
PLAN_REGISTRY = PlanRegistry()
