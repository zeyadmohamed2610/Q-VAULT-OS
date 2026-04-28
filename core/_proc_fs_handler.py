"""
core._proc_fs_handler
────────────────────────────────────────────────────────────────────────────
Q-Vault OS — Virtual Filesystem  |  /proc Handler

Single Responsibility: generate and manage the /proc virtual filesystem.

What /proc is (Linux reference)
────────────────────────────────
/proc is a pseudo-filesystem that the Linux kernel exposes to give user-space
processes a window into kernel data structures.  It is never stored on disk;
its contents are generated on demand.

Key files simulated here
─────────────────────────
  /proc/uptime         — system uptime in seconds since boot
  /proc/meminfo        — memory statistics (MemTotal, MemFree, …)
  /proc/cpuinfo        — processor model and core count
  /proc/version        — kernel version string
  /proc/loadavg        — load averages (1, 5, 15 min)
  /proc/net/dev        — network interface statistics
  /proc/<pid>/status   — per-process status (from ProcessManager)
  /proc/<pid>/cmdline  — process command line
  /proc/<pid>/stat     — process stat line (simplified)

Design
──────
ProcFSHandler is stateless at the class level.  Every generate_* method
returns a plain string that is wrapped in a Meta object by the caller.

The handler is called by VirtualFS._refresh_proc() which is invoked:
  1. On every VirtualFS.ls("/proc", …) call
  2. On every VirtualFS.cat() call that targets a /proc path

This means /proc content is always fresh — no stale snapshot.

Previously
──────────
The /proc entry in the VirtualFS tree was a bare empty dict:
    "proc": {"_meta": Meta("", owner="root")}

It could be stat'd and ls'd (showing nothing) but not cat'd meaningfully.
This handler makes it a living subsystem.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.filesystem import Meta


# ── Boot time (module load = system boot for simulation purposes) ─────────
_BOOT_TIME: float = time.time()


class ProcFSHandler:
    """
    Generates dynamic content for the /proc virtual filesystem.

    All methods are classmethods — no instantiation needed.
    """

    # Simulated hardware constants — realistic for a small VM
    _CPU_MODEL:   str = "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz"
    _CPU_CORES:   int = 6
    _MEM_TOTAL_KB: int = 16_384_000   # 16 GB RAM
    _MEM_CACHED_KB: int = 2_048_000

    # ── Top-level /proc files ─────────────────────────────────────────────

    @classmethod
    def uptime(cls) -> str:
        """
        /proc/uptime
        Format: "<total_uptime_secs>.<centisecs> <idle_secs>.<centisecs>"
        """
        uptime = time.time() - _BOOT_TIME
        idle   = uptime * 0.70   # simulate ~70% idle time
        return f"{uptime:.2f} {idle:.2f}\n"

    @classmethod
    def meminfo(cls, pm=None) -> str:
        """
        /proc/meminfo — memory statistics.

        If ``pm`` (ProcessManager) is supplied, free memory is reduced by
        the sum of all running process simulated RSS values.
        Otherwise, a static mid-load snapshot is used.
        """
        used_kb = 4_096_000   # baseline OS overhead: 4 GB
        if pm is not None:
            # Each running process contributes a rough RSS estimate
            try:
                for proc in pm.all_procs():
                    # 64 MB per process is a rough simulation
                    used_kb += 65_536
            except Exception:
                pass

        free_kb      = max(0, cls._MEM_TOTAL_KB - used_kb)
        available_kb = free_kb + cls._MEM_CACHED_KB
        buffers_kb   = 512_000

        return (
            f"MemTotal:       {cls._MEM_TOTAL_KB:>12} kB\n"
            f"MemFree:        {free_kb:>12} kB\n"
            f"MemAvailable:   {available_kb:>12} kB\n"
            f"Buffers:        {buffers_kb:>12} kB\n"
            f"Cached:         {cls._MEM_CACHED_KB:>12} kB\n"
            f"SwapTotal:               0 kB\n"
            f"SwapFree:                0 kB\n"
        )

    @classmethod
    def cpuinfo(cls) -> str:
        """
        /proc/cpuinfo — minimal processor descriptor.
        """
        blocks = []
        for i in range(cls._CPU_CORES):
            blocks.append(
                f"processor\t: {i}\n"
                f"model name\t: {cls._CPU_MODEL}\n"
                f"cpu MHz\t\t: 2600.000\n"
                f"cache size\t: 12288 KB\n"
                f"siblings\t: {cls._CPU_CORES}\n"
                f"cpu cores\t: {cls._CPU_CORES}\n"
                f"\n"
            )
        return "".join(blocks)

    @classmethod
    def version(cls) -> str:
        """
        /proc/version — kernel version string.
        """
        return (
            "Linux version 5.15.0-qvault (qvault@q-vault) "
            "(gcc version 11.3.0) "
            "#1 SMP PREEMPT Q-Vault OS 2.0\n"
        )

    @classmethod
    def loadavg(cls) -> str:
        """
        /proc/loadavg — load average over 1, 5, and 15 minutes.
        Format: "1min 5min 15min running/total last_pid"
        """
        # Simulate a healthy lightly-loaded system
        return "0.42 0.38 0.31 2/187 4012\n"

    @classmethod
    def net_dev(cls) -> str:
        """
        /proc/net/dev — network interface byte/packet counters.
        """
        uptime_s = int(time.time() - _BOOT_TIME)
        # Simulate modest traffic growth proportional to uptime
        rx_bytes = 1_234_567 + (uptime_s * 1_024)
        tx_bytes =   456_789 + (uptime_s *   512)
        return (
            "Inter-|   Receive                                                "
            "|  Transmit\n"
            " face |bytes    packets errs drop fifo frame compressed multicast"
            "|bytes    packets errs drop fifo colls carrier compressed\n"
            f"    lo: 65536      512    0    0    0     0          0         0"
            f" 65536      512    0    0    0     0       0          0\n"
            f"  eth0: {rx_bytes} {uptime_s * 12}    0    0    0     0          0"
            f"         0 {tx_bytes} {uptime_s * 8}    0    0    0     0       0"
            f"          0\n"
        )

    # ── Per-process /proc/<pid>/ files ────────────────────────────────────

    @classmethod
    def pid_status(cls, pid: int, name: str, owner: str,
                   status: str, vm_rss_kb: int = 65_536) -> str:
        """
        /proc/<pid>/status — process status file.

        Parameters
        ----------
        pid : int
        name : str
            Process name (argv[0] basename).
        owner : str
            Username ("root" or "user").
        status : str
            ProcessManager status string ("running", "sleeping", etc.)
        vm_rss_kb : int
            Simulated resident set size in kB.
        """
        uid = 0 if owner == "root" else 1000
        state_char = {"running": "R", "sleeping": "S",
                      "stopped": "T", "completed": "Z"}.get(status, "S")
        return (
            f"Name:\t{name}\n"
            f"State:\t{state_char} ({status})\n"
            f"Pid:\t{pid}\n"
            f"PPid:\t1\n"
            f"Uid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
            f"Gid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
            f"VmRSS:\t{vm_rss_kb:>8} kB\n"
            f"VmSize:\t{vm_rss_kb * 2:>7} kB\n"
            f"Threads:\t1\n"
        )

    @classmethod
    def pid_cmdline(cls, argv: list[str]) -> str:
        """
        /proc/<pid>/cmdline — NUL-separated command line.
        The terminal renders this as a plain string.
        """
        return "\x00".join(argv) + "\x00"

    @classmethod
    def pid_stat(cls, pid: int, name: str, status: str,
                 start_time_offset: float = 0.0) -> str:
        """
        /proc/<pid>/stat — single-line stat file (simplified subset).
        Only the fields commonly read by tools like ``ps`` are included.
        """
        state_char = {"running": "R", "sleeping": "S",
                      "stopped": "T", "completed": "Z"}.get(status, "S")
        start_jiffies = int(start_time_offset * 100)
        return (
            f"{pid} ({name}) {state_char} 1 {pid} {pid} 0 -1 "
            f"4194304 0 0 0 0 10 5 0 0 20 0 1 0 "
            f"{start_jiffies} 671744 16384\n"
        )

    # ── Tree builder ──────────────────────────────────────────────────────

    @classmethod
    def build_proc_tree(cls, pm=None) -> dict:
        """
        Build a complete /proc subtree dict for injection into the VirtualFS tree.

        Called by VirtualFS._refresh_proc() to regenerate the /proc node
        on every access.  Returns a fresh dict each time so the content
        is always current.

        Parameters
        ----------
        pm : ProcessManager | None
            If supplied, per-PID subdirectories are populated from live data.
        """
        # Import Meta here to avoid circular import at module level
        from core.filesystem import Meta

        def _file(content: str, owner: str = "root",
                  readable: bool = True) -> "Meta":
            return Meta(content, owner=owner, readable_by_user=readable)

        def _dir(owner: str = "root") -> dict:
            return {"_meta": Meta("", owner=owner)}

        tree: dict = {
            "_meta":   Meta("", owner="root"),
            "uptime":  _file(cls.uptime()),
            "meminfo": _file(cls.meminfo(pm)),
            "cpuinfo": _file(cls.cpuinfo()),
            "version": _file(cls.version()),
            "loadavg": _file(cls.loadavg()),
            "net": {
                "_meta": Meta("", owner="root"),
                "dev":   _file(cls.net_dev()),
            },
        }

        # Per-process directories
        if pm is not None:
            try:
                now = time.time()
                for proc_dict in pm.all_procs():
                    pid    = proc_dict["pid"]
                    name   = proc_dict["name"]
                    owner  = proc_dict.get("owner", "root")
                    status = proc_dict.get("status", "sleeping")
                    argv   = proc_dict.get("argv", [name])

                    pid_dir: dict = {
                        "_meta":   Meta("", owner=owner),
                        "status":  _file(
                            cls.pid_status(pid, name, owner, status),
                            owner=owner,
                        ),
                        "cmdline": _file(cls.pid_cmdline(argv), owner=owner),
                        "stat":    _file(
                            cls.pid_stat(pid, name, status),
                            owner=owner,
                        ),
                    }
                    tree[str(pid)] = pid_dir
            except Exception:
                # If PM is unavailable, /proc still exists — just without PIDs
                pass

        return tree
