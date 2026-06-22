---
name: pack
description: Install, list, remove, or apply AgentSpec packs (org-wide agents + KB via git URL or local path)
---

# Pack Command

Manage AgentSpec packs — reusable bundles of agents and KB domains shared across projects without contributing upstream.

## Usage

```bash
/pack install <path-or-git-url>
/pack list
/pack remove <pack-name>
/pack apply <pack-name>
```

## Examples

```bash
/pack install ./vendor/billing-pack
/pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
/pack list
/pack remove billing-pack
/pack apply billing-pack
```

## Execution

Run the pack CLI from the project root:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pack.py install <source>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pack.py list
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pack.py remove <name>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pack.py apply <name>
```

When developing AgentSpec locally, use `scripts/pack.py` from the repository root.

## Behavior

1. **install** — clones/copies pack to `.claude/packs/{name}/`, updates `.claude/packs/.lock.yaml`, applies agents to `${CLAUDE_PLUGIN_ROOT}/agents/custom/` and KB to `${CLAUDE_PLUGIN_ROOT}/kb/` (skips existing files — local-wins)
2. **list** — shows installed packs from lockfile
3. **remove** — deletes staged pack; applied copies remain
4. **apply** — re-runs apply from staged pack

## See Also

- `docs/tutorials/agentspec-packs.md`
- `docs/concepts/kb-agent-reuse.md`
- `${CLAUDE_PLUGIN_ROOT}/sdd/architecture/PACK_SCHEMA.yaml`
