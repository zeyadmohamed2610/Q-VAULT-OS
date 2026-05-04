import json
import logging
import time
import hmac
import hashlib
import threading
import queue
from typing import Any, Optional, Dict, Set
from multiprocessing.connection import Connection

logger = logging.getLogger("system.ipc")

class IPCProtocol:
    """
    Standard Logic for the Q-Vault IPC Protocol (v1.0 Ultimate).
    Includes HMAC-based signing and identity-bound handshakes.
    """
    TYPE_CALL  = "CALL"
    TYPE_RET   = "RET"
    TYPE_EVENT = "EVENT"

    ALLOWED_METHODS: Set[str] = {
        "process.Popen", "process.run", "process.kill",
        "fs.read_file", "fs.write_file", "fs.list_dir", "fs.exists",
        "net.ping", "net.lookup", "vault.status", "vault.get_token",
        "system.list_instances", "system.get_health",
        "intel.analyze_text", "intel.get_shadow_status", "intel.get_audit_summary", "intel.get_system_status",
        "boot_terminal", "execute_command"
    }

    @staticmethod
    def sign(payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode('utf-8'), 
            payload.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify(payload: str, signature: str, secret: str) -> bool:
        expected = IPCProtocol.sign(payload, secret)
        return hmac.compare_digest(expected, signature)

class AsyncIPCBridge:
    """
    Ultimate Hardened Async Bridge (Phase 16.7).
    Featuring Bifurcated Locking, Nonce Capping, and Congestion Control.
    """
    def __init__(self, connection: Connection, secret_key: str):
        self.conn = connection
        self.secret_key = secret_key
        self.queue = queue.Queue(maxsize=100)
        self.running = True
        
        # ── Phase 16.7: Bifurcated Locking ──
        self._state_lock = threading.Lock() # For seen_ids, counters
        self._send_lock  = threading.Lock() # Exclusive for blocking IO
        
        # Security: Hard-capped Nonce Management
        self._seen_ids: Dict[str, float] = {} # msg_id -> expiry_ts
        self._msg_count = 0
        self._last_reset = time.time()
        
        self._listener = threading.Thread(target=self._listen, daemon=True)
        self._listener.start()

    def _listen(self):
        """Dedicated thread with fail-safe error handling and rate recovery."""
        while self.running:
            try:
                now = time.time()
                # Rate Limiting Logic (State Locked)
                with self._state_lock:
                    if now - self._last_reset > 1.0:
                        self._msg_count = 0
                        self._last_reset = now
                
                if self.conn.poll(0.1):
                    with self._state_lock:
                        self._msg_count += 1
                        is_over_limit = self._msg_count > 150
                    
                    if is_over_limit:
                        logger.warning("[IPC] Package Dropped: Rate limit exceeded")
                        self.conn.recv_bytes() # Drain to clear pipe
                        continue
                        
                    data = self.conn.recv_bytes()
                    if not self.queue.full():
                        self.queue.put(data)
                    else:
                        logger.warning("[IPC] Package Dropped: Internal Queue Full")
            except (EOFError, BrokenPipeError):
                self.running = False
            except Exception:
                logger.exception("[IPC Bridge] FATAL: Listener thread crashed")
                self.running = False

    def _cleanup_seen_ids(self, now: float):
        """Removes expired entries. Called while state_lock is held."""
        expired = [mid for mid, exp in self._seen_ids.items() if now > exp]
        for mid in expired: 
            del self._seen_ids[mid]

    def get_message(self) -> Optional[Dict]:
        """Authenticated drain with Nonce Capping and Zero-Leak enforcement."""
        try:
            raw = self.queue.get_nowait()
            packet = json.loads(raw.decode('utf-8'))
            now = time.time()
            
            # 1. TTL Check
            ts = packet.get('ts', 0)
            if abs(now - ts) > 5.0:
                logger.warning("[IPC] Dropped Stale Packet")
                return None
            
            # 2. Nonce Map Management (Phase 16.7: LRU/Cap)
            msg_id = packet.get('id')
            with self._state_lock:
                self._cleanup_seen_ids(now)
                
                # Check for ID Replay
                if msg_id in self._seen_ids:
                    logger.warning(f"[IPC] Replay Blocked: {msg_id}")
                    return None
                
                # Enforce Capacity (1000 entries)
                if len(self._seen_ids) >= 1000:
                    logger.critical("[IPC] Nonce Map Full: System under DoS pressure. Rejecting new IDs.")
                    return None
                
                self._seen_ids[msg_id] = now + 10.0

            # 3. Cryptographic Verification
            if not IPCProtocol.verify(packet['payload'], packet['sig'], self.secret_key):
                logger.critical("[IPC] AUTH FAILURE: Dropping tampered packet")
                return None
            
            # 4. Strict Type Validation
            payload_str = packet.get("payload")
            payload = json.loads(payload_str)
            if not isinstance(payload, dict):
                return None
                
            packet['payload_dict'] = payload
            return packet
        except (queue.Empty, json.JSONDecodeError):
            return None
        except Exception:
            logger.exception("[IPC Bridge] Packet processing error")
            return None

    def send(self, mtype: str, msg_id: str, payload: Any):
        """Packs, signs, and sends data with non-nested send lock."""
        raw_payload = json.dumps(payload)
        sig = IPCProtocol.sign(raw_payload, self.secret_key)
        
        packet = {
            "v": "1.3",
            "type": mtype,
            "id": msg_id,
            "payload": raw_payload,
            "sig": sig,
            "ts": time.time()
        }
        
        # 🟢 Fix: Bifurcated Locking (Phase 16.7)
        # We only lock the blocking IO operation.
        with self._send_lock:
            try:
                self.conn.send_bytes(json.dumps(packet).encode('utf-8'))
            except (EOFError, BrokenPipeError):
                self.running = False

    def stop(self):
        self.running = False
