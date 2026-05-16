# 🛠️ Q-Vault OS: Application Integration Guide

This guide explains how to integrate external applications into the Q-Vault Sovereign Environment.

## 🏗️ Architecture: The App Hosting Model
Q-Vault OS uses a **Dynamic Factory Pattern** to host applications. Apps are not just run; they are **governed** by the kernel.

### 1. Integration Levels
- **Level 1: Native (Direct)**: The app runs within the main UI thread. High performance, but can crash the OS if not careful.
- **Level 2: Isolated (Process)**: The app runs in a separate memory space via `IsolatedAppWidget`. This is the sovereign standard for security.

---

## 🚀 How to Add a New App

### Step 1: Create your App Widget
Place your application code in `src/ui/apps/<your_app_folder>/`. Your main class should inherit from `QWidget`.

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyCustomApp(QWidget):
    def __init__(self, secure_api=None, parent=None, **kwargs):
        super().__init__(parent)
        # Use the provided secure_api for system calls
        self.api = secure_api
        # **kwargs ensures compatibility with dynamic system launches
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from Sovereign Space!"))
```

### Step 2: Register in the Manifest
Open `src/core/app_registry.py` and add your app to the `_MANIFEST` tuple:

```python
AppDefinition(
    name="My App",
    emoji="🚀",
    module="ui.apps.my_app_folder.app_file",
    class_name="MyCustomApp",
    icon_asset="icons/custom_icon.svg",
    isolation_mode="process", # or "direct"
    show_on_desktop=True,
)
```

### Step 3: Add an Icon
Place an SVG icon in `resources/icons/custom_icon.svg`.

---

## 🛡️ The SecureAPI (SDK)
Applications in Q-Vault OS do not talk to the host OS directly. They use the `SecureAPI` proxy:

- `self.api.vfs.read_file(path)`: Securely access the Virtual Filesystem.
- `self.api.events.emit(event)`: Communicate with other apps via the System Bus.
- `self.api.auth.is_root()`: Check permission levels.

---

## 💎 Leveraging the PQC-Vault Engine
Applications can trigger advanced security features by communicating with the **PQC-Vault Engine** via the `SecureAPI`.

### Common Engine Commands:
- `self.api.security.get_quantum_status()`: Retrieve current PQC algorithm metrics.
- `self.api.security.unlock_vault()`: Request hardware-anchored decryption.
- `self.api.security.get_bitlocker_state()`: Audit host-level disk protection.

### Example: Checking Hardware Token
```python
if self.api.security.is_token_connected():
    self.status_label.setText("Secure Identity Verified")
```

---

## 🤝 Inter-App Service Integration
Q-Vault OS supports a **Service-Oriented Architecture (SOA)**. Critical apps like **Q-Vault Security** act as service providers that other applications can interact with.

### Using Q-Vault Security as a Service
If your application needs to verify identity or trigger a secure vault operation, you don't need to implement it yourself. Simply emit a system event:

```python
from core.event_bus import EVENT_BUS, SystemEvent

# Request Q-Vault Security to initiate a hardware handshake
EVENT_BUS.emit(SystemEvent.EVENT_QVAULT_CONNECTED, {"caller": "MyCustomApp"})
```

### Subscribing to Security Updates
Your app can "listen" to the security state of the OS:
```python
def on_vault_unlock(payload):
    print("Security Service notified us: Vault is open!")

EVENT_BUS.subscribe(SystemEvent.EVENT_QVAULT_UNLOCKED, on_vault_unlock)
```

---

## 🧪 Testing your Integration
1. Run `python run.py`.
2. Find your icon on the Desktop.
3. Double-click to launch.
4. Check `vault_data/logs/qvault/app_factory.log` if it fails to load.

---
*Certified for Sovereign Integration v4.1*
