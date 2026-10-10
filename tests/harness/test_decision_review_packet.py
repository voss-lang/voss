from __future__ import annotations

import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.decision_review import (
    CHECK_STATUSES,
    VERIFICATION_NOTE_CHARS,
    CheckResult,
    Criterion,
    build_packet,
    candidate_from_diff,
    checks_from_artifact,
    collect_commit,
    collect_working_tree,
    is_stale,
    load_checks,
    touched_paths,
    tree_digest,
)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "keep.py").write_text("keep = 1\n")
    (root / "edit.py").write_text("value = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def test_check_result_validates_name_and_status():
    assert CheckResult("tests", "passed").status == "passed"
    assert CHECK_STATUSES == ("passed", "failed", "skipped", "not_run", "stale")
    for name, status in (("tests", "unknown"), ("", "passed"), ("x" * 101, "passed")):
        with pytest.raises(ValueError):
            CheckResult(name, status)


def test_checks_from_artifact_keeps_not_run_distinct_from_failed():
    assert checks_from_artifact(None) == ()
    assert checks_from_artifact(SimpleNamespace(tests_passed=True, scope_violations=())) == (
        CheckResult("tests", "passed"),
        CheckResult("scope", "passed"),
    )
    assert checks_from_artifact(SimpleNamespace(tests_passed=False)) == (CheckResult("tests", "failed"),)
    assert checks_from_artifact(SimpleNamespace(scope_violations=("x.py",))) == (
        CheckResult("tests", "not_run"),
        CheckResult("scope", "failed"),
    )
    assert checks_from_artifact(SimpleNamespace(tests_passed=None)) == (CheckResult("tests", "not_run"),)


def test_checks_from_artifact_ignores_reviewer_a_summary_text():
    artifact = SimpleNamespace(a_verification_summary="all tests pass")
    assert checks_from_artifact(artifact) == (CheckResult("tests", "not_run"),)


def test_load_checks_accepts_both_shapes():
    data = [{"name": "unit", "status": "skipped"}, {"type": "cmd", "pass": False, "detail": "boom"}]
    assert load_checks(data) == (CheckResult("unit", "skipped"), CheckResult("cmd", "failed"))
    assert load_checks([{"type": "file_exists", "pass": True}]) == (CheckResult("file_exists", "passed"),)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "unit", "status": "passed"},
        "passed",
        [{"type": "cmd", "pass": "true"}],
        [{"type": "cmd", "pass": 1}],
        [{"name": "unit", "status": "ok"}],
        [{"name": "unit"}],
        ["unit"],
    ],
)
def test_load_checks_rejects_malformed_input(data):
    with pytest.raises(ValueError):
        load_checks(data)


def test_touched_paths_reads_headers_and_drops_unsafe_paths():
    diff = "\n".join(
        [
            "--- a/a.py",
            "+++ b/a.py",
            "--- a/gone.py",
            "+++ /dev/null",
            "--- /dev/null",
            "+++ b/../x",
            "+++ b//abs",
            "+++ b/a.py",
        ]
    )
    assert touched_paths(diff) == ("a.py", "gone.py")


def test_tree_digest_tracks_touched_files_only(tmp_path: Path):
    (tmp_path / "a.py").write_text("a\n")
    (tmp_path / "b.py").write_text("b\n")
    first = tree_digest(tmp_path, ["a.py"])
    assert re.fullmatch(r"[0-9a-f]{16}", first)
    assert tree_digest(tmp_path, ["a.py"]) == first
    (tmp_path / "b.py").write_text("changed\n")
    assert tree_digest(tmp_path, ["a.py"]) == first
    (tmp_path / "a.py").write_text("changed\n")
    edited = tree_digest(tmp_path, ["a.py"])
    assert edited != first
    (tmp_path / "a.py").unlink()
    assert tree_digest(tmp_path, ["a.py"]) not in (first, edited)


def test_collect_working_tree_includes_untracked_and_leaves_index_alone(repo: Path):
    (repo / "edit.py").write_text("value = 2\n")
    (repo / "new_module.py").write_text("def added():\n    return 1\n")
    (repo / ".voss").mkdir()
    (repo / ".voss" / "secret.json").write_text("{}\n")
    diff, candidate = collect_working_tree(repo)
    assert "+value = 2" in diff
    assert "+++ b/new_module.py" in diff
    assert "+def added():" in diff
    assert ".voss" not in diff
    assert candidate["kind"] == "working_tree"
    assert candidate["touched_paths"] == ["edit.py", "new_module.py"]
    assert candidate["tree_digest"] == tree_digest(repo, ["edit.py", "new_module.py"])
    assert subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo).returncode == 0
    assert _git(repo, "ls-files", "new_module.py") == ""


def test_collect_working_tree_outside_git_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        collect_working_tree(tmp_path)


