import logging
import os
import time
from typing import List, Dict, Any
from system.plugin_base import BasePlugin
from system.command_dispatcher import COMMAND_DISPATCHER

logger = logging.getLogger(__name__)

class VSCodePlugin(BasePlugin):
    """
    v3.3 Pilot Workflow Plugin.
    Monitors workspace activity and guides the 'Focus-to-Sync' transition.
    """
    def __init__(self):
        super().__init__()
        self.last_check_time = time.time()
        self.active_files = []
        self.is_coding = False
        self.adaptive_window = 180 # 3 minutes as requested

    def on_activate(self):
        COMMAND_DISPATCHER.register_handler("@vscode", self)

    def on_deactivate(self):
        pass

    def can_handle_command(self, command: str) -> bool:
        return command.startswith("@vscode")

    def get_proactive_actions(self) -> List[Dict[str, Any]]:
        """
        Detection Logic: Detect active coding files in the last 3 minutes.
        """
        now = time.time()
        
        # Don't poll too fast
        if now - self.last_check_time < 30: 
            return self._generate_cards()

        self.last_check_time = now
        new_active = []
        cwd = os.getcwd()
        
        # Simple recursive scan for modified files (ignoring common junk)
        ignore_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.gemini'}
        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fpath)
                    if now - mtime < self.adaptive_window:
                        new_active.append({
                            "name": f,
                            "path": fpath,
                            "ext": os.path.splitext(f)[1]
                        })
                except: pass
        
        self.active_files = new_active
        self.is_coding = len(self.active_files) > 0
        
        return self._generate_cards()

    def _generate_cards(self) -> List[Dict[str, Any]]:
        if not self.is_coding: return []
        
        return [{
            "id": "vscode_review",
            "title": "Review Coding Progress",
            "description": f"Detected changes in {len(self.active_files)} files. Ready to finalize?",
            "confidence": 0.95,
            "command": "@vscode finish",
            "is_sensitive": False,
            "workflow": {"steps": 2, "current": 1, "progress": "● ○"}
        }]

    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        params = params or {}
        sub_cmd = command.replace("@vscode", "").strip()

        if sub_cmd == "finish":
            # 1. Gather Metadata for Handoff
            metadata = {
                "file_count": len(self.active_files),
                "filenames": [f['name'] for f in self.active_files],
                "extensions": list(set([f['ext'] for f in self.active_files])),
                "timestamp": time.time()
            }
            
            # 2. Trigger Handoff to Git
            from system.plugin_manager import PLUGIN_MANAGER
            PLUGIN_MANAGER.trigger_handoff("git", metadata)
            
            # 3. Complete internal step
            self.is_coding = False
            self.active_files = []
            
            return {
                "success": True, 
                "output": f"Workspace context passed to Git Plugin.\nFiles: {', '.join(metadata['filenames'])}", 
                "summary": "Coding session finalized. Transitioning to Sync..."
            }

        return {"success": False, "output": f"Unknown command: {sub_cmd}", "summary": "Error"}
