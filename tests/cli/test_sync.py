"""V16-03 `voss sync` CLI tests (R1 idempotency, R3 machine-owned docs, R4 fence)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from click.testing import CliRunner

from voss.cli import main


CONFIG_REVIEW_ON = """\
project:
  type: python
  install_command: pip install -e .
  check_command: pytest -q
  review:
    enabled: true
    reviewers: [alice, bob]
"""

CONFIG_REVIEW_OFF = """\
project:
  type: python
"""

HUMAN_PROSE = "# Project Guide\n\nKeep this human paragraph intact.\n"


def _fixture(config: str = CONFIG_REVIEW_ON, voss_md: str | None = HUMAN_PROSE) -> None:
    Path(".voss").mkdir()
    Path(".voss/config.yml").write_text(config)
    if voss_md is not None:
        Path("VOSS.md").write_text(voss_md)


def _snapshot() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    candidates = [Path("VOSS.md"), *Path(".voss").rglob("*")]
    for p in candidates:
        if p.is_file():
            files[str(p)] = p.read_bytes()
    return files


def test_sync_creates_docs_fence_manifest():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert Path(".voss/docs/cheatsheet.md").exists()
        assert Path(".voss/docs/commands.md").exists()
        assert Path(".voss/docs/review.md").exists()  # review enabled
        assert Path(".voss/sync-state.json").exists()
        assert "do not edit" in Path(".voss/docs/cheatsheet.md").read_text()
        text = Path("VOSS.md").read_text()
        assert "voss:begin id=workflow" in text
        assert HUMAN_PROSE in text  # prose outside fence preserved


def test_sync_idempotent_second_run_changes_nothing():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        first = runner.invoke(main, ["sync"])
        assert first.exit_code == 0, first.output
        before = _snapshot()
        second = runner.invoke(main, ["sync"])
        assert second.exit_code == 0, second.output  # D-15 no-changes exit 0
        assert _snapshot() == before  # R1: byte-identical files
        assert "unchanged" in second.output
        assert "0 written" in second.output


def test_generated_doc_edit_overwritten():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        doc = Path(".voss/docs/cheatsheet.md")
        pristine = doc.read_text()
        doc.write_text(pristine + "\nMANUAL EDIT\n")
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert doc.read_text() == pristine  # R3: machine-owned
        assert "MANUAL EDIT" not in doc.read_text()


def test_fence_inserted_when_voss_md_absent():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture(voss_md=None)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        text = Path("VOSS.md").read_text()
        assert "voss:begin id=workflow" in text
        assert "voss:end id=workflow" in text


def test_fence_regenerated_in_place_prose_preserved():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        # Change a project fact -> fence body must regenerate in place.
        Path(".voss/config.yml").write_text(
            CONFIG_REVIEW_ON.replace("pip install -e .", "make install")
        )
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        text = Path("VOSS.md").read_text()
        assert HUMAN_PROSE in text  # R4: prose byte-identical
        assert "make install" in text
        assert text.count("voss:begin id=workflow") == 1


def test_fence_drift_refused_nonzero_exit():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        path = Path("VOSS.md")
        drifted = re.sub(
            r"<!-- voss:hash [0-9a-f]{64} -->",
            f"<!-- voss:hash {hashlib.sha256(b'corrupt').hexdigest()} -->",
            path.read_text(),
            count=1,
        )
        path.write_text(drifted)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code != 0  # R4: HashMismatch refusal, not silent overwrite
        assert path.read_text() == drifted  # nothing clobbered


def test_dry_run_writes_nothing():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        before = _snapshot()
        result = runner.invoke(main, ["sync", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert _snapshot() == before  # D-14: zero writes
        assert not Path(".voss/docs").exists()
        assert "written" in result.output  # would-be statuses still reported


def test_review_disabled_skips_review_doc():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture(config=CONFIG_REVIEW_OFF)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert not Path(".voss/docs/review.md").exists()  # D-08
        assert "review.md" not in Path("VOSS.md").read_text()


def test_detected_facts_reported():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".voss").mkdir()
        Path("pyproject.toml").write_text("[project]\nname = 'x'\n")
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert "project.type: python (detected)" in result.output  # D-03


def test_sync_help_registered():
    runner = CliRunner()
    result = runner.invoke(main, ["sync", "--help"])
    assert result.exit_code == 0


PROMPT_FILES = (
    ".voss/prompts/reviewer_a_role.txt",
    ".voss/prompts/reviewer_b_system.txt",
    ".voss/prompts/em_system.txt",
)


def test_sync_writes_three_prompts_with_hashes():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        import json

        manifest = json.loads(Path(".voss/sync-state.json").read_text())
        for rel in PROMPT_FILES:
            assert Path(rel).exists(), rel  # .jinja suffix stripped
            body = Path(rel).read_text()
            assert manifest[rel] == hashlib.sha256(body.encode()).hexdigest()


def test_edited_prompt_skipped_with_warning_exit_zero():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        prompt = Path(PROMPT_FILES[0])
        edited = prompt.read_text() + "\nUSER EDIT\n"
        prompt.write_text(edited)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output  # warning, not failure (D-15)
        assert prompt.read_text() == edited  # R6: never silently clobbered
        assert "skipped (edited)" in result.output
        assert "reviewer_a_role.txt" in result.output + result.stderr  # warning names file


def test_force_overwrites_edited_prompt_and_updates_hash():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        prompt = Path(PROMPT_FILES[0])
        pristine = prompt.read_text()
        prompt.write_text(pristine + "\nUSER EDIT\n")
        result = runner.invoke(main, ["sync", "--force"])
        assert result.exit_code == 0, result.output
        assert prompt.read_text() == pristine  # D-16: --force overwrites
        import json

        manifest = json.loads(Path(".voss/sync-state.json").read_text())
        assert manifest[PROMPT_FILES[0]] == hashlib.sha256(pristine.encode()).hexdigest()


def test_missing_manifest_treats_prompts_as_edited():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        Path(".voss/sync-state.json").unlink()
        before = {rel: Path(rel).read_bytes() for rel in PROMPT_FILES}
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        # D-11: no hash evidence -> skip + warn, files untouched.
        assert "skipped (edited)" in result.output
        for rel in PROMPT_FILES:
            assert Path(rel).read_bytes() == before[rel]
        # --force re-adopts: hashes recorded again.
        result = runner.invoke(main, ["sync", "--force"])
        assert result.exit_code == 0, result.output
        import json

        manifest = json.loads(Path(".voss/sync-state.json").read_text())
        for rel in PROMPT_FILES:
            assert rel in manifest


def test_prompt_idempotency_two_clean_syncs():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        before = {rel: Path(rel).read_bytes() for rel in PROMPT_FILES}
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        for rel in PROMPT_FILES:
            assert Path(rel).read_bytes() == before[rel]
        assert "0 written" in result.output
