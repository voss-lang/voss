"""Ownership detection + revert for R3 CLI swarm members (fs-watch plane).

R3 (see `SWARM-RECONCILIATION.md`) drops the in-process `PermissionGate`
ownership check (VSWARM-05) for CLI members — a black-box `codex`/`claude`
binary writes to disk directly, so voss cannot deny the write before it lands.
The guarantee is restored *post-hoc*: each member works in its own git worktree
(`swarm_worktree`), an fs-watch loop diffs that worktree, and any path the member
touched that is not in its `owned_files` is flagged (operator escalation) and
reverted with `git restore`.

Design split (so the loop is trivially testable):

- **`detect_violations`** — PURE. Decides which changed paths are out of scope.
  It reuses `swarm_store.build_ownership_policy` + `permissions.match_permission_rules`
  — the *same* deny/allow machinery the native gate runs — so CLI enforcement and
  native-gate enforcement give identical verdicts for the same `owned_files`.
- **`revert_paths`** — the only fs/git side effect: `git restore` the listed
  out-of-scope paths in the member's worktree.
- **`OwnershipWatcher`** — a thin `watchfiles` loop. Each batch: `changed_files`
  → `detect_violations` → if any, `on_violation(paths)` then `revert_paths`. All
  judgement lives in the pure function; the loop just plumbs.

`on_violation` is a caller-supplied callback (the server wires it to a
`swarm.needs_operator` emit, VSWARM-10) so this module stays free of any server
or event coupling.
"""
from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable, Iterable

from .permissions import match_permission_rules
from .swarm_store import _WRITE_TOOLS, _norm, build_ownership_policy
from .swarm_worktree import MemberWorktree, changed_files

OnViolation = Callable[[list[str]], None]


def detect_violations(changed: list[str], owned_files: list[str]) -> list[str]:
    """Return the subset of `changed` paths NOT permitted by `owned_files`.

    Pure. Delegates the allow/deny decision to the exact rule machinery the
    native PermissionGate uses: `build_ownership_policy` produces the per-tool
    `{"*": "deny", <owned>: "allow"}` map and `match_permission_rules` resolves
    each path with the same fnmatch + last-match-wins semantics. A path is a
    violation iff it would be denied for the bulk-write tool (the broadest write
    surface). Paths are normalized via `_norm` first, matching how `owned_files`
    were stored at task-creation time, so a `./`-prefixed change still resolves.
    """
    policy = build_ownership_policy(owned_files)
    rules = policy.rules
    # Any write tool gives the same verdict (build_ownership_policy installs the
    # same sub-map for each); pick one deterministically.
    tool = _WRITE_TOOLS[0]
    violations: list[str] = []
    for raw in changed:
        path = _norm(raw)
        decision = match_permission_rules(rules, tool, {"path": path})
        if decision != "allow":
            violations.append(raw)
    return violations


def revert_paths(mw: MemberWorktree, paths: Iterable[str]) -> None:
    """`git restore` the listed out-of-scope paths in the member's worktree.

    Only the named paths are touched, never the member's legit in-scope work.
    `--staged --worktree` undoes both index and working-tree state. For a path
    the member newly *created* (untracked), `git restore` is a no-op, so it is
    removed from disk explicitly — an out-of-scope new file must not survive.
    Best-effort per path: a restore failure on one path does not abort the rest.
    """
    paths = [p for p in paths if p]
    if not paths:
        return
    for p in paths:
        try:
            subprocess.run(
                ["git", "-C", str(mw.path), "restore", "--staged", "--worktree", "--", p],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        # Untracked creates are invisible to `git restore`; delete them so an
        # out-of-scope new file is genuinely gone, not merely un-indexed.
        target = mw.path / p
        if _is_untracked(mw, p) and target.is_file():
            try:
                target.unlink()
            except OSError:
                pass


def _is_untracked(mw: MemberWorktree, path: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(mw.path), "status", "--porcelain", "--", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.stdout.startswith("??")


class OwnershipWatcher:
    """Watch one member's worktree; revert + flag out-of-scope writes.

    Threaded (not asyncio) so the server can run it next to its own loop without
    owning an event loop. `watchfiles.watch` is a blocking generator with a
    `stop_event`; we drive it on a daemon thread and signal that event on
    `stop()`. The loop body is deliberately tiny — every decision is in
    `detect_violations`, every side effect in `revert_paths` — so what is hard to
    test (the live fs race) carries no logic.

    Usable as a context manager (`with OwnershipWatcher(...) as w:`).
    """

    def __init__(
        self,
        mw: MemberWorktree,
        owned_files: list[str],
        on_violation: OnViolation,
    ) -> None:
        self.mw = mw
        self.owned_files = list(owned_files)
        self.on_violation = on_violation
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- the unit the loop calls per batch; pure-path driven, separately testable
    def _handle_batch(self) -> list[str]:
        """Recompute changes → detect → flag+revert. Returns reverted paths."""
        violations = detect_violations(changed_files(self.mw), self.owned_files)
        if violations:
            # Flag first so escalation is recorded even if the revert later fails.
            self.on_violation(violations)
            revert_paths(self.mw, violations)
        return violations

    def _run(self) -> None:
        # Imported lazily so importing this module never hard-requires watchfiles
        # for callers that only use the pure functions.
        from watchfiles import watch

        for _changes in watch(str(self.mw.path), stop_event=self._stop):
            # Ignore the per-event paths watchfiles reports and re-derive truth
            # from git: it is the authority on what changed vs the member's base,
            # and collapses a noisy burst of fs events into one clean diff.
            self._handle_batch()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> OwnershipWatcher:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


__all__ = [
    "OnViolation",
    "OwnershipWatcher",
    "detect_violations",
    "revert_paths",
]
