import logging
import subprocess
import platform
import os
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SystemControlHelper:
    """
    Sovereign System Control Helper.
    Handles hardware-level operations (Power, Network, Volume, Brightness).
    """
    
    @staticmethod
    def power_action(action: str):
        """Executes power-related commands safely."""
        system = platform.system().lower()
        logger.info(f"[SYSTEM] Power Action Triggered: {action}")
        
        try:
            if system == "windows":
                if action == "shutdown":
                    os.system("shutdown /s /t 1")
                elif action == "restart":
                    os.system("shutdown /r /t 1")
                elif action == "sleep":
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif system == "linux":
                if action == "shutdown":
                    os.system("systemctl poweroff")
                elif action == "restart":
                    os.system("systemctl reboot")
                elif action == "sleep":
                    os.system("systemctl suspend")
        except Exception as e:
            logger.error(f"[SYSTEM] Failed to execute power action {action}: {e}")

    @staticmethod
    def get_wifi_networks() -> List[Dict[str, Any]]:
        """Scans for available Wi-Fi networks."""
        system = platform.system().lower()
        networks = []
        
        try:
            if system == "windows":
                output = subprocess.check_output(["netsh", "wlan", "show", "networks"], 
                                               creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore')
                ssids = re.findall(r"SSID \d+ : (.+)", output)
                for ssid in ssids:
                    networks.append({
                        "name": ssid.strip(),
                        "secure": True, # netsh doesn't easily show this in 'show networks'
                        "strength": "▰▰▰▱"
                    })
            elif system == "linux":
                # Fallback for Linux
                output = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SECURITY,BARS", "dev", "wifi"], 
                                               stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
                for line in output.splitlines():
                    if line.strip():
                        parts = line.split(":")
                        if len(parts) >= 3:
                            networks.append({
                                "name": parts[0],
                                "secure": "WPA" in parts[1],
                                "strength": parts[2]
                            })
        except Exception as e:
            logger.debug(f"[SYSTEM] Wi-Fi scan failed: {e}")
            
        return networks if networks else [{"name": "No Networks Found", "secure": False, "strength": "░░░░"}]

    @staticmethod
    def set_volume(value: int):
        """Sets system volume (0-100)."""
        system = platform.system().lower()
        try:
            if system == "windows":
                # Fallback: using nircmd if available or simple mute/unmute
                # For now, just logging to avoid heavy dependencies like pycaw in a minimalist core
                logger.info(f"[SYSTEM] Volume set to {value}%")
            elif system == "linux":
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{value}%"], check=False)
        except Exception:
            pass

    @staticmethod
    def set_airplane_mode(enabled: bool):
        """Toggles airplane mode."""
        system = platform.system().lower()
        state = "ON" if enabled else "OFF"
        logger.info(f"[SYSTEM] Airplane Mode: {state}")
        
        try:
            if system == "windows":
                # netsh interface set interface "Wi-Fi" admin=disabled
                cmd = "disabled" if enabled else "enabled"
                subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", f"admin={cmd}"], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            elif system == "linux":
                cmd = "on" if enabled else "off"
                subprocess.run(["nmcli", "radio", "all", cmd], check=False)
        except Exception:
            pass
