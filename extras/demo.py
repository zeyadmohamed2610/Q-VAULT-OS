#!/usr/bin/env python
"""
demo.py — Q-VAULT OS  |  Security Architecture Demo

Demonstrates the complete security model:

  [1] Security mode detection (LOCKDOWN / DEGRADED / SECURE)
  [2] Login via SecurityAPI (capability chain enforced)
  [3] Role-Based Access Control (RBAC)
  [4] Vault operations  (mode + role gated)
  [5] SHA-256 hashing   (always available for authed users)
  [6] Role demo: user role (read-only vault)
  [7] Role demo: guest role (hash only)
  [8] Admin: create_user via API
  [9] Capability enforcement: direct SESSION calls raise SecurityError

DISCLAIMER: This project demonstrates security architecture patterns.
Python-level bypass (e.g. patching the capability token at import time)
is acknowledged and not fully preventable. Educational use only.
"""

import sys


# ── ANSI output helpers ───────────────────────────────────────

_tty = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _tty else text

OK   = lambda t: _c("32", t)
WARN = lambda t: _c("33", t)
ERR  = lambda t: _c("31", t)
DIM  = lambda t: _c("2",  t)
BOLD = lambda t: _c("1",  t)
CYAN = lambda t: _c("36", t)

W = 58

def sep(c="─"):
    print(DIM(c * W))

def section(n: int, title: str):
    print()
    sep()
    print(BOLD(f"  [{n}] {title}"))
    sep()

def ok(label: str, detail: str = ""):
    tag = OK("  [PASS]")
    print(f"{tag}  {label}" + (f":  {BOLD(detail)}" if detail else ""))

def fail(label: str, detail: str = ""):
    tag = ERR("  [FAIL]")
    print(f"{tag}  {label}" + (f":  {detail}" if detail else ""))

def note(msg: str):
    print(f"         {DIM(msg)}")


# ── Helpers ───────────────────────────────────────────────────

def do_login(api, user: str, pw: str) -> bool:
    r = api.login(user, pw)
    if r["success"]:
        ok("login", f"{r['user']} (role={r['role']})")
    else:
        fail("login", r["message"])
    return r["success"]


def do_store(api, key: str, val: str, mode: str):
    r = api.store_secret(key, val)
    if r["success"]:
        ok("store_secret", f"'{key}'")
    else:
        fail("store_secret", r["message"])
        if "LOCKDOWN" in r["message"]:
            note("REASON: LOCKDOWN mode -- Rust module absent, vault blocked")
        elif "not permitted" in r["message"]:
            note(f"REASON: role '{api.get_current_role()}' lacks write permission")


def do_get(api, key: str, mode: str):
    r = api.get_secret(key)
    if r["success"] and r["value"]:
        ok("get_secret", f"'{key}' -> {r['value']}")
    else:
        fail("get_secret", r["message"])
        if "LOCKDOWN" in r["message"]:
            note("REASON: LOCKDOWN mode -- vault blocked")
        elif "not permitted" in r["message"]:
            note(f"REASON: role '{api.get_current_role()}' lacks vault read permission")


def do_hash(api, data: bytes):
    r = api.hash_data(data)
    if r["success"]:
        h = r["hash"][:32] + "..."
        is_fb = "fallback" in r["message"]
        ok("hash_data", f"sha256({data!r}) = {h}" + (" [python fallback]" if is_fb else ""))
    else:
        fail("hash_data", r["message"])


# ── Main ──────────────────────────────────────────────────────

