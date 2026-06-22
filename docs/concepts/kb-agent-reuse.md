# KB and Agent Reuse Across Projects

AgentSpec content lives in two layers: **plugin-global** (shared everywhere the plugin is installed) and **project-local** (isolated to one repository). Understanding which layer you are editing prevents the most common confusion — expecting a custom agent or KB domain created in Project A to appear automatically in Project B.

## Two Layers

```text
┌─────────────────────────────────────────────────────────────┐
│  AgentSpec plugin (global)                                  │
│  • 58 agents + 24 KB domains                                │
│  • Installed once; shared by every project using the plugin │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ fallback
┌─────────────────────────────────────────────────────────────┐
│  Your project (.claude/)                                    │
│  • agents/workflow/  → override existing agents (local-first)│
│  • agents/custom/    → new project-specific agents          │
│  • kb/{domain}/      → custom or overridden KB content      │
│  • sdd/features/     → SDD artifacts (DEFINE, DESIGN, …)    │
└─────────────────────────────────────────────────────────────┘
```

## What Is Shared vs Local

| Content | Location | Shared across projects? |
|---------|----------|-------------------------|
| Built-in agents (58) | Plugin `${ROOT}/agents/` | Yes — all projects with plugin |
| Built-in KB (24 domains) | Plugin `${ROOT}/kb/` | Yes — all projects with plugin |
| Agent override | `.claude/agents/<category>/<name>.md` | No — this repo only |
| Custom agent | `.claude/agents/custom/<name>.md` | No — this repo only |
| Custom KB domain | `.claude/kb/<domain>/` | No — this repo only |
| SDD documents | `.claude/sdd/features/` | No — this repo only |
| Plugin update | `claude plugin update` / rebuild `dist/` | Yes — propagates to all projects |

## Path Tokens by Platform

Agents and commands in the plugin reference KB paths using platform-specific root tokens. Your **local** project paths always use `.claude/` literally.

| Platform | Plugin root token |
|----------|---------------------|
| Claude Code | `${CLAUDE_PLUGIN_ROOT}` |
| Cursor | `${PLUGIN_ROOT}` |
| VS Code + Copilot | `${CLAUDE_PLUGIN_ROOT}` |
| AgentSpec MCP | `${AGENTSPEC_ROOT}` |

Example: the dbt KB index resolves to `${CLAUDE_PLUGIN_ROOT}/kb/dbt/index.md` in the Claude plugin, but a local override lives at `.claude/kb/dbt/index.md` in your repo.

## Agent Resolution (Implemented)

Local agents take precedence over plugin agents when the `name:` in frontmatter matches:

```text
.claude/agents/<category>/<name>.md   ← your override (wins)
        ↓ if absent
${ROOT}/agents/<category>/<name>.md   ← AgentSpec plugin (fallback)
```

Enforced by the host runtime (Claude Code plugin loader, Cursor agent discovery). See [Agent Overrides](agent-overrides.md).

Custom agents in `.claude/agents/custom/` are **additive** — they do not replace a plugin agent unless you also match an existing name (avoid that).

## KB Resolution (Current Behavior)

KB does **not** yet have the same formal contract as agents, but the practical rule is:

1. If your project contains `.claude/kb/<domain>/`, agents read those files when their prompts reference `.claude/kb/`.
2. Domains that exist only in the plugin remain available from `${ROOT}/kb/`.
3. There is no automatic merge — copy the files you want to customize into your project.

To customize KB today, copy domain files from the plugin into your project:

```bash
mkdir -p .claude/kb/dbt/patterns
cp $CLAUDE_PLUGIN_ROOT/kb/dbt/patterns/incremental-model.md \
   .claude/kb/dbt/patterns/incremental-model.md
```

> **Implemented (v3.4.1):** formal `kb_resolution` contract and SessionStart scaffolding. See [KB Overrides](kb-overrides.md).

## AgentSpec Packs (v3.5+)

For org-wide sharing without upstream PR, install a pack from a git URL:

```bash
/pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
```

Packs stage under `.claude/packs/{name}/` and apply agents/KB with local-wins skip. See [AgentSpec Packs tutorial](../tutorials/agentspec-packs.md).

## Ways to Share Content Between Projects

| Method | Scope | Automatic? |
|--------|-------|------------|
| Install / update plugin | Official catalog | Yes |
| Contribute upstream (PR to AgentSpec) | All plugin users | After release |
| Git submodule or template repo | Repos that reference it | Manual setup |
| Copy-paste between repos | Target repos | Manual |
| AgentSpec packs (v3.5+) | Org-wide via git URL | `pack install` |

For contributing KB or agents back to the official plugin, see [Upstream Contribution Guide](../contributing/upstream-kb-agents.md). Automate pre-PR checks with `/prepare-upstream`.

## FAQ

**I created an agent in `.claude/agents/custom/`. Do other projects see it?**

No. Custom agents are discovered only in the repository where they live. Other projects need a copy, a shared pack (v3.5), or an upstream PR.

**I ran `/create-kb billing` in Project A. Does Project B get the domain?**

No. `/create-kb` writes to `.claude/kb/billing/` in the current project. Register the domain in that project's `_index.yaml` if you maintain a local registry.

**Will updating the plugin overwrite my local agents?**

No. Local files in `.claude/agents/` always win over plugin agents with the same name. Plugin updates only change the fallback layer.

**Does the agent-router skill index my local agents?**

No. `routing.json` is a build-time artifact for the plugin's 58 agents. Local and custom agents are discovered at runtime by the host.

**Can I share proprietary patterns without open-sourcing them?**

Yes — keep them in `.claude/kb/` and `.claude/agents/custom/` per project, or use an private AgentSpec pack (planned v3.5). Do not open a PR upstream with secrets or org-specific data.

## Related

- [Agent Overrides](agent-overrides.md) — local-first agent customization
- [Upstream Contribution Guide](../contributing/upstream-kb-agents.md) — PR workflow for KB and agents
- [Core Concepts](README.md) — SDD phases, agents, and KB mental model
- [WORKFLOW_CONTRACTS.yaml](../../.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml) — `agent_resolution` contract
