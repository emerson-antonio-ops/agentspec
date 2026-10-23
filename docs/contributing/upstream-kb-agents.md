# Upstream Contribution — KB Domains and Agents

This guide walks through contributing a Knowledge Base domain or specialist agent from your project to the AgentSpec repository. After merge and release, every user who updates the plugin receives your content automatically.

**Target repositories:**

| Repo | When to use |
|------|-------------|
| [emerson-antonio-ops/agentspec](https://github.com/emerson-antonio-ops/agentspec) | Multi-platform fork (Claude, Cursor, Copilot, MCP) |
| [luanmorenommaciel/agentspec](https://github.com/luanmorenommaciel/agentspec) | Upstream stable (Claude Code marketplace) |

Validate changes in the fork first, then open a selective PR upstream if the content is generic enough.

---

## Before You Start

### Generalize your content

Remove org-specific references before opening a PR:

- Internal URLs, schema names, table names tied to your company
- Credentials, API keys, emails, private repo paths
- SLAs and team names that do not generalize

Replace with realistic but fictional examples. Every code block should be syntactically valid.

### Check whether you need a new agent

Before creating an agent, verify all four conditions in [.claude/agents/README.md](../../.claude/agents/README.md#when-not-to-create-an-agent):

1. No existing agent covers >60% of the capability
2. The agent has a unique KB domain or tool combination
3. At least three distinct trigger scenarios exist
4. Overlap with an existing agent is <80%

If any condition fails, extend an existing agent or KB domain instead.

### KB file size limits

Defined in `.claude/kb/_index.yaml`:

| File type | Max lines |
|-----------|----------|
| `quick-reference.md` | ~100 |
| `concepts/*.md` | ~150 |
| `patterns/*.md` | ~200 |

---

## Workflow Overview

```text
Prepare content → Fork + branch → Add to .claude/ → Register → Validate → PR → Release
```

---

## Scenario A — New KB Domain Only

Example: contribute a generic `billing/` domain (fictional patterns for subscription analytics).

### 1. Fork and branch

```bash
git clone https://github.com/emerson-antonio-ops/agentspec.git
cd agentspec
git checkout -b feature/add-billing-kb
```

### 2. Create domain structure

```bash
mkdir -p .claude/kb/billing/{concepts,patterns}
cp .claude/kb/_templates/index.md.template .claude/kb/billing/index.md
cp .claude/kb/_templates/quick-reference.md.template .claude/kb/billing/quick-reference.md
cp .claude/kb/_templates/concept.md.template .claude/kb/billing/concepts/subscription-models.md
cp .claude/kb/_templates/pattern.md.template .claude/kb/billing/patterns/revenue-recognition.md
```

Or use the built-in command inside the AgentSpec repo:

```bash
/create-kb billing
```

### 3. Register in `_index.yaml`

Add a block under `domains:` in `.claude/kb/_index.yaml`:

```yaml
  billing:
    name: billing
    description: "Subscription billing patterns — revenue recognition, MRR, invoicing"
    path: billing/
    mcp_validated: "2026-06-22"
    entry_points:
      index: index.md
      quick_reference: quick-reference.md
    concepts:
      - name: subscription-models
        path: concepts/subscription-models.md
        confidence: 0.90
    patterns:
      - name: revenue-recognition
        path: patterns/revenue-recognition.md
        confidence: 0.90
```

### 4. Link to existing agents

Add `billing` to `kb_domains` in relevant agents (e.g. `schema-designer`, `data-quality-analyst`) — only if the domain is genuinely useful to them.

### 5. Update documentation counts

When adding a **new** domain, increment KB counts in: `README.md`, `CLAUDE.md`, `docs/concepts/README.md`, `.claude/kb/README.md`, `CHANGELOG.md`.

### 6. Validate

```bash
make test
make build-all
make validate-all
```

Test locally:

```bash
claude --plugin-dir ./dist/claude
# or: cp -R dist/cursor ~/.cursor/plugins/local/agentspec
```

---

## Scenario B — New KB Domain + New Agent

Example: `billing/` KB plus `billing-specialist` agent.

### Additional steps beyond Scenario A

1. Copy the agent template:

   ```bash
   cp .claude/agents/_template.md \
      .claude/agents/data-engineering/billing-specialist.md
   ```

2. Fill frontmatter — required fields: `name`, `description` (with two `<example>` blocks), `tools`, `kb_domains: [billing, sql-patterns, data-quality]`, `color`, `tier`, `anti_pattern_refs`.

3. Regenerate the agent router (mandatory for new plugin agents):

   ```bash
   make generate
   # or: python3 scripts/generate-agent-router.py
   ```

4. Increment agent counts in documentation (58 → 59).

5. Run drift check:

   ```bash
   python3 scripts/generate-agent-router.py --check
   ```

---

## Scenario C — Improve Existing Content

The fastest path to merge. Edit an existing file:

```bash
git checkout -b fix/dbt-incremental-pattern
$EDITOR .claude/kb/dbt/patterns/incremental-model.md
make test && make validate-all
```

No count updates needed unless you add files or domains.

---

## Pre-PR Checklist

Or run the automated helper:

```bash
/prepare-upstream kb billing
/prepare-upstream agent billing-specialist
```

Which validates line limits, scans for secrets, checks `_index.yaml`, and writes a tree under `/tmp/agentspec-upstream-*/`.

Manual checklist:

- [ ] Content generalized — no secrets or private org data
- [ ] KB files within line limits
- [ ] Domain registered in `_index.yaml` (if new domain)
- [ ] Agent follows `_template.md` and "When NOT to Create" criteria (if new agent)
- [ ] `make generate` run (if agents added or renamed)
- [ ] `make test` passes
- [ ] `make validate-all` passes
- [ ] Manual smoke test with `dist/claude` or `dist/cursor`
- [ ] `CHANGELOG.md` updated under `[Unreleased]`

---

## Opening the Pull Request

**Title examples:**

- `docs: add KB and agent reuse guides`
- `feat(kb): add billing domain`
- `feat(agents): add billing-specialist agent`

**Body template:**

```markdown
## Summary
- Adds billing KB domain with 1 concept + 1 pattern (fictional examples)
- Links billing to schema-designer and data-quality-analyst

## Test plan
- [ ] make test
- [ ] make validate-all
- [ ] Smoke-tested with claude --plugin-dir ./dist/claude
```

---

## After Merge

1. Maintainer tags a release (e.g. v3.4.0)
2. Users update:

   ```bash
   claude plugin update agentspec
   ```

   For Cursor/local installs: `make build-all` and recopy `dist/cursor/`.

3. All projects with the updated plugin receive the new KB/agents automatically — no per-project copy required.

---

## Contributing to Upstream from the Fork

After validating in `emerson-antonio-ops/agentspec`:

```bash
git remote add upstream https://github.com/luanmorenommaciel/agentspec.git
git fetch upstream
# Cherry-pick or open PR with docs/KB only — exclude fork-specific README attribution
```

**Exclude from upstream PRs:** fork maintainer metadata in `scripts/lib/platforms.py`, README install URLs pointing at `emerson-antonio-ops`, Cursor-specific sideload instructions.

---

## Related

- [CONTRIBUTING.md](../../CONTRIBUTING.md) — general contribution guide
- [KB and Agent Reuse](../concepts/kb-agent-reuse.md) — plugin vs local mental model
- [Agent Overrides](../concepts/agent-overrides.md) — project-local customization
- [Adding a KB Domain](../../CONTRIBUTING.md#adding-a-kb-domain) — quick reference
