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


def test_sync_skips_edited_managed_doc_without_force():
    """VRES-01: managed docs get the same hash-guard as prompts (D-11)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        doc = Path(".voss/docs/cheatsheet.md")
        pristine = doc.read_text()
        edited = pristine + "\nMANUAL EDIT\n"
        doc.write_text(edited)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert doc.read_text() == edited  # no silent clobber
        assert "skipped (edited)" in result.output
        assert "cheatsheet.md" in result.output + result.stderr  # warning names file
        result = runner.invoke(main, ["sync", "--force"])
        assert result.exit_code == 0, result.output
        assert doc.read_text() == pristine  # --force overwrites


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
        # Change a fact too: the refused sync must not have rewritten docs.
        Path(".voss/config.yml").write_text(
            CONFIG_REVIEW_ON.replace("pip install -e .", "make install")
        )
        before = _snapshot()
        result = runner.invoke(main, ["sync"])
        assert result.exit_code != 0  # R4: HashMismatch refusal, not silent overwrite
        assert path.read_text() == drifted  # nothing clobbered
        assert _snapshot() == before  # drift gate fires BEFORE any write
        assert "voss memory adopt --id workflow" in result.output  # working remediation


def test_review_disable_removes_stale_review_doc():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()  # review enabled
        runner.invoke(main, ["sync"])
        assert Path(".voss/docs/review.md").exists()
        Path(".voss/config.yml").write_text(CONFIG_REVIEW_OFF)
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        assert not Path(".voss/docs/review.md").exists()  # machine-owned cleanup
        assert "removed" in result.output


def test_scalar_reviewers_not_char_split():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".voss").mkdir()
        Path(".voss/config.yml").write_text(
            "project:\n  review:\n    enabled: true\n    reviewers: alice\n"
        )
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, result.output
        fence = Path("VOSS.md").read_text()
        assert "(alice)" in fence
        assert "`a`, `l`" not in Path(".voss/docs/review.md").read_text()


def test_non_utf8_prompt_clean_error():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        Path(".voss/prompts/em_system.txt").write_bytes(b"\xff\xfe garbage")
        result = runner.invoke(main, ["sync"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output  # clean ClickException, not a dump
        assert "sync failed" in result.output


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


def _snapshot_full() -> dict[str, tuple[bytes, int]]:
    """Bytes + mtime_ns per file: catches rewrite-same-bytes, not just edits."""
    files: dict[str, tuple[bytes, int]] = {}
    for p in [Path("VOSS.md"), *Path(".voss").rglob("*")]:
        if p.is_file():
            files[str(p)] = (p.read_bytes(), p.stat().st_mtime_ns)
    return files


def test_sync_check_detects_edited_managed_doc():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        doc = Path(".voss/docs/cheatsheet.md")
        doc.write_text(doc.read_text() + "\nMANUAL EDIT\n")
        result = runner.invoke(main, ["sync", "--check"])
        assert result.exit_code != 0
        assert ".voss/docs/cheatsheet.md" in result.output
        assert "edited" in result.output


def test_sync_check_clean_exits_zero():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        result = runner.invoke(main, ["sync", "--check"])
        assert result.exit_code == 0, result.output
        assert "in sync" in result.output


def test_sync_check_writes_nothing():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        doc = Path(".voss/docs/cheatsheet.md")
        doc.write_text(doc.read_text() + "\nMANUAL EDIT\n")
        before = _snapshot_full()
        result = runner.invoke(main, ["sync", "--check"])
        assert result.exit_code == 1
        assert _snapshot_full() == before  # zero writes incl. sync-state.json


def test_sync_check_detects_stale_template_output():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        # Config moves on -> rendered != recorded while disk still matches
        # recorded: stale artifacts, not hand edits.
        Path(".voss/config.yml").write_text(
            CONFIG_REVIEW_ON.replace("pip install -e .", "make install")
        )
        result = runner.invoke(main, ["sync", "--check"])
        assert result.exit_code != 0
        assert "stale" in result.output


def test_sync_check_reports_fence_drift():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        path = Path("VOSS.md")
        text = path.read_text()
        assert "pip install -e ." in text  # fence body renders install_command
        path.write_text(text.replace("pip install -e .", "FENCE EDIT"))
        result = runner.invoke(main, ["sync", "--check"])
        assert result.exit_code != 0
        assert "VOSS.md#workflow" in result.output
        assert "Traceback" not in result.output + result.stderr
        assert "memory adopt" not in result.output  # report, not adopt-prompt


def test_sync_check_rejects_force_and_dry_run():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _fixture()
        runner.invoke(main, ["sync"])
        assert runner.invoke(main, ["sync", "--check", "--force"]).exit_code != 0
        assert runner.invoke(main, ["sync", "--check", "--dry-run"]).exit_code != 0


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
