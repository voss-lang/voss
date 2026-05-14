"""E2E for `voss memory <vacuum|adopt|size>`.

vacuum + size require an existing .voss/memory/ tree; we seed it directly
because `voss do` does not create memory entries today. adopt requires a
VOSS.md fence we control end-to-end.
"""
from __future__ import annotations

from pathlib import Path

from .runner import CliRunner


def _seed_memory_tree(project: Path) -> Path:
    mem = project / ".voss" / "memory"
    for sub in ("turns", "ledgers", "decisions", "conventions", "notes", "chroma", ".locks"):
        (mem / sub).mkdir(parents=True, exist_ok=True)
    # Seed a few small files so `size` reports non-zero.
    (mem / "turns" / "t1.json").write_text('{"role": "user", "content": "hello"}')
    (mem / "decisions" / "d1.md").write_text("# Decision\n\nKeep tests fast.\n")
    return mem


def test_memory_size_reports_per_source(cli_runner: CliRunner) -> None:
    _seed_memory_tree(cli_runner.project_root)
    r = cli_runner.run("memory", "size")
    assert r.returncode == 0, r.output
    for source in ("turns", "ledgers", "decisions", "conventions", "notes"):
        assert f"{source}:" in r.stdout, f"missing source {source!r}"
    assert "TOTAL:" in r.stdout, r.stdout


def test_memory_size_with_no_store_exits_1(cli_runner: CliRunner) -> None:
    r = cli_runner.run("memory", "size")
    assert r.returncode == 1, r.output
    assert "no memory store" in r.stderr.lower(), r.stderr


def test_memory_vacuum_reports_reclaimed(cli_runner: CliRunner) -> None:
    _seed_memory_tree(cli_runner.project_root)
    r = cli_runner.run("memory", "vacuum")
    assert r.returncode == 0, r.output
    assert "reclaimed:" in r.stdout, r.stdout
    assert "bytes" in r.stdout, r.stdout


def test_memory_vacuum_with_no_store_exits_1(cli_runner: CliRunner) -> None:
    r = cli_runner.run("memory", "vacuum")
    assert r.returncode == 1, r.output


def test_memory_adopt_unknown_id_exits_1(cli_runner: CliRunner) -> None:
    r = cli_runner.run("memory", "adopt", "--id", "nonexistent-fence")
    assert r.returncode == 1, r.output
    assert "not found" in r.stderr.lower(), r.stderr
