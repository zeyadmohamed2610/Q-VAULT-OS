# Security Policy

## Supported Versions

We currently support the following versions of Q-Vault OS with security updates:

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < v1.0  | :x:                |

## Reporting a Vulnerability

We take the security of Q-Vault OS seriously. If you believe you have found a security vulnerability, please report it to us as follows:

1. **Do not open a public issue.**
2. Send an email to [security@qvault.sim](mailto:security@qvault.sim) (Placeholder - Replace with actual email if available) or DM the maintainers.
3. Include as much detail as possible, including steps to reproduce the vulnerability.

We will acknowledge your report within 48 hours and provide a timeline for a fix if the vulnerability is confirmed.

## Security Architecture

Q-Vault OS employs a dual-layered security model:
- **Rust Core**: All cryptographic operations and memory-sensitive logic are handled by a native Rust module to prevent buffer overflows and Python-level introspection.
- **VFS Isolation**: The Virtual File System is logically separated from the host OS.
- **Process Sandboxing**: Each internal application runs in a restricted widget container with limited API access.
