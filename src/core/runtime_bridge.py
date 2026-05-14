import os
import sys
import logging
from pathlib import Path

# Add binaries directory to path to ensure .pyd can be imported
binaries_path = Path(__file__).parent / "binaries"
sys.path.append(str(binaries_path))

try:
    from qvault_core import SecurityEngine as _SecurityEngine
    
    class SecurityEngineWrapper:
        def __init__(self, root_dir):
            self._engine = _SecurityEngine(root_dir)
        
        def authenticate(self, username, password):
            """Wrapper for login to provide the session token if successful."""
            try:
                token = self._engine.login(username, password)
                return token # Returns string token or None
            except Exception:
                return None
        
        def __getattr__(self, name):
            # Proxy all other calls to the underlying Rust engine
            return getattr(self._engine, name)

    # Initialize the global security engine instance
    project_root = str(Path(__file__).parent.parent)
    SECURITY_ENGINE = SecurityEngineWrapper(project_root)
    
    logging.info(f"[RuntimeBridge] SecurityEngine initialized at {project_root}")
except ImportError as e:
    logging.error(f"[RuntimeBridge] Failed to load qvault_core binary: {e}")
    SECURITY_ENGINE = None
except Exception as e:
    logging.error(f"[RuntimeBridge] Critical error during engine init: {e}")
    SECURITY_ENGINE = None
