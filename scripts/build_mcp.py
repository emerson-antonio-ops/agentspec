#!/usr/bin/env python3
"""Build the AgentSpec MCP distribution under ``dist/mcp/``.

Author: Emerson Antonio
Date: 2026-06-17

The MCP target ships:
- KB and SDD as static resources MCP clients can read on demand
- routing.json so any MCP host can call ``route_agent``
- ``judge.py`` for cross-model second opinions
- ``mcp.json`` snippet ready to drop into Claude Code, Cursor, or VS Code

The actual MCP server lives at ``packages/agentspec-mcp/``; this builder
assembles the artifacts the server depends on and produces a portable
``dist/mcp/`` directory.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import packaging, platforms
from scripts.lib.packaging import (
    EXTRAS_DIR, REPO_ROOT, SCRIPTS_DIR, SOURCE_DIR,
    BuildSummary, info, ok, warn, fail, print_summary,
)


PROFILE = platforms.get_profile(platforms.MCP)
SERVER_PKG = REPO_ROOT / "packages" / "agentspec-mcp"


def _copy_server(output_dir: Path) -> bool:
    """Copy the MCP server package, if present."""
    if not SERVER_PKG.exists():
        warn(f"{SERVER_PKG} not found — server not bundled")
        return False
    packaging.copy_source_tree(SERVER_PKG, output_dir / "server")
    return True


def _copy_resources(output_dir: Path) -> None:
    resources = output_dir / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    for sub in ("kb", "agents", "commands", "skills"):
        src = SOURCE_DIR / sub
        if src.exists():
            packaging.copy_source_tree(src, resources / sub)
    sdd_target = resources / "sdd"
    sdd_target.mkdir(parents=True, exist_ok=True)
    for sub in ("templates", "architecture"):
        s = SOURCE_DIR / "sdd" / sub
        if s.exists():
            packaging.copy_source_tree(s, sdd_target / sub)


def _emit_mcp_config(output_dir: Path) -> None:
    config = {
        "mcpServers": {
            "agentspec-mcp": {
                "command": "python3",
                "args": [
                    "${AGENTSPEC_ROOT}/server/agentspec_mcp/__main__.py"
                ],
                "env": {
                    "AGENTSPEC_ROOT": "${AGENTSPEC_ROOT}",
                    "AGENTSPEC_RESOURCES": "${AGENTSPEC_ROOT}/resources",
                },
            }
        }
    }
    packaging.write_json(output_dir / "mcp.json", config)


def build(strict_stale: bool = True) -> BuildSummary:
    output_dir = platforms.dist_root(REPO_ROOT, PROFILE.id)
    packaging.regenerate_agent_router()
    packaging.clean_output(output_dir)
    _copy_server(output_dir)
    _copy_resources(output_dir)
    packaging.ship_judge_assets(output_dir)
    results = packaging.rewrite_paths(output_dir, PROFILE)
    _emit_mcp_config(output_dir)
    summary = packaging.summarize(PROFILE, output_dir, results)
    if strict_stale and summary.stale_findings > 0:
        fail(f"{summary.stale_findings} stale .claude/ references in {output_dir}")
        raise SystemExit(2)
    report = {
        "platform": PROFILE.id,
        "label": PROFILE.label,
        "agents": summary.agents,
        "commands": summary.commands,
        "skills": summary.skills,
        "kb_domains": summary.kb_domains,
        "rewrite_changes": summary.rewrite_changes,
        "stale_findings": summary.stale_findings,
        "output": str(output_dir),
    }
    packaging.write_json(output_dir / "build-report.json", report)
    print_summary(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-stale", action="store_true")
    args = parser.parse_args()
    try:
        build(strict_stale=not args.allow_stale)
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
