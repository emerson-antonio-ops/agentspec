# Novas Funcionalidades — Reutilização de KB e Agentes entre Projetos

> Documento de funcionalidades derivado de exploração sobre compartilhamento de Knowledge Base e agentes especialistas entre projetos AgentSpec.

## Metadata

| Atributo | Valor |
|----------|-------|
| **Feature** | `KB_AGENT_CROSS_PROJECT_REUSE` |
| **Data** | 2026-06-22 |
| **Autor** | Emerson Antonio |
| **Repositório alvo** | [emerson-antonio-ops/agentspec](https://github.com/emerson-antonio-ops/agentspec) |
| **Status** | Explorado — pronto para `/define` |
| **Origem** | Sessão de exploração (chat) sobre reutilização de KB/agentes e contribuição upstream |

---

## Resumo Executivo

O AgentSpec hoje possui **dois modelos de conteúdo** com comportamentos distintos:

1. **Conteúdo do plugin** (58 agentes + 24 domínios KB) — compartilhado automaticamente entre todos os projetos que instalam o plugin.
2. **Conteúdo local do projeto** (`.claude/agents/`, `.claude/kb/`) — isolado por repositório, sem propagação automática.

A conversa identificou **lacunas de produto e documentação**: falta simetria entre override de agentes e override de KB, não existe mecanismo nativo de compartilhamento entre projetos sem contribuir upstream, e o fluxo de contribuição upstream não está documentado de forma dedicada para usuários finais.

Este documento propõe **7 entregas** (3 documentação, 4 funcionalidade) para fechar essas lacunas no fork multi-plataforma.

---

## Problema

Engenheiros de dados que usam AgentSpec em múltiplos repositórios criam:

- Agentes custom em `.claude/agents/custom/`
- Domínios KB via `/create-kb` em `.claude/kb/`
- Overrides de agentes existentes em `.claude/agents/{categoria}/`

**Expectativa comum:** esse conhecimento institucional se propagaria para outros projetos da mesma organização.

**Realidade atual:** o conteúdo local fica preso ao repositório onde foi criado. Apenas o catálogo oficial do plugin é globalmente reutilizado.

---

## Estado Atual (As-Is)

### Arquitetura de duas camadas

```text
┌─────────────────────────────────────────────────────────────┐
│  Plugin AgentSpec (${CLAUDE_PLUGIN_ROOT}/)                  │
│  • 58 agentes + 24 KB domains                               │
│  • Compartilhado em TODOS os projetos com plugin instalado  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ fallback
┌─────────────────────────────────────────────────────────────┐
│  Projeto local (.claude/)                                   │
│  • agents/workflow/  → override local-first (documentado)   │
│  • agents/custom/    → agentes novos (só neste repo)        │
│  • kb/{dominio}/     → KB custom (só neste repo)            │
│  • sdd/features/     → artefatos SDD (só neste repo)        │
└─────────────────────────────────────────────────────────────┘
```

### Precedência de agentes (implementado)

```text
.claude/agents/<categoria>/<nome>.md   ← override local (vence)
        ↓ se ausente
${CLAUDE_PLUGIN_ROOT}/agents/...       ← plugin AgentSpec (fallback)
```

- Contrato formal: `agent_resolution` em `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml`
- Documentação: `docs/concepts/agent-overrides.md`
- Scaffolding: `init-workspace.sh` cria `.claude/agents/{workflow,custom}/`

### KB (sem override simétrico)

- Não existe contrato `kb_resolution` equivalente ao de agentes.
- Documentação em `docs/concepts/agent-overrides.md` diz explicitamente:

  > KB domains are not overridden by this mechanism. To customize KB content, fork the relevant `kb/<domain>/` files into your project and reference them from your override agent.

- Agentes referenciam `.claude/kb/` no source e `${CLAUDE_PLUGIN_ROOT}/kb/` no plugin build.

### Formas manuais de compartilhar hoje

| Método | Escopo | Automático? |
|--------|--------|-------------|
| Instalar/atualizar plugin | Catálogo oficial | Sim |
| Contribuir upstream (PR) | Todos os usuários do plugin | Após release |
| Git submodule / template repo | Projetos que referenciam o repo | Manual |
| Copy-paste entre repos | Projetos copiados | Manual |
| Legacy `cp -r agentspec/.claude` | Cópia independente por projeto | Manual, sem sync |

### Router de agentes

- `scripts/generate-agent-router.py` indexa apenas agentes em `.claude/agents/` **do repo AgentSpec**.
- Agentes locais de projetos de usuário **não entram** no `routing.json` do plugin — o loader do Claude Code/Cursor descobre em runtime.

---

## Lacunas Identificadas

| # | Lacuna | Impacto |
|---|--------|---------|
| L1 | Sem doc dedicada explicando reutilização KB/agentes entre projetos | Usuários assumem propagação automática |
| L2 | Sem guia passo a passo de contribuição upstream para usuários finais | Barreira alta para devolver conhecimento ao ecossistema |
| L3 | KB não tem override local-first simétrico ao de agentes | Customização de KB é inconsistente e mal documentada |
| L4 | Sem mecanismo de "Agent/KB Pack" instalável entre projetos | Times multi-repo dependem de copy-paste ou submodule |
| L5 | Sem comando para preparar conteúdo local para PR upstream | Trabalho manual de generalização e validação |
| L6 | Router não documenta comportamento com agentes locais | Confusão sobre o que entra no routing.json |

---

## Funcionalidades Propostas

### F1 — Guia: Reutilização de KB e Agentes entre Projetos

| Campo | Valor |
|-------|-------|
| **Prioridade** | P1 |
| **Tipo** | Documentação |
| **Local alvo** | `docs/concepts/kb-agent-reuse.md` |
| **Esforço** | Baixo |

**Descrição:** Documento de referência que explica as duas camadas (plugin vs local), tabela de precedência, o que é e o que não é compartilhado, e opções manuais de compartilhamento.

**Conteúdo mínimo:**

- Diagrama plugin vs projeto local
- Tabela: tipo de conteúdo × localização × reutilizado entre projetos?
- Link para agent overrides e contribuição upstream
- FAQ (ex.: "Criei um agente em custom/, outros projetos veem?")

**Critérios de aceite:**

- [ ] Linkado em `docs/concepts/README.md` e `docs/getting-started/README.md`
- [ ] Referenciado no README raiz na seção Install/Customize

---

### F2 — Guia: Contribuição Upstream (KB e Agentes)

| Campo | Valor |
|-------|-------|
| **Prioridade** | P1 |
| **Tipo** | Documentação |
| **Local alvo** | `docs/contributing/upstream-kb-agents.md` |
| **Esforço** | Médio |

**Descrição:** Guia operacional para levar conteúdo de `.claude/` de um projeto de dados para o repo AgentSpec via PR.

**Conteúdo mínimo (fluxo completo):**

1. **Preparar conteúdo** — generalizar, remover secrets, validar limites de linha KB
2. **Fork e branch** — `feature/add-{domain}-kb` ou `feature/add-{agent}-agent`
3. **Estrutura alvo** — paths em `.claude/kb/` e `.claude/agents/{categoria}/`
4. **Registrar** — `_index.yaml` para KB; frontmatter + `_template.md` para agentes
5. **Conectar** — `kb_domains` nos agentes; critérios "When NOT to Create"
6. **Validar** — `make generate`, `make test`, `make validate-all`
7. **Documentar** — CHANGELOG, contadores (agentes/KB), README
8. **PR** — template de título, corpo, test plan
9. **Pós-merge** — release do plugin, `claude plugin update agentspec`

**Três cenários documentados:**

| Cenário | Entregável upstream |
|---------|---------------------|
| Só KB novo | `.claude/kb/{dominio}/` + `_index.yaml` + ligação em agentes existentes |
| KB + agente novo | KB completo + `.claude/agents/{categoria}/{agente}.md` + `make generate` |
| Melhoria em existente | Edição pontual em KB/agente — PR pequeno, sem mudança de contadores |

**Checklist pré-PR:**

- [ ] Conteúdo generalizado (sem secrets/dados reais)
- [ ] KB dentro dos limites (`quick-reference` 100, `concept` 150, `pattern` 200 linhas)
- [ ] Domínio registrado em `_index.yaml` (se KB novo)
- [ ] Agente segue `_template.md` e critérios "When NOT to Create"
- [ ] `make generate` executado (router atualizado)
- [ ] `make test` e `make validate-all` passando
- [ ] Teste manual com `--plugin-dir ./dist/claude` ou `dist/cursor`

**Critérios de aceite:**

- [ ] Linkado em `CONTRIBUTING.md` na seção "Ways to Contribute"
- [ ] Exemplo concreto (domínio fictício `billing/`) como anexo ou tutorial

---

### F3 — Contrato `kb_resolution` em WORKFLOW_CONTRACTS.yaml

| Campo | Valor |
|-------|-------|
| **Prioridade** | P2 |
| **Tipo** | Especificação / contrato |
| **Local alvo** | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` |
| **Esforço** | Baixo |

**Descrição:** Formalizar precedência de KB equivalente ao `agent_resolution` já existente.

**Proposta de contrato:**

```yaml
kb_resolution:
  order:
    - "local"   # .claude/kb/<domain>/ no projeto do usuário
    - "plugin"  # ${CLAUDE_PLUGIN_ROOT}/kb/<domain>/ (AgentSpec)

  behavior: |
    Domínios KB presentes em .claude/kb/ do projeto do usuário
    complementam ou substituem arquivos homônimos do plugin quando
    o agente referencia .claude/kb/{domain}/. Domínios existentes
    apenas no plugin continuam disponíveis como fallback.

  merge_strategy: "local-wins"  # arquivo a arquivo, não merge profundo
```

**Critérios de aceite:**

- [ ] Documentado em `docs/concepts/kb-agent-reuse.md`
- [ ] Agentes T2+ referenciam o contrato na seção Knowledge Resolution
- [ ] Versão incrementada em `version_history` do WORKFLOW_CONTRACTS

---

### F4 — KB Local-First Override (implementação documentada)

| Campo | Valor |
|-------|-------|
| **Prioridade** | P2 |
| **Tipo** | Feature + documentação |
| **Esforço** | Médio |

**Descrição:** Tornar explícito e ergonômico o padrão de override de KB — hoje possível manualmente, mas sem scaffolding.

**Entregas:**

1. `init-workspace.sh` cria `.claude/kb/` vazio com README explicando override (espelhando agent overrides)
2. Doc `docs/concepts/kb-overrides.md` com receita:

   ```bash
   cp $CLAUDE_PLUGIN_ROOT/kb/dbt/patterns/incremental-model.md \
      .claude/kb/dbt/patterns/incremental-model.md
   ```

3. Comando opcional `/sync-kb dbt` — copia domínio do plugin para local como ponto de partida

**Critérios de aceite:**

- [ ] README em `.claude/kb/README.md` gerado no primeiro SessionStart (idempotente)
- [ ] Paridade conceitual com `docs/concepts/agent-overrides.md`

---

### F5 — Agent/KB Packs (pacotes compartilháveis entre projetos)

| Campo | Valor |
|-------|-------|
| **Prioridade** | P2 |
| **Tipo** | Feature nova |
| **Esforço** | Alto |

**Descrição:** Mecanismo para times publicarem pacotes reutilizáveis sem PR upstream — meio-termo entre "local isolado" e "contribuição global".

**Conceito:**

```text
agentspec-pack.yaml          # manifest do pack
├── agents/
│   └── custom/
│       └── billing-specialist.md
└── kb/
    └── billing/
        ├── index.md
        └── patterns/
```

**Instalação proposta:**

```bash
# Opção A: via git submodule / path local
agentspec pack install ./packs/company-de-standards

# Opção B: via URL de repo
agentspec pack install git@github.com:org/de-standards-pack.git
```

**Resolução proposta (3 níveis):**

```text
.claude/agents|kb/          ← projeto (vence)
        ↓
.claude/packs/{pack}/       ← packs instalados
        ↓
${CLAUDE_PLUGIN_ROOT}/      ← plugin AgentSpec
```

**Critérios de aceite:**

- [ ] Schema `agentspec-pack.yaml` documentado
- [ ] Comando `/pack install|list|remove` ou script CLI
- [ ] Compatível com Claude Code, Cursor e MCP (via `dist/`)
- [ ] Packs não entram no router build-time do plugin (runtime discovery, como agentes locais)

**Fora de escopo (YAGNI v1):**

- Marketplace público de packs
- Versionamento semver automático de packs
- Merge inteligente de KB (file-level local-wins é suficiente)

---

### F6 — Comando `/prepare-upstream` (preparar contribuição)

| Campo | Valor |
|-------|-------|
| **Prioridade** | P3 |
| **Tipo** | Comando + script |
| **Local alvo** | `.claude/commands/core/prepare-upstream.md` + `scripts/prepare-upstream.py` |
| **Esforço** | Médio |

**Descrição:** Automatizar checklist de generalização antes de PR upstream.

**Comportamento:**

```bash
/prepare-upstream kb billing
/prepare-upstream agent billing-specialist
```

**Saída:**

1. Valida limites de linha KB
2. Scan de secrets/patterns sensíveis (URLs internas, emails, tokens)
3. Verifica registro em `_index.yaml`
4. Lista arquivos de contadores a atualizar se for item novo
5. Gera diff-ready tree em `/tmp/agentspec-upstream-{feature}/`
6. Emite checklist pré-PR

**Critérios de aceite:**

- [ ] Integrado ao guia F2
- [ ] Testes unitários para validadores de linha e secret scan básico

---

### F7 — Atualização do Backlog e Cross-Links

| Campo | Valor |
|-------|-------|
| **Prioridade** | P1 |
| **Tipo** | Manutenção |
| **Esforço** | Baixo |

**Descrição:** Registrar itens F1–F6 em `tasks/backlog.md` e cross-linkar documentação existente.

**Arquivos a atualizar:**

| Arquivo | Mudança |
|---------|---------|
| `tasks/backlog.md` | Nova seção "v3.4 — KB/Agent Cross-Project Reuse" |
| `docs/concepts/README.md` | Link para guias F1 e F2 |
| `docs/getting-started/README.md` | Seção "Sharing KB and agents across projects" |
| `CONTRIBUTING.md` | Link para guia upstream F2 |
| `CHANGELOG.md` | Entrada "Unreleased" referenciando este documento |

---

## Priorização Sugerida

| Fase | Itens | Release alvo |
|------|-------|--------------|
| **v3.4.0 — Docs** | F1, F2, F7 | Imediato — zero breaking change |
| **v3.4.x — Contratos** | F3, F4 | Pequena feature, backward compatible |
| **v3.5.0 — Packs** | F5 | Feature maior, precisa `/define` + `/design` |
| **v3.5.x — Tooling** | F6 | Depende de F2 estabilizado |

---

## Abordagens Consideradas

### Abordagem A: Documentação primeiro ⭐ Recomendada

**Por quê:** O comportamento atual já funciona; a dor principal é falta de clareza. Docs (F1, F2) resolvem 80% da confusão sem código.

**Prós:** Entrega rápida, sem risco de regressão, alinha expectativas.

**Contras:** Não elimina copy-paste manual entre projetos.

### Abordagem B: Packs antes de docs

**Por quê:** Resolveria o problema técnico de compartilhamento diretamente.

**Prós:** Valor tangível para times multi-repo.

**Contras:** Alto esforço, precisa design de schema e resolução tripla; docs ainda seriam necessárias.

### Abordagem C: Apenas contribuir upstream (status quo)

**Por quê:** Mantém simplicidade arquitetural.

**Prós:** Zero implementação.

**Contras:** Não atende conhecimento proprietário que não pode ir upstream; barreira alta para contribuições pequenas.

**Decisão:** Abordagem A como MVP, F5 como evolução natural.

---

## YAGNI — Fora de Escopo

| Item removido | Motivo |
|---------------|--------|
| Marketplace público de KB/agentes | Complexidade de curadoria e licenciamento |
| Sync bidirecional projeto ↔ plugin | Conflitos de merge insolúveis automaticamente |
| KB merge semântico (não file-level) | Over-engineering para v1 |
| Indexação build-time de agentes locais no router | Loader runtime já resolve; documentar é suficiente |
| Fork obrigatório do plugin por empresa | Anti-pattern; packs resolvem melhor |

---

## Rascunho de Requisitos (para `/define`)

### Requisitos funcionais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Usuário deve entender em <5 min o que é global vs local | Must |
| RF-02 | Guia upstream deve cobrir KB-only, KB+agent e patch | Must |
| RF-03 | Contrato `kb_resolution` deve espelhar `agent_resolution` | Should |
| RF-04 | Packs devem ser instaláveis sem modificar o plugin | Could |
| RF-05 | `/prepare-upstream` deve validar limites e secrets | Could |

### Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Zero breaking change no plugin existente |
| RNF-02 | Docs em inglês no repo; versão PT-BR opcional em fork |
| RNF-03 | Compatível com Claude Code, Cursor, VS Code + Copilot, MCP |
| RNF-04 | CI existente (`make test`, `validate-all`) continua passando |

### Métricas de sucesso

- Redução de issues/perguntas sobre "KB não aparece em outro projeto"
- Tempo médio para preparar PR upstream < 30 min (com guia F2)
- Pelo menos 1 pack interno de exemplo publicado (se F5 for implementado)

---

## Referências do Codebase

| Recurso | Path |
|---------|------|
| Agent overrides (padrão existente) | `docs/concepts/agent-overrides.md` |
| Contrato agent_resolution | `.claude/sdd/architecture/WORKFLOW_CONTRACTS.yaml` |
| Init workspace / scaffolding | `plugin-extras/scripts/init-workspace.sh` |
| KB registry | `.claude/kb/_index.yaml` |
| Agent template | `.claude/agents/_template.md` |
| Agent router generator | `scripts/generate-agent-router.py` |
| Contributing guide | `CONTRIBUTING.md` |
| Critérios "When NOT to Create" | `.claude/agents/README.md` |
| Backlog existente | `tasks/backlog.md` |

---

## Próximos Passos SDD

```text
Este documento (exploração)
        ↓
/define KB_AGENT_CROSS_PROJECT_REUSE
        ↓
/design KB_AGENT_CROSS_PROJECT_REUSE    ← F5 (packs) exige design; F1-F2 podem ir direto para build
        ↓
/build KB_AGENT_CROSS_PROJECT_REUSE   ← F1, F2, F7 primeiro
        ↓
/ship KB_AGENT_CROSS_PROJECT_REUSE
```

**Comando sugerido:**

```bash
/define KB_AGENT_CROSS_PROJECT_REUSE
```

---

## Changelog deste documento

| Data | Autor | Mudança |
|------|-------|---------|
| 2026-06-22 | Emerson Antonio | Criação inicial a partir de sessão de exploração sobre reutilização KB/agentes e contribuição upstream |
