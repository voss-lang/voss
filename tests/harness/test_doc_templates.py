"""V16-02 doc + fence-body template rendering tests (R3, R4)."""
from __future__ import annotations

import dataclasses
from pathlib import Path

from voss.sync import ReviewFacts, SyncContext
from voss.template_render import render_package_template


def _ctx(**overrides) -> SyncContext:
    base = SyncContext(
        project_name="proj",
        project_root=Path("/repo/proj"),
        is_worktree=False,
        command_prefix="voss",
        voss_dir=Path("/repo/proj/.voss"),
        docs_dir=Path("/repo/proj/.voss/docs"),
        type="python",
        install_command="pip install -e .",
        check_command="pytest -q",
        tools=("ruff",),
        review=ReviewFacts(enabled=True, reviewers=("alice", "bob")),
        capabilities=("memory", "conventions", "review"),
        detected=frozenset({"type"}),
    )
    return dataclasses.replace(base, **overrides)


def _bare_ctx() -> SyncContext:
    """All optional facts absent (D-04 absent-markers)."""
    return _ctx(
        type=None,
        install_command=None,
        check_command=None,
        tools=(),
        review=ReviewFacts(),
        capabilities=(),
        detected=frozenset(),
    )


def _render(name: str, ctx: SyncContext) -> str:
    return render_package_template(
        "voss", f"templates/docs/{name}", dataclasses.asdict(ctx)
    )


DOC_TEMPLATES = ["cheatsheet.md.jinja", "commands.md.jinja", "review.md.jinja"]


class TestGeneratedHeader:
    def test_all_docs_carry_do_not_edit_header(self) -> None:
        for name in DOC_TEMPLATES:
            rendered = _render(name, _ctx())
            first_line = rendered.splitlines()[0]
            assert "do not edit" in first_line, name


class TestCheatsheet:
    def test_full_context_renders_operating_guide(self) -> None:
        out = _render("cheatsheet.md.jinja", _ctx())
        assert "proj" in out
        assert ".voss" in out
        assert "memory" in out  # active capability listed
        assert "pytest -q" in out  # check_command convention

    def test_absent_facts_omit_sections(self) -> None:
        out = _render("cheatsheet.md.jinja", _bare_ctx())
        assert "pip install" not in out
        assert "pytest" not in out


class TestCommandsLayoutAware:
    def test_repo_root_vs_worktree_invocations_differ(self) -> None:
        repo_out = _render("commands.md.jinja", _ctx(is_worktree=False))
        wt_out = _render("commands.md.jinja", _ctx(is_worktree=True))
        assert repo_out != wt_out
        assert "worktree" in wt_out
        assert "worktree" not in repo_out

    def test_capability_sections_conditional(self) -> None:
        full = _render("commands.md.jinja", _ctx())
        bare = _render("commands.md.jinja", _bare_ctx())
        assert "memory" in full
        assert "memory" not in bare


class TestReviewDoc:
    def test_enabled_renders_workflow_with_reviewers(self) -> None:
        out = _render("review.md.jinja", _ctx())
        assert "alice" in out
        assert "bob" in out

    def test_disabled_renders_disabled_notice(self) -> None:
        out = _render(
            "review.md.jinja", _ctx(review=ReviewFacts(enabled=False))
        )
        assert "alice" not in out


class TestAbsentFactsNeverRaise:
    def test_all_templates_render_bare_context(self) -> None:
        # StrictUndefined would raise UndefinedError on any unguarded field.
        for name in DOC_TEMPLATES + ["voss_md_fence.md.jinja"]:
            assert _render(name, _bare_ctx())


class TestFenceBody:
    def test_carries_r4_facts(self) -> None:
        out = _render("voss_md_fence.md.jinja", _ctx())
        assert "proj" in out
        assert "pip install -e ." in out  # install fact
        assert "python" in out  # type
        assert "cheatsheet.md" in out  # generated doc list

    def test_review_doc_link_conditional(self) -> None:
        on = _render("voss_md_fence.md.jinja", _ctx())
        off = _render(
            "voss_md_fence.md.jinja", _ctx(review=ReviewFacts(enabled=False))
        )
        assert "review.md" in on
        assert "review.md" not in off

    def test_no_fence_markers_in_body(self) -> None:
        out = _render("voss_md_fence.md.jinja", _ctx())
        for marker in ("voss:begin", "voss:hash", "voss:end"):
            assert marker not in out
