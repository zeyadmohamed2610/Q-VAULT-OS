import logging
from typing import Optional

from core.event_bus import EVENT_BUS, SystemEvent

logger = logging.getLogger(__name__)


class QVaultRuntimeBridge:
    """
    Bridge between the QVaultAdapter and the OS runtime.

    Singleton — initialized once during service startup.
    Provides the OS with a clean interface to the QVault subsystem
    without any direct coupling to qvault-pc-mediator internals.
    """

    _instance: Optional["QVaultRuntimeBridge"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._adapter = None

    def start(self):
        """Initialize the adapter and wire EventBus subscriptions."""
        if self._adapter is not None:
            return  # Already started

        try:
            from kernel.security.qvault_adapter import QVaultAdapter
            self._adapter = QVaultAdapter()

            # Subscribe to OS events that should trigger QVault actions
            EVENT_BUS.subscribe(
                SystemEvent.SESSION_LOCKED, self._on_session_locked
            )
            EVENT_BUS.subscribe(
                SystemEvent.SESSION_UNLOCKED, self._on_session_unlocked
            )
            EVENT_BUS.subscribe(
                SystemEvent.INTERRUPT_HANDLED, self._on_interrupt_handled
            )
            EVENT_BUS.subscribe(
                SystemEvent.EVENT_USB_DEVICE_CONNECTED, self._on_usb_connected
            )
            EVENT_BUS.subscribe(
                SystemEvent.EVENT_USB_DEVICE_DISCONNECTED, self._on_usb_disconnected
            )

            logger.info("[QVaultBridge] Runtime bridge started")

        except Exception as exc:
            logger.error("[QVaultBridge] Failed to start: %s", exc)
            self._adapter = None

    def stop(self):
        """Cleanup the bridge and adapter."""
        if self._adapter:
            self._adapter.cleanup()
            logger.info("[QVaultBridge] Runtime bridge stopped")

    @property
    def adapter(self):
        """Access the underlying QVaultAdapter instance."""
        return self._adapter

    # ── OS Event Handlers ─────────────────────────────────────

    def _on_session_locked(self, payload):
        """When OS session locks, lock the vault."""
        if self._adapter and self._adapter.is_running():
            self._adapter.set_vault_locked(True)

    def _on_session_unlocked(self, payload):
        """When OS session unlocks, update state."""
        pass  # Vault unlock requires explicit user action

    def _on_interrupt_handled(self, payload):
        """Bridge hardware interrupts to security state."""
        irq_data = payload.data.get("interrupt", {})
        if irq_data.get("type") == "usb":  # InterruptType.USB_DEVICE.value
            state = payload.data.get("state", "connected")
            if state == "connected":
                self._on_usb_connected(payload)
            else:
                self._on_usb_disconnected(payload)

    def _on_usb_connected(self, payload):
        """Hardware USB connect event."""
        if self._adapter and self._adapter.is_running():
            self._adapter.set_token_connected(True)

    def _on_usb_disconnected(self, payload):
        """Hardware USB disconnect event."""
        if self._adapter and self._adapter.is_running():
            self._adapter.set_token_connected(False)
            self._adapter.set_vault_locked(True)


# ── Module-level singleton ────────────────────────────────────

QVAULT_BRIDGE = QVaultRuntimeBridge()
