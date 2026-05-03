"""
apps.terminal._commands — Q-Vault OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terminal Command Registry  |  Upgrade v4 — Full Linux Parity

New commands added
──────────────────
  mv        – move / rename files and directories
  cp        – copy files and directories (-r supported)
  grep      – search file contents with pattern matching
  find      – search filesystem by name / type / size
  less      – paginated file viewing (simulated)
  vim       – vi/vim editor (opens nano overlay — same GUI hook)
  du        – disk usage per entry
  df        – filesystem disk-space summary
  ps        – process list
  top/htop  – live resource monitor (simulated snapshot)
  ping      – ICMP echo (real subprocess via whitelist)
  curl      – HTTP fetch (simulated)
  wget      – HTTP download (simulated)
  ssh       – remote shell (simulated)
  man       – manual pages (built-in docs)
  history   – command history display
  chown     – change file owner (simulated)
  uname     – kernel/system info
  whoami    – current user (already existed — kept)
  id        – uid/gid info
  date      – current date/time
  uptime    – system uptime
  free      – memory usage
  env       – environment variables
  export    – set env variable (session-scoped)
  unset     – clear env variable
  head      – first N lines of file
  tail      – last N lines of file
  wc        – word/line/char count
  sort      – sort lines
  uniq      – deduplicate lines
  diff      – compare two files
  ln        – create symlinks (simulated)
  which     – locate command
  type      – describe command type
  alias     – define command alias
  exit/logout – end session
  tree      – directory tree view

Existing commands preserved (unchanged signatures)
──────────────────────────────────────────────────
  ls, cd, pwd, cat, rm, mkdir, rmdir, touch, stat,
  echo, chmod, bash, nano, exec, stress, fullstress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from ._output_formatter import OutputFormatter
from ._command_parser import ParsedCommand, CommandParser


# ─────────────────────────────────────────────────────────────────────────────
# Context
# ─────────────────────────────────────────────────────────────────────────────

class CommandContext:
    """Runtime context passed to every command's execute()."""

    # Session-scoped environment variables (shared across all instances)
    _session_env: ClassVar[dict[str, str]] = {
        "HOME":    "/home/user",
        "USER":    "user",
        "SHELL":   "/bin/bash",
        "TERM":    "xterm-256color",
        "PATH":    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG":    "en_US.UTF-8",
        "EDITOR":  "nano",
    }
    # Session-scoped aliases
    _aliases: ClassVar[dict[str, str]] = {
        "ll":  "ls -la",
        "la":  "ls -a",
        "l":   "ls -CF",
    }
    # Command history (populated by TerminalEngine before dispatch)
    _history: ClassVar[list[str]] = []

    def __init__(self, executor) -> None:
        self.executor  = executor
        self.cwd       = executor.cwd
        self.base_dir  = executor._base_dir

    def emit_output(self, text: str) -> None:
        self.executor._emit_output(text)

    def set_cwd(self, target: Path) -> None:
        self.executor.cwd = target

    def get_role(self) -> str:
        return self.executor._role_getter()

    def resolve_targets(
        self, args: list[str], must_exist: bool = False
    ) -> list[Path]:
        results: list[Path] = []
        for name in args:
            if "*" in name or "?" in name:
                for p in self.cwd.glob(name):
                    if str(p).startswith(str(self.base_dir)):
                        results.append(p)
            else:
                p = (self.cwd / name).resolve()
                if str(p).startswith(str(self.base_dir)):
                    if must_exist and not p.exists():
                        self.emit_output(f"Error: {name}: No such file or directory\n")
                    else:
                        results.append(p)
                else:
                    self.emit_output(OutputFormatter.permission_denied(name))
        return results

    def resolve_one(self, name: str) -> Path | None:
        """Resolve a single name, returning None if outside base_dir."""
        p = (self.cwd / name).resolve()
        if str(p).startswith(str(self.base_dir)):
            return p
        self.emit_output(OutputFormatter.permission_denied(name))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class BaseCommand:
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# File & Directory Management
# ─────────────────────────────────────────────────────────────────────────────

class LSCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        recursive    = "R" in parsed.flags or "r" in parsed.flags
        all_files    = "a" in parsed.flags or "A" in parsed.flags
        long_format  = "l" in parsed.flags
        human        = "h" in parsed.flags
        target_name  = parsed.args[0] if parsed.args else ""

        target = (ctx.cwd / target_name).resolve() if target_name else ctx.cwd
        if not str(target).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(str(target)))
            return

        try:
            if not target.exists():
                ctx.emit_output(f"ls: cannot access '{target_name}': No such file or directory\n")
                return
            if not target.is_dir():
                # ls on a single file
                entries = [target]
            elif recursive:
                entries = []
                for p in target.rglob("*"):
                    if not all_files and p.name.startswith("."):
                        continue
                    entries.append(p)
                    if len(entries) > 2000:
                        break
            else:
                entries = [
                    p for p in target.iterdir()
                    if all_files or not p.name.startswith(".")
                ]

            entries = sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower()))

            if long_format:
                ctx.emit_output(self._long_format(entries, target, human))
            else:
                ctx.emit_output(OutputFormatter.ls_output(entries, target))
        except PermissionError:
            ctx.emit_output(f"ls: cannot open directory '{target_name}': Permission denied\n")
        except Exception as exc:
            ctx.emit_output(f"ls: {exc}\n")

    @staticmethod
    def _human(size: int) -> str:
        for unit in ("B", "K", "M", "G", "T"):
            if size < 1024:
                return f"{size:>4}{unit}"
            size //= 1024
        return f"{size}P"

    def _long_format(self, entries: list[Path], base: Path, human: bool) -> str:
        lines = []
        total_blocks = 0
        for p in entries:
            try:
                s      = p.stat()
                is_dir = p.is_dir()
                size   = s.st_size
                total_blocks += (size + 511) // 512
                mtime  = datetime.fromtimestamp(s.st_mtime).strftime("%b %d %H:%M")
                size_s = self._human(size) if human else str(size)
                kind   = "d" if is_dir else "-"
                name   = f"\033[34m{p.name}/\033[0m" if is_dir else p.name
                lines.append(f"  {kind}rwxr-xr-x  1 user user {size_s:>7} {mtime} {name}")
            except Exception:
                lines.append(f"  ?           ? ????  {p.name}")
        header = f"total {total_blocks}\n" if lines else ""
        return header + "\n".join(lines) + "\n" if lines else "\n"


class CDCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        raw = parsed.args[0] if parsed.args else "~"
        if raw == "~":
            ctx.set_cwd(ctx.base_dir)
            return
        if raw == "-":
            prev = getattr(ctx.executor, "previous_cwd", None)
            if prev:
                ctx.executor.previous_cwd, ctx.executor.cwd = ctx.executor.cwd, prev
                ctx.cwd = ctx.executor.cwd
                ctx.emit_output(str(ctx.executor.cwd) + "\n")
            else:
                ctx.emit_output("cd: OLDPWD not set\n")
            return
        try:
            candidate = (ctx.cwd / raw).resolve()
            if not str(candidate).startswith(str(ctx.base_dir)):
                ctx.emit_output(f"cd: {raw}: Permission denied\n")
                return
            if not candidate.exists():
                ctx.emit_output(f"cd: {raw}: No such file or directory\n")
                return
            if not candidate.is_dir():
                ctx.emit_output(f"cd: {raw}: Not a directory\n")
                return
            ctx.executor.previous_cwd = ctx.cwd
            ctx.set_cwd(candidate)
        except Exception as exc:
            ctx.emit_output(f"cd: {exc}\n")


class PWDCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        ctx.emit_output(str(ctx.cwd) + "\n")


class MKDirCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("mkdir: missing operand\n")
            return
        parents = "p" in parsed.flags
        mode    = int(parsed.args[0], 8) if ("m" in parsed.flags and len(parsed.args) > 1) else 0o755
        dirs    = parsed.args[1:] if "m" in parsed.flags and len(parsed.args) > 1 else parsed.args

        for name in dirs:
            t = (ctx.cwd / name).resolve()
            if not str(t).startswith(str(ctx.base_dir)):
                ctx.emit_output(OutputFormatter.permission_denied(name))
                continue
            try:
                t.mkdir(parents=parents, exist_ok=parents)
            except FileExistsError:
                ctx.emit_output(f"mkdir: cannot create directory '{name}': File exists\n")
            except Exception as exc:
                ctx.emit_output(f"mkdir: {exc}\n")


class TouchCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("touch: missing operand\n")
            return
        for name in parsed.args:
            t = (ctx.cwd / name).resolve()
            if not str(t).startswith(str(ctx.base_dir)):
                ctx.emit_output(OutputFormatter.permission_denied(name))
                continue
            try:
                t.touch(exist_ok=True)
            except Exception as exc:
                ctx.emit_output(f"touch: {exc}\n")


class RMDirCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("rmdir: missing operand\n")
            return
        for name in parsed.args:
            t = ctx.resolve_one(name)
            if t is None:
                continue
            if not t.is_dir():
                ctx.emit_output(f"rmdir: failed to remove '{name}': Not a directory\n")
                continue
            try:
                t.rmdir()
            except OSError:
                ctx.emit_output(f"rmdir: failed to remove '{name}': Directory not empty\n")
            except Exception as exc:
                ctx.emit_output(f"rmdir: {exc}\n")


class RMCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("rm: missing operand\n")
            return
        force     = "f" in parsed.flags
        recursive = "r" in parsed.flags or "R" in parsed.flags

        if ctx.get_role() != "admin":
            ctx.emit_output(OutputFormatter.admin_required("rm"))
            return

        for name in parsed.args:
            if CommandParser.is_system_path_target(name):
                ctx.emit_output(OutputFormatter.policy_restricted("rm", name))
                ctx.executor._on_rm_policy_violation(name)
                continue

            t = ctx.resolve_one(name)
            if t is None:
                continue

            if not t.exists():
                if not force:
                    ctx.emit_output(f"rm: cannot remove '{name}': No such file or directory\n")
                continue

            try:
                if t.is_dir():
                    if not recursive:
                        ctx.emit_output(f"rm: cannot remove '{name}': Is a directory\n")
                        continue
                    if force:
                        shutil.rmtree(t)
                    else:
                        from system.trash_manager import move_to_trash
                        move_to_trash(str(t))
                else:
                    if force:
                        t.unlink(missing_ok=True)
                    else:
                        from system.trash_manager import move_to_trash
                        if not move_to_trash(str(t)):
                            ctx.emit_output(f"rm: failed to remove '{name}'\n")
            except Exception as exc:
                ctx.emit_output(f"rm: {exc}\n")


class MVCommand(BaseCommand):
    """mv – move or rename files/directories."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if len(parsed.args) < 2:
            ctx.emit_output("mv: missing destination operand\n")
            return
        *sources, dest_str = parsed.args
        dest = (ctx.cwd / dest_str).resolve()
        if not str(dest).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(dest_str))
            return

        for name in sources:
            src = ctx.resolve_one(name)
            if src is None:
                continue
            if not src.exists():
                ctx.emit_output(f"mv: cannot stat '{name}': No such file or directory\n")
                continue
            try:
                real_dest = dest / src.name if dest.is_dir() else dest
                real_dest.parent.mkdir(parents=True, exist_ok=True)
                src.rename(real_dest)
            except Exception as exc:
                ctx.emit_output(f"mv: {exc}\n")


class CPCommand(BaseCommand):
    """cp – copy files/directories."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if len(parsed.args) < 2:
            ctx.emit_output("cp: missing destination operand\n")
            return
        recursive = "r" in parsed.flags or "R" in parsed.flags
        *sources, dest_str = parsed.args
        dest = (ctx.cwd / dest_str).resolve()
        if not str(dest).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(dest_str))
            return

        for name in sources:
            src = ctx.resolve_one(name)
            if src is None:
                continue
            if not src.exists():
                ctx.emit_output(f"cp: cannot stat '{name}': No such file or directory\n")
                continue
            if src.is_dir() and not recursive:
                ctx.emit_output(f"cp: -r not specified; omitting directory '{name}'\n")
                continue
            try:
                real_dest = dest / src.name if dest.is_dir() else dest
                if src.is_dir():
                    shutil.copytree(src, real_dest, dirs_exist_ok=True)
                else:
                    real_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, real_dest)
            except Exception as exc:
                ctx.emit_output(f"cp: {exc}\n")


# ─────────────────────────────────────────────────────────────────────────────
# File Viewing & Editing
# ─────────────────────────────────────────────────────────────────────────────

class CatCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("cat: missing filename\n")
            return
        number_lines = "n" in parsed.flags
        for name in parsed.args:
            t = ctx.resolve_one(name)
            if t is None:
                continue
            if not t.exists():
                ctx.emit_output(f"cat: {name}: No such file or directory\n")
                continue
            if t.is_dir():
                ctx.emit_output(f"cat: {name}: Is a directory\n")
                continue
            try:
                content = t.read_text(errors="replace")
                if number_lines:
                    lines = content.splitlines()
                    content = "\n".join(f"{i+1:6}\t{l}" for i, l in enumerate(lines))
                ctx.emit_output(content + ("\n" if not content.endswith("\n") else ""))
            except Exception as exc:
                ctx.emit_output(f"cat: {exc}\n")


class LessCommand(BaseCommand):
    """less – paginated viewer (shows first 40 lines with navigation hint)."""

    PAGE = 40

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("less: missing filename\n")
            return
        name = parsed.args[0]
        t = ctx.resolve_one(name)
        if t is None:
            return
        if not t.exists():
            ctx.emit_output(f"less: {name}: No such file or directory\n")
            return
        if t.is_dir():
            ctx.emit_output(f"less: {name}: Is a directory\n")
            return
        try:
            lines = t.read_text(errors="replace").splitlines()
            total = len(lines)
            shown = lines[:self.PAGE]
            ctx.emit_output("\n".join(shown) + "\n")
            if total > self.PAGE:
                ctx.emit_output(
                    f"\n\033[7m -- {self.PAGE}/{total} lines shown "
                    f"(use 'cat {name}' for full file) -- \033[0m\n"
                )
            else:
                ctx.emit_output(f"\033[7m(END)\033[0m\n")
        except Exception as exc:
            ctx.emit_output(f"less: {exc}\n")


class HeadCommand(BaseCommand):
    """head – output first N lines."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        try:
            n = int(parsed.args[0]) if parsed.args and parsed.args[0].lstrip("-").isdigit() else 10
            files = [a for a in parsed.args if not a.lstrip("-").isdigit()]
        except Exception:
            n, files = 10, parsed.args
        if not files:
            ctx.emit_output("head: missing operand\n")
            return
        for name in files:
            t = ctx.resolve_one(name)
            if t is None or not t.exists():
                ctx.emit_output(f"head: {name}: No such file or directory\n")
                continue
            try:
                lines = t.read_text(errors="replace").splitlines()[:abs(n)]
                if len(files) > 1:
                    ctx.emit_output(f"==> {name} <==\n")
                ctx.emit_output("\n".join(lines) + "\n")
            except Exception as exc:
                ctx.emit_output(f"head: {exc}\n")


class TailCommand(BaseCommand):
    """tail – output last N lines."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        try:
            n = int(parsed.args[0]) if parsed.args and parsed.args[0].lstrip("-").isdigit() else 10
            files = [a for a in parsed.args if not a.lstrip("-").isdigit()]
        except Exception:
            n, files = 10, parsed.args
        if not files:
            ctx.emit_output("tail: missing operand\n")
            return
        for name in files:
            t = ctx.resolve_one(name)
            if t is None or not t.exists():
                ctx.emit_output(f"tail: {name}: No such file or directory\n")
                continue
            try:
                lines = t.read_text(errors="replace").splitlines()
                show  = lines[-abs(n):] if n else lines
                if len(files) > 1:
                    ctx.emit_output(f"==> {name} <==\n")
                ctx.emit_output("\n".join(show) + "\n")
            except Exception as exc:
                ctx.emit_output(f"tail: {exc}\n")


class NanoCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("nano: missing filename\n")
            return
        ctx.executor._handle_nano(parsed.args[0])


class VimCommand(BaseCommand):
    """vim/vi – opens the nano overlay (same GUI hook)."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("vim: missing filename\n")
            return
        ctx.executor._handle_nano(parsed.args[0])


# ─────────────────────────────────────────────────────────────────────────────
# Permissions & Ownership
# ─────────────────────────────────────────────────────────────────────────────

class ChmodCommand(BaseCommand):
    """chmod – change file permissions (simulated, mirrors Linux output)."""

    _OCTAL_MAP = {
        "0": "---", "1": "--x", "2": "-w-", "3": "-wx",
        "4": "r--", "5": "r-x", "6": "rw-", "7": "rwx",
    }

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if len(parsed.args) < 2:
            ctx.emit_output("chmod: missing operand\n"
                            "Usage: chmod [OPTION]... MODE FILE...\n")
            return
        mode_str, *targets = parsed.args
        recursive = "R" in parsed.flags or "r" in parsed.flags

        perm_str = self._parse_mode(mode_str)

        for name in targets:
            t = ctx.resolve_one(name)
            if t is None:
                continue
            if not t.exists():
                ctx.emit_output(f"chmod: cannot access '{name}': No such file or directory\n")
                continue
            # Simulate: root required for system files
            if ctx.get_role() != "admin" and self._is_system(t, ctx):
                ctx.emit_output(f"chmod: changing permissions of '{name}': Operation not permitted\n")
                continue
            if recursive and t.is_dir():
                ctx.emit_output(f"chmod: mode of '{name}' and its contents changed to {perm_str}\n")
            else:
                ctx.emit_output(f"chmod: mode of '{name}' changed to {perm_str}\n")

    def _parse_mode(self, mode: str) -> str:
        if mode.isdigit() and len(mode) in (3, 4):
            digits = mode[-3:]
            return "".join(self._OCTAL_MAP.get(d, "???") for d in digits)
        return mode  # symbolic like "u+x"

    @staticmethod
    def _is_system(path: Path, ctx: CommandContext) -> bool:
        rel = str(path.relative_to(ctx.base_dir)) if str(path).startswith(str(ctx.base_dir)) else ""
        return rel.startswith(("etc/", "bin/", "usr/"))


class ChownCommand(BaseCommand):
    """chown – change file owner (simulated)."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if len(parsed.args) < 2:
            ctx.emit_output("chown: missing operand\n"
                            "Usage: chown [OPTION]... OWNER[:GROUP] FILE...\n")
            return
        if ctx.get_role() != "admin":
            ctx.emit_output("chown: changing ownership requires root privileges\n")
            return
        owner_str, *targets = parsed.args
        recursive = "R" in parsed.flags
        for name in targets:
            t = ctx.resolve_one(name)
            if t is None:
                continue
            if not t.exists():
                ctx.emit_output(f"chown: cannot access '{name}': No such file or directory\n")
                continue
            suffix = " (recursive)" if recursive and t.is_dir() else ""
            ctx.emit_output(f"chown: '{name}': owner changed to '{owner_str}'{suffix}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────────

class GrepCommand(BaseCommand):
    """grep – search file content for pattern."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("grep: missing pattern\nUsage: grep [OPTIONS] PATTERN [FILE...]\n")
            return

        ignore_case  = "i" in parsed.flags
        invert       = "v" in parsed.flags
        line_nums    = "n" in parsed.flags
        count_only   = "c" in parsed.flags
        recursive    = "r" in parsed.flags or "R" in parsed.flags
        silent       = "l" in parsed.flags   # print only filenames
        whole_word   = "w" in parsed.flags

        pattern  = parsed.args[0]
        files    = parsed.args[1:]

        if recursive and not files:
            files = ["."]

        if not files:
            ctx.emit_output("grep: (reading from stdin is not supported)\n")
            return

        def _match(line: str) -> bool:
            haystack = line.lower() if ignore_case else line
            needle   = pattern.lower() if ignore_case else pattern
            if whole_word:
                import re
                flags = re.IGNORECASE if ignore_case else 0
                return bool(re.search(rf"\b{re.escape(needle)}\b", line, flags))
            hit = needle in haystack
            return (not hit) if invert else hit

        def _search_file(path: Path) -> None:
            try:
                lines   = path.read_text(errors="replace").splitlines()
                matches = [(i + 1, l) for i, l in enumerate(lines) if _match(l)]
                if count_only:
                    prefix = f"{path}:" if len(files) > 1 else ""
                    ctx.emit_output(f"{prefix}{len(matches)}\n")
                elif silent:
                    if matches:
                        ctx.emit_output(str(path) + "\n")
                else:
                    prefix = f"{path}:" if len(files) > 1 or recursive else ""
                    for lineno, text in matches:
                        lnum = f"{lineno}:" if line_nums else ""
                        ctx.emit_output(f"{prefix}{lnum}{text}\n")
            except PermissionError:
                ctx.emit_output(f"grep: {path}: Permission denied\n")
            except Exception:
                pass  # binary / unreadable

        for name in files:
            t = (ctx.cwd / name).resolve()
            if not str(t).startswith(str(ctx.base_dir)):
                ctx.emit_output(OutputFormatter.permission_denied(name))
                continue
            if not t.exists():
                ctx.emit_output(f"grep: {name}: No such file or directory\n")
                continue
            if recursive and t.is_dir():
                for fp in t.rglob("*"):
                    if fp.is_file():
                        _search_file(fp)
            elif t.is_file():
                _search_file(t)
            else:
                ctx.emit_output(f"grep: {name}: Is a directory (use -r)\n")


class FindCommand(BaseCommand):
    """find – search for files matching criteria."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        # find [PATH] [-name PATTERN] [-type f|d] [-size N]
        start_str = parsed.args[0] if parsed.args else "."
        start     = (ctx.cwd / start_str).resolve()
        if not str(start).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(start_str))
            return
        if not start.exists():
            ctx.emit_output(f"find: '{start_str}': No such file or directory\n")
            return

        # Parse predicates from raw parts
        parts  = parsed.parts[1:]  # skip 'find'
        name_pat: str | None = None
        type_f:   str | None = None  # "f" or "d"
        size_min: int | None = None

        i = 0
        while i < len(parts):
            p = parts[i]
            if p == "-name" and i + 1 < len(parts):
                name_pat = parts[i + 1]; i += 2
            elif p == "-type" and i + 1 < len(parts):
                type_f = parts[i + 1]; i += 2
            elif p == "-size" and i + 1 < len(parts):
                try:
                    size_min = int(parts[i + 1].rstrip("ck")); i += 2
                except ValueError:
                    i += 2
            else:
                i += 1

        count = 0
        try:
            for path in start.rglob("*"):
                if not str(path).startswith(str(ctx.base_dir)):
                    continue
                if name_pat and not fnmatch.fnmatch(path.name, name_pat):
                    continue
                if type_f == "f" and not path.is_file():
                    continue
                if type_f == "d" and not path.is_dir():
                    continue
                if size_min is not None:
                    try:
                        if path.stat().st_size < size_min * 1024:
                            continue
                    except Exception:
                        continue
                try:
                    rel = path.relative_to(ctx.base_dir)
                    ctx.emit_output(str(rel) + "\n")
                except ValueError:
                    ctx.emit_output(str(path) + "\n")
                count += 1
                if count > 5000:
                    ctx.emit_output("find: output truncated at 5000 results\n")
                    break
        except Exception as exc:
            ctx.emit_output(f"find: {exc}\n")


