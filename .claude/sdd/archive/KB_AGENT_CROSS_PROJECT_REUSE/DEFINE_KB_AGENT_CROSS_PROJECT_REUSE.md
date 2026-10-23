# DEFINE: KB Agent Cross-Project Reuse

> Document and implement sharing models for Knowledge Base domains and specialist agents across AgentSpec projects — from plugin-global catalog to org-wide packs.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | `KB_AGENT_CROSS_PROJECT_REUSE` |
| **Date** | 2026-06-22 |
| **Author** | Emerson Antonio |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |
| **Brainstorm Input** | `.claude/sdd/features/BRAINSTORM_KB_AGENT_CROSS_PROJECT_REUSE.md` |

---

## Problem Statement

Data engineers using AgentSpec across multiple repositories create custom agents and KB domains expecting that knowledge to propagate automatically. It does not — only the plugin catalog is global. Without clear documentation, upstream contribution guides, and (later) org-wide packs, teams fall back to copy-paste, accumulate drift, and misconfigure local vs plugin paths across Claude Code, Cursor, Copilot, and MCP.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| DE lead | Multi-repo platform owner | Institutional patterns trapped in one repo |
| AgentSpec contributor | Open-source or fork contributor | No step-by-step PR workflow for KB/agents |
| Fork maintainer | `emerson-antonio-ops/agentspec` | Must ship docs/features across 4 platform targets |
| Cursor/Claude user | Daily AgentSpec user | Confuses `${PLUGIN_ROOT}` with `.claude/kb/` local paths |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Users understand plugin-global vs project-local in <5 minutes (F1) |
| **MUST** | Upstream contribution guide covers KB-only, KB+agent, and patch scenarios (F2) |
| **MUST** | Backlog and cross-links register the full F1–F6 roadmap (F7) |
| **SHOULD** | Formal `kb_resolution` contract mirrors `agent_resolution` (F3) |
| **SHOULD** | SessionStart scaffolds `.claude/kb/` with override README (F4) |
| **COULD** | AgentSpec packs installable from satellite repo via git URL (F5) |
| **COULD** | `/prepare-upstream` automates pre-PR validation (F6) |

---

## Success Criteria

- [ ] F1 published at `docs/concepts/kb-agent-reuse.md` and linked from 5+ entry points
- [ ] F2 published at `docs/contributing/upstream-kb-agents.md` with billing walkthrough
- [ ] `make test` and `make validate-all` pass on every sprint PR
- [ ] v3.4.0 tagged after Sprint 1 merge
- [ ] (v3.4.1) `kb_resolution` in WORKFLOW_CONTRACTS.yaml
- [ ] (v3.5.0) `emerson-antonio-ops/agentspec-pack-example` installable via `pack install`
- [ ] Zero breaking changes to existing plugin behavior in v3.4.x

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Read reuse guide | User opens F1 doc | Reads FAQ section | Understands custom agents are repo-local |
| AT-002 | Upstream KB PR | User has generalized billing KB | Follows F2 Scenario A | PR includes `_index.yaml` entry + passing CI |
| AT-003 | Platform paths | User on Cursor | Reads F1 path token table | Finds `${PLUGIN_ROOT}` mapping |
| AT-004 | Agent override link | User reads F1 | Clicks Agent Overrides | Lands on existing override doc |
| AT-005 | Backlog traceability | Maintainer opens backlog | Finds v3.4 section | F1–F6 listed with status |
| AT-006 | (v3.5) Pack install | Pack example repo published | Runs `pack install <url>` | `.claude/packs/billing-pack/` populated |

---

## Out of Scope

- Public pack marketplace with curation and licensing
- Bidirectional sync between project and plugin
- Semantic KB merge (file-level local-wins only)
- Build-time indexing of local agents in `routing.json`
- Mandatory org-wide fork of the plugin

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Source of truth remains `.claude/` | All features start in source; `make build-all` propagates |
| Technical | Multi-platform: Claude, Cursor, Copilot, MCP | Path tokens and `_WORKSPACE_PATHS` must stay consistent |
| Compatibility | Zero breaking change in v3.4.0 | Sprint 1 is documentation only |
| Process | Public docs in English | SDD brainstorm/spec may be PT-BR internally |
| Repository | Pack example in satellite repo `agentspec-pack-example` | F5 requires second GitHub repo (user confirmed option b) |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `docs/`, `.claude/sdd/`, `plugin-extras/scripts/`, `scripts/` | Phased by sprint |
| **KB Domains** | `shared`, agent-overrides patterns | Reference existing anti-patterns and override doc |
| **IaC Impact** | None for Sprint 1; CI unchanged | F5 may add pack validation to pytest |

---

## Phased Delivery

| Phase | Version | Items | Status |
|-------|---------|-------|--------|
| Sprint 1 | v3.4.0 | F1, F2, F7 | **Done** |
| Sprint 2 | v3.4.1 | F3, F4 | **Designed** — see DESIGN doc |
| Sprint 3 | v3.5.0 | F5 + satellite repo | **Designed** — see DESIGN doc |
| Sprint 4 | v3.5.1 | F6 | **Designed** — see DESIGN doc |

### Repository map

| Repository | Role |
|------------|------|
| `emerson-antonio-ops/agentspec` | Plugin source, pack engine, docs |
| `emerson-antonio-ops/agentspec-pack-example` | Billing pack demo (F5) |
| `luanmorenommaciel/agentspec` | Optional upstream PR for generic docs |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Host runtime discovers local agents without router changes | Would need build-time local indexing | [x] Documented in F1 |
| A-002 | File-level local-wins suffices for KB override | Would need semantic merge | [x] YAGNI in brainstorm |
| A-003 | Satellite pack repo is acceptable for F5 demo | Would use `examples/` in monorepo | [x] User chose option b |
| A-004 | Docs alone resolve 80% of confusion | Would prioritize F5 earlier | [ ] Validate after v3.4.0 ship |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific users, clear pain |
| Users | 3 | Four personas identified |
| Goals | 3 | MUST/SHOULD/COULD prioritized |
| Success | 2 | Metrics defined; user test for A-004 pending |
| Scope | 3 | Explicit out-of-scope list |
| **Total** | **14/15** | |

**Minimum to proceed: 12/15** — passed.

---

## Open Questions

None for Sprint 1 (docs). For Sprint 3 (F5):

- Pack manifest semver policy — defer to DESIGN phase
- Private pack auth (SSH vs HTTPS token) — document in DESIGN, not DEFINE

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-22 | Emerson Antonio | Initial define from brainstorm; Sprint 1 marked done |

---

## Next Step

**Ready for:** `/build KB_AGENT_CROSS_PROJECT_REUSE`

**Design artifact:** `.claude/sdd/features/DESIGN_KB_AGENT_CROSS_PROJECT_REUSE.md`

Sprint 2 (F3/F4) build first on branch `feature/kb-reuse-contracts`.
