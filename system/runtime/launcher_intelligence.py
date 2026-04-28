import json
import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from system.intent_engine import INTENT_ENGINE
from system.orchestration_engine import ORCHESTRATION_ENGINE
from system.config import get_qvault_home

logger = logging.getLogger(__name__)

@dataclass
class AppStats:
    launch_count: int = 0
    last_launch: float = 0.0
    hourly_usage: dict = None # { "0": 10, "1": 2, ... "23": 5 }

class BaseCommand:
    """
    v1.6 Formal Command API.
    Provides metadata for Intelligence, Automation, and UI Blending.
    """
    def __init__(self, name, category="System", icon="⚡", description="", sensitive=False):
        self.name = name
        self.category = category
        self.icon = icon
        self.description = description
        self.sensitive = sensitive # True = Requires Smart Confirmation

    def get_preview(self, arg):
        return f"{self.description} (@{self.name} {arg if arg else ''})"
    
    def execute(self, controller, arg):
        pass

class RestartCommand(BaseCommand):
    def __init__(self): 
        super().__init__("restart", icon="󰜉", description="Restart app or system", sensitive=True)
    def execute(self, ctrl, arg): 
        from system.notification_service import NOTIFICATION_SERVICE
        NOTIFICATION_SERVICE.notify(f"Restarting {arg if arg else 'System'}...", "Maintenance")

class LockCommand(BaseCommand):
    def __init__(self): 
        super().__init__("lock", icon="󰌾", description="Protect current session", sensitive=False)
    def execute(self, ctrl, arg): ctrl.lock_session()

class LogoutCommand(BaseCommand):
    def __init__(self): 
        super().__init__("logout", icon="󰗽", description="Terminate OS session", sensitive=True)
    def execute(self, ctrl, arg): ctrl.logout()

class UndoCommand(BaseCommand):
    def __init__(self): 
        super().__init__("undo", icon="󰕌", description="Reverse latest system action", sensitive=False)
    def execute(self, ctrl, arg): 
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.UNDO_REQUESTED, source="UndoCommand")

class ExecutePlanCommand(BaseCommand):
    def __init__(self):
        super().__init__("execute_plan", icon="󰒓", description="Execute a multi-step orchestration plan", sensitive=False)
    def execute(self, ctrl, arg):
        # arg is suggestion_id
        
        sid = arg.split()[0] if arg else ""
        suggestion = INTENT_ENGINE._active_suggestions.get(sid)
        if suggestion and "plan" in suggestion:
            plan = suggestion["plan"]
            ORCHESTRATION_ENGINE.execute_plan(plan)
            # Accept feedback
            INTENT_ENGINE._handle_feedback(sid, accepted=True)

class TileWindowsCommand(BaseCommand):
    def __init__(self):
        super().__init__("tile_windows", icon="󰋘", description="Organize windows into tiles", sensitive=False)
    def execute(self, ctrl, arg):
        from system.window_manager import get_window_manager
        # In a real system, this would call a tiling algorithm
        # For simulation, we'll emit an event
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"setting": "layout", "value": "tiled"}, source="Launcher")

class DebugToggleCommand(BaseCommand):
    def __init__(self):
        super().__init__("debug", icon="🪲", description="Toggle System Stability Monitor", sensitive=False)
    def execute(self, ctrl, arg):
        from core.event_bus import EVENT_BUS, SystemEvent
        EVENT_BUS.emit(SystemEvent.SETTING_CHANGED, {"setting": "diagnostic", "value": "toggle"}, source="Launcher")

class StressTestCommand(BaseCommand):
    def __init__(self):
        super().__init__("stress_test", icon="🔥", description="Run system-wide stability stress test", sensitive=True)
    def execute(self, ctrl, arg):
        from core.event_bus import EVENT_BUS, SystemEvent
        import time
        # 1. Spawn Storm
        for i in range(10):
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": "Terminal"}, source="StressTest")
            # Rapid fire but give event loop a tiny breath
            time.sleep(0.05)

class SnapStressCommand(BaseCommand):
    def __init__(self):
        super().__init__("snap_stress", icon="🧲", description="Automated stress test for Snap Engine", sensitive=True)
    def execute(self, ctrl, arg):
        from system.window_manager import get_window_manager, SnapZone
        from core.event_bus import EVENT_BUS, SystemEvent
        import time
        
        # 1. Spawn a few windows
        wids = []
        for i in range(3):
            # We can't easily capture the ID here as launch_app is async via eventbus,
            # but we can just use existing windows if any or wait.
            EVENT_BUS.emit(SystemEvent.REQ_APP_LAUNCH, {"name": "Terminal"}, source="SnapStress")
            time.sleep(0.1)
        
        # 2. Rapid Snap Cycle
        wm = get_window_manager()
        for wid in list(wm._windows.keys())[-3:]:
            for zone in [SnapZone.LEFT, SnapZone.RIGHT, SnapZone.MAXIMIZE]:
                wm.apply_snap(wid, zone)
                time.sleep(0.2)