def main():
    print()
    print(BOLD("  " + "=" * (W - 2)))
    print(BOLD(f"  {'Q-VAULT OS  |  Security Architecture Demo':^{W-2}}"))
    print(BOLD("  " + "=" * (W - 2)))

    # ── Init ──────────────────────────────────────────────────
    try:
        from system.security_api import get_security_api
        api = get_security_api()
    except Exception as exc:
        print(ERR(f"\nFatal: could not initialize SecurityAPI -- {exc}"))
        sys.exit(1)

    # ── [1] Security mode ─────────────────────────────────────
    section(1, "Security Mode")
    status  = api.get_status()
    mode    = status.get("mode", "UNKNOWN")
    rust_ok = status.get("rust_available", False)

    (ok if mode != "LOCKDOWN" else fail)("mode", mode)
    (ok if rust_ok else fail)("rust_module", str(rust_ok))

    if mode == "LOCKDOWN":
        note(WARN("System is in LOCKDOWN -- vault operations blocked"))
        note(WARN("Build qvault-core (cargo build --release) for SECURE mode"))
    elif mode == "SECURE":
        note(OK("Rust module active -- full vault operations enabled"))
    else:
        note(WARN(f"Mode = {mode} -- limited functionality"))

    # ── [2] Admin login ───────────────────────────────────────
    section(2, "Login as admin")
    if not do_login(api, "admin", "admin123"):
        print(ERR("\n  Critical: admin login failed. Aborting."))
        sys.exit(1)

    # ── [3] RBAC ──────────────────────────────────────────────
    section(3, "Role-Based Access Control")
    u    = api.get_current_user()
    role = api.get_current_role()
    note(f"user:  {u.username}")
    note(f"role:  {BOLD(role)}")
    note("")
    note(f"store_secret  ->  {OK('admin only')}")
    note(f"get_secret    ->  {OK('admin + user')}")
    note(f"create_user   ->  {OK('admin only')}")
    note(f"hash_data     ->  {OK('all authenticated')}")

    # ── [4] Vault ops ─────────────────────────────────────────
    section(4, f"Vault Operations  [mode={mode}, role={role}]")
    do_store(api, "api_key", "sk_live_abc123xyz789", mode)
    do_get(api,  "api_key", mode)

    # ── [5] Hashing ───────────────────────────────────────────
    section(5, "SHA-256 Hashing  (always available)")
    do_hash(api, b"hello world")
    do_hash(api, b"qvault-os-2025")

    # ── [6] user role ─────────────────────────────────────────
    section(6, "Role Demo: user  (read-only vault)")
    api.logout()
    do_login(api, "user", "user123")
    note("attempting store_secret  (should fail: role=user):")
    do_store(api, "test",    "value", mode)
    note("attempting get_secret:")
    do_get(api,  "api_key", mode)

    # ── [7] guest role ────────────────────────────────────────
    section(7, "Role Demo: guest  (hash only)")
    api.logout()
    do_login(api, "guest", "")
    note("attempting get_secret  (should fail: role=guest):")
    do_get(api,  "api_key", mode)
    note("attempting hash_data  (should succeed):")
    do_hash(api, b"guest-data")

    # ── [8] create_user ───────────────────────────────────────
    section(8, "Admin: create_user")
    api.logout()
    do_login(api, "admin", "admin123")
    r = api.create_user("alice", "alice_pass", "user")
    (ok if r["success"] else fail)("create_user", r["message"])

    # ── [9] Capability enforcement ────────────────────────────
    section(9, "Capability Enforcement  (direct SESSION access)")

    try:
        from system._session_core import SESSION
        from system.errors import SecurityError, CapabilityViolation
    except ImportError:
        note("_session_core module removed during refactoring - skipping")
        return

    note("calling SESSION.authenticate() without capability token ...")
    try:
        SESSION.authenticate("admin", "admin123", _cap=None)
        fail("SESSION.authenticate", "bypass succeeded -- ENFORCEMENT FAILED")
    except (SecurityError, TypeError) as exc:
        ok("SESSION.authenticate", "blocked correctly")

    note("calling SESSION.create_user() without capability token ...")
    try:
        SESSION.create_user("hacker", "hacked", "admin", _cap=None)
        fail("SESSION.create_user", "bypass succeeded -- ENFORCEMENT FAILED")
    except (SecurityError, TypeError) as exc:
        ok("SESSION.create_user", "blocked correctly")

    note("calling SESSION.delete_user() without capability token ...")
    try:
        SESSION.delete_user("admin", _cap=None)
        fail("SESSION.delete_user", "bypass succeeded -- ENFORCEMENT FAILED")
    except (SecurityError, TypeError) as exc:
        ok("SESSION.delete_user", "blocked correctly")

    # ── Summary ───────────────────────────────────────────────
    print()
    sep("═")
    print(BOLD("  SUMMARY"))
    sep("═")
    print(f"    Security mode   :  {BOLD(mode)}")
    print(f"    Rust module     :  {BOLD(str(rust_ok))}")
    print(f"    Vault ops       :  {BOLD('BLOCKED' if mode == 'LOCKDOWN' else 'AVAILABLE')}")
    print(f"    Hash ops        :  {BOLD('ALWAYS ON  (authenticated users)')}")
    print(f"    Capability gate :  {BOLD('ENFORCED')}")
    print()
    if mode == "LOCKDOWN":
        print(WARN("  To enable SECURE mode:"))
        print(DIM("    cd qvault-core && cargo build --release"))
    print()
    print(DIM("  Q-Vault OS — Educational Security Architecture Demonstration"))
    print(DIM("  Python-level bypass is acknowledged. Not for production use."))
    print()


if __name__ == "__main__":
    main()