def test_collect_commit_diffs_from_merge_base_and_reads_code_at_sha(repo: Path):
    main = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "edit.py").write_text("value = 'feature'\n")
    (repo / "added.py").write_text("added = True\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feature")
    sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", main)
    (repo / "keep.py").write_text("keep = 2\n")
    _git(repo, "commit", "-q", "-am", "main moves on")
    (repo / "edit.py").write_text("value = 'working tree'\n")

    diff, code, candidate = collect_commit(repo, sha)

    assert "keep.py" not in diff
    assert "+value = 'feature'" in diff
    assert "+++ b/added.py" in diff
    assert "value = 'feature'" in code
    assert "added = True" in code
    assert "working tree" not in code
    assert candidate == {"kind": "commit", "head": sha, "touched_paths": ["added.py", "edit.py"]}
    assert collect_commit(repo, "feature")[2]["head"] == sha


def test_collect_commit_falls_back_to_parent_when_commit_is_head(repo: Path):
    (repo / "edit.py").write_text("value = 3\n")
    _git(repo, "commit", "-q", "-am", "next")
    diff, _, candidate = collect_commit(repo, "HEAD")
    assert "+value = 3" in diff
    assert candidate["touched_paths"] == ["edit.py"]


@pytest.mark.parametrize("ref", ["-x", "--output=/tmp/x", "no-such-ref", ""])
def test_collect_commit_rejects_bad_refs(repo: Path, ref: str):
    with pytest.raises(ValueError):
        collect_commit(repo, ref)


def _packet(**overrides):
    args = {
        "criteria": "AC-1: adds foo\nAC-2: adds bar",
        "diff": "+++ b/a.py\n+foo\n",
        "code": "### a.py\nfoo",
        "checks": [CheckResult("tests", "passed")],
        "candidate": {"kind": "working_tree", "touched_paths": ["a.py"], "tree_digest": "0" * 16},
    }
    args.update(overrides)
    criteria = args.pop("criteria")
    return build_packet(criteria, **args)


def test_packet_id_is_deterministic_and_binds_inputs():
    base = _packet()
    assert re.fullmatch(r"[0-9a-f]{16}", base.packet_id)
    assert _packet().packet_id == base.packet_id
    assert base.criteria == (Criterion("AC-1", "adds foo"), Criterion("AC-2", "adds bar"))
    assert _packet(criteria=list(base.criteria)).packet_id == base.packet_id
    assert _packet(criteria=["adds foo", "adds bar"]).packet_id == base.packet_id
    changed = [
        _packet(criteria="AC-1: adds foo\nAC-2: adds baz"),
        _packet(diff="+++ b/a.py\n+food\n"),
        _packet(checks=[CheckResult("tests", "not_run")]),
        _packet(candidate={"kind": "working_tree", "touched_paths": ["a.py"], "tree_digest": "1" * 16}),
        _packet(candidate={"kind": "commit", "head": "a" * 40, "touched_paths": ["a.py"]}),
    ]
    ids = {p.packet_id for p in changed}
    assert base.packet_id not in ids
    assert len(ids) == len(changed)


def test_verification_note_is_bounded_and_outside_the_digest():
    long_note = "n" * (VERIFICATION_NOTE_CHARS + 50)
    packet = _packet(verification_note=long_note)
    assert packet.verification_note == long_note[:VERIFICATION_NOTE_CHARS]
    assert packet.packet_id == _packet().packet_id
    assert _packet().verification_note == ""


def test_is_stale_after_edit_or_delete(repo: Path):
    (repo / "edit.py").write_text("value = 2\n")
    (repo / "fresh.py").write_text("fresh = 1\n")
    _, candidate = collect_working_tree(repo)
    detail = {"candidate": candidate}
    assert is_stale(repo, detail) is False
    (repo / "keep.py").write_text("untouched change\n")
    assert is_stale(repo, detail) is False
    (repo / "edit.py").write_text("value = 3\n")
    assert is_stale(repo, detail) is True

    _, candidate = collect_working_tree(repo)
    detail = {"candidate": candidate}
    assert is_stale(repo, detail) is False
    (repo / "fresh.py").unlink()
    assert is_stale(repo, detail) is True


def test_is_stale_never_for_commit_or_fixture_candidates(tmp_path: Path):
    assert is_stale(tmp_path, {"candidate": {"kind": "commit", "head": "a" * 40, "touched_paths": ["x.py"]}}) is False
    assert is_stale(tmp_path, {"candidate": {"kind": "fixture"}}) is False


@pytest.mark.parametrize(
    "candidate",
    [
        {"kind": "working_tree", "touched_paths": "a.py", "tree_digest": "0" * 16},
        {"kind": "working_tree", "touched_paths": [1], "tree_digest": "0" * 16},
        {"kind": "working_tree", "touched_paths": ["../a.py"], "tree_digest": "0" * 16},
        {"kind": "working_tree", "touched_paths": ["a.py"]},
        {"kind": "working_tree"},
    ],
)
def test_is_stale_treats_malformed_working_tree_detail_as_stale(tmp_path: Path, candidate: dict):
    assert is_stale(tmp_path, {"candidate": candidate}) is True


def test_candidate_from_diff_matches_tree_digest(tmp_path: Path):
    (tmp_path / "a.py").write_text("a\n")
    candidate = candidate_from_diff(tmp_path, "--- a/a.py\n+++ b/a.py\n")
    assert candidate == {"kind": "working_tree", "touched_paths": ["a.py"], "tree_digest": tree_digest(tmp_path, ["a.py"])}
