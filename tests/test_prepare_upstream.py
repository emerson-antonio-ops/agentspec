"""Tests for scripts/prepare-upstream.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

prep_path = Path(__file__).resolve().parent.parent / "scripts" / "prepare-upstream.py"
_spec = importlib.util.spec_from_file_location("prep_mod", prep_path)
assert _spec and _spec.loader
prep = importlib.util.module_from_spec(_spec)
sys.modules["prep_mod"] = prep
_spec.loader.exec_module(prep)


def test_validate_kb_lines_flags_over_limit(tmp_path: Path):
    domain = tmp_path / "billing"
    patterns = domain / "patterns"
    patterns.mkdir(parents=True)
    long_file = patterns / "big.md"
    long_file.write_text("\n".join(["line"] * 201), encoding="utf-8")

    errors = prep.validate_kb_lines(domain)
    assert any("201 lines" in e for e in errors)


def test_scan_secrets_finds_api_key():
    text_path = Path("/tmp/test-secret-scan.md")
    try:
        text_path.write_text('api_key: "sk-live-abc123"\n', encoding="utf-8")
        findings = prep.scan_secrets([text_path])
        assert findings
    finally:
        if text_path.exists():
            text_path.unlink()


def test_prepare_kb_missing_domain(tmp_path: Path):
    rc = prep.prepare_kb("nonexistent", tmp_path, tmp_path)
    assert rc == 1
