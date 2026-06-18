"""Stdio entrypoint for the AgentSpec MCP server.

Author: Emerson Antonio
Date: 2026-06-17

Usage::

    python3 -m agentspec_mcp
    python3 packages/agentspec-mcp/agentspec_mcp/__main__.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the parent package importable when invoked by absolute path (the build
# emits ``${ROOT}/server/agentspec_mcp/__main__.py`` and MCP clients run it
# directly rather than via ``python -m``).
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from agentspec_mcp.server import serve_stdio


def main() -> int:
    return serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
