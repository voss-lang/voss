"""R3 ownership detection + revert tests (SWARM-RECONCILIATION).

`detect_violations` is exercised exhaustively as a pure function (it is the load-
bearing decision that must match the native PermissionGate). `revert_paths` and
the watcher's per-batch unit run against a real temp git repo. The live
watchfiles loop is NOT raced against real fs events — its body is a thin call to
the deterministic `_handle_batch`, which is tested directly.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from voss.harness.swarm_watch import (
    OwnershipWatcher,
    detect_violations,
    revert_paths,
)
from voss.harness.swarm_worktree import (
    MemberWorktree,
    changed_files,
    create_member_worktree,
)


# ---------------------------------------------------------------------------
# detect_violations — pure, exhaustive
# ---------------------------------------------------------------------------
class TestDetectViolations:
    def test_in_scope_allowed(self) -> None:
        assert detect_violations(["src/a.py"], ["src/a.py"]) == []

    def test_out_of_scope_flagged(self) -> None:
        assert detect_violations(["src/b.py"], ["src/a.py"]) == ["src/b.py"]

    def test_mixed_returns_only_violations(self) -> None:
        changed = ["src/a.py", "src/b.py", "src/c.py"]
        owned = ["src/a.py", "src/c.py"]
        assert detect_violations(changed, owned) == ["src/b.py"]

    def test_dot_slash_prefix_on_changed_is_allowed(self) -> None:
        # A CLI may report a `./`-prefixed path; it must still match its owned form.
        assert detect_violations(["./src/a.py"], ["src/a.py"]) == []

    def test_dot_slash_prefix_on_owned_is_allowed(self) -> None:
        assert detect_violations(["src/a.py"], ["./src/a.py"]) == []

    def test_glob_owned_matches(self) -> None:
        # owned_files may carry a glob; fnmatch semantics (same as the gate) apply.
        assert detect_violations(["src/x.py", "src/y.py"], ["src/*.py"]) == []

    def test_glob_matches_gate_fnmatch_semantics(self) -> None:
        # Documented equivalence to the native gate: it uses stdlib fnmatch,
        # whose `*` DOES cross `/`. So `src/*.py` also permits a nested file.
        # detect_violations mirrors that exactly (it reuses the same matcher),
        # so CLI enforcement and gate enforcement never diverge.
        assert detect_violations(["src/sub/z.py"], ["src/*.py"]) == []
        # A non-.py path is still flagged.
        assert detect_violations(["src/sub/z.txt"], ["src/*.py"]) == ["src/sub/z.txt"]

    def test_empty_owned_flags_everything(self) -> None:
        assert detect_violations(["a", "b"], []) == ["a", "b"]

    def test_empty_changed_is_empty(self) -> None:
        assert detect_violations([], ["src/a.py"]) == []

    def test_preserves_raw_changed_form_in_output(self) -> None:
        # The returned path is the raw changed path (so revert_paths can act on
        # exactly what git reported), not a normalized rewrite.
        out = detect_violations(["./oops.py"], ["src/a.py"])
        assert out == ["./oops.py"]


# ---------------------------------------------------------------------------
# revert_paths + watcher unit — real temp git repo
# ---------------------------------------------------------------------------
def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def member(tmp_path: Path) -> MemberWorktree:
    """A member worktree off a one-commit repo with two committed files."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(["init", "-q"], root)
    _git(["config", "user.email", "test@test"], root)
    _git(["config", "user.name", "test"], root)
    (root / "owned.py").write_text("owned-v1\n")
    (root / "other.py").write_text("other-v1\n")
    _git(["add", "."], root)
    _git(["commit", "-q", "-m", "init"], root)
    return create_member_worktree(root, "sw00", "builder-1")


class TestRevertPaths:
    def test_reverts_tracked_edit(self, member: MemberWorktree) -> None:
        (member.path / "other.py").write_text("CLOBBERED\n")
        revert_paths(member, ["other.py"])
        assert (member.path / "other.py").read_text() == "other-v1\n"

    def test_deletes_untracked_out_of_scope_create(self, member: MemberWorktree) -> None:
        stray = member.path / "stray.py"
        stray.write_text("should not survive\n")
        revert_paths(member, ["stray.py"])
        assert not stray.exists()

    def test_leaves_unlisted_paths_untouched(self, member: MemberWorktree) -> None:
        # Member's legit in-scope edit must survive a revert targeting only the
        # out-of-scope path.
        (member.path / "owned.py").write_text("legit work\n")
        (member.path / "other.py").write_text("bad\n")
        revert_paths(member, ["other.py"])
        assert (member.path / "owned.py").read_text() == "legit work\n"
        assert (member.path / "other.py").read_text() == "other-v1\n"

    def test_empty_list_is_noop(self, member: MemberWorktree) -> None:
        (member.path / "owned.py").write_text("legit\n")
        revert_paths(member, [])
        assert (member.path / "owned.py").read_text() == "legit\n"


class TestWatcherHandleBatch:
    """Drives the watcher's per-batch unit deterministically (no fs race)."""

    def test_violation_flagged_and_reverted(self, member: MemberWorktree) -> None:
        flagged: list[list[str]] = []
        watcher = OwnershipWatcher(
            member, owned_files=["owned.py"], on_violation=flagged.append
        )
        # Member writes BOTH an in-scope edit and an out-of-scope file.
        (member.path / "owned.py").write_text("legit\n")
        (member.path / "other.py").write_text("forbidden\n")

        reverted = watcher._handle_batch()

        assert reverted == ["other.py"]
        assert flagged == [["other.py"]]
        # Out-of-scope reverted, in-scope preserved.
        assert (member.path / "other.py").read_text() == "other-v1\n"
        assert (member.path / "owned.py").read_text() == "legit\n"

    def test_in_scope_only_no_flag(self, member: MemberWorktree) -> None:
        flagged: list[list[str]] = []
        watcher = OwnershipWatcher(
            member, owned_files=["owned.py"], on_violation=flagged.append
        )
        (member.path / "owned.py").write_text("legit\n")
        assert watcher._handle_batch() == []
        assert flagged == []
        assert changed_files(member) == ["owned.py"]  # untouched


class TestWatcherLifecycle:
    def test_start_stop_idempotent(self, member: MemberWorktree) -> None:
        watcher = OwnershipWatcher(member, owned_files=["owned.py"], on_violation=lambda _: None)
        watcher.start()
        watcher.start()  # second start is a no-op, not a second thread
        watcher.stop()
        watcher.stop()  # stop after stop is safe

    def test_context_manager(self, member: MemberWorktree) -> None:
        with OwnershipWatcher(member, owned_files=["owned.py"], on_violation=lambda _: None) as w:
            assert w._thread is not None and w._thread.is_alive()
        assert w._thread is None
