"""AgentSpec MCP server — tool implementations.

Author: Emerson Antonio
Date: 2026-06-17

The server speaks JSON-RPC 2.0 over stdio as required by the Model Context
Protocol specification. We intentionally avoid the optional ``mcp`` SDK so
the package stays zero-dependency — every MCP client can still negotiate
the protocol because we implement the small surface the spec mandates:

- ``initialize``
- ``tools/list``
- ``tools/call``

Tools exposed:

| Tool | Description |
|------|-------------|
| ``kb_search`` | Substring search over ``resources/kb/`` |
| ``kb_read`` | Read a KB markdown/YAML file |
| ``route_agent`` | Recommend agents for a free-form task |
| ``sdd_status`` | Inspect ``.claude/sdd/`` outputs for a feature |
| ``judge`` | Invoke ``scripts/judge.py`` against OpenRouter |
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .routing import _resources_root, load_routing, route


PROTOCOL_VERSION = "2024-11-05"


# ── Tool implementations ─────────────────────────────────────────────────────

def tool_kb_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Substring search across KB index files."""
    root = _resources_root() / "kb"
    if not root.exists():
        return {"hits": [], "query": query, "error": f"kb root missing: {root}"}
    needle = query.strip().lower()
    if not needle:
        return {"hits": [], "query": query}
    hits: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lower = text.lower()
        if needle not in lower:
            continue
        idx = lower.find(needle)
        start = max(idx - 80, 0)
        end = min(idx + 200, len(text))
        excerpt = text[start:end].strip()
        hits.append({
            "path": str(path.relative_to(root)),
            "preview": excerpt,
        })
        if len(hits) >= limit:
            break
    return {"hits": hits, "query": query, "limit": limit}


def tool_kb_read(path: str) -> dict[str, Any]:
    """Return the content of a KB file, relative to the KB resource root."""
    root = _resources_root() / "kb"
    target = (root / path).resolve()
    if not str(target).startswith(str(root.resolve())):
        return {"error": "path escapes kb root", "path": path}
    if not target.exists():
        return {"error": "not found", "path": str(target)}
    return {"path": str(target.relative_to(root)), "content": target.read_text(encoding="utf-8")}


def tool_route_agent(task: str, top_k: int = 5) -> dict[str, Any]:
    """Return ranked agents for the supplied task description."""
    agents = load_routing()
    ranked = route(task, agents, top_k=top_k)
    return {
        "task": task,
        "results": [
            {
                "name": agent.name,
                "category": agent.category,
                "tier": agent.tier,
                "model": agent.model,
                "description": agent.description,
                "kb_domains": list(agent.kb_domains),
                "score": score,
            }
            for agent, score in ranked
        ],
    }


def tool_sdd_status(feature: str, workspace: str | None = None) -> dict[str, Any]:
    """Inspect the SDD workspace for a feature: which phase artifacts exist."""
    base = Path(workspace) if workspace else Path.cwd() / ".claude" / "sdd"
    feature_clean = feature.strip().replace(" ", "_").upper()
    phases = {
        "brainstorm": base / "features" / f"BRAINSTORM_{feature_clean}.md",
        "define": base / "features" / f"DEFINE_{feature_clean}.md",
        "design": base / "features" / f"DESIGN_{feature_clean}.md",
        "build_report": base / "reports" / f"BUILD_REPORT_{feature_clean}.md",
        "archive": base / "archive" / feature_clean,
    }
    return {
        "feature": feature_clean,
        "workspace": str(base),
        "phases": {
            name: {
                "path": str(path),
                "exists": path.exists(),
            }
            for name, path in phases.items()
        },
    }


def tool_judge(target_path: str, model: str | None = None, context: str | None = None) -> dict[str, Any]:
    """Invoke ``scripts/judge.py`` against ``target_path``."""
    judge_script = (
        Path(os.environ.get("AGENTSPEC_ROOT", str(_resources_root().parent)))
        / "scripts" / "judge.py"
    )
    if not judge_script.exists():
        return {"error": "judge.py not bundled", "path": str(judge_script)}
    args = [sys.executable, str(judge_script), target_path]
    if model:
        args.extend(["--model", model])
    if context:
        args.extend(["--context", context])
    completed = subprocess.run(args, capture_output=True, text=True)
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


# ── Tool registry ────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="kb_search",
        description="Substring search across AgentSpec KB markdown files.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search string."},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        },
        handler=tool_kb_search,
    ),
    ToolSpec(
        name="kb_read",
        description="Read a KB markdown file relative to the KB resource root.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to KB root."},
            },
            "required": ["path"],
        },
        handler=tool_kb_read,
    ),
    ToolSpec(
        name="route_agent",
        description="Recommend AgentSpec agents for a free-form task.",
        input_schema={
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            "required": ["task"],
        },
        handler=tool_route_agent,
    ),
    ToolSpec(
        name="sdd_status",
        description="Inspect .claude/sdd/ outputs for a feature.",
        input_schema={
            "type": "object",
            "properties": {
                "feature": {"type": "string", "description": "Feature name."},
                "workspace": {"type": "string", "description": "Workspace root (optional)."},
            },
            "required": ["feature"],
        },
        handler=tool_sdd_status,
    ),
    ToolSpec(
        name="judge",
        description="Run scripts/judge.py against a target file via OpenRouter.",
        input_schema={
            "type": "object",
            "properties": {
                "target_path": {"type": "string"},
                "model": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["target_path"],
        },
        handler=tool_judge,
    ),
)


def _tool_by_name(name: str) -> ToolSpec | None:
    for spec in TOOLS:
        if spec.name == name:
            return spec
    return None


# ── JSON-RPC dispatch ────────────────────────────────────────────────────────

def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a single JSON-RPC request and return the response."""
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return _ok(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "agentspec-mcp", "version": "0.1.0"},
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return _ok(request_id, {
            "tools": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "inputSchema": spec.input_schema,
                }
                for spec in TOOLS
            ],
        })

    if method == "tools/call":
        name = params.get("name", "")
        spec = _tool_by_name(name)
        if not spec:
            return _err(request_id, -32602, f"unknown tool: {name}")
        arguments = params.get("arguments", {}) or {}
        try:
            result = spec.handler(**arguments)
        except TypeError as exc:
            return _err(request_id, -32602, f"invalid arguments: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface unexpected failure
            return _err(request_id, -32603, f"tool error: {exc}")
        return _ok(request_id, {
            "content": [
                {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)},
            ],
        })

    return _err(request_id, -32601, f"unknown method: {method}")


def serve_stdio() -> int:
    """Read JSON-RPC frames from stdin and write responses to stdout."""
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[agentspec-mcp] invalid JSON: {exc}\n")
            continue
        response = handle_request(message)
        if response is None:
            continue
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0
