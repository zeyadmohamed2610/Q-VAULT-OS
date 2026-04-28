# =============================================================
#  sdk/qvault_sdk.py — Q-Vault OS  |  IPC Bridge Adapter
#
#  Legacy / IPC-specific implementation of the QVaultAPI.
#  This file is used by isolated processes to talk to the Kernel.
# =============================================================

import uuid
from typing import Any, Dict
from .api import api

class IPCBridge:
    """Handles the actual IPC messaging for isolated processes."""
    def __init__(self, bridge_impl):
        self._impl = bridge_impl

    def send_event(self, event_name: str, payload: Dict):
        """Map SDK emit to Bridge send_event."""
        self._impl.send_event(event_name, payload)

    def listen(self, event_name: str, callback: callable):
        """Map SDK subscribe to Bridge listen."""
        self._impl.listen(event_name, callback)

    def call(self, method: str, *args, **kwargs) -> Any:
        """Synchronous RPC call over the bridge."""
        msg_id = uuid.uuid4().hex
        self._impl.send_call(msg_id, method, args, kwargs)
        return self._impl.wait_for_return(msg_id)

def initialize_ipc(bridge_impl):
    """
    Bootstrapper for isolated processes.
    Initializes the unified SDK with an IPC bridge.
    """
    bridge = IPCBridge(bridge_impl)
    api.set_bridge(bridge)
    return api
