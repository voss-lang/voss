"""Item 3: single fs_edit preview-then-accept through the diff modal.

Mirrors fs_edit_many's modal contract for the single-edit path: accept writes,
reject/skip leaves the file untouched, and a renderer without show_diff_modal
(JSON/plain/None) writes after validation as before.
"""
from __future__ import annotations

from pathlib import Path

from voss.harness.tools import _line_anchor, make_toolset
from voss.harness.tui.widgets.diff_modal import DiffDecision, Hunk


class _FakeRenderer:
    def __init__(self, decisions: list[DiffDecision]) -> None:
        self._decisions = decisions
        self.last_hunks: list[Hunk] = []

    def show_diff_modal(self, hunks, *, timeout_s: float = 300.0):
        self.last_hunks = list(hunks)
        return list(self._decisions)


def _accept() -> DiffDecision:
    return DiffDecision(file="f.txt", decision="accept")


def _reject() -> DiffDecision:
    return DiffDecision(file="f.txt", decision="reject")


def _skip() -> DiffDecision:
    return DiffDecision(file="f.txt", decision="skip")


async def test_accept_writes(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("alpha\nbeta\n")
    r = _FakeRenderer([_accept()])
    tools = make_toolset(tmp_path, renderer=r)
    out = await tools["fs_edit"].invoke(path="f.txt", old="beta", new="BETA")
    assert "edited f.txt" in out
    assert (tmp_path / "f.txt").read_text() == "alpha\nBETA\n"
    # one staged hunk with the correct start line + +/- lines
    assert len(r.last_hunks) == 1
    assert r.last_hunks[0].start == 2
    assert r.last_hunks[0].lines == ["- beta", "+ BETA"]


async def test_reject_leaves_file_untouched(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("alpha\nbeta\n")
    r = _FakeRenderer([_reject()])
    tools = make_toolset(tmp_path, renderer=r)
    out = await tools["fs_edit"].invoke(path="f.txt", old="beta", new="BETA")
    assert "denied" in out
    assert (tmp_path / "f.txt").read_text() == "alpha\nbeta\n"


async def test_skip_is_strict_reject(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("alpha\n")
    r = _FakeRenderer([_skip()])
    tools = make_toolset(tmp_path, renderer=r)
    out = await tools["fs_edit"].invoke(path="f.txt", old="alpha", new="x")
    assert "denied" in out
    assert (tmp_path / "f.txt").read_text() == "alpha\n"


async def test_anchor_edit_stages_hunk(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("a\nb\nc\nd\n")
    r = _FakeRenderer([_accept()])
    tools = make_toolset(tmp_path, renderer=r)
    out = await tools["fs_edit"].invoke(
        path="f.txt", anchor=_line_anchor("b"), end_anchor=_line_anchor("c"), new="X\nY"
    )
    assert "edited f.txt" in out
    assert (tmp_path / "f.txt").read_text() == "a\nX\nY\nd\n"
    assert r.last_hunks[0].start == 2
    assert r.last_hunks[0].lines == ["- b", "- c", "+ X", "+ Y"]


async def test_no_modal_renderer_writes(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("alpha\n")
    tools = make_toolset(tmp_path, renderer=None)
    out = await tools["fs_edit"].invoke(path="f.txt", old="alpha", new="beta")
    assert "edited f.txt" in out
    assert (tmp_path / "f.txt").read_text() == "beta\n"
