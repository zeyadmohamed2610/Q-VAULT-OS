# =============================================================
#  system/__init__.py — Q-VAULT OS  |  System Package Namespace
#
#  INTENTIONALLY MINIMAL.
#
#  The previous version attempted to import `system.secure_gateway`
#  which does not exist, causing a silent ImportError on every
#  `import system` call throughout the codebase.
#
#  Security initialization is performed exclusively by:
#    - system.security_api  (Rust FFI boundary, fail-fast)
#    - system.app_controller (calls security_api at boot)
#
#  DO NOT add import-time side effects to this file.
# =============================================================
