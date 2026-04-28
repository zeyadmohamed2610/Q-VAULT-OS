# 🔧 Q-Vault OS — Refactoring Plan

**Generated:** 2026-04-28 08:44:06
**Baseline Score:** 46/100
**Total Issues:** 11

---

## Batch Summary

| Batch | Issues | Auto-Fixable | Risk |
|-------|--------|-------------|------|
| Batch 1: Critical Fixes 🚨 | 0 | 0 | low |
| Batch 2: Architecture (God Objects) | 5 | 0 | high |
| Batch 3: UI Consistency (THEME) | 1 | 1 | low |
| Batch 4: EventBus Wiring | 0 | 0 | low |
| Batch 5: Code Quality | 5 | 0 | medium |

---

## Batch 1: Critical Fixes 🚨
> Must fix before ANY deployment

*No issues in this batch.*

## Batch 2: Architecture (God Objects)
> Split safely without changing public API

### 1. `components\desktop.py:71`
- **Problem:** God Object: `Desktop` has 40 methods, 69 attributes
- **Risk:** 🔴 HIGH
- **Fix Strategy:**
  1. Identify responsibility clusters in the class
  1. Extract each cluster into a handler/mixin class
  1. Keep the original class as a facade delegating to handlers
  1. Preserve all public method signatures
  1. Update internal references only

### 2. `system\runtime_manager.py:127`
- **Problem:** God Object: `AppRuntimeManager` has 32 methods, 44 attributes
- **Risk:** 🔴 HIGH
- **Fix Strategy:**
  1. Identify responsibility clusters in the class
  1. Extract each cluster into a handler/mixin class
  1. Keep the original class as a facade delegating to handlers
  1. Preserve all public method signatures
  1. Update internal references only

### 3. `system\security_api.py:36`
- **Problem:** God Object: `SecurityAPI` has 21 methods, 15 attributes
- **Risk:** 🔴 HIGH
- **Fix Strategy:**
  1. Identify responsibility clusters in the class
  1. Extract each cluster into a handler/mixin class
  1. Keep the original class as a facade delegating to handlers
  1. Preserve all public method signatures
  1. Update internal references only

### 4. `core\filesystem.py:106`
- **Problem:** God Object: `VirtualFS` has 24 methods, 6 attributes
- **Risk:** 🔴 HIGH
- **Fix Strategy:**
  1. Identify responsibility clusters in the class
  1. Extract each cluster into a handler/mixin class
  1. Keep the original class as a facade delegating to handlers
  1. Preserve all public method signatures
  1. Update internal references only

### 5. `apps\terminal\_output_formatter.py:22`
- **Problem:** God Object: `OutputFormatter` has 32 methods, 0 attributes
- **Risk:** 🔴 HIGH
- **Fix Strategy:**
  1. Identify responsibility clusters in the class
  1. Extract each cluster into a handler/mixin class
  1. Keep the original class as a facade delegating to handlers
  1. Preserve all public method signatures
  1. Update internal references only

## Batch 3: UI Consistency (THEME)
> Auto-fixable — replace hex → THEME tokens

### 1. `components\ai_inspector.py:0` `[AUTO-FIX]`
- **Problem:** 6 hardcoded hex colors (vs 4 THEME refs)
- **Risk:** 🟢 LOW
- **Fix Strategy:**
  1. Import THEME from assets.theme
  1. Map each hex color to the closest THEME token
  1. Replace hex literal with f-string THEME reference
  1. Convert surrounding string to f-string if needed
  1. Escape CSS braces as {{ }}

## Batch 4: EventBus Wiring
> Wire orphan events or remove dead ones

*No issues in this batch.*

## Batch 5: Code Quality
> Safe mechanical refactors

### 1. `components\lock_screen.py:18`
- **Problem:** Long function `__init__`: 134 lines
- **Risk:** 🟡 MEDIUM
- **Fix Strategy:**
  1. Identify logical sections via comment blocks
  1. Extract each section into a private helper method
  1. Call helpers from original method in sequence
  1. Run tests to verify behavior preserved

### 2. `components\taskbar_ui.py:51`
- **Problem:** Long function `__init__`: 159 lines
- **Risk:** 🟡 MEDIUM
- **Fix Strategy:**
  1. Identify logical sections via comment blocks
  1. Extract each section into a private helper method
  1. Call helpers from original method in sequence
  1. Run tests to verify behavior preserved

### 3. `components\welcome_screen.py:40`
- **Problem:** Long function `_setup_ui`: 128 lines
- **Risk:** 🟡 MEDIUM
- **Fix Strategy:**
  1. Identify logical sections via comment blocks
  1. Extract each section into a private helper method
  1. Call helpers from original method in sequence
  1. Run tests to verify behavior preserved

### 4. `system\runtime_manager.py:540`
- **Problem:** Long function `_update_system_pressure`: 122 lines
- **Risk:** 🟡 MEDIUM
- **Fix Strategy:**
  1. Identify logical sections via comment blocks
  1. Extract each section into a private helper method
  1. Call helpers from original method in sequence
  1. Run tests to verify behavior preserved

### 5. `apps\system_monitor\attack_engine.py:28`
- **Problem:** Long function `_test_pipeline`: 144 lines
- **Risk:** 🟡 MEDIUM
- **Fix Strategy:**
  1. Identify logical sections via comment blocks
  1. Extract each section into a private helper method
  1. Call helpers from original method in sequence
  1. Run tests to verify behavior preserved

---

## Recommended Execution Order

```
1. python tools/refactor_executor.py   # Batch 5 auto-fixes (bare except, mutable defaults)
2. python tools/ui_auto_fix.py         # Batch 3 auto-fixes (hex → THEME)
3. python run_full_audit.py             # Verify score improved
4. Manual: Batch 1 critical fixes       # Fix failing tests
5. Manual: Batch 2 God Objects           # Careful decomposition
6. Manual: Batch 4 EventBus wiring       # Connect orphan events
7. python tools/quality_pipeline.py     # Full regression check
```
