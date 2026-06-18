#!/usr/bin/env python3
"""Build the VS Code + GitHub Copilot distribution under ``dist/vscode-copilot/``.

Author: Emerson Antonio
Date: 2026-06-17

VS Code 1.110+ Agent Plugins (Preview) auto-detect ``.claude-plugin``
manifests, so the safest approach is to ship a Claude-format bundle plus
Copilot-friendly workspace fallbacks:

- ``.claude-plugin/plugin.json`` — recognized by Copilot Agent Plugins
- ``.github/prompts/<command>.prompt.md`` — slash commands available even
  without the plugin
- ``.github/agents/<agent>.agent.md`` — selected agents exposed as native
  Copilot custom agents with SDD handoffs

We keep ``${CLAUDE_PLUGIN_ROOT}`` because VS Code expands it for
Claude-format plugins.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import frontmatter, packaging, platforms
from scripts.lib.packaging import (
    EXTRAS_DIR, REPO_ROOT, SCRIPTS_DIR, SOURCE_DIR,
    BuildSummary, info, ok, warn, fail, print_summary,
)


PROFILE = platforms.get_profile(platforms.COPILOT)
PLUGIN_VERSION = "3.3.0"


# Map of workflow agents to their handoff target. We use the SDD contract
# (Brainstorm → Define → Design → Build → Ship) to drive these.
SDD_HANDOFFS: dict[str, tuple[str, str]] = {
    "brainstorm-agent": ("define-agent", "Capture requirements based on the brainstorm above."),
    "define-agent": ("design-agent", "Design the architecture for the defined feature."),
    "design-agent": ("build-agent", "Implement the design above with tests."),
    "build-agent": ("ship-agent", "Archive the feature with lessons learned."),
}


def _copy_source(output_dir: Path) -> None:
    for sub in ("agents", "commands", "skills", "kb"):
        src = SOURCE_DIR / sub
        if src.exists():
            packaging.copy_source_tree(src, output_dir / sub)
    sdd_target = output_dir / "sdd"
    sdd_target.mkdir(parents=True, exist_ok=True)
    for sub in ("templates", "architecture"):
        s = SOURCE_DIR / "sdd" / sub
        if s.exists():
            packaging.copy_source_tree(s, sdd_target / sub)
    for fname in ("_index.md", "README.md"):
        f = SOURCE_DIR / "sdd" / fname
        if f.exists():
            shutil.copy2(f, sdd_target / fname)


def _copy_extras(output_dir: Path) -> None:
    if not EXTRAS_DIR.exists():
        return
    skill_root = output_dir / "skills"
    skill_root.mkdir(parents=True, exist_ok=True)
    if (EXTRAS_DIR / "skills").exists():
        for skill_dir in (EXTRAS_DIR / "skills").iterdir():
            if skill_dir.is_dir():
                packaging.copy_source_tree(skill_dir, skill_root / skill_dir.name)
    for sub in ("hooks", "scripts"):
        s = EXTRAS_DIR / sub
        if s.exists():
            packaging.copy_source_tree(s, output_dir / sub)


def _ship_judge(output_dir: Path) -> None:
    judge_src = SCRIPTS_DIR / "judge.py"
    if not judge_src.exists():
        warn("scripts/judge.py missing — /judge will not work for Copilot users")
        return
    target = output_dir / "scripts"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(judge_src, target / "judge.py")


# ── Workspace fallback: .github/prompts ──────────────────────────────────────

def _emit_workspace_prompts(output_dir: Path) -> int:
    """Render Copilot prompt files under ``.github/prompts/`` for workspace use."""
    commands_src = output_dir / "commands"
    if not commands_src.exists():
        return 0
    target = output_dir / ".github" / "prompts"
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for md in commands_src.rglob("*.md"):
        if md.name.lower() == "readme.md":
            continue
        fm = frontmatter.parse_file(md)
        name = str(fm.data.get("name") or md.stem)
        description = str(fm.data.get("description") or f"AgentSpec command: {name}")
        body = fm.body if fm.body else md.read_text(encoding="utf-8")
        rendered = frontmatter.render(
            {
                "description": description.replace("\n", " "),
                "mode": "agent",
            },
            body,
        )
        (target / f"{name}.prompt.md").write_text(rendered, encoding="utf-8")
        count += 1
    return count


# ── Workspace fallback: .github/agents (Copilot custom agents) ───────────────

def _emit_workspace_agents(output_dir: Path) -> int:
    """Render selected Claude agents as Copilot ``.agent.md`` files."""
    agents_src = output_dir / "agents"
    if not agents_src.exists():
        return 0
    target = output_dir / ".github" / "agents"
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for md in agents_src.rglob("*.md"):
        if md.name in {"README.md", "_template.md"}:
            continue
        fm = frontmatter.parse_file(md)
        if not fm.data:
            continue
        name = str(fm.data.get("name") or md.stem)
        description = str(fm.data.get("description") or f"AgentSpec specialist: {name}")
        portable: dict[str, object] = {
            "name": name,
            "description": description.replace("\n", " ")[:980],
        }
        model = fm.data.get("model")
        if isinstance(model, str) and model:
            portable["model"] = model
        # Workflow agents get SDD handoffs so the multi-phase flow is native.
        if name in SDD_HANDOFFS:
            target_name, handoff_prompt = SDD_HANDOFFS[name]
            portable["handoffs"] = [
                {
                    "label": f"Continue with {target_name}",
                    "agent": target_name,
                    "prompt": handoff_prompt,
                    "send": False,
                }
            ]
        # Use a YAML block we render by hand because frontmatter.render does
        # not nest dicts; this keeps Copilot-specific handoff schema intact.
        body = fm.body if fm.body else md.read_text(encoding="utf-8")
        rendered = _render_copilot_agent(portable, body)
        (target / f"{name}.agent.md").write_text(rendered, encoding="utf-8")
        count += 1
    return count


def _render_copilot_agent(data: dict[str, object], body: str) -> str:
    """Render a Copilot ``.agent.md`` file with handoff support."""
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append("  -")
                    for k, v in item.items():
                        if isinstance(v, bool):
                            lines.append(f"    {k}: {str(v).lower()}")
                        else:
                            sval = str(v).replace('"', "'")
                            lines.append(f"    {k}: \"{sval}\"")
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


# ── Manifests ────────────────────────────────────────────────────────────────

def _emit_manifest(output_dir: Path) -> None:
    plugin_manifest = {
        "name": "agentspec",
        "version": PLUGIN_VERSION,
        "description": (
            "AgentSpec: Spec-Driven Data Engineering for VS Code + Copilot — "
            "58 agents, 31 commands, 24 KB domains."
        ),
        "author": {
            "name": "Luan Moreno",
            "email": "luan.moreno@owshq.com",
            "url": "https://github.com/luanmorenommaciel",
        },
        "license": "MIT",
        "repository": "https://github.com/luanmorenommaciel/agentspec",
        "skills": "skills/",
        "agents": "agents/",
        "commands": "commands/",
        "hooks": "hooks/hooks.json",
        "mcpServers": ".mcp.json",
    }
    packaging.write_json(output_dir / ".claude-plugin" / "plugin.json", plugin_manifest)


def _emit_mcp_config(output_dir: Path) -> None:
    config = {
        "mcpServers": {
            "agentspec-mcp": {
                "command": "python3",
                "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/server.py"],
                "env": {
                    "AGENTSPEC_ROOT": "${CLAUDE_PLUGIN_ROOT}",
                },
            }
        }
    }
    packaging.write_json(output_dir / ".mcp.json", config)


def _emit_install_settings(output_dir: Path) -> None:
    """Document recommended VS Code settings for workspace installs."""
    settings = {
        "chat.plugins.enabled": True,
        "chat.useCustomizationsInParentRepositories": True,
        "chat.pluginLocations": {
            "${workspaceFolder}/dist/vscode-copilot": True,
        },
    }
    target = output_dir / ".vscode" / "settings.recommended.json"
    packaging.write_json(target, settings)


def build(strict_stale: bool = True) -> BuildSummary:
    output_dir = platforms.dist_root(REPO_ROOT, PROFILE.id)
    packaging.regenerate_agent_router()
    packaging.clean_output(output_dir)
    _copy_source(output_dir)
    _copy_extras(output_dir)
    _ship_judge(output_dir)
    results = packaging.rewrite_paths(output_dir, PROFILE)
    prompts = _emit_workspace_prompts(output_dir)
    agents = _emit_workspace_agents(output_dir)
    info(f"Workspace prompts emitted: {prompts}")
    info(f"Workspace agents emitted: {agents}")
    _emit_manifest(output_dir)
    _emit_mcp_config(output_dir)
    _emit_install_settings(output_dir)
    summary = packaging.summarize(PROFILE, output_dir, results)
    if strict_stale and summary.stale_findings > 0:
        fail(f"{summary.stale_findings} stale .claude/ references in {output_dir}")
        raise SystemExit(2)
    report = {
        "platform": PROFILE.id,
        "label": PROFILE.label,
        "version": PLUGIN_VERSION,
        "skills": summary.skills,
        "agents": summary.agents,
        "commands": summary.commands,
        "kb_domains": summary.kb_domains,
        "workspace_prompts": prompts,
        "workspace_agents": agents,
        "rewrite_changes": summary.rewrite_changes,
        "stale_findings": summary.stale_findings,
        "output": str(output_dir),
    }
    packaging.write_json(output_dir / "build-report.json", report)
    print_summary(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-stale", action="store_true")
    args = parser.parse_args()
    try:
        build(strict_stale=not args.allow_stale)
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
