"""T2-05 / PAR-04: fs_read_many bundled multi-file read primitive.

SPEC PAR-04 acceptance fixtures (a/b/c/d) + edge cases:
- three readable files in request order (a)
- partial result with inline error for missing slot (b)
- duplicate paths not deduped (c)
- empty paths sentinel (d)
- 30KB truncation boundaries (==30720, ==30721, >>30720)
- jail violation inline error (D-14)
- directory inline error
- binary file inline error
- registration with is_mutating=False
- fs_read coexistence
- deterministic output
- exact bundle format
"""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.tools import make_toolset


async def _call(tools, **kwargs) -> str:
    return await tools["fs_read_many"].invoke(**kwargs)


# ---------------------------------------------------------------------------
# Acceptance fixture a — 3 readable files, request order, exact format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_readable_bundle_format(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha\n")
    (tmp_path / "b.txt").write_text("beta\n")
    (tmp_path / "c.txt").write_text("gamma\n")
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["a.txt", "b.txt", "c.txt"])
    # Each section: "=== {path} ===\n{body}\n"; sections joined by "\n".
    # body for "a.txt" is "alpha\n", so section = "=== a.txt ===\nalpha\n\n"
    # Final bundle: sec0 + "\n" + sec1 + "\n" + sec2
    expected = (
        "=== a.txt ===\nalpha\n\n"
        "\n=== b.txt ===\nbeta\n\n"
        "\n=== c.txt ===\ngamma\n\n"
    )
    assert result == expected


# ---------------------------------------------------------------------------
# Acceptance fixture b — partial result, inline error for missing slot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_slot_inline_error(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("aaa\n")
    (tmp_path / "c.txt").write_text("ccc\n")
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["a.txt", "missing.txt", "c.txt"])
    assert "<error: not found: missing.txt>" in result
    assert "aaa" in result
    assert "ccc" in result
    # call did not raise — we got a 3-section bundle
    assert result.count("=== ") == 3


# ---------------------------------------------------------------------------
# Acceptance fixture c — duplicate paths not deduped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_paths_no_dedup(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello\n")
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["a.txt", "a.txt"])
    assert result.count("=== a.txt ===") == 2
    assert result.count("hello") == 2


# ---------------------------------------------------------------------------
# Acceptance fixture d — empty paths sentinel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_paths_returns_sentinel(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=[])
    assert result == "<no paths requested>"


# ---------------------------------------------------------------------------
# 30KB truncation boundaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_truncation_30kb(tmp_path: Path) -> None:
    content = "x" * 50000
    (tmp_path / "big.txt").write_text(content)
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["big.txt"])
    assert "<truncated, total 50000 bytes>" in result
    assert "x" * 30720 in result


@pytest.mark.asyncio
async def test_exactly_30kb_not_truncated(tmp_path: Path) -> None:
    content = "y" * 30720
    (tmp_path / "exact.txt").write_text(content)
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["exact.txt"])
    assert "<truncated" not in result
    assert "y" * 30720 in result


@pytest.mark.asyncio
async def test_just_over_30kb_truncated(tmp_path: Path) -> None:
    content = "z" * 30721
    (tmp_path / "over.txt").write_text(content)
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["over.txt"])
    assert "<truncated, total 30721 bytes>" in result


# ---------------------------------------------------------------------------
# Jail violation — inline error, other slots still readable (D-14)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jail_violation_inline_error(tmp_path: Path) -> None:
    (tmp_path / "valid.txt").write_text("ok\n")
    (tmp_path / "other.txt").write_text("also ok\n")
    tools = make_toolset(tmp_path)
    result = await _call(
        tools, paths=["valid.txt", "../../etc/passwd", "other.txt"]
    )
    assert "<error: path outside cwd: ../../etc/passwd>" in result
    assert "ok" in result
    assert "also ok" in result
    assert result.count("=== ") == 3


# ---------------------------------------------------------------------------
# Directory inline error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_directory_inline_error(tmp_path: Path) -> None:
    (tmp_path / "subdir").mkdir()
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["subdir"])
    assert "<error: is a directory: subdir>" in result


# ---------------------------------------------------------------------------
# Binary file inline error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_binary_file_inline_error(tmp_path: Path) -> None:
    (tmp_path / "bin.dat").write_bytes(b"\xff\xfe\x00\x01\x02")
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["bin.dat"])
    assert "<error: binary file: bin.dat>" in result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_registered_with_is_mutating_false(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)
    assert "fs_read_many" in tools
    assert tools["fs_read_many"].is_mutating is False


def test_fs_read_still_registered(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)
    assert "fs_read" in tools
    assert tools["fs_read"].is_mutating is False


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_output(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("one\n")
    (tmp_path / "y.txt").write_text("two\n")
    tools = make_toolset(tmp_path)
    result1 = await _call(tools, paths=["x.txt", "y.txt"])
    result2 = await _call(tools, paths=["x.txt", "y.txt"])
    assert result1 == result2


# ---------------------------------------------------------------------------
# Exact bundle format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bundle_format_exact(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("AAA\n")
    (tmp_path / "b.txt").write_text("BBB\n")
    tools = make_toolset(tmp_path)
    result = await _call(tools, paths=["a.txt", "b.txt"])
    assert result.startswith("=== a.txt ===\n")
    assert "\n=== b.txt ===\n" in result
