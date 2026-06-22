#!/usr/bin/env python3
"""Validate AgentSpec distributable artifacts.

Author: Emerson Antonio
Date: 2026-06-17

Runs sanity checks against the ``dist/`` tree produced by build_all.py.
We check counts (58 agents, 31 commands, 24 KB domains), required files
(plugin manifests, judge.py, init-workspace.sh), JSON validity for every
emitted manifest, and the absence of stale ``.claude/`` references.

Exits with a non-zero status code as soon as any target fails, so this
script is suitable as a CI gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import packaging, platforms
from scripts.lib.path_rewrite import stale_legacy_tokens, stale_references
from scripts.lib.platforms import PlatformProfile

REPO_ROOT = Path(__file__).resolve().parent.parent


# Minimum counts so we catch silent regressions where an agent or KB domain
# stops getting copied. We deliberately stay below the documented counts
# (58/31/24) to leave room for normal churn while still catching big drops.
MIN_COUNTS = {
    "agents": 50,
    "commands": 25,
    "kb_domains": 20,
    "skills": 4,
}

# MCP ships only the 3 source skills (no plugin-extras), so its floor differs.
MCP_MIN_COUNTS = {**MIN_COUNTS, "skills": 3}


@dataclass
class CheckResult:
    target: str
    passed: bool
    messages: list[str]


def _count(root: Path, exclude: set[str]) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*.md") if p.name not in exclude)


def _count_skills(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob("SKILL.md"))


def _count_kb(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(
        1 for child in root.iterdir()
        if child.is_dir() and child.name not in {"_templates"}
    )


def _check_json(path: Path, required_keys: tuple[str, ...] = ()) -> list[str]:
    if not path.exists():
        return [f"missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON {path}: {exc}"]
    return [f"missing key {k} in {path}" for k in required_keys if k not in data]


def validate_target(profile: PlatformProfile) -> CheckResult:
    out = platforms.dist_root(REPO_ROOT, profile.id)
    msgs: list[str] = []
    if not out.exists():
        return CheckResult(profile.id, False, [f"dist not built: {out}"])

    agents = _count(out / profile.agent_root, {"README.md", "_template.md"})
    commands = _count(out / profile.command_root, {"README.md"})
    skills = _count_skills(out / profile.skill_root)
    kb_domains = _count_kb(out / profile.kb_root)

    counts = MCP_MIN_COUNTS if profile.id == platforms.MCP else MIN_COUNTS

    if agents < counts["agents"]:
        msgs.append(f"agents below minimum: {agents} < {counts['agents']}")
    if commands < counts["commands"]:
        msgs.append(f"commands below minimum: {commands} < {counts['commands']}")
    if skills < counts["skills"]:
        msgs.append(f"skills below minimum: {skills} < {counts['skills']}")
    if kb_domains < counts["kb_domains"]:
        msgs.append(f"kb domains below minimum: {kb_domains} < {counts['kb_domains']}")

    # Manifest checks per platform
    if profile.id == platforms.CLAUDE:
        msgs.extend(_check_json(out / ".claude-plugin" / "plugin.json", ("name", "version", "description")))
        msgs.extend(_check_json(out / ".claude-plugin" / "marketplace.json", ("name", "owner", "plugins")))
    elif profile.id == platforms.CURSOR:
        msgs.extend(_check_json(out / ".cursor-plugin" / "plugin.json", ("name", "version", "description")))
        msgs.extend(_check_json(out / ".claude-plugin" / "plugin.json", ("name", "version")))
    elif profile.id == platforms.COPILOT:
        msgs.extend(_check_json(out / ".claude-plugin" / "plugin.json", ("name", "version", "description")))
        prompts_dir = out / ".github" / "prompts"
        if not prompts_dir.exists() or not any(prompts_dir.iterdir()):
            msgs.append("missing or empty .github/prompts directory")
        agents_dir = out / ".github" / "agents"
        if not agents_dir.exists() or not any(agents_dir.iterdir()):
            msgs.append("missing or empty .github/agents directory")
    elif profile.id == platforms.MCP:
        msgs.extend(_check_json(out / "mcp.json", ("mcpServers",)))

    # judge.py shipping
    judge_path = out / "scripts" / "judge.py"
    if profile.id != platforms.MCP and not judge_path.exists():
        msgs.append(f"missing scripts/judge.py at {judge_path}")
    if profile.id == platforms.MCP and not judge_path.exists():
        msgs.append("missing scripts/judge.py in MCP bundle")

    # Judge setup guide (shipped with every target that bundles judge.py)
    judge_doc = out / "docs" / "getting-started" / "judge-setup.md"
    if not judge_doc.exists():
        msgs.append(f"missing docs/getting-started/judge-setup.md at {judge_doc}")

    # Stale path detection
    stale = stale_references(out, profile)
    if stale:
        msgs.append(f"{len(stale)} stale .claude/ references")
        for path, line_no, line in stale[:5]:
            msgs.append(f"  {path}:{line_no} → {line.strip()}")

    # Non-Claude targets must not retain ${CLAUDE_PLUGIN_ROOT} after rewrite
    legacy = stale_legacy_tokens(out, profile)
    if legacy:
        msgs.append(f"{len(legacy)} stale ${'{CLAUDE_PLUGIN_ROOT}'} references")
        for path, line_no, line in legacy[:5]:
            msgs.append(f"  {path}:{line_no} → {line.strip()}")

    return CheckResult(profile.id, not msgs, msgs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(platforms.PROFILES), help="Validate a single target")
    args = parser.parse_args()

    targets = [args.only] if args.only else list(platforms.PROFILES)
    failures: list[CheckResult] = []
    for target in targets:
        profile = platforms.get_profile(target)
        result = validate_target(profile)
        status = "OK" if result.passed else "FAIL"
        print(f"[{status}] {result.target}")
        for msg in result.messages:
            print(f"   - {msg}")
        if not result.passed:
            failures.append(result)

    if failures:
        print(f"\n{len(failures)} target(s) failed validation")
        return 1
    print(f"\nAll {len(targets)} target(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
