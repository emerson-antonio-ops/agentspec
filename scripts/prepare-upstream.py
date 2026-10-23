#!/usr/bin/env python3
"""Prepare local KB or agent content for upstream AgentSpec contribution.

Author: Emerson Antonio
Date: 2026-06-22

Usage:
  python3 scripts/prepare-upstream.py kb <domain>
  python3 scripts/prepare-upstream.py agent <agent-name>
  python3 scripts/prepare-upstream.py --project-root . kb billing
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

KB_LIMITS = {
    "quick-reference": 100,
    "concept": 150,
    "pattern": 200,
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"@[a-z0-9.-]+\.(?:internal|corp|local)\b"),
]

COUNTER_FILES = [
    "README.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "docs/concepts/README.md",
    "docs/reference/README.md",
    ".claude/kb/README.md",
    ".claude/agents/README.md",
    "tasks/backlog.md",
]


def classify_kb_file(path: Path) -> str | None:
    if path.name == "quick-reference.md":
        return "quick-reference"
    if "concepts" in path.parts:
        return "concept"
    if "patterns" in path.parts:
        return "pattern"
    return None


def validate_kb_lines(domain_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(domain_dir.rglob("*.md")):
        kind = classify_kb_file(path)
        if not kind:
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        limit = KB_LIMITS[kind]
        if lines > limit:
            errors.append(f"{path}: {lines} lines exceeds {kind} limit {limit}")
    return errors


def scan_secrets(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path}:{i}: possible secret pattern")
    return findings


def check_index_registration(domain: str, index_path: Path) -> list[str]:
    if not index_path.is_file():
        return [f"Missing registry: {index_path}"]
    text = index_path.read_text(encoding="utf-8")
    if f"\n  {domain}:" in text or f"\n  {domain}\n" in text:
        return []
    if re.search(rf"^\s+{re.escape(domain)}:\s*$", text, re.MULTILINE):
        return []
    return [f"Domain '{domain}' not found in {index_path} — register under domains:"]


def prepare_kb(domain: str, project_root: Path, agentspec_root: Path) -> int:
    src = project_root / ".claude" / "kb" / domain
    if not src.is_dir():
        print(f"error: KB domain not found: {src}", file=sys.stderr)
        return 1

    errors = validate_kb_lines(src)
    errors.extend(scan_secrets(list(src.rglob("*.md"))))

    index_path = agentspec_root / ".claude" / "kb" / "_index.yaml"
    if domain != "shared":
        errors.extend(check_index_registration(domain, index_path))

    out_dir = Path("/tmp") / f"agentspec-upstream-kb-{domain}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    dest = out_dir / ".claude" / "kb" / domain
    shutil.copytree(src, dest)

    print(f"Prepared tree: {out_dir}")
    print("\nPre-PR checklist:")
    checks = [
        ("Content generalized (no org-specific names)", "manual"),
        ("KB line limits", "pass" if not validate_kb_lines(src) else "FAIL"),
        ("Secret scan", "pass" if not scan_secrets(list(src.rglob('*.md'))) else "FAIL"),
        ("Registered in _index.yaml", "pass" if domain == "shared" or not check_index_registration(domain, index_path) else "FAIL"),
        ("Run make generate (if new agent)", "if applicable"),
        ("Run make test && make validate-all", "required"),
    ]
    for label, status in checks:
        print(f"  [{'x' if status == 'pass' else ' '}] {label}: {status}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")
        print("\nCounter files to update if NEW domain/agent:")
        for f in COUNTER_FILES:
            print(f"  - {f}")
        return 1

    print("\nCounter files to update if NEW domain:")
    for f in COUNTER_FILES:
        print(f"  - {f}")
    return 0


def prepare_agent(agent_name: str, project_root: Path) -> int:
    candidates = list((project_root / ".claude" / "agents").rglob(f"{agent_name}.md"))
    if not candidates:
        print(f"error: agent not found: {agent_name}", file=sys.stderr)
        return 1

    src = candidates[0]
    errors = scan_secrets([src])

    out_dir = Path("/tmp") / f"agentspec-upstream-agent-{agent_name}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    rel = src.relative_to(project_root / ".claude" / "agents")
    dest = out_dir / ".claude" / "agents" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    print(f"Prepared tree: {out_dir}")
    print(f"Source: {src}")
    print("\nPre-PR checklist:")
    print("  [ ] Follows _template.md and 'When NOT to Create' criteria")
    print("  [ ] make generate (router must be updated)")
    print("  [ ] make test && make validate-all")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare upstream KB/agent contribution")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--agentspec-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="kind", required=True)

    p_kb = sub.add_parser("kb", help="Prepare KB domain")
    p_kb.add_argument("domain", help="KB domain name")

    p_agent = sub.add_parser("agent", help="Prepare agent file")
    p_agent.add_argument("name", help="Agent name (filename without .md)")

    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    spec_root = args.agentspec_root.resolve()

    if args.kind == "kb":
        return prepare_kb(args.domain, root, spec_root)
    return prepare_agent(args.name, root)


if __name__ == "__main__":
    raise SystemExit(main())
