"""Byte-parity guard for prompt user-messages migrated to Jinja (Phase 1).

Each migrated user-message template must render byte-identical to the original
inline f-string it replaced. The `_old_*` functions below are frozen copies of
that pre-migration logic; the assertions compare them against the live template
output. If a template edit changes the bytes, these tests fail.
"""
from __future__ import annotations

import pytest

from voss.template_render import render_package_template
from voss.harness.board.reviewer_a import _reviewer_a_task


# --- frozen pre-migration reference implementations -------------------------

def _old_reviewer_b(
    original_idea, acceptance, artifact_text, file_diff, a_verification, repo_context
):
    user_msg = (
        f"## Original Idea\n{original_idea}\n\n"
        f"## Acceptance Criteria\n{acceptance}\n\n"
        f"## Artifact\n{artifact_text}\n\n"
        f"## File Diff\n{file_diff}\n\n"
        f"## Reviewer-A Verification Summary\n{a_verification}\n"
    )
    if repo_context:
        user_msg += (
            "\n## Repo Context (current source of files touched by the diff)\n"
            f"{repo_context}\n"
        )
    return user_msg


def _old_em(idea, snapshot, roster_descriptions):
    roster_text = ""
    if roster_descriptions:
        lines = [f"  - {role}: {desc}" for role, desc in roster_descriptions.items()]
        roster_text = "\n## Available Roster Roles\n" + "\n".join(lines) + "\n"
    return (
        f"## Original Idea\n{idea}\n\n"
        f"## Current Board Snapshot\n{snapshot}\n"
        f"{roster_text}"
    )


def _old_note(stem, session_id, ts, text):
    return (
        "---\n"
        f"id: {stem}\n"
        f"related_session: {session_id}\n"
        f"created_at: {ts}\n"
        "---\n\n"
        f"{text}\n"
    )


def _old_convention(stem, session_id, evidence_turn_idx, confidence, ts, statement, quote):
    return (
        "---\n"
        f"id: {stem}\n"
        "status: active\n"
        f"related_session: {session_id}\n"
        f"evidence_turn_idx: {evidence_turn_idx}\n"
        f"confidence: {confidence:.2f}\n"
        f"created_at: {ts}\n"
        "---\n\n"
        f"# {statement}\n\n"
        f"## Evidence\n\n> {quote}\n"
    )


def _new_note(stem, session_id, ts, text):
    return render_package_template(
        "voss",
        "templates/memory/note.md.jinja",
        {"id": stem, "session_id": session_id, "created_at": ts, "text": text},
    )


def _new_convention(stem, session_id, evidence_turn_idx, confidence, ts, statement, quote):
    return render_package_template(
        "voss",
        "templates/memory/convention.md.jinja",
        {
            "id": stem,
            "session_id": session_id,
            "evidence_turn_idx": evidence_turn_idx,
            "confidence": f"{confidence:.2f}",
            "created_at": ts,
            "statement": statement,
            "evidence_quote": quote,
        },
    )


def _old_reviewer_a(original_idea, artifact_text, domain):
    return (
        f"## Original Idea\n{original_idea}\n\n"
        f"## Artifact\n{artifact_text}\n\n"
        f"## Domain\n{domain}\n\n"
        f"Derive verification from the original idea and produce the "
        f"{'test file (run it via shell_run)' if domain == 'code' else 'rubric'}."
    )


# --- helpers mirroring the live call sites ----------------------------------

def _new_reviewer_b(
    original_idea, acceptance, artifact_text, file_diff, a_verification, repo_context
):
    return render_package_template(
        "voss",
        "templates/prompts/reviewer_b_user.md.jinja",
        {
            "original_idea": original_idea,
            "acceptance": acceptance,
            "artifact_text": artifact_text,
            "file_diff": file_diff,
            "a_verification": a_verification,
            "repo_context": repo_context,
        },
    )


def _new_em(idea, snapshot, roster_descriptions):
    return render_package_template(
        "voss",
        "templates/prompts/em_user.md.jinja",
        {
            "idea": idea,
            "snapshot": snapshot,
            "roster": list(roster_descriptions.items()) if roster_descriptions else [],
        },
    )


# --- cases ------------------------------------------------------------------

_TEXT = "single line"
_MULTI = "line one\nline two\n  indented"

_B_CASES = [
    ("idea", "ac", "art", "diff", "asum", ""),
    ("idea", "ac", "art", "diff", "asum", "repo source here"),
    (_MULTI, _MULTI, _MULTI, _MULTI, _MULTI, _MULTI),
    ("", "", "", "", "", ""),
]

_EM_CASES = [
    ("idea", "snap", None),
    ("idea", "snap", {}),
    ("idea", "snap", {"reviewer-a": "derives bar"}),
    (_MULTI, _MULTI, {"a": "first", "b": "second\nwrapped"}),
]

_A_CASES = [
    ("idea", "art", "code"),
    ("idea", "art", "ai"),
    (_MULTI, _MULTI, "code"),
    ("", "", "ai"),
]


@pytest.mark.parametrize("args", _B_CASES)
def test_reviewer_b_user_parity(args):
    assert _new_reviewer_b(*args) == _old_reviewer_b(*args)


@pytest.mark.parametrize("args", _EM_CASES)
def test_em_user_parity(args):
    assert _new_em(*args) == _old_em(*args)


@pytest.mark.parametrize("args", _A_CASES)
def test_reviewer_a_task_parity(args):
    assert _reviewer_a_task(*args) == _old_reviewer_a(*args)


_NOTE_CASES = [
    ("note-abc", "sess-1", "2026-06-13T00:00:00+00:00", _TEXT),
    ("note-xyz", "sess-2", "2026-06-13T12:34:56+00:00", _MULTI),
    ("note-empty", "sess-3", "2026-06-13T00:00:00+00:00", ""),
]

_CONV_CASES = [
    ("conv-1", "sess-1", 3, 0.5, "2026-06-13T00:00:00+00:00", "Prefer X over Y", "quote here"),
    ("conv-2", "sess-2", 0, 1.0, "2026-06-13T12:00:00+00:00", _MULTI, _MULTI),
    ("conv-3", "sess-3", 42, 0.333, "2026-06-13T00:00:00+00:00", "stmt", "> nested quote"),
]


@pytest.mark.parametrize("args", _NOTE_CASES)
def test_memory_note_parity(args):
    assert _new_note(*args) == _old_note(*args)


@pytest.mark.parametrize("args", _CONV_CASES)
def test_memory_convention_parity(args):
    assert _new_convention(*args) == _old_convention(*args)
