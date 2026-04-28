"""
apps.terminal
─────────────────────────────────────────────────────────────────────────────
Q-Vault OS Terminal Package

Public surface
--------------
  TerminalEngine   — the engine loaded by IsolatedAppWidget
  TerminalApp      — the Qt widget frontend
  EngineState      — the state-machine enum
  TerminalWorker   — background subprocess worker (for external test access)

Internal components (underscore prefix = package-private)
---------------------------------------------------------
  _output_formatter.py  — OutputFormatter
  _command_parser.py    — CommandParser
  _command_executor.py  — CommandExecutor
  _sudo_manager.py      — SudoManager

Callers outside this package should only import from terminal_engine or
terminal_app — never from the underscore modules directly.
"""
# Expose the primary public names at the package level so that
#   from apps.terminal import TerminalEngine
# continues to work if anyone uses that form.
from .terminal_engine import TerminalEngine, EngineState, TerminalWorker