# ─────────────────────────────────────────────────────────────────────────────
# System Information
# ─────────────────────────────────────────────────────────────────────────────

class PSCommand(BaseCommand):
    """ps – list running processes."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        aux = "a" in parsed.flags or "aux" in " ".join(parsed.parts)
        try:
            import psutil
            procs = list(psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status"]))
            if aux:
                header = f"{'USER':<12} {'PID':>6} {'%CPU':>5} {'%MEM':>5} {'STAT':<6} COMMAND\n"
                ctx.emit_output(header)
                for p in procs[:50]:
                    try:
                        inf = p.info
                        ctx.emit_output(
                            f"{(inf['username'] or '?'):<12} {inf['pid']:>6} "
                            f"{inf['cpu_percent']:>5.1f} {inf['memory_percent']:>5.1f} "
                            f"{inf['status']:<6} {inf['name']}\n"
                        )
                    except Exception:
                        pass
            else:
                ctx.emit_output(f"{'PID':>6}  {'TTY':<8} {'TIME':<8}  COMMAND\n")
                for p in procs[:20]:
                    try:
                        ctx.emit_output(f"{p.pid:>6}  pts/0    00:00:00  {p.name()}\n")
                    except Exception:
                        pass
        except ImportError:
            self._simulated(ctx, aux)

    @staticmethod
    def _simulated(ctx: CommandContext, aux: bool) -> None:
        rows = [
            ("root",   1,   "systemd",        0.0, 0.1, "Ss"),
            ("root",   2,   "kthreadd",       0.0, 0.0, "S"),
            ("user",   512, "bash",           0.0, 0.2, "S"),
            ("user",   513, "python3",        1.2, 3.4, "S"),
            ("user",   514, "qvault-os",      2.1, 5.6, "S"),
            ("root",   98,  "sshd",           0.0, 0.1, "S"),
            ("user",   600, "ps",             0.0, 0.1, "R"),
        ]
        if aux:
            ctx.emit_output(f"{'USER':<12} {'PID':>6} {'%CPU':>5} {'%MEM':>5} {'STAT':<5} COMMAND\n")
            for user, pid, name, cpu, mem, stat in rows:
                ctx.emit_output(f"{user:<12} {pid:>6} {cpu:>5.1f} {mem:>5.1f} {stat:<5} {name}\n")
        else:
            ctx.emit_output(f"{'PID':>6}  {'TTY':<8} {'TIME':<8}  COMMAND\n")
            for user, pid, name, *_ in rows:
                ctx.emit_output(f"{pid:>6}  pts/0    00:00:00  {name}\n")


class TopCommand(BaseCommand):
    """top/htop – live resource monitor (snapshot mode)."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        is_htop = parsed.base == "htop"
        try:
            import psutil
            cpu   = psutil.cpu_percent(interval=0.3)
            mem   = psutil.virtual_memory()
            procs = list(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]))
            procs.sort(key=lambda p: p.info.get("cpu_percent", 0) or 0, reverse=True)
        except ImportError:
            cpu  = 12.4
            mem  = type("M", (), {"percent": 45.2, "used": 1_800_000_000, "total": 4_000_000_000, "available": 2_200_000_000})()
            procs = []

        now   = datetime.now().strftime("%H:%M:%S")
        title = "htop" if is_htop else "top"
        ctx.emit_output(
            f"\033[1m{title} - {now}\033[0m\n"
            f"Tasks: {len(procs) or 7} total\n"
            f"%Cpu(s): {cpu:.1f}  us,  0.0 sy,  0.0 ni, {100-cpu:.1f} id\n"
            f"MiB Mem : {mem.total/1e6:>8.1f} total, {mem.available/1e6:>8.1f} free, "
            f"{mem.used/1e6:>8.1f} used\n\n"
            f"{'PID':>6}  {'%CPU':>5}  {'%MEM':>5}  COMMAND\n"
        )
        shown = procs[:15] if procs else []
        for p in shown:
            try:
                inf = p.info
                ctx.emit_output(
                    f"{inf['pid']:>6}  {inf['cpu_percent']:>5.1f}  "
                    f"{inf['memory_percent']:>5.1f}  {inf['name']}\n"
                )
            except Exception:
                pass
        if not shown:
            for pid, name, cpu_p, mem_p in [
                (1, "systemd", 0.0, 0.1), (512, "bash", 0.0, 0.2),
                (513, "qvault-os", 2.1, 5.6), (514, "python3", 1.2, 3.4),
            ]:
                ctx.emit_output(f"{pid:>6}  {cpu_p:>5.1f}  {mem_p:>5.1f}  {name}\n")


