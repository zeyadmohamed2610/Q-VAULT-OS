"""
system/sandbox/network_guard.py
─────────────────────────────────────────────────────────────────────────────
Safe Network Abstraction Layer — Controlled Enforcement.

Apps MUST use these wrappers instead of raw socket/subprocess/requests calls.

Allowed operations:
  ping(host, count)       -> calls system ping via ProcessGuard
  port_scan(host, ports)  -> TCP connect-only via controlled socket wrapper
  get_local_info()        -> read-only hostname / local IP
  is_wan_allowed(app_id)  -> checks manifest network_access == "wan"

Blocked:
  Raw socket.socket(AF_INET, SOCK_RAW, ...)  -> never
  socket.socket(AF_PACKET, ...)             -> never
  requests / urllib to arbitrary WAN URLs   -> denied unless manifest says "wan"
"""

import logging
import socket
import time
import random
from collections import deque
from typing import List, Dict, Tuple, Optional
from .process_guard import ProcessGuard
from .permissions import PM_GUARD
from system.runtime_manager import RUNTIME_MANAGER

logger = logging.getLogger("sandbox.network_guard")


class NetworkGuard:
    """
    High-level safe networking API injected into every app via SecureAPI.
    Replaces direct subprocess.run(ping), socket.socket(), etc.
    """

    def __init__(self, app_id: str, api=None):
        self.app_id = app_id
        self.api = api # Reference to SecureAPI for lock checks
        self._process = ProcessGuard(app_id, api=api)
        self._call_window = deque() # Sliding window for rate limiting

    def _is_url_malicious(self, url: str) -> Optional[str]:
        """Returns a reason string if URL is malicious, else None."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            host = (parsed.hostname or "").lower()

            # 1. Scheme Validation
            if scheme not in ["http", "https"]:
                return f"Forbidden scheme: {scheme}"

            # 2. SSRF / Localhost Protection
            forbidden_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
            if host in forbidden_hosts:
                return f"SSRF Attack Blocked: {host}"
            
            return None
        except Exception:
            return "Invalid URL format"

    def _enforce_rate_limit(self):
        """Graduated Penalty Rate Limiting based on Hybrid Model."""
        now = time.time()
        # 1. Clean old timestamps (>1s)
        while self._call_window and now - self._call_window[0] > 1.0:
            self._call_window.popleft()
        
        count = len(self._call_window)
        self._call_window.append(now)

        if count < 10:
            return # Within normal limits

        # 2. Hybrid Penalty Calculation
        overflow = count - 10

        # Use instance_id when available — the registry is keyed on instance_id
        # (e.g. "bad_actor_app_abc123_9f2e"), NOT on bare app_id.
        # Falling back to app_id keeps the call safe for callers that construct
        # a guard directly without an API wrapper.
        target_id = (self.api.instance_id if self.api else None) or self.app_id

        if 1 <= overflow <= 2:
            # Level 1: Soft Warning (Log only)
            logger.debug("[NetworkGuard] Rate Limit Soft Warning for '%s' (Calls: %d)", self.app_id, count)
        
        elif 3 <= overflow <= 5:
            # Level 2: Suspicious Behavior (-5 Trust)
            RUNTIME_MANAGER.apply_penalty(target_id, -5, f"Suspicious network activity speed ({count} calls/sec)")
            raise PermissionError(f"[Sandbox] Rate Limit Exceeded (Suspicious Activity). Please slow down.")

        elif overflow > 5:
            # Level 3: Confirmed Abuse (-30 Trust / Violation)
            RUNTIME_MANAGER.report_violation(target_id, f"Network Flooding Attempt detected ({count} calls/sec)")
            raise PermissionError(f"[Sandbox] CRITICAL: Network Flooding Blocked.")

    # ── Ping ─────────────────────────────────────────────────────────────────

    def ping(
        self,
        host: str,
        count: int = 4,
        *,
        result_callback=None,
    ) -> List[Dict]:
        """
        Safe ping.  Uses ProcessGuard -> subprocess ping.
        result_callback(text: str, color: str) called for each line (for Qt UIs).
        Returns list of dicts with per-packet results.
        """
        self._enforce_rate_limit()
        PM_GUARD.check(self.app_id, "network_access", host)

        import platform, time as _time

        host = host.strip()

        # Injection guard: reject host strings with shell chars
        _BAD = set("&|;$`\n<>(){}[]")
        if any(c in host for c in _BAD):
            msg = f"[NetworkGuard] Injection detected in host '{host}' — blocked."
            logger.critical(msg)
            if result_callback:
                result_callback(msg, "#ff4444")
            return []

        results: List[Dict] = []
        cmd = (
            ["ping", "-n", str(count), host]
            if platform.system() == "Windows"
            else ["ping", "-c", str(count), host]
        )

        # Stage B: Spawn Control Hook
        import contextlib
        token_ctx = self.api.worker_token("network") if self.api else contextlib.nullcontext()

        with token_ctx:
            try:
                proc = self._process.run(
                    cmd, capture_output=True, text=True, timeout=count * 3
                )
                if result_callback:
                    for line in proc.stdout.splitlines():
                        result_callback(line, "#00d4ff")
                results.append({"host": host, "returncode": proc.returncode})
            except Exception as exc:
                logger.warning("[NetworkGuard] ping failed: %s — simulating.", exc)
                # Controlled fallback: simulated result
                for i in range(1, count + 1):
                    t = round(random.uniform(8.0, 42.0), 1)
                    msg = f"  {i}: {host}  time={t}ms  TTL=64  (simulated)"
                    if result_callback:
                        result_callback(msg, "#888888")
                    results.append({"host": host, "seq": i, "time_ms": t, "simulated": True})

        return results

    # ── Port Scan ─────────────────────────────────────────────────────────────

    def port_scan(
        self,
        host: str,
        ports: Optional[List[int]] = None,
        timeout: float = 0.5,
        result_callback=None,
    ) -> List[Dict]:
        """
        Safe TCP connect scan — NO raw sockets.
        result_callback(port: int, service: str, status: str) for Qt UIs.
        """
        self._enforce_rate_limit()
        PM_GUARD.check(self.app_id, "network_access", host)

        _DEFAULT_PORTS = [
            21, 22, 23, 25, 53, 80, 110, 143, 443, 465,
            587, 993, 995, 1433, 3306, 3389, 5432, 5900,
            6379, 8080, 8443, 8888, 9000, 9200, 27017,
        ]
        _SERVICES = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
            53: "dns", 80: "http", 110: "pop3", 143: "imap",
            443: "https", 465: "smtps", 587: "submission",
            993: "imaps", 995: "pop3s", 1433: "mssql",
            3306: "mysql", 3389: "rdp", 5432: "postgres",
            5900: "vnc", 6379: "redis", 8080: "http-alt",
            8443: "https-alt", 8888: "jupyter", 9000: "middleware",
            9200: "elasticsearch", 27017: "mongodb",
        }

        ports = ports or _DEFAULT_PORTS
        results: List[Dict] = []

        import contextlib
        token_ctx = self.api.worker_token("network") if self.api else contextlib.nullcontext()

        with token_ctx:
            for port in ports:
                svc = _SERVICES.get(port, "unknown")
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    code = s.connect_ex((host, port))
                    s.close()
                    status = "open" if code == 0 else "closed"
                except Exception:
                    status = "filtered"

                r = {"port": port, "service": svc, "status": status}
                results.append(r)
                if result_callback:
                    result_callback(port, svc, status)

        return results

    # ── Local Info ────────────────────────────────────────────────────────────

    def get_local_info(self) -> Dict[str, str]:
        """Returns read-only local network information. Never contacts WAN."""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname, local_ip = "q-vault", "127.0.0.1"

        return {
            "hostname": hostname,
            "local_ip": local_ip,
            "gateway": "192.168.1.1 (simulated)",
            "dns_primary": "8.8.8.8",
            "dns_secondary": "8.8.4.4",
        }

    # ── HTTP Requests ─────────────────────────────────────────────────────────

    def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        timeout: float = 10.0
    ) -> Dict:
        """
        Safe HTTP request wrapper.
        Enforces PM_GUARD network checks and limits execution time.
        Returns a dict: {'status': int, 'content': str, 'error': str}
        """
        self._enforce_rate_limit()
        if self.api:
            self.api.check_api_lock("network")

        # 1. Internal Malicious URL Filter (SSRF/Protocols)
        attack_reason = self._is_url_malicious(url)
        if attack_reason:
            logger.critical("[NetworkGuard][ATTACK_BLOCKED] App='%s' URL='%s' Reason='%s'",
                            self.app_id, url, attack_reason)
            return {"status": 403, "content": None, "error": f"Access Denied: {attack_reason}"}

        import urllib.request
        import urllib.error
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or url
        PM_GUARD.check(self.app_id, "network_access", host)

        import contextlib
        token_ctx = self.api.worker_token("network") if self.api else contextlib.nullcontext()

        with token_ctx:
            try:
                # Build a proper Request object so custom headers and method work
                # and so `req` is always defined before urlopen() is called.
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers=headers or {},
                    method=method.upper(),
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='replace')
                    return {
                        "status": response.status,
                        "content": content,
                        "error": None
                    }
            except urllib.error.HTTPError as e:
                logger.warning("[NetworkGuard] HTTP error for %s: %s", url, e.code)
                return {"status": e.code, "content": None, "error": str(e)}
            except urllib.error.URLError as e:
                logger.warning("[NetworkGuard] URL error for %s: %s", url, e.reason)
                return {"status": 0, "content": None, "error": str(e.reason)}
            except Exception as e:
                logger.warning("[NetworkGuard] Request failed to %s: %s", url, str(e))
                return {"status": 0, "content": None, "error": str(e)}

