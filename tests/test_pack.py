"""Tests for scripts/pack.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

FIXTURE_PACK = Path(__file__).resolve().parent / "fixtures" / "pack-billing"


def _load_pack():
    spec_path = Path(__file__).resolve().parent.parent / "scripts" / "pack.py"
    spec = importlib.util.spec_from_file_location("pack_mod", spec_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["pack_mod"] = module
    spec.loader.exec_module(module)
    return module


pack_mod = _load_pack()


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".claude").mkdir()
    return tmp_path


def test_parse_manifest(fixture_path: Path = FIXTURE_PACK):
    manifest = pack_mod.parse_manifest(fixture_path)
    assert manifest.name == "billing-pack"
    assert manifest.version == "0.1.0"


def test_install_stages_and_applies(project_root: Path):
    rc = pack_mod.cmd_install(str(FIXTURE_PACK), project_root)
    assert rc == 0

    staged = project_root / ".claude" / "packs" / "billing-pack"
    assert staged.is_dir()
    assert (staged / "agentspec-pack.yaml").is_file()

    agent = project_root / ".claude" / "agents" / "custom" / "billing-specialist.md"
    kb = project_root / ".claude" / "kb" / "billing" / "index.md"
    assert agent.is_file()
    assert kb.is_file()

    lock = pack_mod.read_lockfile(project_root)
    assert "billing-pack" in lock["packs"]


def test_apply_skips_local_wins(project_root: Path):
    pack_mod.cmd_install(str(FIXTURE_PACK), project_root)

    local_kb = project_root / ".claude" / "kb" / "billing" / "index.md"
    local_kb.write_text("# Local wins\n", encoding="utf-8")

    staged = project_root / ".claude" / "packs" / "billing-pack"
    result = pack_mod.apply_pack(staged, project_root)
    assert "index.md" in str(result.skipped) or any("billing" in s for s in result.skipped)
    assert local_kb.read_text(encoding="utf-8") == "# Local wins\n"


def test_list_and_remove(project_root: Path):
    pack_mod.cmd_install(str(FIXTURE_PACK), project_root)
    assert pack_mod.cmd_list(project_root) == 0

    assert pack_mod.cmd_remove("billing-pack", project_root) == 0
    assert not (project_root / ".claude" / "packs" / "billing-pack").exists()
    # Applied agent remains
    assert (project_root / ".claude" / "agents" / "custom" / "billing-specialist.md").is_file()