class DFCommand(BaseCommand):
    """df – report filesystem disk space."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        human = "h" in parsed.flags
        try:
            import psutil
            usage = psutil.disk_usage(str(ctx.base_dir))
            total = usage.total
            used  = usage.used
            free  = usage.free
            pct   = usage.percent
        except Exception:
            total, used, free, pct = 50 * 2**30, 22 * 2**30, 28 * 2**30, 44.0

        def fmt(b: int) -> str:
            if not human:
                return str(b // 1024)
            for unit in ("K", "M", "G", "T"):
                b //= 1024
                if b < 1024:
                    return f"{b}{unit}"
            return f"{b}T"

        hdr = f"{'Filesystem':<20} {'Size':>8} {'Used':>8} {'Avail':>8} {'Use%':>5}  Mounted on\n"
        ctx.emit_output(hdr)
        ctx.emit_output(f"{'q-vault-fs':<20} {fmt(total):>8} {fmt(used):>8} {fmt(free):>8} {pct:>4.0f}%  /\n")
        ctx.emit_output(f"{'tmpfs':<20} {'64M':>8} {'0':>8} {'64M':>8} {0:>4}%  /tmp\n")


class DUCommand(BaseCommand):
    """du – estimate file/directory space usage."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        human    = "h" in parsed.flags
        summary  = "s" in parsed.flags
        max_dep  = 1 if summary else (int(parsed.args[0]) if ("d" in parsed.flags and parsed.args) else 999)
        targets  = [a for a in parsed.args if not a.isdigit()] or ["."]

        def fmt(b: int) -> str:
            if not human:
                return str(b // 1024)
            for unit in ("K", "M", "G"):
                b //= 1024
                if b < 1024:
                    return f"{b}{unit}"
            return f"{b}G"

        def _size(path: Path, depth: int = 0) -> int:
            if path.is_file():
                return path.stat().st_size
            total = 0
            try:
                for child in path.iterdir():
                    total += _size(child, depth + 1)
                    if not summary and depth < max_dep:
                        try:
                            rel = str(child.relative_to(ctx.base_dir))
                        except ValueError:
                            rel = str(child)
                        ctx.emit_output(f"{fmt(child.stat().st_size if child.is_file() else total):>8}  {rel}\n")
            except PermissionError:
                pass
            return total

        for name in targets:
            t = (ctx.cwd / name).resolve()
            if not str(t).startswith(str(ctx.base_dir)):
                ctx.emit_output(OutputFormatter.permission_denied(name))
                continue
            if not t.exists():
                ctx.emit_output(f"du: cannot access '{name}': No such file or directory\n")
                continue
            total_size = _size(t)
            try:
                rel = str(t.relative_to(ctx.base_dir))
            except ValueError:
                rel = str(t)
            ctx.emit_output(f"{fmt(total_size):>8}  {rel}\n")


class FreeCommand(BaseCommand):
    """free – display amount of free and used memory."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        human = "h" in parsed.flags
        try:
            import psutil
            m = psutil.virtual_memory()
            s = psutil.swap_memory()
            total, used, free, shared, buffers = m.total, m.used, m.available, 0, m.buffers if hasattr(m, "buffers") else 0
            stotal, sused, sfree = s.total, s.used, s.free
        except ImportError:
            total, used, free, shared, buffers = 4 * 2**30, 2 * 2**30, 2 * 2**30, 100 * 2**20, 200 * 2**20
            stotal, sused, sfree = 2 * 2**30, 0, 2 * 2**30

        div  = 1 if human else 1024
        unit = "" if human else "Ki"

        def f(b: int) -> str:
            if human:
                for u in ("B", "Ki", "Mi", "Gi"):
                    if b < 1024:
                        return f"{b}{u}"
                    b //= 1024
                return f"{b}Gi"
            return str(b // 1024)

        ctx.emit_output(
            f"{'':>15} {'total':>10} {'used':>10} {'free':>10} {'shared':>10} {'buff/cache':>10} {'available':>10}\n"
            f"{'Mem:':<15} {f(total):>10} {f(used):>10} {f(free):>10} {f(shared):>10} {f(buffers):>10} {f(free):>10}\n"
            f"{'Swap:':<15} {f(stotal):>10} {f(sused):>10} {f(sfree):>10}\n"
        )


class StatCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("stat: missing operand\n")
            return
        for name in parsed.args:
            t = ctx.resolve_one(name)
            if t is None:
                continue
            if not t.exists():
                ctx.emit_output(f"stat: cannot stat '{name}': No such file or directory\n")
                continue
            try:
                s    = t.stat()
                kind = "directory" if t.is_dir() else "regular file"
                ctx.emit_output(
                    f"  File: {t.name}\n"
                    f"  Size: {s.st_size:<12} Blocks: {(s.st_size+511)//512:<8} {kind}\n"
                    f"Access: (0755/-rwxr-xr-x)  Uid: (1000/   user)  Gid: (1000/   user)\n"
                    f"Access: {datetime.fromtimestamp(s.st_atime)}\n"
                    f"Modify: {datetime.fromtimestamp(s.st_mtime)}\n"
                    f"Change: {datetime.fromtimestamp(s.st_ctime)}\n"
                )
            except Exception as exc:
                ctx.emit_output(f"stat: {exc}\n")


class WCCommand(BaseCommand):
    """wc – word, line, and character count."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("wc: missing operand\n")
            return
        count_l = "l" in parsed.flags
        count_w = "w" in parsed.flags
        count_c = "c" in parsed.flags or "m" in parsed.flags
        if not (count_l or count_w or count_c):
            count_l = count_w = count_c = True

        totals = [0, 0, 0]
        for name in parsed.args:
            t = ctx.resolve_one(name)
            if t is None or not t.exists():
                ctx.emit_output(f"wc: {name}: No such file or directory\n")
                continue
            try:
                text  = t.read_text(errors="replace")
                lines = len(text.splitlines())
                words = len(text.split())
                chars = len(text)
                totals[0] += lines; totals[1] += words; totals[2] += chars
                parts = []
                if count_l: parts.append(f"{lines:>7}")
                if count_w: parts.append(f"{words:>7}")
                if count_c: parts.append(f"{chars:>7}")
                ctx.emit_output(" ".join(parts) + f" {name}\n")
            except Exception as exc:
                ctx.emit_output(f"wc: {exc}\n")

        if len(parsed.args) > 1:
            parts = []
            if count_l: parts.append(f"{totals[0]:>7}")
            if count_w: parts.append(f"{totals[1]:>7}")
            if count_c: parts.append(f"{totals[2]:>7}")
            ctx.emit_output(" ".join(parts) + " total\n")


class SortCommand(BaseCommand):
    """sort – sort lines of text files."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        reverse = "r" in parsed.flags
        unique  = "u" in parsed.flags
        numeric = "n" in parsed.flags
        if not parsed.args:
            ctx.emit_output("sort: reading from stdin not supported\n")
            return
        for name in parsed.args:
            t = ctx.resolve_one(name)
            if t is None or not t.exists():
                ctx.emit_output(f"sort: {name}: No such file or directory\n")
                continue
            try:
                lines = t.read_text(errors="replace").splitlines()
                key   = (lambda x: float(x) if x.replace(".", "").lstrip("-").isdigit() else 0) if numeric else str.lower
                lines = sorted(set(lines) if unique else lines, key=key, reverse=reverse)
                ctx.emit_output("\n".join(lines) + "\n")
            except Exception as exc:
                ctx.emit_output(f"sort: {exc}\n")


class UniqCommand(BaseCommand):
    """uniq – report or omit repeated lines."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        count = "c" in parsed.flags
        if not parsed.args:
            ctx.emit_output("uniq: reading from stdin not supported\n")
            return
        t = ctx.resolve_one(parsed.args[0])
        if t is None or not t.exists():
            ctx.emit_output(f"uniq: {parsed.args[0]}: No such file or directory\n")
            return
        try:
            lines = t.read_text(errors="replace").splitlines()
            result, prev, cnt = [], None, 0
            for line in lines:
                if line == prev:
                    cnt += 1
                else:
                    if prev is not None:
                        result.append((cnt, prev))
                    prev, cnt = line, 1
            if prev is not None:
                result.append((cnt, prev))
            for c, l in result:
                prefix = f"{c:>7} " if count else ""
                ctx.emit_output(prefix + l + "\n")
        except Exception as exc:
            ctx.emit_output(f"uniq: {exc}\n")


class DiffCommand(BaseCommand):
    """diff – compare two files line by line."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if len(parsed.args) < 2:
            ctx.emit_output("diff: missing operand\nUsage: diff FILE1 FILE2\n")
            return
        t1 = ctx.resolve_one(parsed.args[0])
        t2 = ctx.resolve_one(parsed.args[1])
        if t1 is None or t2 is None:
            return
        if not t1.exists():
            ctx.emit_output(f"diff: {parsed.args[0]}: No such file or directory\n"); return
        if not t2.exists():
            ctx.emit_output(f"diff: {parsed.args[1]}: No such file or directory\n"); return
        try:
            import difflib
            lines1 = t1.read_text(errors="replace").splitlines(keepends=True)
            lines2 = t2.read_text(errors="replace").splitlines(keepends=True)
            diff   = list(difflib.unified_diff(
                lines1, lines2,
                fromfile=parsed.args[0], tofile=parsed.args[1], lineterm=""
            ))
            if diff:
                ctx.emit_output("\n".join(diff) + "\n")
            else:
                ctx.emit_output("")  # files identical — no output (POSIX)
        except Exception as exc:
            ctx.emit_output(f"diff: {exc}\n")


class TreeCommand(BaseCommand):
    """tree – display directory structure as a tree."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        target_str = parsed.args[0] if parsed.args else "."
        target = (ctx.cwd / target_str).resolve()
        if not str(target).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(target_str))
            return
        if not target.exists() or not target.is_dir():
            ctx.emit_output(f"tree: {target_str}: No such file or directory\n")
            return

        max_depth = 3
        all_files = "a" in parsed.flags
        lines = []
        dir_count = [0]
        file_count = [0]

        def _walk(path: Path, prefix: str, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return
            entries = [e for e in entries if all_files or not e.name.startswith(".")]
            for i, entry in enumerate(entries):
                is_last  = (i == len(entries) - 1)
                connector = "└── " if is_last else "├── "
                extension = "    " if is_last else "│   "
                name = f"\033[34m{entry.name}\033[0m" if entry.is_dir() else entry.name
                lines.append(f"{prefix}{connector}{name}")
                if entry.is_dir():
                    dir_count[0] += 1
                    _walk(entry, prefix + extension, depth + 1)
                else:
                    file_count[0] += 1

        lines.append(target_str)
        _walk(target, "", 0)
        lines.append(f"\n{dir_count[0]} directories, {file_count[0]} files")
        ctx.emit_output("\n".join(lines) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Network
# ─────────────────────────────────────────────────────────────────────────────

class PingCommand(BaseCommand):
    """ping – real subprocess ping (already in whitelist)."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("ping: missing host operand\nUsage: ping [-c count] HOST\n")
            return
        # Delegate to real subprocess via executor
        ctx.executor.run_subprocess(parsed.parts)


class CurlCommand(BaseCommand):
    """curl – HTTP request simulator."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("curl: try 'curl --help' for more information\n")
            return
        url      = parsed.args[-1]
        verbose  = "v" in parsed.flags
        output   = None
        for i, p in enumerate(parsed.parts):
            if p in ("-o", "--output") and i + 1 < len(parsed.parts):
                output = parsed.parts[i + 1]

        ctx.emit_output(f"  % Total    % Received  Xferd  Average Speed   Time\n")
        ctx.emit_output(f"  0     0    0     0    0     0      0      0 --:--:--\n")
        ctx.emit_output(f"curl: (simulated) GET {url}\n")
        ctx.emit_output(f"HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html><!-- simulated response --></html>\n")

        if output:
            t = ctx.resolve_one(output)
            if t:
                try:
                    t.write_text(f"<!-- Simulated curl response from {url} -->\n")
                    ctx.emit_output(f"  Saved to '{output}'\n")
                except Exception as exc:
                    ctx.emit_output(f"curl: write failed: {exc}\n")


class WgetCommand(BaseCommand):
    """wget – non-interactive download simulator."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("wget: missing URL\n")
            return
        url      = parsed.args[-1]
        filename = url.split("/")[-1] or "index.html"
        outfile  = None
        for i, p in enumerate(parsed.parts):
            if p in ("-O", "--output-document") and i + 1 < len(parsed.parts):
                outfile = parsed.parts[i + 1]
        outfile = outfile or filename

        ctx.emit_output(f"--{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n")
        ctx.emit_output(f"Resolving host... (simulated)\nConnecting... connected.\n")
        ctx.emit_output(f"HTTP request sent, awaiting response... 200 OK\n")
        ctx.emit_output(f"Length: 4096 (4.0K) [text/html]\nSaving to: '{outfile}'\n\n")
        ctx.emit_output(f"100%[================================>] 4,096  --.-KB/s    in 0.001s\n\n")
        ctx.emit_output(f"'{outfile}' saved [4096/4096]\n")

        t = ctx.resolve_one(outfile)
        if t:
            try:
                t.write_text(f"<!-- Simulated wget download from {url} -->\n")
            except Exception:
                pass


class SSHCommand(BaseCommand):
    """ssh – remote shell simulator."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("usage: ssh [-p port] [user@]hostname [command]\n")
            return
        target = parsed.args[-1]
        port   = "22"
        for i, p in enumerate(parsed.parts):
            if p == "-p" and i + 1 < len(parsed.parts):
                port = parsed.parts[i + 1]

        ctx.emit_output(f"ssh: Connecting to {target} on port {port}...\n")
        ctx.emit_output(f"ssh: [SIMULATED] Remote connections are not available in Q-Vault OS sandbox.\n")
        ctx.emit_output(f"ssh: Connection closed.\n")


# ─────────────────────────────────────────────────────────────────────────────
# Documentation & Help
# ─────────────────────────────────────────────────────────────────────────────

MAN_PAGES: dict[str, str] = {
    "ls":      "ls - list directory contents\n\nUsage: ls [OPTION]... [FILE]...\n\n  -a   do not ignore entries starting with .\n  -l   use a long listing format\n  -h   with -l, print sizes in human readable format\n  -R   list subdirectories recursively\n",
    "cd":      "cd - change the shell working directory\n\nUsage: cd [DIR]\n\n  ~   home directory\n  -   previous directory\n  ..  parent directory\n",
    "pwd":     "pwd - print name of current/working directory\n",
    "mkdir":   "mkdir - make directories\n\nUsage: mkdir [OPTION]... DIRECTORY...\n\n  -p   no error if existing, make parent directories as needed\n  -m   set file mode (as in chmod)\n",
    "rm":      "rm - remove files or directories\n\nUsage: rm [OPTION]... FILE...\n\n  -r, -R  remove directories and their contents recursively\n  -f      ignore nonexistent files, never prompt\n",
    "cp":      "cp - copy files and directories\n\nUsage: cp [OPTION]... SOURCE DEST\n\n  -r, -R  copy directories recursively\n",
    "mv":      "mv - move (rename) files\n\nUsage: mv [OPTION]... SOURCE DEST\n       mv [OPTION]... SOURCE... DIRECTORY\n",
    "cat":     "cat - concatenate files and print on the standard output\n\nUsage: cat [OPTION]... [FILE]...\n\n  -n   number all output lines\n",
    "less":    "less - opposite of more (file viewer)\n\nUsage: less [FILE]\n\nShows the first 40 lines. Use 'cat' for full output.\n",
    "grep":    "grep - print lines matching a pattern\n\nUsage: grep [OPTION]... PATTERN [FILE]...\n\n  -i   ignore case\n  -n   print line numbers\n  -r   recursive\n  -v   invert match\n  -c   count matches only\n  -l   print filenames only\n  -w   match whole words\n",
    "find":    "find - search for files in a directory hierarchy\n\nUsage: find [PATH] [EXPRESSION]\n\n  -name PATTERN   file name matches shell pattern\n  -type f|d       file type (f=file, d=directory)\n  -size N         file uses more than N*1024 bytes\n",
    "chmod":   "chmod - change file mode bits\n\nUsage: chmod [OPTION]... MODE FILE...\n\n  Modes: octal (755) or symbolic (u+x, go-w)\n  -R   change files and directories recursively\n",
    "chown":   "chown - change file owner and group\n\nUsage: chown [OPTION]... OWNER[:GROUP] FILE...\n\n  -R   operate on files and directories recursively\n  Requires root/sudo privileges.\n",
    "sudo":    "sudo - execute a command as another user\n\nUsage: sudo [OPTION] COMMAND\n\n  Run a command with elevated (root) privileges.\n  You will be prompted for your password.\n",
    "ps":      "ps - report a snapshot of current processes\n\nUsage: ps [OPTIONS]\n\n  aux   show all processes with CPU and memory usage\n",
    "top":     "top - display Linux processes\n\nUsage: top\n\nProvides a dynamic real-time view of running processes.\n",
    "htop":    "htop - interactive process viewer\n\nUsage: htop\n\nSimilar to top but with an improved, interactive interface.\n",
    "df":      "df - report file system disk space usage\n\nUsage: df [OPTION]... [FILE]...\n\n  -h   print sizes in human readable format\n",
    "du":      "du - estimate file space usage\n\nUsage: du [OPTION]... [FILE]...\n\n  -h   human-readable sizes\n  -s   display only a total for each argument\n",
    "free":    "free - display amount of free and used memory\n\nUsage: free [OPTION]\n\n  -h   human-readable output\n",
    "ping":    "ping - send ICMP ECHO_REQUEST to network hosts\n\nUsage: ping [-c count] HOST\n\n  -c N   stop after N replies\n",
    "curl":    "curl - transfer a URL\n\nUsage: curl [OPTIONS] URL\n\n  -o FILE   save output to FILE\n  -v        verbose output\n",
    "wget":    "wget - non-interactive network downloader\n\nUsage: wget [OPTIONS] URL\n\n  -O FILE   save output to FILE\n",
    "ssh":     "ssh - OpenSSH remote login client\n\nUsage: ssh [OPTIONS] [user@]hostname\n\n  -p PORT   specify port number\n",
    "nano":    "nano - command line text editor\n\nUsage: nano [FILE]\n\nOpens the built-in graphical editor overlay.\n",
    "vim":     "vim - Vi IMproved text editor\n\nUsage: vim [FILE]\n\nOpens the built-in graphical editor overlay (same as nano).\n",
    "touch":   "touch - change file timestamps\n\nUsage: touch [OPTION]... FILE...\n\nCreate an empty FILE if it does not exist.\n",
    "man":     "man - an interface to the system reference manuals\n\nUsage: man [COMMAND]\n\nDisplays the manual page for the given command.\n",
    "history": "history - display command history\n\nUsage: history [N]\n\nDisplays the last N commands (default: all).\n",
    "clear":   "clear - clear the terminal screen\n",
    "echo":    "echo - display a line of text\n\nUsage: echo [STRING]...\n\n  -n   do not output the trailing newline\n",
    "whoami":  "whoami - print effective user name\n",
    "id":      "id - print real and effective user and group IDs\n",
    "date":    "date - print or set the system date and time\n",
    "uname":   "uname - print system information\n\nUsage: uname [OPTION]\n\n  -a   print all information\n  -r   kernel release\n  -s   kernel name\n",
    "wc":      "wc - print newline, word, and byte counts for each file\n\nUsage: wc [OPTION]... [FILE]...\n\n  -l   print newline counts\n  -w   print word counts\n  -c   print byte counts\n",
    "sort":    "sort - sort lines of text files\n\nUsage: sort [OPTION]... [FILE]...\n\n  -r   reverse the result\n  -n   compare according to string numerical value\n  -u   output only the first of an equal run\n",
    "diff":    "diff - compare files line by line\n\nUsage: diff FILE1 FILE2\n",
    "tree":    "tree - list contents of directories in a tree-like format\n\nUsage: tree [OPTIONS] [DIRECTORY]\n\n  -a   all files including hidden\n",
    "env":     "env - run a program in a modified environment\n\nUsage: env\n\nPrint current environment variables.\n",
    "which":   "which - locate a command\n\nUsage: which COMMAND\n",
    "type":    "type - describe a command\n\nUsage: type COMMAND\n",
    "alias":   "alias - define or display aliases\n\nUsage: alias [name[='value'] ...]\n",
    "exit":    "exit - exit the shell\n\nUsage: exit [N]\n",
}


class ManCommand(BaseCommand):
    """man – display manual pages."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("What manual page do you want?\n")
            return
        cmd = parsed.args[0].lower()
        page = MAN_PAGES.get(cmd)
        if page:
            ctx.emit_output(f"\nMANUAL PAGE: {cmd.upper()}\n{'─'*50}\n{page}\n")
        else:
            ctx.emit_output(f"No manual entry for {cmd}\n")


class HistoryCommand(BaseCommand):
    """history – show command history."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        hist = CommandContext._history
        n    = int(parsed.args[0]) if parsed.args and parsed.args[0].isdigit() else len(hist)
        show = hist[-n:] if n < len(hist) else hist
        for i, cmd in enumerate(show, start=max(1, len(hist) - n + 1)):
            ctx.emit_output(f"  {i:>4}  {cmd}\n")


# ─────────────────────────────────────────────────────────────────────────────
# System Info
# ─────────────────────────────────────────────────────────────────────────────

class UnameCommand(BaseCommand):
    """uname – print system information."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        all_info = "a" in parsed.flags
        release  = "r" in parsed.flags
        sysname  = "s" in parsed.flags or not parsed.flags

        sn  = "Q-VaultOS"
        hn  = "q-vault"
        rel = "5.15.0-qvault"
        ver = "#1 SMP Q-Vault 5.15.0 (2025)"
        mch = "x86_64"

        if all_info:
            ctx.emit_output(f"{sn} {hn} {rel} {ver} {mch} GNU/Linux\n")
        elif release:
            ctx.emit_output(rel + "\n")
        else:
            ctx.emit_output(sn + "\n")


class DateCommand(BaseCommand):
    """date – print current date/time."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        fmt = parsed.args[0] if parsed.args and parsed.args[0].startswith("+") else None
        now = datetime.now()
        if fmt:
            # Convert strftime-like +FORMAT
            out = now.strftime(fmt[1:].replace("%D", "%m/%d/%y").replace("%T", "%H:%M:%S"))
        else:
            out = now.strftime("%a %b %d %H:%M:%S %Z %Y")
        ctx.emit_output(out + "\n")


class UptimeCommand(BaseCommand):
    """uptime – tell how long the system has been running."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        try:
            import psutil
            bt    = psutil.boot_time()
            delta = time.time() - bt
        except ImportError:
            delta = 3600.0
        hours, rem = divmod(int(delta), 3600)
        mins = rem // 60
        now  = datetime.now().strftime("%H:%M:%S")
        ctx.emit_output(f" {now} up {hours}:{mins:02d},  1 user,  load average: 0.10, 0.12, 0.08\n")


class IDCommand(BaseCommand):
    """id – print user and group identifiers."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        role = ctx.get_role()
        if role == "admin":
            ctx.emit_output("uid=0(root) gid=0(root) groups=0(root),4(adm),27(sudo)\n")
        else:
            ctx.emit_output("uid=1000(user) gid=1000(user) groups=1000(user),4(adm)\n")


class WhoamiCommand(BaseCommand):
    """whoami – print effective user name."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        # Delegated to TerminalEngine hook which knows current_user
        ctx.executor._handle_whoami([])


class WhichCommand(BaseCommand):
    """which – show path of a command."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("which: missing argument\n")
            return
        for cmd in parsed.args:
            if cmd in COMMAND_REGISTRY or cmd in CommandParser.BUILTIN_COMMANDS:
                ctx.emit_output(f"/usr/bin/{cmd}\n")
            else:
                ctx.emit_output(f"which: no {cmd} in ({CommandContext._session_env.get('PATH', '/usr/bin')})\n")


class TypeCommand(BaseCommand):
    """type – describe a command."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            ctx.emit_output("type: missing argument\n")
            return
        for cmd in parsed.args:
            if cmd in CommandContext._aliases:
                ctx.emit_output(f"{cmd} is aliased to '{CommandContext._aliases[cmd]}'\n")
            elif cmd in COMMAND_REGISTRY or cmd in CommandParser.BUILTIN_COMMANDS:
                ctx.emit_output(f"{cmd} is a shell builtin\n")
            elif cmd in CommandParser.SUBPROCESS_WHITELIST:
                ctx.emit_output(f"{cmd} is /usr/bin/{cmd}\n")
            else:
                ctx.emit_output(f"bash: type: {cmd}: not found\n")


# ─────────────────────────────────────────────────────────────────────────────
# Environment & Session
# ─────────────────────────────────────────────────────────────────────────────

class EnvCommand(BaseCommand):
    """env – print environment variables."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        for k, v in sorted(CommandContext._session_env.items()):
            ctx.emit_output(f"{k}={v}\n")


class ExportCommand(BaseCommand):
    """export – set environment variable."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            # print all exported vars
            for k, v in sorted(CommandContext._session_env.items()):
                ctx.emit_output(f"declare -x {k}=\"{v}\"\n")
            return
        for arg in parsed.args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                CommandContext._session_env[k.strip()] = v.strip()
            else:
                ctx.emit_output(f"export: {arg}: not a valid identifier\n")


class UnsetCommand(BaseCommand):
    """unset – remove environment variable."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        for arg in parsed.args:
            CommandContext._session_env.pop(arg, None)


class AliasCommand(BaseCommand):
    """alias – define or display aliases."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        if not parsed.args:
            for k, v in sorted(CommandContext._aliases.items()):
                ctx.emit_output(f"alias {k}='{v}'\n")
            return
        for arg in parsed.args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                CommandContext._aliases[k.strip()] = v.strip().strip("'\"")
            else:
                v = CommandContext._aliases.get(arg)
                if v:
                    ctx.emit_output(f"alias {arg}='{v}'\n")
                else:
                    ctx.emit_output(f"alias: {arg}: not found\n")


class ExitCommand(BaseCommand):
    """exit/logout – terminate the shell session."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        ctx.emit_output("logout\n")
        # Signal TerminalEngine to lock (graceful exit)
        ctx.executor._emit_output("logout\n")


class LnCommand(BaseCommand):
    """ln – create symbolic links (simulated)."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        symbolic = "s" in parsed.flags
        if len(parsed.args) < 2:
            ctx.emit_output("ln: missing file operand\nUsage: ln [-s] TARGET LINK_NAME\n")
            return
        target, link = parsed.args[0], parsed.args[1]
        kind = "symbolic" if symbolic else "hard"
        ctx.emit_output(f"ln: created {kind} link '{link}' -> '{target}' (simulated)\n")


# ─────────────────────────────────────────────────────────────────────────────
# Existing commands preserved
# ─────────────────────────────────────────────────────────────────────────────

class BashCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        ctx.emit_output("Q-Vault Bourne-Again SHell (bash) v5.2.1\n")
        ctx.emit_output("Type 'exit' to return to main shell.\n")


class ExecCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        target_name = parsed.parts[0][2:] if len(parsed.parts[0]) > 2 else ""
        if not target_name:
            ctx.emit_output("sh: missing operand\n")
            return
        target = (ctx.cwd / target_name).resolve()
        if not str(target).startswith(str(ctx.base_dir)):
            ctx.emit_output(OutputFormatter.permission_denied(target_name))
            return
        if not target.exists():
            ctx.emit_output(f"sh: {target_name}: No such file or directory\n")
            return
        ctx.emit_output(f"[*] Executing {target_name}...\n")
        try:
            content = target.read_text(errors="replace")
            for line in content.splitlines()[:10]:
                if line.strip() and not line.startswith("#"):
                    ctx.emit_output(f"  > {line[:60]}\n")
            ctx.emit_output("[+] Script execution completed.\n")
        except Exception as e:
            ctx.emit_output(f"[ERROR] {e}\n")


class EchoCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        no_newline = "n" in parsed.flags
        text = " ".join(parsed.args)
        # Expand $VAR
        import re
        def _expand(m):
            return CommandContext._session_env.get(m.group(1), "")
        text = re.sub(r"\$(\w+)", _expand, text)
        ctx.emit_output(text + ("" if no_newline else "\n"))


class StressCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        try:
            count = int(parsed.args[0]) if parsed.args else 20
        except ValueError:
            count = 20
        ctx.emit_output(f"[*] Starting Stress Test: Spawning {count} dummy processes...\n")
        from core.event_bus import EVENT_BUS, SystemEvent
        from kernel.memory_manager import MEMORY_MANAGER
        import random
        for i in range(count):
            MEMORY_MANAGER.deallocate(pid=1000 + i)
        for i in range(count):
            pid = 1000 + i
            EVENT_BUS.emit(SystemEvent.PROC_SPAWNED, {"pid": pid, "name": f"stress_{i}"}, source="StressTest")
            size = random.randint(10, 50)
            MEMORY_MANAGER.allocate(pid=pid, size=size, label=f"stress_{i}")
            core_id = i % 4
            EVENT_BUS.emit(SystemEvent.CORE_ASSIGNED, {"pid": pid, "core_id": core_id}, source="StressTest")
            EVENT_BUS.emit(SystemEvent.PROC_SCHEDULED, {"pid": pid, "core_id": core_id}, source="StressTest")
            if i % 5 == 0:
                EVENT_BUS.emit(SystemEvent.INTERRUPT_RAISED, {
                    "interrupt": {"type": "io_burst", "priority": 3, "source_pid": pid, "tick": 0}
                }, source="StressTest")
        ctx.emit_output("[+] Stress test signals sent to EventBus.\n")


class FullStressCommand(BaseCommand):
    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        ctx.emit_output("[*] INITIATING FULL OS COMPREHENSIVE STRESS TEST...\n")
        try:
            from components import stress_tester
            stress_tester._global_tester = stress_tester.AutomatedStressTester(parent=None)
            stress_tester._global_tester.start()
            ctx.emit_output("[+] Stress Test sequence started.\n")
        except Exception as e:
            ctx.emit_output(f"[-] Error: {e}\n")


class EnduranceCommand(BaseCommand):
    """endurance – long-running GUI stress test with leak detection."""

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        try:
            minutes = int(parsed.args[0]) if parsed.args else 5
        except ValueError:
            minutes = 5
        ctx.emit_output(f"[*] Starting {minutes}-minute endurance test...\n")
        ctx.emit_output("    Phases: OPEN -> FOCUS_STORM -> MIN/MAX -> RESIZE -> REOPEN -> SOAK -> CLOSE\n")
        ctx.emit_output("    Monitoring: RSS memory, thread count, window lifecycle\n")
        ctx.emit_output("    Report will be logged when complete.\n\n")
        try:
            from components.endurance_tester import run_endurance
            run_endurance(duration_minutes=minutes)
            ctx.emit_output("[+] Endurance test started. Check logs for telemetry and final report.\n")
        except Exception as e:
            ctx.emit_output(f"[-] Error: {e}\n")


class LegacyDelegateCommand(BaseCommand):
    """Delegates to legacy _handle_X methods on executor."""
    def __init__(self, method_name: str):
        self.method_name = method_name

    def execute(self, parsed: ParsedCommand, ctx: CommandContext) -> None:
        func = getattr(ctx.executor, self.method_name)
        func(parsed.parts)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

COMMAND_REGISTRY: dict[str, BaseCommand] = {
    # ── File & Directory ──
    "ls":          LSCommand(),
    "cd":          CDCommand(),
    "pwd":         PWDCommand(),
    "mkdir":       MKDirCommand(),
    "touch":       TouchCommand(),
    "rmdir":       RMDirCommand(),
    "rm":          RMCommand(),
    "mv":          MVCommand(),
    "cp":          CPCommand(),
    "ln":          LnCommand(),
    "tree":        TreeCommand(),
    # ── Viewing & Editing ──
    "cat":         CatCommand(),
    "less":        LessCommand(),
    "more":        LessCommand(),       # alias for less
    "head":        HeadCommand(),
    "tail":        TailCommand(),
    "nano":        NanoCommand(),
    "vim":         VimCommand(),
    "vi":          VimCommand(),
    # ── Permissions ──
    "chmod":       ChmodCommand(),
    "chown":       ChownCommand(),
    # ── Search ──
    "grep":        GrepCommand(),
    "egrep":       GrepCommand(),       # alias
    "fgrep":       GrepCommand(),       # alias
    "find":        FindCommand(),
    # ── Text Processing ──
    "echo":        EchoCommand(),
    "wc":          WCCommand(),
    "sort":        SortCommand(),
    "uniq":        UniqCommand(),
    "diff":        DiffCommand(),
    # ── System Info ──
    "stat":        StatCommand(),
    "ps":          PSCommand(),
    "top":         TopCommand(),
    "htop":        TopCommand(),
    "df":          DFCommand(),
    "du":          DUCommand(),
    "free":        FreeCommand(),
    "uname":       UnameCommand(),
    "date":        DateCommand(),
    "uptime":      UptimeCommand(),
    "id":          IDCommand(),
    "whoami":      WhoamiCommand(),
    "which":       WhichCommand(),
    "type":        TypeCommand(),
    # ── Network ──
    "ping":        PingCommand(),
    "curl":        CurlCommand(),
    "wget":        WgetCommand(),
    "ssh":         SSHCommand(),
    # ── Documentation ──
    "man":         ManCommand(),
    "history":     HistoryCommand(),
    # ── Environment & Session ──
    "env":         EnvCommand(),
    "export":      ExportCommand(),
    "unset":       UnsetCommand(),
    "alias":       AliasCommand(),
    "exit":        ExitCommand(),
    "logout":      ExitCommand(),
    # ── Shell Builtins (legacy delegate) ──
    "clear":       LegacyDelegateCommand("_handle_clear"),
    "help":        LegacyDelegateCommand("_handle_help"),
    "status":      LegacyDelegateCommand("_handle_status"),
    "ask":         LegacyDelegateCommand("_handle_ask"),
    "passwd":      LegacyDelegateCommand("_handle_passwd"),
    "verify_audit": LegacyDelegateCommand("_handle_verify_audit"),
    # ── Scripting & Extras ──
    "bash":        BashCommand(),
    "sh":          BashCommand(),
    "exec":        ExecCommand(),
    "stress":      StressCommand(),
    "fullstress":  FullStressCommand(),
    "endurance":   EnduranceCommand(),
}
