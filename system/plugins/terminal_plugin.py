import logging
import subprocess
from system.plugin_base import BasePlugin
from system.command_dispatcher import COMMAND_DISPATCHER

logger = logging.getLogger(__name__)

class TerminalPlugin(BasePlugin):
    """
    v3.1 Execution Bridge to the system shell.
    Handles background command execution and output capturing.
    """
    def on_activate(self):
        COMMAND_DISPATCHER.register_handler("@launch terminal", self)
        COMMAND_DISPATCHER.register_handler("@run", self)

    def on_deactivate(self):
        pass

    def can_handle_command(self, command: str) -> bool:
        return command.startswith("@run") or command.startswith("@launch terminal")

    def execute(self, command: str, params: dict = None) -> dict:
        """Executes a shell command."""
        params = params or {}
        # Extract command after @run or from --arg
        cmd_to_run = ""
        if "@run" in command:
            cmd_to_run = command.replace("@run", "").strip()
        elif "--arg" in command:
            import shlex
            parts = shlex.split(command)
            if "--arg" in parts:
                cmd_to_run = parts[parts.index("--arg") + 1]

        if not cmd_to_run:
            return {"success": False, "output": "No command specified", "summary": "N/A"}

        logger.info(f"TerminalPlugin: Executing '{cmd_to_run}'")
        try:
            # v3.1: Always run in background shell
            result = subprocess.run(cmd_to_run, shell=True, capture_output=True, text=True, timeout=10)
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            summary = f"Executed: {cmd_to_run[:20]}..."
            
            return {
                "success": success,
                "output": output,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"TerminalPlugin: Execution error: {e}")
            return {"success": False, "output": str(e), "summary": "Execution Failed"}
