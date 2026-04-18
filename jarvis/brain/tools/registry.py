"""
Tool registry for JARVIS.

Each tool is a Python function + an Anthropic tool-spec dict. The agent picks
which tool to call; we execute it and pass the result back. Nothing fancy.

Security model:
- Every tool has a policy (safe | confirm | deny) loaded from jarvis.yaml.
- `safe` runs immediately.
- `confirm` returns a CONFIRMATION_REQUIRED sentinel and the caller (server.py)
  asks the user over voice before actually invoking.
- `deny` refuses outright.
"""
from __future__ import annotations
import asyncio
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Awaitable

import paramiko
import httpx
import structlog

log = structlog.get_logger()


# ── Tool specs for the Anthropic API ───────────────────────────────────
TOOL_SPECS = [
    {
        "name": "web_search",
        "description": "Search the web for current information. Returns titles, URLs, and snippets. Use sparingly — each search costs $0.01.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, 1-6 words ideal"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ssh_run_readonly",
        "description": "Run a whitelisted read-only command on a lab host. Use for status checks, disk usage, process listings, etc. Safe — no confirmation needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Host name from config: proxmox, kali, splunk, pi, or proliant"},
                "command": {"type": "string", "description": "Command to run. Must be in the readonly whitelist."},
            },
            "required": ["target", "command"],
        },
    },
    {
        "name": "ssh_run_command",
        "description": "Run an arbitrary shell command on a lab host. REQUIRES CONFIRMATION. Use only for state-changing operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Host name from config"},
                "command": {"type": "string", "description": "Shell command"},
                "reason": {"type": "string", "description": "One-line reason for this command, spoken to the user before confirmation"},
            },
            "required": ["target", "command", "reason"],
        },
    },
    {
        "name": "docker_ps",
        "description": "List running Docker containers on a host.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "all": {"type": "boolean", "description": "Include stopped containers", "default": False},
            },
            "required": ["target"],
        },
    },
    {
        "name": "docker_logs",
        "description": "Fetch recent logs from a Docker container.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "container": {"type": "string"},
                "lines": {"type": "integer", "default": 50},
            },
            "required": ["target", "container"],
        },
    },
    {
        "name": "docker_restart",
        "description": "Restart a Docker container. REQUIRES CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "container": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["target", "container", "reason"],
        },
    },
    {
        "name": "launch_app",
        "description": "Launch a desktop application on the Fedora ProBook frontend. REQUIRES CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "Application name, e.g. 'firefox', 'code', 'terminal'"},
                "reason": {"type": "string"},
            },
            "required": ["app", "reason"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in a directory on the ProLiant brain host. For laptop files, use the frontend tool bridge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file on the ProLiant brain host. Max 100KB.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "home_assistant_query",
        "description": "Query Home Assistant state for an entity (light, sensor, switch, etc).",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "e.g. 'light.living_room' or 'sensor.outdoor_temp'"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "home_assistant_action",
        "description": "Call a Home Assistant service (turn on/off, set brightness, etc). REQUIRES CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "e.g. 'light', 'switch'"},
                "service": {"type": "string", "description": "e.g. 'turn_on', 'turn_off'"},
                "entity_id": {"type": "string"},
                "data": {"type": "object", "description": "Additional service data"},
            },
            "required": ["domain", "service", "entity_id"],
        },
    },
    {
        "name": "budget_status",
        "description": "Report current API spend and remaining budget.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class Toolbox:
    """Holds runtime state (config, clients) and dispatches tool calls."""

    def __init__(self, config: dict, spend_tracker, frontend_bridge):
        self.config = config
        self.spend = spend_tracker
        self.frontend = frontend_bridge  # websocket handle to the ProBook
        self._ssh_clients: dict[str, paramiko.SSHClient] = {}

    # ── SSH connection pool ────────────────────────────────────────────
    def _ssh(self, target: str) -> paramiko.SSHClient:
        targets = self.config["ssh_targets"]
        if target not in targets:
            raise ValueError(f"Unknown SSH target: {target}")
        if target in self._ssh_clients:
            client = self._ssh_clients[target]
            transport = client.get_transport()
            if transport and transport.is_active():
                return client
        t = targets[target]
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=t["host"],
            username=t["user"],
            key_filename="/home/jarvis/.ssh/id_ed25519",
            timeout=10,
        )
        self._ssh_clients[target] = client
        return client

    def _ssh_exec(self, target: str, command: str, timeout: int = 30) -> dict:
        client = self._ssh(target)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")[:8000]
        err = stderr.read().decode(errors="replace")[:2000]
        rc = stdout.channel.recv_exit_status()
        return {"exit_code": rc, "stdout": out, "stderr": err}

    def _is_readonly_command(self, command: str) -> bool:
        wl = self.config.get("ssh_readonly_commands", [])
        cmd_stripped = command.strip()
        for allowed in wl:
            if cmd_stripped == allowed or cmd_stripped.startswith(allowed + " "):
                return True
        return False

    # ── Tool implementations ──────────────────────────────────────────
    async def web_search(self, query: str) -> dict:
        self.spend.check_web_search()
        # Claude's native web_search tool handles this better than us hitting
        # a search API directly — it's invoked via server-side tool passthrough.
        # This stub exists so the schema is complete; server.py routes web_search
        # to Anthropic's built-in tool instead of this function.
        return {"_passthrough": True, "query": query}

    async def ssh_run_readonly(self, target: str, command: str) -> dict:
        if not self._is_readonly_command(command):
            return {
                "error": f"Command not in readonly whitelist. Use ssh_run_command (requires confirmation) for: {command}"
            }
        return self._ssh_exec(target, command)

    async def ssh_run_command(self, target: str, command: str, reason: str) -> dict:
        # Confirmation gate is handled upstream in server.py before this runs.
        return self._ssh_exec(target, command, timeout=120)

    async def docker_ps(self, target: str, all: bool = False) -> dict:
        cmd = "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'" if all \
              else "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'"
        return self._ssh_exec(target, cmd)

    async def docker_logs(self, target: str, container: str, lines: int = 50) -> dict:
        safe_container = shlex.quote(container)
        cmd = f"docker logs --tail {int(lines)} {safe_container} 2>&1"
        return self._ssh_exec(target, cmd)

    async def docker_restart(self, target: str, container: str, reason: str) -> dict:
        safe_container = shlex.quote(container)
        return self._ssh_exec(target, f"docker restart {safe_container}")

    async def launch_app(self, app: str, reason: str) -> dict:
        # Delegated to frontend over websocket — the ProBook runs the app
        if not self.frontend:
            return {"error": "Frontend not connected"}
        return await self.frontend.request({
            "type": "launch_app",
            "app": app,
        })

    async def list_files(self, path: str) -> dict:
        p = Path(path).expanduser()
        if not p.exists():
            return {"error": f"Path does not exist: {path}"}
        if not p.is_dir():
            return {"error": f"Not a directory: {path}"}
        entries = []
        for child in sorted(p.iterdir())[:200]:
            entries.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            })
        return {"path": str(p), "entries": entries}

    async def read_file(self, path: str) -> dict:
        p = Path(path).expanduser()
        if not p.is_file():
            return {"error": f"Not a file: {path}"}
        size = p.stat().st_size
        if size > 100_000:
            return {"error": f"File too large ({size} bytes, max 100000)"}
        try:
            return {"path": str(p), "content": p.read_text(errors="replace")}
        except Exception as e:
            return {"error": str(e)}

    async def home_assistant_query(self, entity_id: str) -> dict:
        ha = self.config.get("home_assistant", {})
        if not ha.get("enabled"):
            return {"error": "Home Assistant not enabled in config"}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{ha['url']}/api/states/{entity_id}",
                headers={"Authorization": f"Bearer {ha['token']}"},
            )
            return r.json() if r.status_code == 200 else {"error": f"HA {r.status_code}"}

    async def home_assistant_action(self, domain: str, service: str,
                                    entity_id: str, data: dict = None) -> dict:
        ha = self.config.get("home_assistant", {})
        if not ha.get("enabled"):
            return {"error": "Home Assistant not enabled"}
        payload = {"entity_id": entity_id, **(data or {})}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{ha['url']}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {ha['token']}"},
                json=payload,
            )
            return {"status": r.status_code, "body": r.text[:500]}

    async def budget_status(self) -> dict:
        return self.spend.status()

    # ── Dispatcher ────────────────────────────────────────────────────
    async def dispatch(self, name: str, args: dict) -> Any:
        method = getattr(self, name, None)
        if not method:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await method(**args)
        except TypeError as e:
            return {"error": f"Bad arguments for {name}: {e}"}
        except Exception as e:
            log.exception("tool_error", tool=name)
            return {"error": f"{type(e).__name__}: {e}"}

    def policy_for(self, tool_name: str) -> str:
        return self.config.get("tool_policy", {}).get(tool_name, "confirm")
