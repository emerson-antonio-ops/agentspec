#!/usr/bin/env python3
"""Build the Claude Code distribution under ``dist/claude/``.

Author: Emerson Antonio
Date: 2026-06-17

This builder mirrors the historical ``build-plugin.sh`` behavior but uses the
shared Python build core under ``scripts/lib/``. The legacy ``plugin/``
directory continues to be produced by ``build-plugin.sh`` for backwards
compatibility; ``dist/claude/`` is the new authoritative artifact.

Steps:
1. Regenerate ``agent-router`` SKILL.md and routing.json.
2. Copy ``.claude/`` → ``dist/claude/`` (drops template/workspace dirs).
3. Merge ``plugin-extras/`` (hooks, scripts, plugin-only skills).
4. Copy ``scripts/judge.py`` so the ``/judge`` command works end-to-end.
5. Rewrite ``.claude/`` references to ``${CLAUDE_PLUGIN_ROOT}/``.
6. Write the Claude plugin manifest + marketplace manifest.
7. Summarize and emit ``build-report.json`` for CI consumption.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from scripts.lib import packaging, platforms
from scripts.lib.packaging import (
    EXTRAS_DIR, REPO_ROOT, SCRIPTS_DIR, SOURCE_DIR,
    BuildSummary, info, ok, warn, fail, print_summary,
)


PROFILE = platforms.get_profile(platforms.CLAUDE)
META = platforms.PROJECT_METADATA
PLUGIN_VERSION = META.version


def _copy_source(output_dir: Path) -> None:
    """Copy ``.claude/`` content into the dist tree."""
    info(f"Copying .claude/ → {output_dir}")
    # We copy individual subtrees instead of the whole .claude/ so we can drop
    # workspace-only directories before any rewriting.
    for sub in ("agents", "commands", "skills", "kb"):
        src = SOURCE_DIR / sub
        if src.exists():
            packaging.copy_source_tree(src, output_dir / sub)
    # SDD: templates + architecture only (features/reports/archive belong to
    # the user workspace and are excluded).
    sdd_target = output_dir / "sdd"
    sdd_target.mkdir(parents=True, exist_ok=True)
    for sub in ("templates", "architecture"):
        src = SOURCE_DIR / "sdd" / sub
        if src.exists():
            packaging.copy_source_tree(src, sdd_target / sub)
    for fname in ("_index.md", "README.md"):
        f = SOURCE_DIR / "sdd" / fname
        if f.exists():
            shutil.copy2(f, sdd_target / fname)


def _copy_extras(output_dir: Path) -> None:
    """Merge plugin-only content from ``plugin-extras/``."""
    if not EXTRAS_DIR.exists():
        return
    info("Merging plugin-extras/")
    extras_skills = EXTRAS_DIR / "skills"
    if extras_skills.exists():
        target_skills = output_dir / "skills"
        target_skills.mkdir(parents=True, exist_ok=True)
        for skill_dir in extras_skills.iterdir():
            if skill_dir.is_dir():
                packaging.copy_source_tree(skill_dir, target_skills / skill_dir.name)
    for sub in ("hooks", "scripts"):
        src = EXTRAS_DIR / sub
        if src.exists():
            packaging.copy_source_tree(src, output_dir / sub)


def _cleanup_scaffolding(output_dir: Path) -> None:
    """Drop scaffolding files that confuse loaders."""
    for stale in (output_dir / "agents").rglob("_template.md"):
        stale.unlink()


def _emit_manifest(output_dir: Path) -> None:
    """Write the canonical Claude plugin manifest."""
    manifest_dir = output_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    plugin_manifest = {
        "name": META.name,
        "version": META.version,
        "description": META.description_with_credit(META.description_short),
        "author": META.author(),
        "contributors": META.contributors(),
        "license": META.license,
        "repository": META.repository,
        "homepage": META.homepage,
        "upstream": META.upstream_repository,
        "keywords": list(META.keywords),
    }
    packaging.write_json(manifest_dir / "plugin.json", plugin_manifest)
    marketplace = {
        "name": META.name,
        "metadata": {"description": plugin_manifest["description"]},
        "owner": {
            "name": META.author_name,
            "email": META.author_email,
        },
        "plugins": [
            {
                "name": META.name,
                "version": META.version,
                "description": plugin_manifest["description"],
                "source": "./",
                "keywords": list(META.keywords[:7]),
            }
        ],
    }
    packaging.write_json(manifest_dir / "marketplace.json", marketplace)
    ok("Manifest emitted")


def _emit_report(output_dir: Path, summary: BuildSummary) -> None:
    """Write a machine-readable build report next to the artifacts."""
    report = {
        "platform": PROFILE.id,
        "label": PROFILE.label,
        "version": PLUGIN_VERSION,
        "agents": summary.agents,
        "commands": summary.commands,
        "skills": summary.skills,
        "kb_domains": summary.kb_domains,
        "rewrite_changes": summary.rewrite_changes,
        "stale_findings": summary.stale_findings,
        "output": str(output_dir),
    }
    packaging.write_json(output_dir / "build-report.json", report)


def build(check_router: bool = False, strict_stale: bool = True) -> BuildSummary:
    """Run the Claude target build end-to-end."""
    output_dir = platforms.dist_root(REPO_ROOT, PROFILE.id)
    packaging.regenerate_agent_router(check_only=check_router)
    packaging.clean_output(output_dir)
    _copy_source(output_dir)
    _copy_extras(output_dir)
    packaging.ship_judge_assets(output_dir)
    _cleanup_scaffolding(output_dir)
    results = packaging.rewrite_paths(output_dir, PROFILE)
    _emit_manifest(output_dir)
    summary = packaging.summarize(PROFILE, output_dir, results)
    if strict_stale and summary.stale_findings > 0:
        fail(f"{summary.stale_findings} stale .claude/ references in {output_dir}")
        # Surface the first few so contributors can fix them quickly.
        from scripts.lib.path_rewrite import stale_references
        for path, line_no, line in stale_references(output_dir, PROFILE)[:5]:
            warn(f"  {path}:{line_no} → {line.strip()}")
        raise SystemExit(2)
    _emit_report(output_dir, summary)
    print_summary(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-router-check", action="store_true",
                        help="Skip agent-router drift check.")
    parser.add_argument("--allow-stale", action="store_true",
                        help="Do not fail if stale .claude/ references remain.")
    args = parser.parse_args()
    try:
        build(check_router=False, strict_stale=not args.allow_stale)
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
