---
name: prepare-upstream
description: Validate and stage local KB or agent content for an upstream AgentSpec pull request
---

# Prepare Upstream Command

Automates the pre-PR checklist before contributing a KB domain or agent to the AgentSpec repository.

## Usage

```bash
/prepare-upstream kb <domain>
/prepare-upstream agent <agent-name>
```

## Examples

```bash
/prepare-upstream kb billing
/prepare-upstream agent billing-specialist
```

## Execution

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare-upstream.py kb <domain>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare-upstream.py agent <name>
```

Optional flags:

```bash
python3 scripts/prepare-upstream.py --project-root . --agentspec-root /path/to/agentspec kb billing
```

## What It Checks

- KB line limits (`quick-reference` 100, `concept` 150, `pattern` 200)
- Basic secret/credential patterns
- `_index.yaml` registration (for KB domains)
- Emits diff-ready tree under `/tmp/agentspec-upstream-{kind}-{name}/`
- Lists documentation counter files to update

## See Also

- `docs/contributing/upstream-kb-agents.md`
- `CONTRIBUTING.md`
