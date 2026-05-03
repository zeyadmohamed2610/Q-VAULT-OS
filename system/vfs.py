import time
import json
from typing import Dict, Any, List, Optional
from system.security_api import get_security_api

class VNode:
    """Virtual Filesystem Node."""
    def __init__(self, is_dir: bool, content: str = "", owner: str = "root"):
        self.is_dir = is_dir
        self.content = content
        self.owner = owner
        self.created_at = time.time()
        self.modified_at = time.time()
        self.children: Dict[str, 'VNode'] = {}

    @property
    def size(self) -> int:
        if self.is_dir:
            return sum(c.size for c in self.children.values()) + 4096
        return len(self.content.encode('utf-8'))

class VirtualFilesystem:
    def __init__(self):
        self.root = VNode(is_dir=True)
        self._init_tree()

    def _init_tree(self):
        # /home/user
        home = self._mkdir_path("/home/user", owner="user")
        
        # /etc
        etc = self._mkdir_path("/etc")
        self._add_file(etc, "passwd", "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000::/home/user:/bin/bash")
        self._add_file(etc, "os-release", 'NAME="Q-Vault Linux"\nVERSION="1.0"')
        self._add_file(etc, "hostname", "qvault")
        
        # /var/log
        log = self._mkdir_path("/var/log")
        self._add_file(log, "auth.log", "[auth] system booted\n[auth] secure vault initialized")
        
        # /vault -> dynamically resolved folder, but we create a physical hook
        self._mkdir_path("/vault", owner="root")

    def _mkdir_path(self, path: str, owner: str = "root") -> VNode:
        curr = self.root
        for part in filter(None, path.split("/")):
            if part not in curr.children:
                curr.children[part] = VNode(is_dir=True, owner=owner)
            curr = curr.children[part]
        return curr

    def _add_file(self, parent: VNode, name: str, content: str = "", owner: str = "root"):
        parent.children[name] = VNode(is_dir=False, content=content, owner=owner)

    def _resolve_parts(self, start_path: str, cwd: str) -> List[str]:
        if start_path.startswith("/"):
            parts = [p for p in start_path.split("/") if p]
        else:
            base = [p for p in cwd.split("/") if p]
            parts = base + [p for p in start_path.split("/") if p]
            
        final = []
        for p in parts:
            if p == "." or not p:
                continue
            elif p == "..":
                if final: final.pop()
            else:
                final.append(p)
        return final

    def _get_node(self, parts: List[str]) -> Optional[VNode]:
        curr = self.root
        for p in parts:
            if p not in curr.children:
                return None
            curr = curr.children[p]
        return curr

    # ── High Level API ───────────────────────────────────────

    def pwd(self, cwd: str) -> str:
        parts = self._resolve_parts(".", cwd)
        return "/" + "/".join(parts)

    def cd(self, dest: str, cwd: str) -> str:
        parts = self._resolve_parts(dest, cwd)
        node = self._get_node(parts)
        if not node:
            raise FileNotFoundError(f"cd: {dest}: No such file or directory")
        if not node.is_dir:
            raise NotADirectoryError(f"cd: {dest}: Not a directory")
        return "/" + "/".join(parts)

    def ls(self, target: str, cwd: str) -> List[dict]:
        parts = self._resolve_parts(target, cwd)
        
        # Special case for /vault dynamic listing
        if len(parts) == 1 and parts[0] == "vault":
            return self._ls_vault()
            
        node = self._get_node(parts)
        if not node:
            raise FileNotFoundError(f"ls: cannot access '{target}': No such file or directory")
        if not node.is_dir:
            return [{"name": parts[-1], "is_dir": False, "size": node.size, "owner": node.owner}]
            
        return [
            {"name": k, "is_dir": v.is_dir, "size": v.size, "owner": v.owner}
            for k, v in node.children.items()
        ]

    def _ls_vault(self):
        api = get_security_api()
        res = api.list_secrets()
        items = []
        for name in res:
            items.append({"name": name, "is_dir": False, "size": 64, "owner": "vault"})
        return items

    def cat(self, target: str, cwd: str) -> str:
        parts = self._resolve_parts(target, cwd)
        
        # Special case for /vault/ secret reading
        if len(parts) == 2 and parts[0] == "vault":
            api = get_security_api()
            res = api.get_secret(parts[1])
            if res.get("success"):
                return res["value"]
            else:
                raise PermissionError(f"cat: {target}: {res.get('message', 'Access denied')}")

        node = self._get_node(parts)
        if not node:
            raise FileNotFoundError(f"cat: {target}: No such file or directory")
        if node.is_dir:
            raise IsADirectoryError(f"cat: {target}: Is a directory")
            
        return node.content

    def touch(self, target: str, cwd: str, content: str = ""):
        parts = self._resolve_parts(target, cwd)
        if len(parts) == 0:
            raise ValueError("Invalid path")

        if len(parts) == 2 and parts[0] == "vault":
            # Store secret -> /vault dynamic bridge
            api = get_security_api()
            res = api.store_secret(parts[1], content)
            if not res.get("success"):
                raise PermissionError(f"touch: {target}: {res.get('message', 'Failed to write')}")
            return

        parent_parts = parts[:-1]
        parent = self._get_node(parent_parts)
        if not parent or not parent.is_dir:
            raise FileNotFoundError(f"touch: cannot touch '{target}': No such directory")

        name = parts[-1]
        if name in parent.children:
            parent.children[name].modified_at = time.time()
            if content:
                parent.children[name].content = content
        else:
            parent.children[name] = VNode(is_dir=False, content=content, owner="user")

    def mkdir(self, target: str, cwd: str):
        parts = self._resolve_parts(target, cwd)
        if not parts:
            raise ValueError("Invalid path")
            
        if parts[0] == "vault":
            raise PermissionError("mkdir: cannot create directory under /vault")

        parent_parts = parts[:-1]
        parent = self._get_node(parent_parts)
        if not parent or not parent.is_dir:
            raise FileNotFoundError(f"mkdir: cannot create directory '{target}': No such file or directory")

        name = parts[-1]
        if name in parent.children:
            raise FileExistsError(f"mkdir: cannot create directory '{target}': File exists")
            
        parent.children[name] = VNode(is_dir=True, owner="user")

    def rm(self, target: str, cwd: str, recursive: bool = False):
        parts = self._resolve_parts(target, cwd)
        if not parts:
            raise ValueError("Invalid path")
            
        if parts[0] == "vault":
            raise PermissionError("rm: access denied to vault data")

        parent_parts = parts[:-1]
        parent = self._get_node(parent_parts)
        name = parts[-1]
        
        if not parent or name not in parent.children:
            raise FileNotFoundError(f"rm: cannot remove '{target}': No such file or directory")
            
        node = parent.children[name]
        if node.is_dir and not recursive:
            raise IsADirectoryError(f"rm: cannot remove '{target}': Is a directory")
            
        del parent.children[name]

VFS = VirtualFilesystem()
