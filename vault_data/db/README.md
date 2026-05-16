# 📂 db
### *Sovereign OS Data Storage*

---

## 📖 Overview
This directory is used for **storing system data**. It stores runtime artifacts and persistent state information.

## 🛠️ Governance
- **Access Level**: Restricted (System/Root)
- **Persistence**: Permanent
- **Security**: Encrypted at Rest (if applicable)

## 📁 Current Data Entries
| 📄 | `master.key` | System artifact |
| 📄 | `vault_salts.json` | JSON Metadata/State |
| 📄 | `vault_salts.json.mac` | System artifact |
| 📄 | `vault_users.json` | JSON Metadata/State |
| 📄 | `vault_users.json.mac` | System artifact |
| 📄 | `vault_versions.json` | JSON Metadata/State |
| 📄 | `vault_versions.json.mac` | System artifact |

---
*Part of the Q-Vault Sovereign Infrastructure.*
