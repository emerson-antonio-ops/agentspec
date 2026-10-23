#!/usr/bin/env python3
"""Orchestrate every AgentSpec build target.

Author: Emerson Antonio
Date: 2026-06-17

Usage::

    python3 scripts/build_all.py                # build all targets
    python3 scripts/build_all.py --only claude  # build a single target
    python3 scripts/build_all.py --no-mcp       # build everything except MCP
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import build_claude, build_copilot, build_cursor, build_mcp
from scripts.lib import platforms
from scripts.lib.packaging import fail, info, ok


TARGETS = {
    platforms.CLAUDE: build_claude.build,
    platforms.CURSOR: build_cursor.build,
    platforms.COPILOT: build_copilot.build,
    platforms.MCP: build_mcp.build,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only", choices=sorted(TARGETS),
        help="Build a single target instead of all.",
    )
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--no-cursor", action="store_true")
    parser.add_argument("--no-copilot", action="store_true")
    parser.add_argument("--no-mcp", action="store_true")
    parser.add_argument("--allow-stale", action="store_true")
    args = parser.parse_args()

    selected: list[str]
    if args.only:
        selected = [args.only]
    else:
        skip = set()
        if args.no_claude:
            skip.add(platforms.CLAUDE)
        if args.no_cursor:
            skip.add(platforms.CURSOR)
        if args.no_copilot:
            skip.add(platforms.COPILOT)
        if args.no_mcp:
            skip.add(platforms.MCP)
        selected = [t for t in TARGETS if t not in skip]

    failures: list[tuple[str, str]] = []
    for target in selected:
        info(f"Building target: {target}")
        try:
            TARGETS[target](strict_stale=not args.allow_stale)
        except SystemExit as exc:
            failures.append((target, f"exit {exc.code}"))
        except Exception as exc:  # noqa: BLE001 — surfaces unexpected errors
            failures.append((target, str(exc)))

    print("")
    if failures:
        fail("Multi-target build had failures:")
        for target, reason in failures:
            fail(f"  - {target}: {reason}")
        return 1

    ok(f"All {len(selected)} targets built successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
