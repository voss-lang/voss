"""V16-04 project prompt override loader tests (R5, D-18)."""
from __future__ import annotations

from pathlib import Path

from voss.harness.prompt_override import load_prompt
from voss.template_render import render_package_template


_RESOURCE = "templates/prompts/reviewer_a_role.txt.jinja"


def _write_project_copy(root: Path, name: str, text: str) -> None:
    prompts = root / ".voss" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / f"{name}.txt").write_text(text)


def test_no_project_copy_falls_back_byte_identical(tmp_path: Path) -> None:
    # R5: absent copy => behavior unchanged from today's package render.
    out = load_prompt("reviewer_a_role", resource=_RESOURCE, cwd=tmp_path)
    assert out == render_package_template("voss", _RESOURCE, {})


def test_project_copy_preferred_with_substitution(tmp_path: Path) -> None:
    _write_project_copy(
        tmp_path,
        "reviewer_a_role",
        "Hello ${AGENT}, project ${PROJECT}, workspace ${WORKSPACE}.\n",
    )
    out = load_prompt(
        "reviewer_a_role",
        resource=_RESOURCE,
        cwd=tmp_path,
        runtime_vars={"AGENT": "reviewer-a", "PROJECT": "proj", "WORKSPACE": "/w"},
    )
    assert out == "Hello reviewer-a, project proj, workspace /w.\n"


def test_placeholders_without_vars_stay_literal(tmp_path: Path) -> None:
    # str.replace only (D-18): no vars supplied -> literals pass through,
    # and nothing resembling Jinja/StrictUndefined can detonate.
    _write_project_copy(tmp_path, "reviewer_a_role", "Keep ${AGENT} and {{ weird }}.\n")
    out = load_prompt("reviewer_a_role", resource=_RESOURCE, cwd=tmp_path)
    assert out == "Keep ${AGENT} and {{ weird }}.\n"


def test_unknown_vars_only_replace_named_placeholders(tmp_path: Path) -> None:
    _write_project_copy(tmp_path, "reviewer_a_role", "${AGENT} / ${OTHER}\n")
    out = load_prompt(
        "reviewer_a_role",
        resource=_RESOURCE,
        cwd=tmp_path,
        runtime_vars={"AGENT": "em"},
    )
    assert out == "em / ${OTHER}\n"
