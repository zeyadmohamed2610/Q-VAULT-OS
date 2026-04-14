# Q-VAULT OS SDK

Extending Q-VAULT OS through plugins.

## Installation

Copy your plugin to:
```
~/.qvault/plugins/your_plugin/
```

Each plugin needs:
- `plugin.json` - Plugin manifest
- `main.py` - Plugin entry point

## Quick Start

```python
# main.py - Your plugin
from qvault_sdk import Plugin

class MyPlugin(Plugin):
    def on_load(self):
        self.api.ui.notify('Hello', 'Plugin loaded!')

# Create instance
plugin = MyPlugin(api)
```

## API Reference

### File System
```python
content = api.fs.read('/home/user/file.txt')
api.fs.write('/home/user/file.txt', 'Hello!')
files = api.fs.list_dir('/home/user')
```

### Storage
```python
api.storage.save_data('settings', {'key': 'value'})
settings = api.storage.load_data('settings', default={})
data_dir = api.storage.get_data_dir()
```

### UI
```python
api.ui.notify('Title', 'Message', 'info')
window = api.ui.create_window('My Window', 800, 600)
```

### Security
```python
alerts = api.security.get_alerts(10)
api.security.log_security_event('Suspicious activity', 'WARNING')
```

### Process
```python
processes = api.process.get_processes()
api.process.kill_process(1234)
```

### Utilities
```python
api.log('Info message', 'info')
config = api.get_config('theme', 'dark')
api.set_config('theme', 'light')
```

## Permissions

Required in `plugin.json`:
```json
{
  "permissions": ["storage", "ui", "security"]
}
```

Available:
- `filesystem` - Read/write files
- `process` - Manage processes
- `network` - Network operations
- `security` - Security events
- `ui` - UI elements
- `storage` - Plugin data

## Publishing

1. Test locally
2. Add signature in manifest
3. Package as ZIP
4. Submit to plugin store