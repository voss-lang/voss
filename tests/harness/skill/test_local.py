from __future__ import annotations

import pytest
from click.testing import CliRunner

from voss.harness import local_sources
from voss.harness.cli import _ambient_route, _expand_local_skill, skills_cmd
from voss.harness.skill.local import discover
from voss.harness.skill_registry import default_skill_registry
from voss.harness.tools import make_toolset


def skill(root, folder="review", description="Review code"):
    path = root / folder / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {folder}\ndescription: {description}\n---\nRead the diff before reviewing.\n")
    return path


def test_voss_skills_override_upstream_and_project_overrides_user(tmp_path):
    skill(local_sources.user_home() / ".claude/skills", description="Claude user")
    skill(local_sources.codex_home() / "skills", description="Codex user")
    skill(tmp_path / ".agents/skills", description="Project")
    assert discover(tmp_path)["review"].description == "Project"
    skill(tmp_path / ".voss/skills", description="Voss")
    assert discover(tmp_path)["review"].description == "Voss"


def test_nested_project_and_symlinked_skills(tmp_path):
    (tmp_path / ".git").mkdir()
    path = skill(tmp_path / ".agents/skills")
    cwd = tmp_path / "src"
    cwd.mkdir()
    external = skill(tmp_path / "installed", "explain")
    root = local_sources.codex_home() / "skills"
    root.mkdir(parents=True)
    (root / "explain").symlink_to(external.parent)
    found = discover(cwd)
    assert found["review"].path == path
    assert found["explain"].path == external


def test_disabled_codex_skill_is_not_registered(tmp_path):
    path = skill(local_sources.codex_home() / "skills")
    (local_sources.codex_home() / "config.toml").write_text(
        f"[[skills.config]]\npath = '{path}'\nenabled = false\n"
    )
    assert "review" not in discover(tmp_path)
    assert default_skill_registry(tmp_path).get("review") is None


@pytest.mark.asyncio
async def test_skill_tool_reads_instructions_and_references_without_escaping(tmp_path):
    path = skill(local_sources.codex_home() / "skills")
    (path.parent / "reference.md").write_text("Reference content")
    (path.parent / "outside").symlink_to(tmp_path)
    (tmp_path / "private.txt").write_text("synthetic-private")
    tools = make_toolset(tmp_path, background_indexing=False)
    reader = tools["skill_read"]
    assert "review: Review code" in reader.description
    assert not reader.is_mutating
    assert "Read the diff" in await reader.invoke(name="review")
    assert await reader.invoke(name="review", path="reference.md") == "Reference content"
    assert "<error:" in await reader.invoke(name="review", path="outside/private.txt")
    assert "<error:" in await reader.invoke(name="review", path="../../private.txt")


@pytest.mark.parametrize("command", ["/skill review the changes", "$review the changes"])
def test_explicit_local_skill_enters_tool_enabled_run(tmp_path, command):
    skill(tmp_path / ".agents/skills")
    registry = default_skill_registry(tmp_path)
    expanded = _expand_local_skill(command, registry)
    assert "skill_read" in expanded
    assert "review" in expanded
    assert "the changes" in expanded
    assert _ambient_route(expanded) == "voss_run"


def test_skill_inventory_includes_local_skills_without_building_tools(tmp_path, monkeypatch):
    skill(tmp_path / ".agents/skills")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("voss.harness.cli.make_toolset", lambda *a, **kw: pytest.fail("inventory started tools"))
    result = CliRunner().invoke(skills_cmd)
    assert result.exit_code == 0, result.output
    assert "review" in result.output
    assert "local" in result.output
