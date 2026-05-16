import logging
import sys
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SystemControlHelper:
    """
    Sovereign System Control Helper v2.0
    All operations are VIRTUAL and operate only within the Q-Vault environment.
    No host OS mutations. No registry writes. No network stack changes.

    READ operations (e.g. scanning WiFi via netsh) are permitted and delegated
    to the dedicated scanner threads in systray panels.
    """

    # ── Internal state (simulated hardware layer) ─────────────────
    _volume: int = 75
    _brightness: int = 90

    # ── Power Control ─────────────────────────────────────────────

    @staticmethod
    def power_action(action: str):
        """Virtual power actions — operate on the Q-Vault process, not the host OS."""
        logger.info(f"[SOVEREIGN] Power action triggered: {action}")
        try:
            if action == "shutdown":
                # Gracefully quit the Q-Vault application
                from PyQt5.QtWidgets import QApplication
                QApplication.quit()
                sys.exit(0)

            elif action == "restart":
                # Re-launch this Python process (Q-Vault only, not Windows)
                python = sys.executable
                os.execl(python, python, *sys.argv)

            elif action in ("sleep", "lock"):
                # Emit a session-lock event — no host sleep command
                from core.event_bus import EVENT_BUS, SystemEvent
                EVENT_BUS.emit(SystemEvent.SESSION_LOCKED, {"reason": action}, source="SystemControlHelper")

        except Exception as e:
            logger.error(f"[SOVEREIGN] Power action failed ({action}): {e}")

    # ── Volume Control (Virtual) ──────────────────────────────────

    @staticmethod
    def set_volume(value: int):
        """
        Sets the internal audio gain level within the Q-Vault environment.
        Does NOT touch the host Windows mixer or any WASAPI/ASIO session.
        """
        value = max(0, min(100, int(value)))
        SystemControlHelper._volume = value
        logger.info(f"[SOVEREIGN] Virtual volume → {value}%")

        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(
                SystemEvent.SETTING_CHANGED,
                {"key": "volume", "value": value},
                source="SystemControlHelper"
            )
        except Exception as e:
            logger.debug(f"[SOVEREIGN] Volume event emit failed: {e}")

    @staticmethod
    def get_volume() -> int:
        return SystemControlHelper._volume

    # ── Brightness Control (Virtual) ──────────────────────────────

    @staticmethod
    def set_brightness(value: int):
        """
        Sets the virtual screen brightness within the Q-Vault environment.
        Does NOT call WMI, brightnessctl, or any display driver.
        A future implementation may adjust Qt widget opacity as a visual metaphor.
        """
        value = max(0, min(100, int(value)))
        SystemControlHelper._brightness = value
        logger.info(f"[SOVEREIGN] Virtual brightness → {value}%")

        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(
                SystemEvent.SETTING_CHANGED,
                {"key": "brightness", "value": value},
                source="SystemControlHelper"
            )
        except Exception as e:
            logger.debug(f"[SOVEREIGN] Brightness event emit failed: {e}")

    @staticmethod
    def get_brightness() -> int:
        return SystemControlHelper._brightness

    # ── Airplane Mode (Virtual Network Isolation) ─────────────────

    @staticmethod
    def set_airplane_mode(enabled: bool):
        """
        Activates/deactivates the Q-Vault virtual network isolation layer.
        Does NOT call netsh, PowerShell, or modify any Windows NIC settings.
        """
        state = "ISOLATED" if enabled else "CONNECTED"
        logger.info(f"[SOVEREIGN] Virtual network stack → {state}")

        try:
            from core.event_bus import EVENT_BUS, SystemEvent
            EVENT_BUS.emit(
                SystemEvent.SETTING_CHANGED,
                {"key": "airplane_mode", "value": enabled},
                source="SystemControlHelper"
            )
        except Exception as e:
            logger.debug(f"[SOVEREIGN] Airplane mode event emit failed: {e}")

    # ── Hardware Scanning (Sovereign Gateway) ─────────────────────

    @staticmethod
    def get_wifi_networks() -> List[Dict[str, Any]]:
        """
        Reads available WiFi networks via Sovereign Intelligence layer (READ-ONLY).
        This does NOT connect, disconnect, or modify any settings.
        """
        # Fully virtualized Sovereign network simulation to avoid Host OS leaks.
        return [
            {"name": "Sovereign Central Gateway", "signal": 95, "secure": True},
            {"name": "Air-Gap Intelligence",      "signal": 78, "secure": True},
            {"name": "Quantum-Vault-Link",        "signal": 62, "secure": True},
            {"name": "Legacy Guest Void",         "signal": 35, "secure": False},
        ]

    @staticmethod
    def get_bluetooth_devices() -> List[Dict[str, Any]]:
        """
        Reads available Bluetooth devices via Sovereign Intelligence layer (READ-ONLY).
        This does NOT connect, disconnect, or modify any settings.
        """
        # Fully virtualized Sovereign BT simulation to avoid Host OS leaks.
        return [
            {"name": "Sovereign Audio Interface", "connected": True,  "type": "Headphones 🎧"},
            {"name": "Bio-Metric Security Key",   "connected": False, "type": "Identity Token 🔑"},
            {"name": "Encrypted Control Hub",     "connected": False, "type": "Keyboard ⌨️"},
            {"name": "Vault Precision Mouse",     "connected": False, "type": "Mouse 🖱️"},
        ]
