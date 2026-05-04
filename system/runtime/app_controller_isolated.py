import multiprocessing
import logging
import time
import threading
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from system.runtime.ipc import AsyncIPCBridge, IPCProtocol
from system.runtime.app_runner import run_isolated_app

logger = logging.getLogger("runtime.isolated_controller")

class RuntimeState(Enum):
    BOOTING = 0
    RUNNING = 1
    CONGESTED = 2
    THROTTLED = 3
    RECOVERING = 4
    TERMINATED = 5
    BOOT_FAILED = 6

class IsolatedAppController(QObject):
    """
    Non-UI High-Performance Controller for Isolated Applications (v1.0).
    Handles IPC, Governance, and Lifecycle in a background thread.
    """
    # Signals for UI Layer
    state_changed = pyqtSignal(object)  # RuntimeState
    metrics_updated = pyqtSignal(float, int, int)  # hz, qsize, trust
    crashed = pyqtSignal(str) # reason
    event_received = pyqtSignal(str, object) # event, data
    
    def __init__(self, app_id: str, instance_id: str, secure_api: Any = None, boot_timeout: float = 5.0):
        super().__init__()
        self.app_id = app_id
        self.instance_id = instance_id
        self.api = secure_api
        self.boot_timeout = boot_timeout
        
        self.session_secret = uuid.uuid4().hex
        self.state = RuntimeState.BOOTING # 🟢 Phase 1.2: Initial State
        self.running = False
        
        self._pending_calls = {}
        self._handshake_done = False
        self._ipc_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock() # 🟢 Phase 1.2.1: Lifecycle Serialization
        
        # Performance Tracking
        self._last_metrics_emit = 0.0
        self._last_congestion_signal = 0.0
        self._last_metrics_log = 0.0
        
        self._proc = None
        self.bridge = None
        self._drain_thread = None
        self._boot_timer = None
        
        # Store launch info for restarts
        self._last_launch_info = (None, None)

    def start(self, module_path: str, class_name: str):
        """Launches the isolated process and starts the drain thread."""
        with self._lifecycle_lock:
            self._last_launch_info = (module_path, class_name)
            self._parent_conn, self._child_conn = multiprocessing.Pipe()
            self.bridge = AsyncIPCBridge(self._parent_conn, self.session_secret)
            
            self._proc = multiprocessing.Process(
                target=run_isolated_app,
                args=(
                    self._child_conn, 
                    self.app_id, 
                    self.instance_id,
                    module_path,
                    class_name,
                    self.session_secret
                ),
                daemon=True
            )
            self._proc.start()
            self.running = True
            
            # Start Background Drain Thread
            self._drain_thread = threading.Thread(target=self._drain_loop, daemon=True)
            self._drain_thread.start()
            
            # 🟢 Phase 1.2: Handshake Timeout Guard
            if self._boot_timer: self._boot_timer.cancel()
            self._boot_timer = threading.Timer(self.boot_timeout, self._verify_handshake)
            self._boot_timer.start()
            
            logger.info(f"[Controller] Started {self.app_id} (PID: {self._proc.pid})")

    def restart(self):
        """Authoritative Safe Restart with Debounce (Phase 1.2)."""
        with self._lifecycle_lock:
            logger.info(f"[Controller] Restarting {self.app_id}...")
            self.stop_locked()
            self.state = RuntimeState.BOOTING
            self.state_changed.emit(self.state)
            
        module_path, class_name = self._last_launch_info
        if module_path and class_name:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, lambda: self.start(module_path, class_name))

    def start_locked(self, module_path, class_name):
        """Internal start helper that assumes lock is already held."""
        self._last_launch_info = (module_path, class_name)
        self._parent_conn, self._child_conn = multiprocessing.Pipe()
        self.bridge = AsyncIPCBridge(self._parent_conn, self.session_secret)
        self._proc = multiprocessing.Process(
            target=run_isolated_app,
            args=(self._child_conn, self.app_id, self.instance_id, module_path, class_name, self.session_secret),
            daemon=True
        )
        self._proc.start()
        self.running = True
        self._drain_thread = threading.Thread(target=self._drain_loop, daemon=True)
        self._drain_thread.start()
        if self._boot_timer: self._boot_timer.cancel()
        self._boot_timer = threading.Timer(self.boot_timeout, self._verify_handshake)
        self._boot_timer.start()

    def _verify_handshake(self):
        if not self._handshake_done and self.running:
            logger.critical(f"[SECURITY] Handshake Timeout for {self.app_id}.")
            self._handle_shutdown("INITIALIZATION_TIMEOUT", state=RuntimeState.BOOT_FAILED)

    def stop(self):
        """Authoritative cleanup of process and thread resources."""
        with self._lifecycle_lock:
            self.stop_locked()

    def stop_locked(self):
        """Internal stop helper that assumes lock is already held."""
        self.running = False
        if self._boot_timer: self._boot_timer.cancel()
        
        if self.bridge:
            self.bridge.stop()
            
        if self._proc and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=0.1)
            
        with self._ipc_lock:
            self._pending_calls.clear()
            
        logger.info(f"[Controller] Stopped {self.app_id} (Locked)")

    def _drain_loop(self):
        """
        Kernel-grade drain loop. 
        Runs in background thread. Communicates via Signals only.
        """
        while self.running:
            try:
                # 1. Process Check
                if self._proc and not self._proc.is_alive():
                    self._handle_shutdown("Engine Disconnected")
                    break

                # 2. Extract Message
                packet = self.bridge.get_message()
                
                # 3. Handle Metrics & State Governance (Every ~16ms)
                self._update_governance()

                if not packet:
                    if self.bridge.queue.empty():
                        time.sleep(0.02)
                    else:
                        time.sleep(0.005)
                    continue

                self._process_packet(packet)

            except Exception as e:
                logger.exception(f"[Controller] Error in drain loop for {self.app_id}")
                time.sleep(0.1)

    def _update_governance(self):
        """Batch metrics and monitor trust/backpressure."""
        now = time.perf_counter()
        if now - self._last_metrics_emit < 0.016: # ~60FPS
            return
            
        from system.runtime_manager import AppRuntimeManager
        rm = AppRuntimeManager()
        record = rm.get_record(self.instance_id)
        if not record: return

        qsize = self.bridge.queue.qsize()
        
        # Update Record Metrics
        if now - record.last_hz_calc_time >= 1.0:
            dt = now - record.last_hz_calc_time
            record.msg_hz = (record.total_msgs_handled - record.last_msgs_count) / dt
            record.last_msgs_count = record.total_msgs_handled
            record.last_hz_calc_time = now
            
            # Periodic Audit Log
            if now - self._last_metrics_log >= 10.0:
                rm.log_event("METRICS_SNAPSHOT", {
                    "app_id": self.app_id,
                    "msg_hz": round(record.msg_hz, 2),
                    "q_sat": qsize,
                    "trust": record.trust_score
                })
                self._last_metrics_log = now

        # ── State Machine Transitions ──
        old_state = self.state
        if record.trust_score < 20:
             # Global Kill check moved to handle_shutdown for clarity
             self._handle_shutdown("UNTRUSTED_TERMINATION")
             return

        if qsize > 50:
            self.state = RuntimeState.CONGESTED
        elif record.local_throttled or record.trust_score < 70:
            self.state = RuntimeState.THROTTLED
        elif old_state == RuntimeState.CONGESTED and qsize < 10:
            self.state = RuntimeState.RECOVERING
        else:
            self.state = RuntimeState.RUNNING

        if self.state != old_state:
            self.state_changed.emit(self.state)

        # Emit Batched Metrics Signal
        self.metrics_updated.emit(record.msg_hz, qsize, record.trust_score)
        self._last_metrics_emit = now

    def _process_packet(self, packet: dict):
        """Identifies and routes IPC packets."""
        from system.runtime_manager import AppRuntimeManager
        rm = AppRuntimeManager()
        record = rm.get_record(self.instance_id)
        if record:
            record.total_msgs_handled += 1
            record.peak_queue_size = max(record.peak_queue_size, self.bridge.queue.qsize())

        payload = packet.get('payload_dict')
        mtype = packet.get("type")
        msg_id = packet.get("id")

        # ── Security: Hardened Handshake ──
        if mtype == IPCProtocol.TYPE_EVENT and payload.get("event") == "HANDSHAKE":
            if self._handshake_done: return
            expected_auth = IPCProtocol.sign(self.instance_id, self.session_secret)
            if payload.get("auth") == expected_auth:
                self._handshake_done = True
                logger.info(f"[Controller] Identity Verified: {self.app_id}")
            else:
                self._handle_shutdown("AUTH_SPOOFING_FAILURE")
            return
            
        if not self._handshake_done: return

        # ── Routing ──
        if mtype == IPCProtocol.TYPE_RET:
            with self._ipc_lock:
                callback = self._pending_calls.pop(msg_id, None)
            if callback: 
                # Note: Callbacks run in the DRAIN THREAD. 
                # SecureAPI should handle its own signal-to-UI if needed.
                callback(payload)
        elif mtype == IPCProtocol.TYPE_EVENT:
            event = payload.get("event")
            if event == "system_failure":
                self._handle_shutdown(payload.get("data", "Unknown Error"))
            else:
                self.event_received.emit(event, payload.get("data"))
        elif mtype == IPCProtocol.TYPE_CALL:
            self._dispatch_call(msg_id, payload)

    def _dispatch_call(self, msg_id: str, payload: dict):
        method = payload.get("method")
        if method not in IPCProtocol.ALLOWED_METHODS:
            self.bridge.send(IPCProtocol.TYPE_RET, msg_id, {"status": "error", "error": "FORBIDDEN"})
            return
            
        try:
            res = self._route_secure_api(method, payload.get("args", []), payload.get("kwargs", {}))
            self.bridge.send(IPCProtocol.TYPE_RET, msg_id, {"status": "success", "value": res})
        except Exception:
            logger.exception(f"Internal SecureAPI Failure: {method}")
            self.bridge.send(IPCProtocol.TYPE_RET, msg_id, {"status": "error", "error": "INTERNAL_ERROR"})

    def _route_secure_api(self, method, args, kwargs):
        parts = method.split(".")
        namespace, func_name = parts[0], parts[1]
        guard = getattr(self.api, namespace, None)
        if guard:
            func = getattr(guard, func_name, None)
            if func: return func(*args, **kwargs)
        return None

    def call_remote(self, method: str, *args, callback=None, **kwargs):
        """Thread-safe entry point for UI calls to the child process."""
        if self.bridge and self.bridge.queue.qsize() > 80:
            logger.warning(f"[Controller] Dropping call {method} due to IPC congestion")
            return

        msg_id = uuid.uuid4().hex[:8]
        with self._ipc_lock:
            if callback: self._pending_calls[msg_id] = callback
        if self.bridge:
            self.bridge.send(IPCProtocol.TYPE_CALL, msg_id, {"method": method, "args": args, "kwargs": kwargs})

    def _handle_shutdown(self, reason: str, state=RuntimeState.TERMINATED):
        self.stop()
        self.state = state
        try:
            self.state_changed.emit(self.state)
            self.crashed.emit(reason)
        except RuntimeError:
            pass # QObject has been deleted by Qt

