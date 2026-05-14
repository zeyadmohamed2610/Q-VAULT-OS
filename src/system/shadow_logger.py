import os
import logging
from datetime import datetime

class ShadowLogger:
    """
    v1.0 Discrete Event Recording System.
    Logs system decisions and AI reasoning without cluttering main logs.
    """
    def __init__(self):
        self.log_dir = os.path.join(os.path.expanduser("~"), ".qvault", "logs", "shadow")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.current_log = os.path.join(self.log_dir, f"shadow_{datetime.now().strftime('%Y-%m-%d')}.log")
        
    def log_decision(self, component: str, decision: str, context: dict = None):
        """Records a system decision with context in a structured format."""
        import json
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        entry = {
            "time_str": timestamp,
            "component": component.upper(),
            "decision": decision,
            "context": context or {}
        }
        
        try:
            with open(self.current_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def info(self, msg: str):
        self.log_decision("SYSTEM", msg)

    def _read_all_events(self):
        """Helper for intelligence analysis - reads and parses JSON log entries."""
        import json
        if not os.path.exists(self.current_log):
            return []
        try:
            events = []
            with open(self.current_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            continue
            return events
        except Exception:
            return []

    def archive_current_session(self):
        """Moves current log to an archive folder for session cleanup."""
        import shutil
        archive_dir = os.path.join(self.log_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        if os.path.exists(self.current_log):
            dest = os.path.join(archive_dir, f"shadow_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            try:
                shutil.move(self.current_log, dest)
                # Re-init current log
                self.current_log = os.path.join(self.log_dir, f"shadow_{datetime.now().strftime('%Y-%m-%d')}.log")
            except Exception:
                pass

# Singleton Instance
SHADOW_LOGGER = ShadowLogger()
