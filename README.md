# 🛡️ Q-Vault OS: The Ultimate Secure AI-Native Simulator

<div align="center">
  <img src="assets/icons/qvault_logo.svg" width="120" height="120" alt="Q-Vault Logo">
  <h3><b>Next-Generation Secure OS Simulation Environment</b></h3>
  <p><i>Fusing Python's agility with Rust's uncompromising safety.</i></p>

  ![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
  ![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![Rust](https://img.shields.io/badge/rust-1.75%2B-DEA584?style=for-the-badge&logo=rust&logoColor=white)
  ![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
</div>

---

## 🌌 Overview

**Q-Vault OS** is not just an application; it is a high-fidelity **Operating System Simulation Framework** designed for researchers, security enthusiasts, and developers. It provides a hardened sandbox environment where every application, thread, and byte of data is governed by a dual-layered security architecture.

At its heart lies the **Q-Vault Security Core**, a native Rust implementation that handles the heavy lifting of cryptography and resource governance, while the **Fluid UI Layer** (PyQt5) delivers a premium, zero-latency desktop experience.

---

## 🚀 Key Pillars of Excellence

### 🦀 Rust-Hardened Kernel
Leveraging `PyO3`, the security-critical logic is offloaded to a native Rust binary. 
- **Zero-Knowledge Architecture**: Encryption keys never touch the Python memory space.
- **AES-256-GCM Encryption**: Every file in the virtual filesystem is encrypted at rest.
- **Argon2id KDF**: Industrial-grade password hashing and key derivation.

### 🧠 AI-Native Governance
Q-Vault is built for the age of AI. The **Runtime Intelligence Manager** monitors application behavior in real-time.
- **Dynamic Trust Scores**: Apps are assigned trust levels based on their API call patterns.
- **Automated Quarantine**: Any anomalous behavior (e.g., unauthorized memory access) triggers an immediate system-level freeze and containment.
- **Context-Aware Terminal**: A specialized shell that understands system state and provides AI-assisted command suggestions.

### 🖥️ Fluid Multitasking Engine
A custom-built window manager designed for maximum productivity.
- **Tiling & Snapping**: Intelligent window placement with physics-based animations.
- **Sub-Millisecond IPC**: Ultra-fast inter-process communication via an internal secure event bus.
- **Glassmorphic Aesthetics**: A modern, dark-themed UI with vibrant accents and smooth transitions.

---

## 🛠️ Technical Architecture

```mermaid
graph TD
    User([User Interface]) --> Compositor[Window Compositor]
    Compositor --> AppContainer[Application Container]
    
    subgraph "Secure Sandbox"
        AppContainer --> EventBus[Secure Event Bus]
        EventBus --> SecurityAPI[Python Security Bridge]
    end

    subgraph "Native Core (Rust)"
        SecurityAPI --> RustCore{qvault_core.pyd}
        RustCore --> Crypto[AES-GCM / Argon2]
        RustCore --> VFS[Encrypted File System]
    end

    Runtime[Runtime Manager] -.-> |Monitor| AppContainer
    Runtime -.-> |Quarantine| SecurityAPI
```

---

## 📦 Included Subsystems

| Subsystem | Description | Technology |
| :--- | :--- | :--- |
| **Terminal** | POSIX-compliant shell with VFS integration. | Python + Rust |
| **File Manager** | Encrypted explorer with drag-and-drop support. | PyQt5 |
| **System Monitor** | Live telemetry, resource graphs, and Trust Scores. | Matplotlib + IPC |
| **Security Hub** | RBAC policy management and audit log viewer. | Rust Core |
| **Browser** | Isolated web environment with restricted API access. | QtWebEngine |

---

## ⚡ Quick Deployment

Q-Vault features a **One-Command Bootstrapper** that handles environment setup, dependency resolution, and native compilation.

### Prerequisites
- **Python 3.10+**
- **Rust Toolchain** (for compiling the security core)
- **Git**

### Installation

```bash
# Clone the repository
git clone https://github.com/q-vault-group/Q-VAULT-project.git
cd Q-VAULT-project

# Launch the OS (This will auto-install dependencies and build Rust binaries)
python run.py
```

---

## 🔒 Security Model

The simulation operates on the **Principle of Least Privilege (PoLP)**:
1. **Isolated Widgets**: Each application runs as an isolated proxy.
2. **Permissioned API**: No application can access the host filesystem or network without explicit user-granted tokens.
3. **Audit Logging**: Every system event is signed and stored in a secure ledger for forensic analysis.

---

## 🤝 Contributing

We welcome contributions from the community! Whether it's a new feature, a bug fix, or a design improvement.

1. **Fork** the project.
2. **Branch**: `git checkout -b feature/AmazingFeature`
3. **Commit**: `git commit -m 'Add some AmazingFeature'`
4. **Push**: `git push origin feature/AmazingFeature`
5. **PR**: Open a Pull Request.

---

<div align="center">
  <p>Built with ❤️ by the Q-Vault Development Team</p>
  <p><i>Protecting the simulation, one byte at a time.</i></p>
</div>
