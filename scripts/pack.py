#!/usr/bin/env python3
"""AgentSpec pack manager — install, list, remove, apply org-wide agent/KB packs.

Author: Emerson Antonio
Date: 2026-06-22

Usage:
  python3 scripts/pack.py install <path-or-git-url>
  python3 scripts/pack.py list
  python3 scripts/pack.py remove <pack-name>
  python3 scripts/pack.py apply <pack-name>
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_NAME = "agentspec-pack.yaml"
LOCKFILE_NAME = ".lock.yaml"
PACKS_DIR = Path(".claude/packs")


@dataclass(frozen=True, slots=True)
class PackManifest:
    name: str
    version: str
    description: str
    min_agentspec: str | None = None
    author: str | None = None
    repository: str | None = None


@dataclass(frozen=True, slots=True)
class ApplyResult:
    copied: tuple[str, ...]
    skipped: tuple[str, ...]


def _require_yaml() -> None:
    if yaml is None:
        print("error: PyYAML required — pip install pyyaml", file=sys.stderr)
        sys.exit(2)


def _load_yaml(path: Path) -> dict:
    _require_yaml()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def _save_yaml(path: Path, data: dict) -> None:
    _require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def parse_manifest(pack_root: Path) -> PackManifest:
    manifest_path = pack_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError(f"Missing {MANIFEST_NAME} in {pack_root}")

    raw = _load_yaml(manifest_path)
    name = raw.get("name")
    version = raw.get("version")
    description = raw.get("description")
    if not name or not version or not description:
        raise ValueError(f"{manifest_path}: name, version, and description are required")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", str(name)):
        raise ValueError(f"Invalid pack name: {name}")

    return PackManifest(
        name=str(name),
        version=str(version),
        description=str(description),
        min_agentspec=str(raw["min_agentspec"]) if raw.get("min_agentspec") else None,
        author=str(raw["author"]) if raw.get("author") else None,
        repository=str(raw["repository"]) if raw.get("repository") else None,
    )


def lockfile_path(project_root: Path) -> Path:
    return project_root / PACKS_DIR / LOCKFILE_NAME


def read_lockfile(project_root: Path) -> dict:
    path = lockfile_path(project_root)
    if not path.is_file():
        return {"packs": {}}
    data = _load_yaml(path)
    if not isinstance(data, dict):
        return {"packs": {}}
    data.setdefault("packs", {})
    return data


def write_lock_entry(
    project_root: Path,
    manifest: PackManifest,
    source: str,
    staged_path: Path,
) -> None:
    lock = read_lockfile(project_root)
    lock["packs"][manifest.name] = {
        "version": manifest.version,
        "source": source,
        "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "staged_path": str(staged_path.relative_to(project_root)),
    }
    _save_yaml(lockfile_path(project_root), lock)


def remove_lock_entry(project_root: Path, pack_name: str) -> None:
    lock = read_lockfile(project_root)
    lock.get("packs", {}).pop(pack_name, None)
    _save_yaml(lockfile_path(project_root), lock)


def is_git_source(source: str) -> bool:
    return (
        source.startswith("git@")
        or source.startswith("https://")
        or source.startswith("http://")
        or source.endswith(".git")
    )


def fetch_pack_source(source: str, dest: Path) -> None:
    if source.startswith("/") or source.startswith("."):
        src = Path(source).resolve()
        if not src.is_dir():
            raise ValueError(f"Local pack path not found: {src}")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return

    if is_git_source(source):
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", source, str(dest)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {proc.stderr.strip()}")
        return

    raise ValueError(f"Unsupported pack source: {source}")


def apply_pack(staged_root: Path, project_root: Path) -> ApplyResult:
    copied: list[str] = []
    skipped: list[str] = []

    agents_dir = staged_root / "agents" / "custom"
    if agents_dir.is_dir():
        for src in sorted(agents_dir.glob("*.md")):
            dest = project_root / ".claude" / "agents" / "custom" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            rel = str(dest.relative_to(project_root))
            if dest.exists():
                skipped.append(rel)
                continue
            shutil.copy2(src, dest)
            copied.append(rel)

    kb_root = staged_root / "kb"
    if kb_root.is_dir():
        for src in sorted(kb_root.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(kb_root)
            dest = project_root / ".claude" / "kb" / rel
            dest_rel = str(dest.relative_to(project_root))
            if dest.exists():
                skipped.append(dest_rel)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(dest_rel)

    return ApplyResult(copied=tuple(copied), skipped=tuple(skipped))


def cmd_install(source: str, project_root: Path, apply: bool = True) -> int:
    _require_yaml()
    with tempfile.TemporaryDirectory(prefix="agentspec-pack-") as tmp:
        tmp_path = Path(tmp) / "pack"
        fetch_pack_source(source, tmp_path)
        manifest = parse_manifest(tmp_path)

        if manifest.min_agentspec:
            print(f"note: pack requires AgentSpec >= {manifest.min_agentspec}")

        stage_dest = project_root / PACKS_DIR / manifest.name
        if stage_dest.exists():
            shutil.rmtree(stage_dest)
        stage_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tmp_path, stage_dest)

        write_lock_entry(project_root, manifest, source, stage_dest)
        print(f"staged: {stage_dest.relative_to(project_root)}")

        if apply:
            result = apply_pack(stage_dest, project_root)
            print(f"applied: {len(result.copied)} copied, {len(result.skipped)} skipped (local-wins)")
            for path in result.copied:
                print(f"  + {path}")
            for path in result.skipped:
                print(f"  ~ skip {path}")

    return 0


def cmd_list(project_root: Path) -> int:
    _require_yaml()
    lock = read_lockfile(project_root)
    packs = lock.get("packs", {})
    if not packs:
        print("No packs installed.")
        return 0
    for name, meta in sorted(packs.items()):
        version = meta.get("version", "?")
        source = meta.get("source", "?")
        print(f"{name}@{version}  ({source})")
    return 0


def cmd_remove(pack_name: str, project_root: Path) -> int:
    _require_yaml()
    lock = read_lockfile(project_root)
    if pack_name not in lock.get("packs", {}):
        print(f"error: pack not installed: {pack_name}", file=sys.stderr)
        return 1

    staged = project_root / PACKS_DIR / pack_name
    if staged.is_dir():
        shutil.rmtree(staged)
    remove_lock_entry(project_root, pack_name)
    print(f"removed staged pack: {pack_name}")
    print("note: files already applied to .claude/agents/ and .claude/kb/ are not deleted")
    return 0


def cmd_apply(pack_name: str, project_root: Path) -> int:
    staged = project_root / PACKS_DIR / pack_name
    if not staged.is_dir():
        print(f"error: staged pack not found: {staged}", file=sys.stderr)
        return 1
    result = apply_pack(staged, project_root)
    print(f"applied: {len(result.copied)} copied, {len(result.skipped)} skipped")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentSpec pack manager")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Stage and apply a pack")
    p_install.add_argument("source", help="Local path or git URL")

    sub.add_parser("list", help="List installed packs")

    p_remove = sub.add_parser("remove", help="Remove staged pack")
    p_remove.add_argument("name", help="Pack name")

    p_apply = sub.add_parser("apply", help="Re-apply staged pack to workspace")
    p_apply.add_argument("name", help="Pack name")

    args = parser.parse_args(argv)
    root = args.project_root.resolve()

    try:
        if args.command == "install":
            return cmd_install(args.source, root)
        if args.command == "list":
            return cmd_list(root)
        if args.command == "remove":
            return cmd_remove(args.name, root)
        if args.command == "apply":
            return cmd_apply(args.name, root)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
