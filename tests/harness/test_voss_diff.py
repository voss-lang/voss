from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.voss_diff import render_voss_py_diff


def test_temp_voss_file_renders_generated_python_without_writing_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "simple.voss"
    source.write_text(
        'fn greet(name: string) -> string {\n    return "hello " + name\n}\n',
        encoding="utf-8",
    )

    rendered = render_voss_py_diff(source, cwd=tmp_path)

    assert "Voss source" in rendered
    assert "Generated Python" in rendered
    assert "fn greet" in rendered
    assert "def greet" in rendered
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == [
        Path("simple.voss")
    ]


def test_planner_voss_renders_from_cached_artifact_or_memory_generation() -> None:
    repo = Path(__file__).resolve().parents[2]
    source = repo / "voss" / "harness" / "agent" / "planner.voss"

    rendered = render_voss_py_diff(source, cwd=repo)

    assert "Voss source" in rendered
    assert "Generated Python" in rendered
    assert "fn plan_task" in rendered
    assert "async def plan_task" in rendered


def test_wrong_suffix_errors_cleanly(tmp_path: Path) -> None:
    source = tmp_path / "not-voss.py"
    source.write_text("print('not voss')\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.voss"):
        render_voss_py_diff(source, cwd=tmp_path)


def test_render_does_not_claim_source_map_precision(tmp_path: Path) -> None:
    source = tmp_path / "simple.voss"
    source.write_text(
        'fn greet(name: string) -> string {\n    return "hello " + name\n}\n',
        encoding="utf-8",
    )

    rendered = render_voss_py_diff(source, cwd=tmp_path).lower()

    assert "source map" not in rendered
    assert "line mapped" not in rendered
