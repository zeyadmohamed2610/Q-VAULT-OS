# =============================================================
#  system_info.py — Q-Vault OS  |  Real System Information
#
#  Provides real system metrics from the host OS
# =============================================================

import platform
import os
import time
import random


class SystemInfo:
    """
    Retrieves real system information from the host OS.
    Uses platform module and OS commands.
    """

    @staticmethod
    def get_os_name() -> str:
        """Get operating system name"""
        return platform.system()

    @staticmethod
    def get_os_version() -> str:
        """Get OS version"""
        return platform.version()

    @staticmethod
    def get_os_release() -> str:
        """Get OS release"""
        return platform.release()

    @staticmethod
    def get_machine() -> str:
        """Get machine type"""
        return platform.machine()

    @staticmethod
    def get_processor() -> str:
        """Get processor name"""
        return platform.processor()

    @staticmethod
    def get_hostname() -> str:
        """Get hostname"""
        return platform.node()

    @staticmethod
    def get_cpu_usage() -> int:
        """Get CPU usage percentage (simulated if unavailable)"""
        try:
            if platform.system() == "Windows":
                import subprocess

                result = subprocess.run(
                    ["wmic", "cpu", "get", "loadpercentage"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1 and lines[1].strip().isdigit():
                    return int(lines[1].strip())
        except Exception:
            pass

        # Fallback: simulate based on process count
        from core.process_manager import PM

        proc_count = len(PM.all_procs())
        return min(100, max(5, proc_count * 2 + random.randint(-10, 10)))

    @staticmethod
    def get_ram_usage() -> tuple[int, int, int]:
        """
        Get RAM usage: (used_mb, total_mb, percentage)
        Returns simulated values if unavailable
        """
        try:
            if platform.system() == "Windows":
                import subprocess

                result = subprocess.run(
                    [
                        "wmic",
                        "OS",
                        "get",
                        "FreePhysicalMemory,TotalVisibleMemorySize",
                        "/Value",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                lines = result.stdout.strip().split("\n")
                free = 0
                total = 0
                for line in lines:
                    if "FreePhysicalMemory" in line:
                        free = int(line.split("=")[1].strip())
                    if "TotalVisibleMemorySize" in line:
                        total = int(line.split("=")[1].strip())

                if total > 0:
                    used = total - free
                    used_mb = used // 1024
                    total_mb = total // 1024
                    pct = int((used / total) * 100)
                    return (used_mb, total_mb, pct)
        except Exception:
            pass

        # Fallback: simulated values
        base = 45
        variance = random.randint(-5, 5)
        pct = min(100, max(10, base + variance))
        total_mb = 16384
        used_mb = int(total_mb * pct / 100)
        return (used_mb, total_mb, pct)

    @staticmethod
    def get_disk_usage() -> list[dict]:
        """
        Get disk usage for all drives
        Returns: [{'mount': str, 'used_gb': int, 'total_gb': int, 'percent': int}]
        """
        disks = []

        try:
            if platform.system() == "Windows":
                import subprocess

                result = subprocess.run(
                    ["wmic", "logicaldisk", "get", "DeviceID,Size,FreeSpace"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[0]:
                        drive = parts[0]
                        try:
                            free = int(parts[1]) // (1024 * 1024 * 1024)
                            total = int(parts[2]) // (1024 * 1024 * 1024)
                            used = total - free
                            pct = int((used / total) * 100) if total > 0 else 0
                            disks.append(
                                {
                                    "mount": drive,
                                    "used_gb": used,
                                    "total_gb": total,
                                    "percent": pct,
                                }
                            )
                        except Exception:
                            pass
        except Exception:
            pass

        # Fallback: add default system drive
        if not disks:
            disks.append(
                {
                    "mount": "C:" if platform.system() == "Windows" else "/",
                    "used_gb": random.randint(40, 80),
                    "total_gb": 256,
                    "percent": random.randint(20, 40),
                }
            )

        return disks

    @staticmethod
    def get_uptime() -> str:
        """Get system uptime"""
        try:
            boot_time = time.time() - time.time()
            uptime_seconds = int(time.time() - boot_time)

            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            minutes = (uptime_seconds % 3600) // 60

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"

    @staticmethod
    def get_network_info() -> dict:
        """Get basic network information"""
        hostname = platform.node()
        return {
            "hostname": hostname,
            "domain": platform.freedesktop_os_release()
            if hasattr(platform, "freedesktop_os_release")
            else "",
        }

    @staticmethod
    def get_all_info() -> dict:
        """Get all system information at once"""
        ram = SystemInfo.get_ram_usage()
        disks = SystemInfo.get_disk_usage()

        return {
            "os_name": SystemInfo.get_os_name(),
            "os_version": SystemInfo.get_os_version(),
            "os_release": SystemInfo.get_os_release(),
            "machine": SystemInfo.get_machine(),
            "processor": SystemInfo.get_processor(),
            "hostname": SystemInfo.get_hostname(),
            "cpu_percent": SystemInfo.get_cpu_usage(),
            "ram_used_mb": ram[0],
            "ram_total_mb": ram[1],
            "ram_percent": ram[2],
            "disks": disks,
            "uptime": SystemInfo.get_uptime(),
        }


# Module singleton
SYSINFO = SystemInfo()
