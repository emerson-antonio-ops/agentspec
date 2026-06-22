# AgentSpec Packs Tutorial

Install org-wide agents and KB domains across multiple repositories without opening a PR to the main AgentSpec plugin.

## Prerequisites

- AgentSpec v3.5.0+ (includes `scripts/pack.py` and `/pack` command)
- Git (for remote pack URLs)
- PyYAML (`pip install pyyaml`) for lockfile support

## Quick Start

```bash
# From your data project root
python3 /path/to/agentspec/scripts/pack.py install \
  git@github.com:emerson-antonio-ops/agentspec-pack-example.git

# Or via slash command (when plugin is installed)
/pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
```

## What Happens

1. Pack is cloned to `.claude/packs/billing-pack/`
2. Lockfile updated at `.claude/packs/.lock.yaml`
3. Agents copied to `.claude/agents/custom/` (skip if file exists)
4. KB copied to `.claude/kb/` (skip if file exists — local-wins)

## Pack Repository Layout

```text
your-pack-repo/
├── agentspec-pack.yaml
├── agents/
│   └── custom/
│       └── billing-specialist.md
└── kb/
    └── billing/
        ├── index.md
        └── patterns/
```

See `.claude/sdd/architecture/PACK_SCHEMA.yaml` for the full schema.

## Satellite Example Repository

The reference pack lives in a **separate repository** (not inside the AgentSpec monorepo):

**[emerson-antonio-ops/agentspec-pack-example](https://github.com/emerson-antonio-ops/agentspec-pack-example)** — tag `v0.1.0`

Install directly:

```bash
python3 scripts/pack.py install \
  https://github.com/emerson-antonio-ops/agentspec-pack-example.git
```

The monorepo keeps a minimal copy at `tests/fixtures/pack-billing/` for pytest only.

## Commands

| Command | Action |
|---------|--------|
| `pack install <url>` | Stage + apply |
| `pack list` | Show lockfile entries |
| `pack apply <name>` | Re-apply from staged pack |
| `pack remove <name>` | Remove staged pack only |

## Important Notes

- **remove does not delete applied files** — copies in `.claude/agents/` and `.claude/kb/` stay
- **Local files always win** on install/apply conflicts
- **Private packs** — use private git repos + SSH URLs
- **Upstream alternative** — generic patterns should still go via [upstream contribution](../contributing/upstream-kb-agents.md)

## Related

- [KB and Agent Reuse](../concepts/kb-agent-reuse.md)
- [KB Overrides](../concepts/kb-overrides.md)
