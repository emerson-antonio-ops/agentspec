# AgentSpec MCP Server

Universal MCP server that exposes AgentSpec capabilities (KB search, agent
routing, judge, SDD status) to any MCP-compatible client — Claude Code,
Cursor, VS Code + Copilot, and so on.

The server reads its content from a packaged ``resources/`` tree generated
by ``python3 scripts/build_mcp.py`` (output under ``dist/mcp/``).

## Tools

| Tool | Purpose |
|------|---------|
| ``kb_search`` | Substring search across KB index headings |
| ``kb_read`` | Read a KB file (markdown / YAML) on demand |
| ``route_agent`` | Recommend an AgentSpec agent for a given task |
| ``sdd_status`` | Inspect ``.claude/sdd/`` workspace state for a feature |
| ``judge`` | Trigger ``scripts/judge.py`` via OpenRouter for a second opinion |

## Layout

```
packages/agentspec-mcp/
├── agentspec_mcp/
│   ├── __init__.py
│   ├── __main__.py        # stdio entrypoint
│   ├── server.py          # tool implementations
│   └── routing.py         # router built from routing.json
├── pyproject.toml         # package metadata (PEP 621)
└── README.md
```

## Author

- Emerson Antonio — 2026-06-17