class ChaosDragCommand(BaseCommand):
    def __init__(self):
        super().__init__("chaos_drag", icon="🌀", description="Simulate rapid boundary-crossing drag intent", sensitive=True)
    def execute(self, ctrl, arg):
        from system.window_manager import get_window_manager, SnapZone
        from core.event_bus import EVENT_BUS, SystemEvent
        import time
        
        wm = get_window_manager()
        if not wm._active: return
        
        # Rapidly emit drag updates near edges
        wid = wm._active
        pw, ph = 1920, 1080 # Fallback
        
        # Simulate moving mouse back and forth across a threshold
        for _ in range(20):
            # Near Left Edge (Trigger)
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_DRAG_UPDATE, {"id": wid, "x": 10, "y": 500})
            time.sleep(0.05)
            # Away from Edge (Cancel)
            EVENT_BUS.emit(SystemEvent.REQ_WINDOW_DRAG_UPDATE, {"id": wid, "x": 100, "y": 500})
            time.sleep(0.05)

class KillCommand(BaseCommand):
    def __init__(self):
        super().__init__("kill", icon="󰗽", description="Forcibly close an application", sensitive=True)
    def execute(self, ctrl, arg):
        from system.window_manager import get_window_manager
        wm = get_window_manager()
        # Find window by title or partial ID
        if arg:
            for wid in list(wm._windows.keys()):
                if arg.lower() in wid.lower():
                    wm.close_window(wid)
                    break

class LauncherIntelligence:
    """
    v1.6 Intelligence Engine.
    Handles Layered Context Memory (Session/Persistent) and Blended Ranking.
    """
    def __init__(self):
        self.config_dir = Path(get_qvault_home()) / ".config" / "qvault"
        self.stats_path = self.config_dir / "launcher_intelligence.json"
        
        # Layered Memory initialization
        self._persistent_stats: dict[str, AppStats] = {}
        self._session_stats = {} # Cleared on reload/lock (logic-only here)
        
        self.commands = {
            "restart": RestartCommand(),
            "lock":    LockCommand(),
            "logout":  LogoutCommand(),
            "kill":    KillCommand(),
            "undo":    UndoCommand(),
            "execute_plan": ExecutePlanCommand(),
            "tile_windows": TileWindowsCommand(),
            "stress_test": StressTestCommand(),
            "debug": DebugToggleCommand(),
            "snap_stress": SnapStressCommand(),
            "chaos_drag": ChaosDragCommand()
        }
        self._load()

    def _load(self):
        if not self.stats_path.exists(): return
        try:
            with open(self.stats_path, "r") as f:
                data = json.load(f)
                for app_id, stats in data.items():
                    if "hourly_usage" not in stats or stats["hourly_usage"] is None:
                        stats["hourly_usage"] = {str(h): 0 for h in range(24)}
                    self._persistent_stats[app_id] = AppStats(**stats)
        except Exception as e:
            logger.error(f"Intelligence: Load failed: {e}")

    def _save(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.stats_path, "w") as f:
                json.dump({k: asdict(v) for k, v in self._persistent_stats.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Intelligence: Save failed: {e}")

    def record_launch(self, app_id: str):
        if app_id not in self._persistent_stats:
            self._persistent_stats[app_id] = AppStats(hourly_usage={str(h): 0 for h in range(24)})
        
        ps = self._persistent_stats[app_id]
        ps.launch_count += 1
        ps.last_launch = time.time()
        
        hour = str(time.localtime().tm_hour)
        ps.hourly_usage[hour] += 1
        self._save()

    def get_ranked_results(self, query: str, app_list: list) -> list:
        """
        v1.6 Blended Search: Injects Apps + System Commands.
        """
        now = time.time()
        curr_hour = str(time.localtime().tm_hour)
        results = []

        q = query.lower().strip()
        is_cmd_mode = q.startswith("@")
        search_term = q[1:] if is_cmd_mode else q

        # 1. Evaluate Apps
        for app_def in app_list:
            if search_term and search_term not in app_def.name.lower(): continue
            
            stats = self._persistent_stats.get(app_def.name, AppStats(hourly_usage={str(h): 0 for h in range(24)}))
            
            # Recency Decay
            days_ago = (now - stats.last_launch) / 86400.0 if stats.last_launch > 0 else 365.0
            recency = 1.0 / (days_ago + 1.0)
            
            # Time Match
            time_factor = min(stats.hourly_usage.get(curr_hour, 0) / 5.0, 1.0)

            score = (stats.launch_count * recency * 0.7) + (time_factor * 20.0)
            if not search_term: score *= 1.2 # Boost favorites on empty search
            
            results.append({"score": score, "type": "app", "data": app_def})

        # 2. Evaluate Commands (Blended)
        for name, cmd in self.commands.items():
            # If explicit @ mode, only match commands
            # If normal mode, only match if the query is a strong match for the command name
            if is_cmd_mode:
                if name.startswith(search_term):
                    results.append({"score": 100, "type": "command", "data": cmd})
            else:
                if search_term and name.startswith(search_term):
                    # Commands get a 'high' score to float near the top if matching
                    results.append({"score": 50, "type": "command", "data": cmd})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def get_command_preview(self, query: str):
        if not query.startswith("@"): return None
        ps = query[1:].lower().split(maxsplit=1)
        name = ps[0]
        arg = ps[1] if len(ps) > 1 else None
        
        if name in self.commands:
            cmd = self.commands[name]
            return {
                "name": name,
                "obj": cmd,
                "arg": arg,
                "is_dangerous": cmd.sensitive,
                "preview": cmd.get_preview(arg)
            }
        return {"name": "unknown", "preview": "UNKNOWN COMMAND"}

    def reset_session_context(self):
        """Clears the Tier 1 (Session) memory. Called on lock/logout."""
        self._session_stats = {}
        logger.info("Intelligence: Session context reset.")

# Singleton Instance
BRAIN = LauncherIntelligence()
