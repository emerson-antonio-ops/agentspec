"""Agent routing logic for the MCP server.

Author: Emerson Antonio
Date: 2026-06-17

We do not duplicate the agent-router skill; we read the ``routing.json``
that ``scripts/generate-agent-router.py`` already emits and match incoming
tasks against agent descriptions, KB domains and category labels.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AgentEntry:
    name: str
    category: str
    description: str
    tier: str
    model: str
    kb_domains: tuple[str, ...]
    escalates_to: tuple[str, ...]


def _resources_root() -> Path:
    """Resolve the resource root used to load routing.json.

    Order of precedence:
    1. ``AGENTSPEC_RESOURCES`` environment variable (set by build_mcp.py).
    2. ``AGENTSPEC_ROOT`` environment variable + ``resources``.
    3. Repository ``dist/mcp/resources`` (during local dev).
    4. Repository ``.claude`` (final fallback).
    """
    env_resources = os.environ.get("AGENTSPEC_RESOURCES")
    if env_resources:
        return Path(env_resources)
    env_root = os.environ.get("AGENTSPEC_ROOT")
    if env_root:
        return Path(env_root) / "resources"
    here = Path(__file__).resolve()
    # packages/agentspec-mcp/agentspec_mcp/routing.py → repo root is parents[3]
    repo_root = here.parents[3]
    dev_resources = repo_root / "dist" / "mcp" / "resources"
    if dev_resources.exists():
        return dev_resources
    return repo_root / ".claude"


def load_routing(resources_root: Path | None = None) -> list[AgentEntry]:
    """Load every agent declared in ``routing.json``."""
    root = resources_root or _resources_root()
    routing_json = root / "skills" / "agent-router" / "routing.json"
    if not routing_json.exists():
        return []
    data = json.loads(routing_json.read_text(encoding="utf-8"))
    agents: list[AgentEntry] = []
    for entry in data.get("agents", []):
        agents.append(AgentEntry(
            name=entry.get("name", ""),
            category=entry.get("category", ""),
            description=entry.get("description", ""),
            tier=entry.get("tier", "T1"),
            model=entry.get("model", "sonnet"),
            kb_domains=tuple(entry.get("kb_domains", ())),
            escalates_to=tuple(entry.get("escalates_to", ())),
        ))
    return agents


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens used for scoring."""
    return {tok for tok in re.split(r"[^a-z0-9]+", text.lower()) if tok}


def score_agent(agent: AgentEntry, query_tokens: set[str]) -> int:
    """Rank an agent against the query. Higher score wins.

    The heuristic is intentionally simple: count overlap between query
    tokens and agent description/name/kb tokens. Production routing should
    use Embedding-based matching, but this is the source of truth for the
    rule-based skill so we keep parity here.
    """
    if not query_tokens:
        return 0
    name_tokens = _tokenize(agent.name)
    desc_tokens = _tokenize(agent.description)
    kb_tokens = {token for kb in agent.kb_domains for token in _tokenize(kb)}
    score = 0
    score += len(query_tokens & name_tokens) * 4
    score += len(query_tokens & desc_tokens) * 2
    score += len(query_tokens & kb_tokens) * 3
    return score


def route(query: str, agents: Iterable[AgentEntry] | None = None, top_k: int = 5) -> list[tuple[AgentEntry, int]]:
    """Return the top-K agents ranked against ``query``."""
    pool = list(agents) if agents is not None else load_routing()
    tokens = _tokenize(query)
    ranked = [(agent, score_agent(agent, tokens)) for agent in pool]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return [pair for pair in ranked if pair[1] > 0][:top_k] or ranked[:top_k]
