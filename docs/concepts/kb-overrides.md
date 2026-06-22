# KB Overrides — Local-First Resolution

AgentSpec ships 24 KB domains in the plugin, but teams often need project-specific patterns or tweaked examples. Copy KB files into your repository and they take precedence over the plugin versions at the same path.

## The Resolution Rule

```text
.claude/kb/<domain>/<file>   ← your override (wins)
        ↓ if absent
${ROOT_TOKEN}/kb/<domain>/<file>   ← AgentSpec plugin (fallback)
```

Resolution is **per file**, not per domain. You can override one pattern while the rest of the domain still loads from the plugin.

Formal contract: `kb_resolution` in `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`.

## Platform Root Tokens

| Platform | Token |
|----------|-------|
| Claude Code | `${CLAUDE_PLUGIN_ROOT}` |
| Cursor | `${PLUGIN_ROOT}` |
| VS Code + Copilot | `${CLAUDE_PLUGIN_ROOT}` |
| AgentSpec MCP | `${AGENTSPEC_ROOT}` |

## When to Override

| Situation | Action |
|-----------|--------|
| Tweak an incremental dbt pattern for your warehouse | Copy `dbt/patterns/incremental-model.md` locally |
| Add org-specific anti-patterns to a domain | Add files under `.claude/kb/{domain}/` |
| Create a domain that does not exist in the plugin | Use `/create-kb <domain>` |

## How to Override

`init-workspace.sh` creates `.claude/kb/` and writes `.claude/kb/README.md` on first SessionStart (idempotent).

```bash
mkdir -p .claude/kb/dbt/patterns
cp $CLAUDE_PLUGIN_ROOT/kb/dbt/patterns/incremental-model.md \
   .claude/kb/dbt/patterns/incremental-model.md
$EDITOR .claude/kb/dbt/patterns/incremental-model.md
```

## What This Does Not Do

- **Does not sync across projects** — overrides stay in this repository
- **Does not replace the plugin KB globally** — contribute upstream for that
- **Does not deep-merge** — whole file wins; edit the full file locally

For sharing across multiple repos without upstream PR, see [AgentSpec Packs](../tutorials/agentspec-packs.md).

## Related

- [KB and Agent Reuse](kb-agent-reuse.md) — plugin vs local mental model
- [Agent Overrides](agent-overrides.md) — same pattern for agents
- [Upstream Contribution](../contributing/upstream-kb-agents.md) — contribute generic KB upstream
