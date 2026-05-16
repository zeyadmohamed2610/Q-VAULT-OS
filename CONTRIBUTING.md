# 🤝 Contributing to Q-Vault Sovereign OS

First off, thank you for considering contributing to Q-Vault OS! It's people like you that make Q-Vault such a great sovereign environment.

## ⚖️ Code of Conduct
By participating in this project, you agree to abide by our professional standards of respect and integrity.

## 🚀 Getting Started
1. **Fork** the repository on GitHub.
2. **Clone** your fork locally.
3. **Install dependencies**: `pip install -r requirements.txt`.
4. **Create a branch**: `git checkout -b feature/my-new-feature`.

## 🛠️ Development Standards
As a sovereign framework, we maintain extremely high standards for code quality:

- **Type Hinting**: All new functions must include Python type hints.
- **Thread Safety**: Ensure all UI interactions are handled via the `EVENT_BUS` or proper thread-safe signals.
- **Security**: Never bypass the `SecureAPI`. Direct host OS calls are forbidden within applications.
- **Aesthetics**: Follow the "Cyan-Glow" design system defined in `src/resources/theme.py`.

## 🧪 Testing
We use `pytest`. Please ensure your feature includes tests.
```powershell
pytest
```

## 📬 Pull Request Process
1. Update the `README.md` in the relevant directory if you changed functionality.
2. Ensure the CI pipeline passes.
3. Submit the PR with a clear description of the "Why" and "How".

---
*Stay Sovereign.*
