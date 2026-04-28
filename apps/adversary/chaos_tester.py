from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import Qt
from system.runtime.isolated_widget import IsolatedAppWidget
from assets.theme import THEME

class ChaosTester(IsolatedAppWidget):
    """
    Main-Process Control Panel for offensive stress testing (Phase 15.3).
    """
    APP_ID = "chaos_tester"

    def __init__(self, secure_api=None, parent=None):
        super().__init__(
            app_id=self.APP_ID,
            module_path="apps.adversary.chaos_engine",
            class_name="ChaosEngine",
            secure_api=secure_api,
            parent=parent
        )
        
        self.setWindowTitle("Chaos Tester v1.0")
        self.resize(500, 400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"background: #000; color: {THEME['success']}; font-family: Consolas;")
        layout.addWidget(self.log)

        def btn(text, slot):
            b = QPushButton(text)
            b.clicked.connect(slot)
            layout.addWidget(b)
            return b

        btn("🔥 Start IPC Flood (500 calls)", self._start_flood)
        btn("🌊 Trigger Backpressure (Overflow)", self._start_backpressure)
        btn("💀 Self-Destruct Subprocess", self._self_destruct)
        btn("💤 Trigger Hang (10s)", self._trigger_hang)
        btn("📈 Memory Spike (50MB)", self._trigger_leak)
        btn("🧪 Verify Ordering", self._check_ordering)

    def _trigger_hang(self):
        self.log.append("[UI] Testing Hang Resilience... (Should not block UI)")
        self.call_remote("run_hang", duration=10, callback=lambda p: self.log.append("Hang Callback Received!"))

    def _trigger_leak(self):
        self.log.append("[UI] Forcing Memory Spike in Subprocess...")
        self.call_remote("run_memory_spike", size_mb=50)

    def _start_flood(self):
        self.log.append("[UI] Starting IPC Flood...")
        self.call_remote("run_flood", count=500, callback=self._on_result)

    def _start_backpressure(self):
        self.log.append("[UI] Flooding Kernel Pending Map...")
        self.call_remote("run_backpressure", count=200, callback=self._on_result)

    def _self_destruct(self):
        self.log.append("[UI] Killing Subprocess Engine...")
        self.call_remote("self_destruct")
        # Subprocess should die; UI should detect it if we improve IsolatedAppWidget

    def _check_ordering(self):
        self.log.append("[UI] Verifying Message Sequencing...")
        for i in range(1, 11):
            self.call_remote("check_ordering", i, callback=lambda p, idx=i: self.log.append(f"Received: {p.get('value')} (Expected: {idx})"))

    def _on_result(self, payload):
        if payload.get("status") == "success":
            self.log.append(f"Result: {str(payload.get('value'))[:100]}...")
        else:
            self.log.append(f"[!] Error: {payload.get('message')}")

    def handle_event(self, event, data):
        self.log.append(f"Event: {event} -> {data}")
