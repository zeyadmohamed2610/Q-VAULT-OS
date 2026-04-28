import logging
import subprocess
import os
from enum import Enum
from typing import List, Dict, Any
from system.plugin_base import BasePlugin
from system.command_dispatcher import COMMAND_DISPATCHER
from system.reasoning_engine import REASONING_ENGINE

logger = logging.getLogger(__name__)

class GitState(Enum):
    IDLE = "IDLE"
    STAGED = "STAGED"
    COMMITTED = "COMMITTED"

class GitPlugin(BasePlugin):
    """
    v3.5.2 Wisely Vigilant Partner.
    Respects 'Professional Silence' and handles chaotic diffs with transparency.
    """
    def __init__(self):
        super().__init__()
        self.state = GitState.IDLE
        self.pending_files = 0
        self.handoff_metadata = {}
        self.ai_evaluation = {}

    def on_activate(self):
        COMMAND_DISPATCHER.register_handler("@git", self)

    def receive_handoff(self, metadata: Dict[str, Any]):
        self.handoff_metadata = metadata
        self.state = GitState.IDLE

    def get_proactive_actions(self) -> List[Dict[str, Any]]:
        try:
            if self.state == GitState.IDLE:
                res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True, timeout=2)
                self.pending_files = len(res.stdout.strip().split("\n")) if res.stdout.strip() else 0
                if self.pending_files == 0: return []
            
            if self.state == GitState.IDLE:
                # Basic staging is low-noise, always suggest if files exist
                return [{
                    "id": "git_stage", "title": "Stage Changes", "description": f"Sync {self.pending_files} modifications?",
                    "confidence": 0.95, "command": "@git stage", "is_sensitive": False,
                    "workflow": {"steps": 3, "current": 1, "progress": "● ○ ○"}
                }]
            
            elif self.state == GitState.STAGED:
                # v3.5.2: Professional Silence Logic
                diff_res = subprocess.run("git diff --staged --unified=1", shell=True, capture_output=True, text=True)
                self.ai_evaluation = REASONING_ENGINE.summarize_diff(diff_res.stdout, self.handoff_metadata)
                
                # If the AI suggests silence, we return NO actions for the commit phase
                if self.ai_evaluation.get('silent'):
                    logger.info("GitPlugin: Professional Silence active for commit phase.")
                    return []
                
                return [{
                    "id": "git_commit",
                    "title": "Commit Staged Changes",
                    "description": "Semantic intent based on diff analysis.",
                    "confidence": self.ai_evaluation['confidence'], # v3.5.2 Chaos transparency
                    "command": "@git commit_step",
                    "is_sensitive": True,
                    "workflow": {"steps": 3, "current": 2, "progress": "● ● ○"},
                    "ai_metadata": {
                        "confidence": self.ai_evaluation['confidence'], 
                        "is_ai": True,
                        "impact": self.ai_evaluation['impact'],
                        "risks": self.ai_evaluation['risks'],
                        "internal_score": self.ai_evaluation.get('internal_score')
                    },
                    "inputs": [{"id": "message", "label": "Commit Intent", "default": self.ai_evaluation['message']}]
                }]
            
            elif self.state == GitState.COMMITTED:
                return [{
                    "id": "git_push", "title": "Push to Remote", "description": "Sync changes to origin.",
                    "confidence": 1.0, "command": "@git push_step", "is_sensitive": True,
                    "workflow": {"steps": 3, "current": 3, "progress": "● ● ●"}
                }]
                
        except Exception as e:
            logger.error(f"GitPlugin: Proactive check failed: {e}")
        return []

    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        params = params or {}
        sub_cmd = command.replace("@git", "").strip()

        if params.get("override_safety"):
             logger.warning("GitPlugin: Security Protocol Bypassed by User.")
        elif "commit_step" in sub_cmd and not params.get("risk_acknowledged"):
             if any(r['tier'] == 'CRITICAL' for r in self.ai_evaluation.get('risks', [])):
                 return {"success": False, "output": "Critical Risks. Acknowledge or Bypass to proceed.", "summary": "Blocked by Quality Gate"}

        if params.get("ignore"):
            self.state = GitState.IDLE; self.handoff_metadata = {}; self.ai_evaluation = {}
            return {"success": True, "output": "Reset.", "summary": "Reset Done"}

        if sub_cmd == "stage":
            subprocess.run("git add .", shell=True)
            self.state = GitState.STAGED
            return {"success": True, "output": "Staged.", "summary": "Staging Complete"}

        elif "commit_step" in sub_cmd:
            msg = params.get("message", self.ai_evaluation.get('message', "Update"))
            res = subprocess.run(f'git commit -m "{msg}"', shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.state = GitState.COMMITTED
                return {"success": True, "output": res.stdout, "summary": "Commit Finalized"}
            return {"success": False, "output": res.stderr, "summary": "Commit Failed"}

        elif "push_step" in sub_cmd:
            res = subprocess.run("git push", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.state = GitState.IDLE
                if self.ai_evaluation.get('impact', {}).get('level') == 'HIGH':
                    from core.event_bus import EVENT_BUS
                    EVENT_BUS.emit("DISPATCH_PROACTIVE", {
                        "id": "post_sync_test", "title": "Verification Required", "description": "High impact changes synced. Verify stability?",
                        "command": "@run pytest", "confidence": 0.88, "source_plugin": "git"
                    }, source="GitPlugin")
                return {"success": True, "output": res.stdout, "summary": "Sync Complete 🚀"}
            return {"success": False, "output": res.stderr, "summary": "Push Failed"}

        return {"success": False, "output": "Unknown cmd", "summary": "Error"}
