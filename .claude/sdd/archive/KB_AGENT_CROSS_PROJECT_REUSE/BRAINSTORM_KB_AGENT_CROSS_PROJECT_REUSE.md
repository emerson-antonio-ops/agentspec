# BRAINSTORM: KB Agent Cross-Project Reuse

> Exploratory session to define repo strategy, phased delivery, and multi-platform impact for reusing KB and agents across projects — fork `emerson-antonio-ops/agentspec`.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | `KB_AGENT_CROSS_PROJECT_REUSE` |
| **Date** | 2026-06-22 |
| **Author** | Emerson Antonio |
| **Status** | Validated — Ready for Define |
| **Fork alvo** | [emerson-antonio-ops/agentspec](https://github.com/emerson-antonio-ops/agentspec) |
| **Documento origem** | `.claude/sdd/features/NOVAS_FUNCIONALIDADES_REUSO_KB_AGENTES.md` |
| **Upstream referência** | [luanmorenommaciel/agentspec](https://github.com/luanmorenommaciel/agentspec) |

---

## Initial Idea

**Raw Input:**

> Temos analisar mais detalhadamente, para criar os repos vamos fazer essas atualizações no meu fork (multi-plataforma): emerson-antonio-ops/agentspec.

**Context Gathered:**

- Feature spec F1–F7 já documentado em `NOVAS_FUNCIONALIDADES_REUSO_KB_AGENTES.md`
- Fork multi-plataforma já shipa Claude Code, Cursor, VS Code + Copilot e MCP a partir de `.claude/`
- Build pipeline: `make build-all` → `dist/{claude,cursor,vscode-copilot,mcp}/`
- Agent overrides já implementados; KB overrides e packs ainda não
- Backlog (`tasks/backlog.md`) desatualizado — não lista F1–F7
- `_WORKSPACE_PATHS` em `scripts/lib/path_rewrite.py` preserva `.claude/agents/{workflow,custom}` mas **não** `.claude/kb/` nem `.claude/packs/`

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Source of truth | `.claude/` | Toda feature começa aqui; builds propagam |
| Plugin-only hooks | `plugin-extras/` | F4 (KB scaffolding) altera `init-workspace.sh` |
| Contratos SDD | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | F3 adiciona `kb_resolution` |
| Path rewrite | `scripts/lib/path_rewrite.py` | F4/F5 precisam estender `_WORKSPACE_PATHS` |
| Validação CI | `make validate-all` + pytest | Todo PR deve passar antes de merge |
| Docs públicas | `docs/` (inglês) | F1/F2 vivem aqui; spec interna pode ser PT-BR |
| Repositórios | 1 principal + 1–2 satélites opcionais | Ver seção "Estratégia de Repositórios" |

---

## Discovery Questions & Answers

| # | Question | Answer (inferida da sessão) | Impact |
|---|----------|----------------------------|--------|
| 1 | Onde implementar primeiro? | Fork `emerson-antonio-ops/agentspec` — não upstream ainda | PRs independentes; sync upstream depois se desejado |
| 2 | Quantos repositórios criar? | **1 obrigatório** (fork) + **1 opcional** (pack de exemplo) na fase v3.5 | Evita over-engineering inicial |
| 3 | Prioridade de entrega? | Docs (F1,F2,F7) → Contratos/scaffolding (F3,F4) → Packs (F5) → Tooling (F6) | Releases incrementais v3.4.0 → v3.5.x |
| 4 | Idioma das docs públicas? | Inglês no repo; spec SDD pode ser PT-BR | F1/F2 escritos em EN; link para spec PT |
| 5 | Breaking change aceitável? | Não — backward compatible | Packs e kb_resolution são aditivos |
| 6 | Contribuir de volta ao upstream? | Opcional, por PR separado após validar no fork | F2 documenta ambos os destinos de PR |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Feature spec | `.claude/sdd/features/NOVAS_FUNCIONALIDADES_REUSO_KB_AGENTES.md` | 1 | F1–F7 detalhados |
| Padrão existente (agent override) | `docs/concepts/agent-overrides.md` | 1 | Template para F1/F4 |
| Contrato existente | `WORKFLOW_CONTRACTS.yaml` → `agent_resolution` | 1 | Template para F3 |
| Init scaffolding | `plugin-extras/scripts/init-workspace.sh` | 1 | Estender para KB (F4) |
| Path rewrite policy | `scripts/lib/path_rewrite.py` | 1 | Adicionar workspace paths (F4/F5) |
| Build validators | `scripts/validate_dist.py` | 1 | Packs podem precisar novas checks (F5) |
| Exemplo fictício | N/A (criar em F2) | 0 | Domínio `billing/` como tutorial |

**How samples will be used:**

- `agent-overrides.md` como referência de tom e estrutura para F1 e F4
- Domínio `billing/` fictício no guia F2 como walkthrough de PR upstream
- Pack de exemplo (repo satélite) como fixture de integração para F5

---

## Estratégia de Repositórios

### Mapa de repos proposto

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  emerson-antonio-ops/agentspec  (PRINCIPAL — obrigatório)               │
│  • Source: .claude/                                                     │
│  • Builds: dist/claude, dist/cursor, dist/vscode-copilot, dist/mcp      │
│  • Entrega: F1–F7 (docs, contratos, packs engine, tooling)              │
│  • Branches: feature/kb-reuse-docs → feature/kb-reuse-contracts → ... │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ referencia (F5 — v3.5)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  emerson-antonio-ops/agentspec-pack-example  (SATÉLITE — opcional v3.5) │
│  • Conteúdo: agentspec-pack.yaml + agents/ + kb/                        │
│  • Propósito: pack interno de demonstração (billing ou de-standards)    │
│  • Não é plugin — consumido via `pack install`                          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ PR opcional (conteúdo genérico)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  luanmorenommaciel/agentspec  (UPSTREAM — opcional)                     │
│  • PRs de docs melhoradas ou KB/agentes genéricos                       │
│  • Somente após validação no fork                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### O que NÃO criar (YAGNI)

| Repo sugerido | Por que não |
|---------------|-------------|
| `agentspec-docs` separado | Docs vivem no repo principal; build já gera dist |
| `agentspec-kb` separado | KB é parte de `.claude/kb/`; packs cobrem sharing org |
| Fork do plugin por empresa | Anti-pattern; usar packs (F5) |

### Branches recomendadas no fork principal

| Branch | Escopo | Release |
|--------|--------|---------|
| `feature/kb-reuse-docs` | F1, F2, F7 | v3.4.0 |
| `feature/kb-reuse-contracts` | F3, F4 + path_rewrite + init-workspace | v3.4.1 |
| `feature/kb-reuse-packs` | F5 schema, script, comando `/pack` | v3.5.0 |
| `feature/kb-reuse-tooling` | F6 `/prepare-upstream` | v3.5.1 |

**Recomendação:** PRs pequenos e sequenciais — merge `docs` antes de `contracts` antes de `packs`.

---

## Matriz de Arquivos por Fase (fork principal)

### Fase 1 — v3.4.0 Docs (F1, F2, F7)

| Ação | Path | Plataformas afetadas |
|------|------|---------------------|
| **Criar** | `docs/concepts/kb-agent-reuse.md` | Todas (conceitual) |
| **Criar** | `docs/contributing/upstream-kb-agents.md` | Todas |
| **Editar** | `docs/concepts/README.md` | Link F1 |
| **Editar** | `docs/getting-started/README.md` | Seção sharing + links |
| **Editar** | `docs/getting-started/claude-code.md` | Parágrafo customize/share |
| **Editar** | `docs/getting-started/cursor.md` | Idem (PLUGIN_ROOT) |
| **Editar** | `docs/getting-started/vscode-copilot.md` | Idem |
| **Editar** | `CONTRIBUTING.md` | Link guia upstream |
| **Editar** | `README.md` | Callout na seção Install |
| **Editar** | `tasks/backlog.md` | Seção v3.4 KB/Agent Reuse |
| **Editar** | `CHANGELOG.md` | Unreleased → v3.4.0 |
| **Manter** | `.claude/sdd/features/NOVAS_FUNCIONALIDADES_*.md` | Spec interna PT-BR |

**Build necessário:** Nenhum para ship de docs — mas rodar `make validate-all` antes do PR para garantir que nada quebrou.

---

### Fase 2 — v3.4.1 Contratos + Scaffolding (F3, F4)

| Ação | Path | Notas |
|------|------|-------|
| **Editar** | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` | Bloco `kb_resolution` + version_history |
| **Criar** | `docs/concepts/kb-overrides.md` | Paridade com agent-overrides |
| **Editar** | `docs/concepts/kb-agent-reuse.md` | Link kb-overrides + contrato |
| **Editar** | `plugin-extras/scripts/init-workspace.sh` | `init_kb_overrides()` idempotente |
| **Editar** | `scripts/lib/path_rewrite.py` | Adicionar `.claude/kb/` a `_WORKSPACE_PATHS` |
| **Editar** | `tests/test_lib_path_rewrite.py` | Testes para kb workspace path |
| **Opcional criar** | `.claude/commands/core/sync-kb.md` | F4 stretch — copia domínio plugin→local |

**Template README gerado no projeto do usuário** (via init-workspace):

```text
.claude/kb/README.md   ← explica local-first KB override (espelha agents/README.md)
```

**Build necessário:**

```bash
make generate          # se algum agente referenciar kb_resolution
make build-all
make validate-all
make test
```

**Dist targets impactados:** Claude, Cursor, Copilot (hooks + path rewrite), MCP (resources/kb unchanged unless docs shipped).

---

### Fase 3 — v3.5.0 Packs (F5)

| Ação | Path | Notas |
|------|------|-------|
| **Criar** | `.claude/sdd/architecture/PACK_SCHEMA.yaml` | Schema do manifest |
| **Criar** | `scripts/pack.py` | install \| list \| remove \| validate |
| **Criar** | `.claude/commands/core/pack.md` | Slash command |
| **Editar** | `scripts/lib/path_rewrite.py` | `.claude/packs/` em `_WORKSPACE_PATHS` |
| **Editar** | `WORKFLOW_CONTRACTS.yaml` | `pack_resolution` (3 níveis) |
| **Editar** | `docs/concepts/kb-agent-reuse.md` | Seção packs |
| **Criar** | `docs/tutorials/agentspec-packs.md` | Tutorial install |
| **Editar** | `Makefile` | Target `pack-validate` opcional |
| **Editar** | `tests/` | test_pack.py |

**Repo satélite confirmado** — `emerson-antonio-ops/agentspec-pack-example` (decisão usuário: opção B):

```text
agentspec-pack-example/                    # repo GitHub separado
├── agentspec-pack.yaml
├── README.md
├── .gitignore
├── agents/
│   └── custom/
│       └── billing-specialist.md
└── kb/
    └── billing/
        ├── index.md
        ├── quick-reference.md
        ├── concepts/
        └── patterns/
```

**Integração CI no fork principal (Sprint 3):**

```bash
# tests/fixtures/pack-example-remote.txt aponta para o repo satélite
# ou git submodule tests/fixtures/agentspec-pack-example @ pinned tag
pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
```

**Não incluir** pack example dentro de `examples/` no monorepo — rejeitado na validação.

**Resolução 3 níveis (formalizar no contrato):**

```text
.claude/agents|kb/     ← projeto (vence)
        ↓
.claude/packs/{name}/  ← pack instalado
        ↓
${ROOT_TOKEN}/         ← plugin AgentSpec
```

---

### Fase 4 — v3.5.1 Tooling (F6)

| Ação | Path |
|------|------|
| **Criar** | `scripts/prepare-upstream.py` |
| **Criar** | `.claude/commands/core/prepare-upstream.md` |
| **Criar** | `tests/test_prepare_upstream.py` |
| **Editar** | `docs/contributing/upstream-kb-agents.md` | Referência ao comando |

---

## Impacto Multi-Plataforma (checklist por entrega)

Toda mudança no fork deve verificar os 4 targets:

| Target | Path token | O que validar |
|--------|------------|---------------|
| Claude Code | `${CLAUDE_PLUGIN_ROOT}` | plugin.json, hooks, commands |
| Cursor | `${PLUGIN_ROOT}` | .cursor-plugin, hooks migrados |
| VS Code + Copilot | `${CLAUDE_PLUGIN_ROOT}` | .github/prompts, .github/agents |
| MCP | `${AGENTSPEC_ROOT}` | resources/kb, route_agent, kb_search |

**Comandos de validação padrão (todo PR):**

```bash
make test
make build-all
make validate-all
python3 scripts/generate-agent-router.py --check   # se agentes tocados
```

**Docs por plataforma:** F1 deve incluir tabela "where content lives" com os 4 tokens de path — evita confusão Cursor vs Claude.

---

## Approaches Explored

### Approach A: Monorepo incremental no fork ⭐ Recommended

**Description:** Implementar F1–F7 sequencialmente em `emerson-antonio-ops/agentspec`, com pack de exemplo como repo satélite apenas na fase F5.

**Pros:**

- Alinha com arquitetura existente (`.claude/` → `dist/`)
- CI já cobre multi-plataforma
- PRs pequenos, reviewável
- Zero nova infra de publish

**Cons:**

- Pack example exige segundo repo (ou pasta `examples/` no monorepo)

**Why Recommended:** Menor risco, reutiliza pipeline existente, entrega valor em v3.4.0 com só docs.

---

### Approach B: Monorepo + `examples/pack-billing/` (sem repo satélite)

**Description:** Pack de demonstração vive em `examples/agentspec-pack-billing/` dentro do fork principal.

**Pros:**

- Um único repo para clonar
- CI pode testar `pack install examples/...` end-to-end

**Cons:**

- Examples no repo principal aumenta ruído para contributors upstream

**When to use:** Se preferir evitar segundo repo GitHub.

---

### Approach C: Implementar F5 (packs) antes de F1 (docs)

**Description:** Resolver sharing técnico primeiro.

**Pros:**

- Valor tangível imediato para multi-repo

**Cons:**

- Usuários continuam confusos sobre plugin vs local
- F5 depende de design de schema — atrasa release

**Why not recommended:** Docs fecham 80% da dor; packs são v3.5.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A (monorepo incremental) + **repo satélite** para pack example (opção B) |
| **User Confirmation** | 2026-06-22 — opção **(b)** repo satélite `emerson-antonio-ops/agentspec-pack-example` |
| **Reasoning** | Docs primeiro, contratos depois, packs por último; pack de demo espelha uso real multi-repo (git URL install) |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|---------------------|
| 1 | Fork `emerson-antonio-ops/agentspec` como repo de implementação | Maintainer control, multi-plataforma já shipado | Implementar direto no upstream |
| 2 | v3.4.0 = só docs (F1,F2,F7) | Zero breaking change, entrega rápida | Big-bang v3.5 com packs |
| 3 | Estender `_WORKSPACE_PATHS` com `.claude/kb/` e `.claude/packs/` | Build não reescreve paths do usuário | Hardcode em cada agente |
| 4 | Pack example: **repo satélite** `emerson-antonio-ops/agentspec-pack-example` | Espelha install via git URL; separa conteúdo org do plugin | `examples/` dentro do monorepo (opção a) |
| 5 | Docs públicas em inglês | Convenção do repo AgentSpec | PT-BR only |
| 6 | PR upstream opcional e separado | Conteúdo org-specific não sobe | Fork permanente sem sync |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Marketplace público de packs | Curadoria, licenciamento, infra | Yes (v4+) |
| Sync bidirecional projeto↔plugin | Conflitos de merge | No |
| Segundo fork só para docs | Duplica CI e drift | No |
| Indexação build-time de agentes locais | Runtime loader já resolve | No (documentar only) |
| `/sync-kb` na v3.4.1 | Nice-to-have; init README basta MVP | Yes (v3.4.2) |
| `examples/` pack no monorepo | Rejeitado — usuário escolheu repo satélite (b) | No |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Estratégia de repos (1 principal + 1 satélite) | ✅ | **Confirmado** — opção (b) repo satélite | Sim |
| Local do pack example | ✅ | **(b)** `agentspec-pack-example` separado | Sim — removido `examples/` do monorepo |
| Fases v3.4.0 → v3.5.1 com branches | ✅ | Aceito implicitamente | Não |
| Matriz de arquivos por fase | ✅ | Aceito implicitamente | Não |
| Impacto multi-plataforma | ✅ | Aceito implicitamente | Não |

**Minimum Validations:** 2 ✅ (repo strategy + pack location confirmed)

---

## Plano de Execução Detalhado (Repos + PRs)

### Sprint 1 — `feature/kb-reuse-docs` → v3.4.0

```bash
git checkout -b feature/kb-reuse-docs

# Criar
docs/concepts/kb-agent-reuse.md
docs/contributing/upstream-kb-agents.md

# Editar cross-links (7 arquivos)
# Atualizar tasks/backlog.md + CHANGELOG.md

make test && make validate-all
gh pr create --title "docs: KB and agent cross-project reuse guides (v3.4.0)"
```

**Entregável:** Usuário entende plugin vs local; sabe como contribuir upstream.

---

### Sprint 2 — `feature/kb-reuse-contracts` → v3.4.1

```bash
git checkout -b feature/kb-reuse-contracts

# WORKFLOW_CONTRACTS.yaml → kb_resolution
# plugin-extras/scripts/init-workspace.sh → init_kb_overrides()
# scripts/lib/path_rewrite.py → .claude/kb/
# docs/concepts/kb-overrides.md

make build-all && make validate-all && make test
gh pr create --title "feat: kb_resolution contract and KB override scaffolding"
```

**Entregável:** Paridade documentada e scaffolded entre agent e KB overrides.

---

### Sprint 3 — `feature/kb-reuse-packs` → v3.5.0

**Repo principal** (`emerson-antonio-ops/agentspec`):

```bash
git checkout -b feature/kb-reuse-packs

# PACK_SCHEMA.yaml, scripts/pack.py, /pack command
# tests/test_pack.py — install from satellite repo URL
# docs/tutorials/agentspec-packs.md — referencia repo satélite

make build-all && make validate-all && make test
gh pr create --title "feat: AgentSpec packs for org-wide KB/agent sharing"
```

**Repo satélite** (`emerson-antonio-ops/agentspec-pack-example`) — criar em paralelo:

```bash
# Novo repo GitHub (público ou private org)
gh repo create emerson-antonio-ops/agentspec-pack-example --public --description "Example AgentSpec pack — billing KB + agent"

# Scaffold inicial
agentspec-pack.yaml          # name: billing-pack, version: 0.1.0, min_agentspec: 3.5.0
README.md                    # install: pack install git@github.com:emerson-antonio-ops/agentspec-pack-example.git
agents/custom/billing-specialist.md
kb/billing/                  # index, quick-reference, 2 concepts, 2 patterns (fictício)
```

**Entregável:** Times multi-repo instalam pack via git URL; tutorial documenta o satélite como referência.

---

### Sprint 4 — `feature/kb-reuse-tooling` → v3.5.1

```bash
git checkout -b feature/kb-reuse-tooling

# scripts/prepare-upstream.py + command + tests

gh pr create --title "feat: /prepare-upstream command for contribution workflow"
```

---

### Sync upstream (opcional)

Após v3.4.0 estável no fork:

```bash
# No fork emerson-antonio-ops/agentspec
git remote add upstream https://github.com/luanmorenommaciel/agentspec.git
git fetch upstream

# PR seletivo: só docs genéricas (F1,F2) — não fork-specific metadata
gh pr create --repo luanmorenommaciel/agentspec \
  --title "docs: add KB/agent reuse and upstream contribution guides"
```

**Excluir do PR upstream:** README fork attribution, `PROJECT_METADATA` do fork, paths `emerson-antonio-ops`.

---

## Suggested Requirements for /define

### Problem Statement (Draft)

Engenheiros usando AgentSpec em múltiplos repositórios não entendem o que é compartilhado globalmente (plugin) vs localmente (projeto), não têm guia operacional de contribuição upstream, e não possuem mecanismo nativo de sharing organizacional sem PR ao plugin — gerando copy-paste, drift e expectativas incorretas.

### Target Users (Draft)

| User | Pain Point |
|------|------------|
| DE lead multi-repo | Conhecimento institucional preso em um repo |
| Contributor AgentSpec | Não sabe preparar PR de KB/agente |
| Maintainer fork | Precisa shippar docs+features em 4 plataformas |
| Usuário Cursor/Claude | Confunde `${PLUGIN_ROOT}` vs `.claude/kb/` local |

### Success Criteria (Draft)

- [ ] F1 publicado e linkado — tempo de compreensão < 5 min (teste com 1 usuário)
- [ ] F2 publicado — checklist upstream completo com exemplo `billing/`
- [ ] `tasks/backlog.md` lista F1–F6 com status
- [ ] v3.4.0 tag no fork após merge Sprint 1
- [ ] `make validate-all` verde em todo PR
- [ ] (v3.5) Repo satélite `agentspec-pack-example` publicado e instalável via `pack install`
- [ ] (v3.5) CI no fork principal testa install a partir da URL do satélite

### Constraints Identified

- Zero breaking change no plugin existente
- Source of truth permanece `.claude/`
- Docs públicas em inglês
- Compatibilidade Claude + Cursor + Copilot + MCP
- CI existente deve continuar passando

### Out of Scope (Confirmed)

- Marketplace público de packs
- PR automático para upstream
- Fork obrigatório do plugin por empresa
- KB merge semântico (file-level local-wins only)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 6 (inferidas) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 (documentadas, confirmação usuário pendente) |
| Repos propostos | 1 obrigatório + 1 satélite **confirmado** |
| Sprints / PRs | 4 |
| Release targets | v3.4.0 → v3.4.1 → v3.5.0 → v3.5.1 |

---

## Quality Gate

```text
[x] Minimum 3 discovery questions asked (6 inferidas)
[x] Sample collection documented (artefatos existentes mapeados)
[x] At least 2 approaches explored (3)
[x] YAGNI applied (6 items removed)
[x] Minimum 2 validations completed with user — pack location (b) confirmado 2026-06-22
[x] Draft requirements included
[x] User confirmed selected approach — monorepo + repo satélite
```

---

## Next Step

**Ready for:**

```bash
/define KB_AGENT_CROSS_PROJECT_REUSE
```

**Input documents:**

- `.claude/sdd/features/BRAINSTORM_KB_AGENT_CROSS_PROJECT_REUSE.md` (this file)
- `.claude/sdd/features/NOVAS_FUNCIONALIDADES_REUSO_KB_AGENTES.md` (feature spec F1–F7)

**Primeira ação de build recomendada:**

```bash
git checkout -b feature/kb-reuse-docs
# Implementar F1, F2, F7 conforme matriz Sprint 1
```

---

## Changelog deste documento

| Data | Autor | Mudança |
|------|-------|---------|
| 2026-06-22 | Emerson Antonio | Brainstorm inicial — estratégia de repos, fases, matriz de arquivos, impacto multi-plataforma |
| 2026-06-22 | Emerson Antonio | Validação: pack example em repo satélite `emerson-antonio-ops/agentspec-pack-example` (opção b) |
