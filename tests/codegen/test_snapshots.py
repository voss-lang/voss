from __future__ import annotations

import ast
import re
from pathlib import Path

from tests.codegen.helpers import fake_analysis
from tests.codegen.test_examples import _compile_example, _write_support_manifest


SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"


def _generated_sources(tmp_path: Path) -> dict[str, str]:
    support_manifest = _write_support_manifest(tmp_path)
    return {
        "classify": _compile_example(tmp_path, "classify").source,
        "support": _compile_example(
            tmp_path, "support", analysis=fake_analysis(support_manifest)
        ).source,
        "research": _compile_example(tmp_path, "research").source,
    }


def _assert_starts_with_imports(source: str) -> None:
    lines = source.splitlines()
    assert lines, "snapshot must not be empty"
    first = lines[0]
    if first.startswith("# Generated"):
        first = lines[1]
    assert first.startswith(("import ", "from ")), (
        "snapshot must start with imports or a generated-source comment followed by imports"
    )


def _assert_no_compiler_imports(source: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "voss" and not alias.name.startswith("voss.")
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "voss" and not node.module.startswith("voss.")


def _assert_readable_snapshot(name: str, source: str) -> None:
    ast.parse(source, filename=f"{name}.py")
    _assert_starts_with_imports(source)
    assert ";" not in source
    assert not re.search(r"(?m)^[ \t]*if\b[^\n]*:[ \t]*return\b", source), (
        "snapshot contains one-line if ...: return"
    )
    assert "from voss " not in source
    assert "import voss " not in source
    _assert_no_compiler_imports(source)
    assert source.endswith("\n") and not source.endswith("\n\n")


def test_generated_example_sources_match_snapshots(tmp_path):
    generated = _generated_sources(tmp_path)

    for name, source in generated.items():
        snapshot_path = SNAPSHOTS / f"{name}.py"
        snapshot = snapshot_path.read_text()
        assert source == snapshot


def test_snapshots_are_readable_and_parseable():
    for name in ("classify", "support", "research"):
        snapshot = (SNAPSHOTS / f"{name}.py").read_text()
        _assert_readable_snapshot(name, snapshot)


def test_snapshots_include_async_main_for_top_level_statements():
    for name in ("classify", "research"):
        snapshot = (SNAPSHOTS / f"{name}.py").read_text()
        assert "async def main():" in snapshot

    support = (SNAPSHOTS / "support.py").read_text()
    assert "async def main():" not in support
