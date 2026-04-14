# =============================================================
#  network_manager.py — Q-Vault OS  |  Network Stack
#
#  Simulated sockets with connection states
# =============================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time
import random


class ConnectionState(Enum):
    CLOSED = "closed"
    LISTENING = "listening"
    CONNECTING = "connecting"
    ESTABLISHED = "established"
    CLOSING = "closing"


@dataclass
class Socket:
    socket_id: int
    protocol: str
    local_addr: str
    local_port: int
    remote_addr: str = ""
    remote_port: int = 0
    state: ConnectionState = ConnectionState.CLOSED
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    data_buffer: list[str] = field(default_factory=list)


class NetworkManager:
    """Simulated network stack with socket management."""

    def __init__(self):
        self._next_socket_id = 1
        self._sockets: dict[int, Socket] = {}
        self._listeners: dict[tuple[str, int], int] = {}  # (addr, port) -> socket_id

    def create_socket(self, protocol: str = "tcp") -> int:
        """Create a new socket."""
        socket_id = self._next_socket_id
        self._next_socket_id += 1

        sock = Socket(
            socket_id=socket_id,
            protocol=protocol,
            local_addr="0.0.0.0",
            local_port=0,
        )

        self._sockets[socket_id] = sock
        return socket_id

    def bind(self, socket_id: int, addr: str, port: int) -> bool:
        """Bind socket to address and port."""
        sock = self._sockets.get(socket_id)
        if not sock:
            return False

        sock.local_addr = addr
        sock.local_port = port
        sock.last_activity = time.time()
        return True

    def listen(self, socket_id: int, backlog: int = 5) -> bool:
        """Start listening on socket."""
        sock = self._sockets.get(socket_id)
        if not sock:
            return False

        sock.state = ConnectionState.LISTENING
        self._listeners[(sock.local_addr, sock.local_port)] = socket_id
        sock.last_activity = time.time()
        return True

    def connect(self, socket_id: int, addr: str, port: int) -> bool:
        """Connect to remote address."""
        sock = self._sockets.get(socket_id)
        if not sock:
            return False

        sock.remote_addr = addr
        sock.remote_port = port
        sock.state = ConnectionState.CONNECTING
        sock.last_activity = time.time()

        if random.random() > 0.1:
            sock.state = ConnectionState.ESTABLISHED
            return True
        return False

    def accept(self, listening_socket_id: int) -> Optional[int]:
        """Accept incoming connection. Returns new socket ID."""
        listener = self._sockets.get(listening_socket_id)
        if not listener or listener.state != ConnectionState.LISTENING:
            return None

        new_id = self.create_socket("tcp")
        new_sock = self._sockets[new_id]
        new_sock.local_addr = listener.local_addr
        new_sock.local_port = listener.local_port
        new_sock.remote_addr = f"192.168.1.{random.randint(2, 254)}"
        new_sock.remote_port = random.randint(1024, 65535)
        new_sock.state = ConnectionState.ESTABLISHED

        return new_id

    def send(self, socket_id: int, data: str) -> int:
        """Send data on socket. Returns bytes sent."""
        sock = self._sockets.get(socket_id)
        if not sock or sock.state != ConnectionState.ESTABLISHED:
            return 0

        sock.data_buffer.append(data)
        sock.last_activity = time.time()
        return len(data)

    def receive(self, socket_id: int, max_bytes: int = 4096) -> Optional[str]:
        """Receive data from socket."""
        sock = self._sockets.get(socket_id)
        if not sock or sock.state != ConnectionState.ESTABLISHED:
            return None

        if not sock.data_buffer:
            return None

        data = sock.data_buffer.pop(0)
        sock.last_activity = time.time()
        return data[:max_bytes]

    def close(self, socket_id: int) -> bool:
        """Close socket."""
        sock = self._sockets.get(socket_id)
        if not sock:
            return False

        sock.state = ConnectionState.CLOSED
        key = (sock.local_addr, sock.local_port)
        if key in self._listeners:
            del self._listeners[key]

        sock.last_activity = time.time()
        return True

    def get_socket(self, socket_id: int) -> Optional[Socket]:
        """Get socket by ID."""
        return self._sockets.get(socket_id)

    def list_sockets(self) -> list[Socket]:
        """List all sockets."""
        return list(self._sockets.values())

    def get_stats(self) -> dict:
        """Get network statistics."""
        states = {}
        for sock in self._sockets.values():
            states[sock.state.value] = states.get(sock.state.value, 0) + 1

        return {
            "total_sockets": len(self._sockets),
            "states": states,
            "listening_ports": len(self._listeners),
        }


NET_MGR = NetworkManager()
