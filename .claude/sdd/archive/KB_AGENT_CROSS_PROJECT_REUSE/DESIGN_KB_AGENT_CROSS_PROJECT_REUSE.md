# DESIGN: KB Agent Cross-Project Reuse

> Technical design for Sprints 2–4: KB resolution contract, override scaffolding, org-wide packs, and upstream tooling.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | `KB_AGENT_CROSS_PROJECT_REUSE` |
| **Date** | 2026-06-22 |
| **Author** | Emerson Antonio |
| **DEFINE** | [DEFINE_KB_AGENT_CROSS_PROJECT_REUSE.md](./DEFINE_KB_AGENT_CROSS_PROJECT_REUSE.md) |
| **BRAINSTORM** | [BRAINSTORM_KB_AGENT_CROSS_PROJECT_REUSE.md](./BRAINSTORM_KB_AGENT_CROSS_PROJECT_REUSE.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTENT RESOLUTION (runtime, user project)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Tier 1 — Project local (wins)                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ .claude/agents/{workflow,custom,category}/                          │   │
│   │ .claude/kb/{domain}/                                                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                               │
│                              │ file-level local-wins                         │
│   Tier 2 — Installed packs (v3.5)                                            │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ .claude/packs/{pack_id}/          ← staged source (git clone)       │   │
│   │ .claude/packs/.lock.yaml          ← install registry                │   │
│   │ apply → copies to agents/custom + kb/ (skip conflicts)              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                               │
│                              │ fallback                                      │
│   Tier 3 — Plugin global                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ ${ROOT_TOKEN}/agents/  (58 agents)                                  │   │
│   │ ${ROOT_TOKEN}/kb/      (24 domains)                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                     BUILD-TIME (AgentSpec repo only)                         │
│   .claude/ → make build-all → dist/{claude,cursor,vscode-copilot,mcp}       │
│   scripts/generate-agent-router.py → routing.json (plugin agents only)       │
│   plugin-extras/init-workspace.sh → scaffolds user .claude/ on SessionStart  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Sprint 1 (shipped):** documentation only — `docs/concepts/kb-agent-reuse.md`, `docs/contributing/upstream-kb-agents.md`.

**Sprints 2–4 (this design):** contracts, scaffolding, pack engine, upstream CLI.

---

## Components

| Component | Purpose | Technology | Sprint |
|-----------|---------|------------|--------|
| `kb_resolution` contract | Formalize KB local-first precedence | YAML in WORKFLOW_CONTRACTS | 2 |
| `init_kb_overrides()` | Scaffold `.claude/kb/README.md` on SessionStart | Bash in init-workspace.sh | 2 |
| `path_rewrite` extension | Preserve `.claude/kb/`, `.claude/packs/` in dist builds | Python | 2, 3 |
| `docs/concepts/kb-overrides.md` | User guide for KB customization | Markdown | 2 |
| `PACK_SCHEMA.yaml` | Pack manifest schema | YAML | 3 |
| `scripts/pack.py` | install \| list \| remove \| apply | Python 3.10+ | 3 |
| `.claude/commands/core/pack.md` | Slash command wrapper | Markdown | 3 |
| `pack_resolution` contract | Three-tier resolution order | YAML | 3 |
| Satellite repo | `agentspec-pack-example` billing demo | Git + agentspec-pack.yaml | 3 |
| `scripts/prepare-upstream.py` | Pre-PR validation for KB/agent contributions | Python | 4 |
| `.claude/commands/core/prepare-upstream.md` | Slash command wrapper | Markdown | 4 |

---

## Key Decisions

### Decision 1: File-Level Local-Wins (No Semantic KB Merge)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Context:** KB domains can have dozens of concept/pattern files. Users may override one pattern without forking the entire domain.

**Choice:** Resolution is **per file path**. If `.claude/kb/dbt/patterns/incremental-model.md` exists locally, that file wins; other files in the same domain still load from plugin.

**Rationale:** Matches how agents already override by whole file. Avoids merge conflicts and parser complexity.

**Alternatives Rejected:**
1. Whole-domain override only — rejected because users would copy entire domains to change one pattern
2. Semantic/deep merge — rejected as over-engineering (YAGNI)

**Consequences:**
- Agents must reference `.claude/kb/{domain}/` paths for local resolution to work
- Plugin build must NOT rewrite workspace `.claude/kb/` paths (see Decision 3)

---

### Decision 2: Pack Install Stages + Apply with Local-Wins Skip

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Context:** Claude Code discovers agents under `.claude/agents/`, not `.claude/packs/`. Packs must materialize content into discoverable paths.

**Choice:** `pack install <source>` performs two steps:
1. **Stage** — clone/copy pack to `.claude/packs/{pack_id}/`
2. **Apply** — copy `agents/custom/*.md` → `.claude/agents/custom/` and `kb/{domain}/**` → `.claude/kb/{domain}/`, **skipping** any destination file that already exists

**Rationale:** Satisfies AT-006 (`.claude/packs/` populated) and makes agents/KB usable without host loader changes.

**Alternatives Rejected:**
1. Packs only in `.claude/packs/` without apply — rejected; agents would not be discoverable
2. Symlinks — rejected; Windows/Cursor portability issues
3. Build-time pack indexing in routing.json — rejected; out of scope per DEFINE

**Consequences:**
- `pack remove` deletes staged dir + lock entry; applied copies remain (documented)
- `pack update` re-stages and re-applies with same skip rules

---

### Decision 3: Extend `_WORKSPACE_PATHS` for kb and packs

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Context:** `scripts/lib/path_rewrite.py` rewrites `.claude/kb/` to `${ROOT}/kb/` in shipped artifacts unless listed as workspace paths. User KB overrides would break.

**Choice:** Add to `_WORKSPACE_PATHS`:
- `.claude/kb`
- `.claude/packs`

Also extend `PlatformProfile.workspace_paths` in `platforms.py` for validate_dist consistency.

**Rationale:** Same pattern as `.claude/agents/workflow` and `.claude/agents/custom`.

**Alternatives Rejected:**
1. Change all agent prompts to use workspace-only KB refs — rejected; massive diff, breaks plugin-relative docs

---

### Decision 4: Satellite Repo for Pack Example (Option B)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Context:** User confirmed pack demo lives in `emerson-antonio-ops/agentspec-pack-example`, not `examples/` in monorepo.

**Choice:** Separate GitHub repo; CI in main fork runs `pack install` against pinned tag URL in tests.

**Rationale:** Mirrors real org workflow (private pack repo + git URL install).

---

### Decision 5: Pack Semver — Loose `min_agentspec` Gate Only

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Context:** DEFINE open question on pack semver policy.

**Choice:** Manifest fields:
- `version` — semver string (informational + lockfile)
- `min_agentspec` — minimum plugin version (e.g. `"3.5.0"`); `pack.py` warns if below, does not hard-fail in v1

**Rationale:** Avoids complex resolver; packs are org-internal in v1.

**Alternatives Rejected:**
1. Strict semver resolver like npm — YAGNI for v1

---

### Decision 6: Private Pack Auth — Document SSH/HTTPS, No Token Vault

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-06-22 |

**Choice:** `pack install` accepts local path, `https://`, or `git@` SSH URLs. Auth uses ambient git credentials. No AgentSpec token store.

**Rationale:** Reuses git; zero new secret surface.

---

## Resolution Contracts (YAML Spec)

### `kb_resolution` (Sprint 2 — add to WORKFLOW_CONTRACTS.yaml)

```yaml
kb_resolution:
  order:
    - "local"   # .claude/kb/<domain>/ in the user's project
    - "plugin"  # ${ROOT_TOKEN}/kb/<domain>/ (AgentSpec)

  merge_strategy: "local-wins"  # per-file, not deep merge

  behavior: |
    When an agent references .claude/kb/{domain}/, the runtime checks the
    user's project first. Existing files in .claude/kb/{domain}/ override
    plugin files at the same relative path. Missing files fall back to the
    plugin KB. Domains that exist only in the plugin are loaded entirely
    from the plugin.

  scaffolding:
    description: |
      SessionStart hook creates .claude/kb/ and writes README on first run.
    paths:
      - ".claude/kb/"
    readme: ".claude/kb/README.md"

  documentation:
    user_facing: "docs/concepts/kb-overrides.md"
    reuse_guide: "docs/concepts/kb-agent-reuse.md"
```

Update `agent_resolution.rules` line 105 — replace outdated "KB loaded only from CLAUDE_PLUGIN_ROOT" with pointer to `kb_resolution`.

### `pack_resolution` (Sprint 3)

```yaml
pack_resolution:
  order:
    - "local"   # .claude/agents/, .claude/kb/
    - "pack"    # .claude/packs/{pack_id}/ (staged; applied copies in local)
    - "plugin"  # ${ROOT_TOKEN}/

  behavior: |
    pack install stages content under .claude/packs/{pack_id}/ and applies
    agents/kb into workspace paths. Local files always win on conflict.
    pack remove deletes staged content only.

  lockfile: ".claude/packs/.lock.yaml"
  schema: ".claude/sdd/architecture/PACK_SCHEMA.yaml"
```

---

## File Manifest

### Sprint 2 — v3.4.1 (F3, F4)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 1 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Edit | Add `kb_resolution`; fix agent_resolution KB rule | @design-agent | — |
| 2 | `plugin-extras/scripts/init-workspace.sh` | Edit | Add `init_kb_overrides()` + call in main | @shell-script-specialist | 1 |
| 3 | `docs/concepts/kb-overrides.md` | Create | KB override user guide | @code-documenter | 1 |
| 4 | `docs/concepts/kb-agent-reuse.md` | Edit | Link kb-overrides; remove "planned" note | @code-documenter | 3 |
| 5 | `scripts/lib/path_rewrite.py` | Edit | Add `.claude/kb`, `.claude/packs` to `_WORKSPACE_PATHS` | @python-developer | — |
| 6 | `scripts/lib/platforms.py` | Edit | Extend `workspace_paths` on profiles | @python-developer | 5 |
| 7 | `tests/test_lib_path_rewrite.py` | Edit | Tests for kb/packs workspace preservation | @test-generator | 5 |
| 8 | `CHANGELOG.md` | Edit | v3.4.1 entry | — | 1–7 |
| 9 | `tasks/backlog.md` | Edit | Mark F3/F4 shipped | — | 1–7 |

### Sprint 3 — v3.5.0 (F5)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 10 | `.claude/sdd/architecture/PACK_SCHEMA.yaml` | Create | Pack manifest schema | @kb-architect | — |
| 11 | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Edit | Add `pack_resolution` | @design-agent | 10 |
| 12 | `scripts/pack.py` | Create | Pack CLI engine | @python-developer | 10 |
| 13 | `.claude/commands/core/pack.md` | Create | `/pack` slash command | @python-developer | 12 |
| 14 | `docs/tutorials/agentspec-packs.md` | Create | Install tutorial + satellite repo | @code-documenter | 12 |
| 15 | `docs/concepts/kb-agent-reuse.md` | Edit | Packs section | @code-documenter | 14 |
| 16 | `tests/test_pack.py` | Create | install/list/remove/apply tests | @test-generator | 12 |
| 17 | `Makefile` | Edit | Optional `pack-validate` target | @python-developer | 12 |
| 18 | `CHANGELOG.md` | Edit | v3.5.0 entry | — | 10–17 |

**External repo** `emerson-antonio-ops/agentspec-pack-example`:

| # | File | Action | Purpose |
|---|------|--------|---------|
| E1 | `agentspec-pack.yaml` | Create | Manifest `billing-pack` v0.1.0 |
| E2 | `agents/custom/billing-specialist.md` | Create | Demo T2 agent |
| E3 | `kb/billing/` | Create | index, quick-reference, 1 concept, 1 pattern |
| E4 | `README.md` | Create | Install instructions |

### Sprint 4 — v3.5.1 (F6)

| # | File | Action | Purpose | Agent | Deps |
|---|------|--------|---------|-------|------|
| 19 | `scripts/prepare-upstream.py` | Create | Line limits, secret scan, index check | @python-developer | — |
| 20 | `.claude/commands/core/prepare-upstream.md` | Create | `/prepare-upstream` command | @python-developer | 19 |
| 21 | `tests/test_prepare_upstream.py` | Create | Validator unit tests | @test-generator | 19 |
| 22 | `docs/contributing/upstream-kb-agents.md` | Edit | Reference `/prepare-upstream` | @code-documenter | 19 |
| 23 | `CHANGELOG.md` | Edit | v3.5.1 entry | — | 19–22 |

**Total files (main repo):** 23 modifications/creates across 3 sprints.

---

## Agent Assignment Rationale

| Agent | Files | Why |
|-------|-------|-----|
| @shell-script-specialist | 2 | init-workspace.sh bash patterns |
| @python-developer | 5, 6, 12, 19 | pack.py, prepare-upstream, path_rewrite |
| @test-generator | 7, 16, 21 | pytest for lib + new scripts |
| @code-documenter | 3, 4, 14, 15, 22 | User-facing docs |
| @kb-architect | 10 | PACK_SCHEMA + KB layout |
| @design-agent | 1, 11 | WORKFLOW_CONTRACTS |

---

## Code Patterns

### Pattern 1: `init_kb_overrides()` in init-workspace.sh

```bash
init_kb_overrides() {
    if [[ ! -d ".git" ]] && [[ ! -f "CLAUDE.md" ]] && [[ ! -d ".claude" ]]; then
        return 0
    fi

    mkdir -p .claude/kb 2>/dev/null || true

    local readme=".claude/kb/README.md"
    if [[ -f "$readme" ]]; then
        return 0
    fi

    cat > "$readme" <<'EOF'
# Local KB — Override AgentSpec

Knowledge base files in `.claude/kb/` **override plugin KB files**
at the same path (file-level local-wins).

## Override a plugin KB file

```bash
mkdir -p .claude/kb/dbt/patterns
cp $CLAUDE_PLUGIN_ROOT/kb/dbt/patterns/incremental-model.md \
   .claude/kb/dbt/patterns/incremental-model.md
```

## Add a custom domain

Use `/create-kb <domain>` or copy templates from the plugin `_templates/`.

See docs/concepts/kb-overrides.md in the AgentSpec repo.
EOF
}

# In main():
init_workspace
init_agent_overrides
init_kb_overrides    # NEW
generate_context_hint
```

### Pattern 2: `_WORKSPACE_PATHS` extension

```python
_WORKSPACE_PATHS: tuple[str, ...] = (
    ".claude/sdd",
    ".claude/storage",
    ".claude/settings",
    ".claude/plans",
    ".claude/memory",
    ".claude/CLAUDE.md",
    ".claude/agents/workflow",
    ".claude/agents/custom",
    ".claude/kb",          # NEW — Sprint 2
    ".claude/packs",       # NEW — Sprint 3
)
```

### Pattern 3: `agentspec-pack.yaml` manifest

```yaml
# agentspec-pack.yaml — required at pack repository root
name: billing-pack
version: "0.1.0"
description: "Fictional billing analytics patterns for AgentSpec pack demo"
min_agentspec: "3.5.0"
author: "Emerson Antonio"

# Optional metadata
repository: "https://github.com/emerson-antonio-ops/agentspec-pack-example"

contents:
  agents:
    - path: agents/custom/billing-specialist.md
  kb_domains:
    - path: kb/billing/
      domain: billing
```

### Pattern 4: `.claude/packs/.lock.yaml` lockfile

```yaml
# Auto-generated by scripts/pack.py — do not edit manually
packs:
  billing-pack:
    version: "0.1.0"
    source: "git@github.com:emerson-antonio-ops/agentspec-pack-example.git"
    installed_at: "2026-06-22T12:00:00Z"
    staged_path: ".claude/packs/billing-pack"
```

### Pattern 5: `pack.py` apply with local-wins

```python
def apply_pack(staged_root: Path, project_root: Path) -> ApplyResult:
    """Copy agents/kb from staged pack into workspace; skip existing files."""
    skipped: list[str] = []
    copied: list[str] = []

    for src in (staged_root / "agents" / "custom").glob("*.md"):
        dest = project_root / ".claude" / "agents" / "custom" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            skipped.append(str(dest.relative_to(project_root)))
            continue
        shutil.copy2(src, dest)
        copied.append(str(dest.relative_to(project_root)))

    kb_root = staged_root / "kb"
    if kb_root.is_dir():
        for src in kb_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(kb_root)
            dest = project_root / ".claude" / "kb" / rel
            if dest.exists():
                skipped.append(str(dest.relative_to(project_root)))
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(str(dest.relative_to(project_root)))

    return ApplyResult(copied=copied, skipped=skipped)
```

### Pattern 6: `prepare-upstream.py` validators

```python
KB_LIMITS = {"quick-reference": 100, "concept": 150, "pattern": 200}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"@(?:gmail|company-internal)\."),  # extend as needed
]

def validate_kb_lines(domain_dir: Path) -> list[str]:
    errors = []
    for path in domain_dir.rglob("*.md"):
        lines = len(path.read_text().splitlines())
        kind = "pattern" if "patterns" in path.parts else "concept" if "concepts" in path.parts else \
               "quick-reference" if path.name == "quick-reference.md" else None
        if kind and lines > KB_LIMITS[kind]:
            errors.append(f"{path}: {lines} lines exceeds {kind} limit {KB_LIMITS[kind]}")
    return errors
```

---

## Data Flow

### Pack install flow

```text
1. User runs: /pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
   │
   ▼
2. pack.py validates agentspec-pack.yaml in cloned repo
   │
   ▼
3. Stage → .claude/packs/billing-pack/  (full tree copy)
   │
   ▼
4. Update → .claude/packs/.lock.yaml
   │
   ▼
5. Apply → copy agents/custom/*.md + kb/** to .claude/ (skip conflicts)
   │
   ▼
6. Report: copied N files, skipped M (local-wins)
```

### KB read flow (agent runtime)

```text
1. Agent prompt: Read .claude/kb/dbt/patterns/incremental-model.md
   │
   ▼
2. Host checks: .claude/kb/dbt/patterns/incremental-model.md exists?
   ├─ YES → load local file
   └─ NO  → load ${ROOT_TOKEN}/kb/dbt/patterns/incremental-model.md
```

---

## Integration Points

| System | Integration | Auth |
|--------|-------------|------|
| Git | `pack install` clone/fetch | SSH / HTTPS ambient |
| GitHub | Satellite repo `agentspec-pack-example` | Public repo |
| SessionStart hook | `init_kb_overrides()` | None |
| pytest CI | `test_pack.py` uses local fixture pack dir | None |
| Multi-platform build | `path_rewrite` workspace paths | None |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Goal |
|-----------|-------|-------|-------|------|
| Unit | path_rewrite kb/packs paths | `test_lib_path_rewrite.py` | pytest | Workspace preserved |
| Unit | pack manifest validation | `test_pack.py` | pytest | Invalid manifest fails |
| Unit | pack apply skip logic | `test_pack.py` | pytest + tmp_path | Local-wins |
| Unit | prepare-upstream validators | `test_prepare_upstream.py` | pytest | Line limits + secrets |
| Integration | init-workspace idempotent | manual / optional shell test | bash | README written once |
| E2E | satellite pack install | `test_pack.py` with fixture mirror | pytest | AT-006 |
| Build | multi-platform | `make validate-all` | validate_dist.py | No stale `.claude/kb` refs |

**Fixture pack for tests** (in main repo, not satellite):

```text
tests/fixtures/pack-billing/
├── agentspec-pack.yaml
├── agents/custom/billing-specialist.md
└── kb/billing/index.md
```

CI does not depend on network clone of satellite repo; satellite is for human tutorial + optional nightly job.

---

## Error Handling

| Error | Strategy | Retry? |
|-------|----------|--------|
| Invalid `agentspec-pack.yaml` | Exit 1, print schema errors | No |
| Git clone failed | Exit 2, surface git stderr | User retries |
| Apply conflict (file exists) | Skip file, log in report | N/A |
| `min_agentspec` below installed | Warn to stderr, continue | N/A |
| Secret pattern in prepare-upstream | Exit 1, list matches | No |
| KB line limit exceeded | Exit 1, list files | No |

---

## Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `PACK_LOCKFILE` | path | `.claude/packs/.lock.yaml` | Installed packs registry |
| `PACK_STAGE_DIR` | path | `.claude/packs/{name}/` | Staged pack content |
| `KB_LIMITS` | dict | from `_index.yaml` | Line limits for prepare-upstream |

---

## Security Considerations

- `prepare-upstream.py` scans for secret patterns before PR; not exhaustive — human review still required
- Pack install executes `git clone` — only trusted URLs; document in tutorial
- No pack code execution — only markdown/YAML copied
- Satellite repo public; org packs should use private repos + SSH

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| pack install | stdout report: staged path, copied/skipped counts |
| prepare-upstream | stdout checklist + `/tmp/agentspec-upstream-{feature}/` tree |
| init-workspace | silent on success (existing behavior) |

---

## Build Order (for `/build`)

```text
Sprint 2 PR: feature/kb-reuse-contracts
  1. WORKFLOW_CONTRACTS.yaml
  2. path_rewrite.py + platforms.py + tests
  3. init-workspace.sh
  4. docs/concepts/kb-overrides.md
  5. make build-all && make validate-all && make test

Sprint 3 PR: feature/kb-reuse-packs
  1. PACK_SCHEMA.yaml
  2. scripts/pack.py + tests/fixtures/pack-billing/
  3. pack.md command
  4. WORKFLOW_CONTRACTS pack_resolution
  5. docs/tutorials/agentspec-packs.md
  6. Create satellite repo (manual gh repo create)
  7. make build-all && make validate-all && make test

Sprint 4 PR: feature/kb-reuse-tooling
  1. prepare-upstream.py + tests
  2. prepare-upstream.md command
  3. docs link update
  4. make test
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-22 | Emerson Antonio | Initial design — Sprints 2–4 |

---

## Next Step

**Ready for:**

```bash
/build KB_AGENT_CROSS_PROJECT_REUSE
```

**Recommended build sequence:** Sprint 2 first (`feature/kb-reuse-contracts`), then Sprint 3, then Sprint 4. Sprint 1 docs already shipped on `feature/kb-reuse-docs`.

**Satellite repo** (`emerson-antonio-ops/agentspec-pack-example`) is created manually during Sprint 3 build, after `PACK_SCHEMA.yaml` is finalized.
