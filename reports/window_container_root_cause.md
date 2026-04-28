# Root Cause Analysis: Systemic Window Rendering Failure

## 🔍 Executive Summary
A systemic layout regression was identified affecting the entire Q-Vault OS windowing framework. Application windows (Terminal, Files, System Monitor) were failing to expand their content areas, resulting in "tiny boxes" (96x28px) with unrendered or invisible widgets.

## 🛠️ Root Causes Identified

### 1. Architectural Shadowing (The Silent Bug)
`IsolatedAppWidget` (the base class for all process-isolated apps) was defining a member variable `self.layout = QVBoxLayout(self)`. 
- **Impact**: In PyQt5/Qt, `QWidget.layout()` is a built-in method. Overriding it with an attribute shadowed the method, causing external layout managers and diagnostic tools to crash or fail when trying to query the widget's layout state.
- **Fix**: Renamed `self.layout` to `self.main_layout`.

### 2. Layout Disconnection (The Hollow Container)
The `self.container` frame inside `IsolatedAppWidget` was initialized without a layout manager.
- **Impact**: Even if apps added child widgets to the container, those children had no layout instructions. They defaulted to minimum sizes and did not expand to fill the window. This explains why the content area appeared empty or broken.
- **Fix**: Added a `QVBoxLayout` to `self.container` and implemented an authoritative `set_content()` method for proxies to safely inject UI.

### 3. Hollow UI Proxies (The Missing Frontend)
The `app_registry` was pointing to proxy classes in `components/app_proxies.py` (e.g., `TerminalProxy`), but these classes were empty shells that did not instantiate the actual UI widgets (`TerminalWidget`, `FileManagerApp`, etc.).
- **Impact**: The window system was successfully launching the "engines" (backend processes), but there was no "frontend" (UI) code to display the output or receive input.
- **Fix**: Rebuilt the proxy classes to instantiate and connect their respective UI components on initialization.

### 4. Animation Race Condition (The 96x28 Trap)
`OSWindow` was initialized with a default size of 100x30. The `MotionController` captured this size at the moment of `WINDOW_OPENED` to calculate the "spawn" animation.
- **Impact**: The animation started at 96x28 (0.96 scale). Because `QPropertyAnimation` operates at the C++ level, it bypassed the Window Manager's geometry constraints, forcing the window to stay at the animated size.
- **Fix**: Enforced a `setMinimumSize(400, 300)` constraint on both `OSWindow` and `IsolatedAppWidget`, ensuring they never collapse into unreadable dimensions, even during animations.

## 🚀 Corrective Actions Taken
- [x] **Core Refactor**: Fixed `IsolatedAppWidget` hierarchy and layout propagation.
- [x] **Proxy Populating**: Injected real UI components into `Terminal`, `Files`, and `System Monitor` proxies.
- [x] **Constraint Enforcement**: Applied systemic minimum size locks to prevent geometry-based rendering failures.
- [x] **Event Bridging**: Restored IPC event handlers in `TerminalProxy` to pipe output from the engine to the emulator.

## 📊 Verification Result
Layout diagnostics confirm that `OSWindow` now maintains a valid minimum viewport, and `IsolatedAppWidget` correctly hosts and expands the application UI. The "hollow window" effect has been resolved across all system tools.
