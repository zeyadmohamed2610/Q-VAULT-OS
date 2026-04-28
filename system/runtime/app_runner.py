import sys
import os
import logging
import time
import threading
import queue
from typing import Any

# Add workspace to path
sys.path.append(os.getcwd())

logger = logging.getLogger("system.app_runner")

class GovernedSpawnHandle:
    def __init__(self, data):
        self._data = data
        self.returncode = data.get("returncode", 0)
        self.stdout = data.get("stdout", "")
        self.stderr = data.get("stderr", "")
    def communicate(self):
        return self.stdout, self.stderr

class ResponseManager:
    def __init__(self):
        self._responses = {} 
        self._lock = threading.Lock()
    def get_queue(self, msg_id: str) -> queue.Queue:
        with self._lock:
            q = queue.Queue(maxsize=1)
            self._responses[msg_id] = q
            return q
    def deliver(self, msg_id: str, payload: Any):
        with self._lock:
            if msg_id in self._responses:
                try: self._responses[msg_id].put_nowait(payload)
                except queue.Full: pass
    def cleanup(self, msg_id: str):
        with self._lock: self._responses.pop(msg_id, None)

class RemoteBaseProxy:
    def __init__(self, bridge: Any, response_mgr: ResponseManager):
        self.bridge = bridge
        self.response_mgr = response_mgr
    def _sync_call(self, method: str, *args, **kwargs) -> Any:
        import uuid
        msg_id = uuid.uuid4().hex[:8]
        q = self.response_mgr.get_queue(msg_id)
        try:
            self.bridge.send("CALL", msg_id, {"method": method, "args": args, "kwargs": kwargs})
            return q.get(timeout=5.0)
        except queue.Empty: return {"error": "TIMEOUT"}
        finally: self.response_mgr.cleanup(msg_id)

class RemoteProcessProxy(RemoteBaseProxy):
    def Popen(self, cmd, **kwargs):
        res = self._sync_call("process.Popen", cmd, **kwargs)
        return GovernedSpawnHandle(res.get("value", {}) if isinstance(res, dict) else {})
    def kill(self, pid):
        return self._sync_call("process.kill", pid)

class RemoteFSProxy(RemoteBaseProxy):
    def read_file(self, path):
        res = self._sync_call("fs.read_file", path)
        return res.get("value") if isinstance(res, dict) else None
    def list_dir(self, path="."):
        res = self._sync_call("fs.list_dir", path)
        return res.get("value") if isinstance(res, dict) else []
    def write_file(self, path, content):
        return self._sync_call("fs.write_file", path, content)

class RemoteNetProxy(RemoteBaseProxy):
    def ping(self, host):
        res = self._sync_call("net.ping", host)
        return res.get("value") if isinstance(res, dict) else False

class RemoteSecureAPI:
    def __init__(self, bridge: Any, response_mgr: ResponseManager, instance_id: str):
        self.process = RemoteProcessProxy(bridge, response_mgr)
        self.fs = RemoteFSProxy(bridge, response_mgr)
        self.net = RemoteNetProxy(bridge, response_mgr)
        self.instance_id = instance_id

def run_isolated_app(conn: "Connection", app_id: str, instance_id: str, module_path: str, class_name: str, secret_key: str):
    """
    Subprocess Entry Point with Hardened Identity & Congestion Control.
    """
    import importlib
    from PyQt5.QtCore import QCoreApplication, QTimer
    from system.runtime.ipc import AsyncIPCBridge, IPCProtocol
    
    app = QCoreApplication(sys.argv)
    bridge = AsyncIPCBridge(conn, secret_key)
    
    try:
        # 1. ── Hardened Identity Handshake (Phase 16.7) ──
        # Provide proof of secret knowledge bound to this instance_id
        from system.runtime.ipc import IPCProtocol
        auth_tag = IPCProtocol.sign(instance_id, secret_key)
        bridge.send(IPCProtocol.TYPE_EVENT, "0", {"event": "HANDSHAKE", "auth": auth_tag})
        
        response_mgr = ResponseManager()
        remote_api = RemoteSecureAPI(bridge, response_mgr, instance_id)
        
        mod = importlib.import_module(module_path)
        app_cls = getattr(mod, class_name)
        engine = app_cls(secure_api=remote_api)
        
        # 2. ── Signal Bridging (Phase 16.8) ──
        # Connect known engine signals to IPC events
        if hasattr(engine, "output_ready"):
            engine.output_ready.connect(
                lambda data: bridge.send(IPCProtocol.TYPE_EVENT, "0", {"event": "output_ready", "data": data})
            )
        if hasattr(engine, "prompt_update"):
            engine.prompt_update.connect(
                lambda ev, data: bridge.send(IPCProtocol.TYPE_EVENT, "0", {"event": ev, "data": data})
            )
        if hasattr(engine, "password_mode"):
            engine.password_mode.connect(
                lambda ev, data: bridge.send(IPCProtocol.TYPE_EVENT, "0", {"event": ev, "data": data})
            )

        def listener_drain():
            while True:
                packet = bridge.get_message()
                if not packet: break
                mtype, msg_id, payload = packet.get("type"), packet.get("id"), packet['payload_dict']
                
                # ── Phase 16.7: Congestion Control ──
                if mtype == IPCProtocol.TYPE_EVENT and payload.get("event") == "SYSTEM_CONGESTION":
                    # Soft feedback: slow down the polling timer
                    if timer.interval() < 50:
                        timer.setInterval(timer.interval() + 10)
                    continue

                if mtype == IPCProtocol.TYPE_RET: response_mgr.deliver(msg_id, payload)
                elif mtype == IPCProtocol.TYPE_CALL: command_queue.put((msg_id, payload))

        command_queue = queue.Queue(maxsize=100)
        def process_commands():
            # Recovery logic: if congestion is clearing, speed up timer slowly
            if command_queue.empty() and timer.interval() > 10:
                timer.setInterval(timer.interval() - 1)

            while not command_queue.empty():
                mid, p = command_queue.get_nowait()
                meth = p.get("method")
                if hasattr(engine, meth):
                    try: 
                        res = getattr(engine, meth)(*p.get("args", []), **p.get("kwargs", {}))
                        bridge.send(IPCProtocol.TYPE_RET, mid, {"status": "success", "value": res})
                    except Exception as e: bridge.send(IPCProtocol.TYPE_RET, mid, {"status": "error", "message": str(e)})
                else: bridge.send(IPCProtocol.TYPE_RET, mid, {"status": "error", "message": "Method Not Found"})

        timer = QTimer()
        timer.timeout.connect(listener_drain)
        timer.timeout.connect(process_commands)
        timer.start(10)
        
        app.exec_()
    except Exception as e:
        logger.exception(f"Isolated Engine '{app_id}' Crashed during init/execution")
        try: bridge.send(IPCProtocol.TYPE_EVENT, "0", {"event": "system_failure", "data": str(e)})
        except: pass
    finally:
        bridge.stop()
