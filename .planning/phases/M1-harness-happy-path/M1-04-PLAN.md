---
phase: M1-harness-happy-path
plan: 04
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - voss/harness/edit_scope.py
  - voss/harness/cli.py
  - voss/harness/permissions.py
  - tests/harness/test_edit_scope.py
  - tests/harness/test_edit_cmd.py
autonomous: true
requirements:
  - CLIH-04
  - CTRL-08
tags:
  - harness
  - cli
  - edit

must_haves:
  truths:
    - "`voss edit <path>` starts a REPL session and exits on /quit, Ctrl-D, or EOF."
    - "Default editable scope is `<path>` + sibling test mirror, resolved at session start."
    - "Reads are always allowed under the cwd path jail; only writes are scope-checked."
    - "Out-of-scope writes prompt `expand scope to include <path>? [y/once/always/n]`."
    - "'always' persists for the session only; new `voss edit` or `voss resume` starts fresh."
    - "Mutating tool calls render a diff preview before applying (CTRL-08)."
  artifacts:
    - path: "voss/harness/edit_scope.py"
      provides: "EditScope dataclass: resolve(cwd, path), allows_write(target), expand(target)"
      contains: "class EditScope"
    - path: "voss/harness/cli.py"
      provides: "edit_cmd click command + scope-aware REPL"
      contains: "@click.command(\"edit\")"
    - path: "voss/harness/permissions.py"
      provides: "PermissionGate threads an optional edit_scope to expand prompt"
      contains: "edit_scope"
  key_links:
    - from: "voss/harness/cli.py::edit_cmd"
      to: "voss/harness/edit_scope.py::EditScope.resolve"
      via: "scope = EditScope.resolve(cwd, path)"
      pattern: "EditScope\\.resolve"
    - from: "voss/harness/permissions.py::PermissionGate.check"
      to: "voss/harness/edit_scope.py::EditScope.allows_write"
      via: "scope.allows_write(target) before prompting expand"
      pattern: "scope\\.allows_write"
---

<objective>
Add `voss edit <path>` as a scoped REPL session. Resolves the editable scope to `<path>` + sibling test mirror at session start. Reads stay free under the cwd jail; writes outside the scope trigger an `expand scope?` prompt. A diff preview renders before writes apply.

Purpose: Implements D-01..D-04 and CTRL-08. The `voss edit` flow is one of the four canonical M1 commands. Without it, the harness can do `voss do` but not a focused edit session — which is the entire reason a user invokes `voss edit` instead of `voss chat`.

Output:
- New module `voss/harness/edit_scope.py` with `EditScope` dataclass.
- New `edit_cmd` click command in `voss/harness/cli.py`, wired via `register(group)`.
- `PermissionGate` accepts an optional `edit_scope` and routes write-target prompts through it.
- Diff preview for `fs_write` and `fs_edit` calls before they're applied (uses Python's `difflib.unified_diff`).
- Tests for scope resolution, sibling-test mirror logic, expand-prompt behavior, and diff preview.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@.planning/phases/M1-harness-happy-path/M1-01-PLAN.md
@voss/harness/cli.py
@voss/harness/permissions.py
@voss/harness/tools.py
@voss/harness/sandbox.py

<interfaces>
After Plan 01:
  - voss.harness.tools.ToolEntry has .is_mutating: bool
  - voss.harness.permissions.PermissionGate.check(name, args, *, is_mutating: bool=False)
  - voss.harness.permissions.mode_allows(mode, name, is_mutating) — structural denial

Existing REPL pattern (voss/harness/cli.py:_run_repl, lines 227-326). Reuse it. Pass
the scope into the gate.

EditScope sibling resolution rules (D-02):
  - If <path> is a file like src/foo/bar.py:
      sibling candidates =
        tests/foo/test_bar.py
        tests/test_bar.py
        src/foo/test_bar.py
        tests/foo/bar_test.py    # pytest style
        src/foo/bar_test.py
      Pick all that exist; include them in scope.
  - If <path> is a directory like src/foo/:
      scope = src/foo/** (recursive)
      sibling = tests/foo/** if exists
  - If no test mirror exists, scope = just <path>.

The scope-summary line on session start lists the resolved set so user sees it (D-02).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: EditScope module with sibling-mirror resolution</name>
  <files>voss/harness/edit_scope.py, tests/harness/test_edit_scope.py</files>
  <read_first>
    - voss/harness/sandbox.py (jail_path — scope must compose with the cwd jail)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-01..D-04)
  </read_first>
  <behavior>
    - Test 1 (file with sibling): in a tmp tree where `src/foo/bar.py` and `tests/foo/test_bar.py` both exist, `EditScope.resolve(cwd, "src/foo/bar.py")` returns a scope where `allows_write("src/foo/bar.py") == True`, `allows_write("tests/foo/test_bar.py") == True`, `allows_write("src/foo/baz.py") == False`.
    - Test 2 (file no sibling): in a tmp tree where only `src/foo/bar.py` exists, `EditScope.resolve(cwd, "src/foo/bar.py")` has scope only `{src/foo/bar.py}`.
    - Test 3 (directory): given `src/foo/` containing `a.py`, `b.py`, and `tests/foo/` containing `test_a.py`, scope.allows_write covers all 4 files; `tests/bar/test_x.py` returns False.
    - Test 4 (pytest-style sibling): `src/foo/bar.py` with `src/foo/bar_test.py` next to it — both in scope.
    - Test 5 (top-level): `bar.py` with `test_bar.py` next to it — both in scope.
    - Test 6 (expand): `scope.expand(cwd / "src/foo/baz.py")` mutates scope; `allows_write("src/foo/baz.py") == True` after.
    - Test 7 (summary): `scope.summary()` returns a list of relative path strings sorted, suitable for printing in the session banner.
    - Test 8 (cwd jail composition): `allows_write` for a path outside cwd returns False (caller still uses `jail_path` to surface the SandboxError; this is a belt-and-braces check).
  </behavior>
  <action>
1. Create `voss/harness/edit_scope.py`:
```python
"""Editable scope for `voss edit` sessions.

Reads are unrestricted under cwd (the existing path jail covers that). The
scope only restricts WRITES. Per D-02, default scope = <path> + sibling test
mirror. Per D-04, out-of-scope writes prompt; "always" expands the scope for
the rest of the session only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _candidate_test_siblings(p: Path) -> list[Path]:
    """Return potential test-mirror file paths for a source file `p`.

    Order does not matter; the caller filters to ones that exist.
    """
    name = p.stem
    suffix = p.suffix
    parent = p.parent
    candidates: list[Path] = []
    # tests/<rest>/test_<name>.py and bar_test.py
    # Walk up from p, find the project root candidate (first dir that has a sibling "tests").
    # Simple heuristic: take every parent up to 4 levels; for each, try parent/tests/<rel>/...
    candidates.append(parent / f"test_{name}{suffix}")
    candidates.append(parent / f"{name}_test{suffix}")
    for up in range(1, 5):
        anchor = parent
        for _ in range(up):
            if anchor.parent == anchor:
                break
            anchor = anchor.parent
        try:
            rel = parent.relative_to(anchor)
        except ValueError:
            continue
        tests_root = anchor / "tests"
        candidates.append(tests_root / rel / f"test_{name}{suffix}")
        candidates.append(tests_root / rel / f"{name}_test{suffix}")
        candidates.append(tests_root / f"test_{name}{suffix}")
    return candidates


@dataclass
class EditScope:
    """Set of files/dirs allowed to be written during a `voss edit` session."""
    cwd: Path
    files: set[Path] = field(default_factory=set)
    dirs: set[Path] = field(default_factory=set)

    @classmethod
    def resolve(cls, cwd: Path, path: str) -> "EditScope":
        cwd = cwd.resolve()
        target = (cwd / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        scope = cls(cwd=cwd)
        if target.is_dir():
            scope.dirs.add(target)
            # Look for tests/<same_rel>/
            try:
                rel = target.relative_to(cwd)
                tests_mirror = cwd / "tests" / rel
                if tests_mirror.exists() and tests_mirror.is_dir():
                    scope.dirs.add(tests_mirror.resolve())
            except ValueError:
                pass
        else:
            scope.files.add(target)
            for cand in _candidate_test_siblings(target):
                if cand.exists() and cand.is_file():
                    scope.files.add(cand.resolve())
        return scope

    def allows_write(self, target: str | Path) -> bool:
        p = (self.cwd / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
        # Must be inside cwd.
        try:
            p.relative_to(self.cwd)
        except ValueError:
            return False
        if p in self.files:
            return True
        for d in self.dirs:
            try:
                p.relative_to(d)
                return True
            except ValueError:
                continue
        return False

    def expand(self, target: str | Path) -> None:
        """Add target to the scope for the rest of the session (D-04)."""
        p = (self.cwd / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
        if p.is_dir():
            self.dirs.add(p)
        else:
            self.files.add(p)

    def summary(self) -> list[str]:
        """Sorted list of relative paths for banner display."""
        out: list[str] = []
        for f in self.files:
            try:
                out.append(str(f.relative_to(self.cwd)))
            except ValueError:
                out.append(str(f))
        for d in self.dirs:
            try:
                out.append(str(d.relative_to(self.cwd)) + "/")
            except ValueError:
                out.append(str(d) + "/")
        return sorted(out)
```

2. Create `tests/harness/test_edit_scope.py` covering behaviors 1-8 above. Build fixtures in `tmp_path` for each test.

3. Run `pytest tests/harness/test_edit_scope.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_edit_scope.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/edit_scope.py` exists.
    - `grep -c "class EditScope" voss/harness/edit_scope.py` returns 1.
    - `grep -c "def resolve" voss/harness/edit_scope.py` returns at least 1.
    - `grep -c "def allows_write" voss/harness/edit_scope.py` returns 1.
    - `grep -c "def expand" voss/harness/edit_scope.py` returns 1.
    - `grep -c "def summary" voss/harness/edit_scope.py` returns 1.
    - `pytest tests/harness/test_edit_scope.py -x` exits 0.
  </acceptance_criteria>
  <done>EditScope resolves siblings; expand mutates in-session; summary reports the resolved set.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: voss edit CLI command with scope-aware gate + diff preview</name>
  <files>voss/harness/cli.py, voss/harness/permissions.py, tests/harness/test_edit_cmd.py</files>
  <read_first>
    - voss/harness/cli.py (entire — focus on _run_repl pattern at 227-326 and chat_cmd at 185-224)
    - voss/harness/permissions.py (entire — gate.check needs edit_scope routing)
    - voss/harness/edit_scope.py (from Task 1)
    - voss/harness/tools.py (ToolEntry from Plan 01)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-01..D-04, D-07)
  </read_first>
  <behavior>
    - Test 1 (registration): `python -m voss --help` lists `edit`. `python -m voss edit --help` mentions `<path>`.
    - Test 2 (scope summary): launching `voss edit src/foo/bar.py` in a test tree prints a banner that lists the resolved scope set including the sibling test file.
    - Test 3 (in-scope write): when the agent calls `fs_write` on a path inside scope, the gate prompts the normal `[a/A/d]` prompt (no scope expansion needed).
    - Test 4 (out-of-scope write): when the agent calls `fs_write` on a path outside scope, the gate emits the expand prompt `expand scope to include <path>? [y/once/always/n]`. Choice 'y' or 'once' allows this single write without persisting scope; choice 'always' calls `scope.expand(target)`; choice 'n' denies.
    - Test 5 (diff preview): the gate emits a unified diff for `fs_write` (new content vs current) and for `fs_edit` (old → new) BEFORE the call is allowed to proceed. The diff appears via `click.echo` to stderr.
    - Test 6 (scope-resets-per-session): a `scope.expand(...)` during session 1 does NOT persist; a second `voss edit` invocation starts with the default-resolved scope. (Verified by not writing scope to PermissionStore.)
    - Test 7 (default mode wiring): `voss edit` defaults to `mode='edit'` (D-07). `voss edit --mode=plan` overrides.
  </behavior>
  <action>
1. In `voss/harness/permissions.py`, extend `PermissionGate`:
```python
@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False
    prompt_fn = None
    edit_scope: "EditScope | None" = None      # NEW
    scope_prompt_fn = None                     # NEW (injected for tests)

    def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
        allowed_by_mode, why = mode_allows(self.mode, tool_name, is_mutating)
        if not allowed_by_mode:
            return False, why

        # Scope check for write tools.
        if self.edit_scope is not None and tool_name in WRITE:
            target = args.get("path", "")
            if target and not self.edit_scope.allows_write(target):
                # Render diff preview first (D-04 + CTRL-08).
                self._render_diff_preview(tool_name, args)
                ok, expand_kind = self._prompt_expand(target)
                if not ok:
                    return False, "out-of-scope denied"
                if expand_kind == "always":
                    self.edit_scope.expand(target)
                # ok == True with expand_kind in {"once", "always"} → allow this call.
                return True, f"out-of-scope: {expand_kind}"
            # In-scope write: still render diff preview (CTRL-08).
            self._render_diff_preview(tool_name, args)

        if not self.needs_prompt(tool_name):
            return True, "auto"
        if self.store is not None:
            sig = self.signature(tool_name, args)
            if sig in self.store.always:
                return True, "remembered"
        return self._prompt(tool_name, args)

    def _render_diff_preview(self, tool_name: str, args: dict) -> None:
        """Render a unified diff to stderr before applying a write (CTRL-08)."""
        import difflib
        from pathlib import Path as _P
        try:
            path = args.get("path", "")
            if not path:
                return
            base = _P(self.edit_scope.cwd if self.edit_scope else ".").resolve()
            p = (base / path).resolve()
            current = p.read_text() if p.exists() else ""
            if tool_name == "fs_write":
                new = args.get("content", "")
            elif tool_name == "fs_edit":
                old = args.get("old", "")
                replacement = args.get("new", "")
                new = current.replace(old, replacement, 1) if old in current else current
            else:
                return
            diff = "".join(difflib.unified_diff(
                current.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{path}", tofile=f"b/{path}", n=3,
            ))
            if diff:
                sys.stderr.write("\n  diff preview:\n")
                for line in diff.splitlines():
                    sys.stderr.write(f"    {line}\n")
                sys.stderr.flush()
        except (OSError, UnicodeDecodeError):
            return

    def _prompt_expand(self, target: str) -> tuple[bool, str]:
        """Prompt: expand scope to include <target>? [y/once/always/n]."""
        prompt = self.scope_prompt_fn or _interactive_expand_prompt
        if not sys.stdin.isatty() and self.scope_prompt_fn is None:
            return False, "non-interactive denial"
        choice = prompt(target)
        if choice in ("y", "once"):
            return True, "once"
        if choice == "always":
            return True, "always"
        return False, "denied"
```

   Add module-level `_interactive_expand_prompt`:
```python
def _interactive_expand_prompt(target: str) -> str:
    sys.stderr.write(f"\n  ⚠  expand scope to include {target}?\n")
    sys.stderr.write("     [y] yes once  [a] always (this session)  [n] no: ")
    sys.stderr.flush()
    line = sys.stdin.readline().strip().lower()
    if not line:
        return "n"
    if line.startswith("a"):
        return "always"
    if line.startswith("y"):
        return "once"
    return "n"
```

   Forward-declare `EditScope` via `from typing import TYPE_CHECKING` to avoid circular import.

2. In `voss/harness/cli.py`, add `edit_cmd`:
```python
@click.command("edit")
@click.argument("path", type=click.Path(exists=True))
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--model", default=None, help="Override default model.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="edit",
    help="Permission tier (default edit per D-07).",
)
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
def edit_cmd(path: str, cwd_str: str, model: str | None, json_mode: bool, mode: str, auth_pref: str) -> None:
    """Scoped edit REPL. Edits restricted to <path> + sibling test mirror (D-02)."""
    from .edit_scope import EditScope

    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    scope = EditScope.resolve(cwd, path)
    record = session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model, name=f"edit-{Path(path).name}")

    click.echo(f"  edit scope: {', '.join(scope.summary()) or path}")

    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        mode=mode,
        history=EpisodicMemory(capacity=40),
        record=record,
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
        edit_scope=scope,
    )
```

   Update `_run_repl` to accept `edit_scope: EditScope | None = None` and thread it into `PermissionGate(...)`. Also add `edit_cmd` to the `AGENT_COMMANDS` tuple at the bottom.

3. Create `tests/harness/test_edit_cmd.py`:
```python
from click.testing import CliRunner
from pathlib import Path

import pytest

from voss.harness.cli import edit_cmd
from voss.harness.edit_scope import EditScope
from voss.harness.permissions import PermissionGate, WRITE


class TestEditCmdRegistration:
    def test_edit_help_mentions_path(self):
        result = CliRunner().invoke(edit_cmd, ["--help"])
        assert result.exit_code == 0
        assert "PATH" in result.output or "<path>" in result.output.lower()


class TestScopedGate:
    def test_in_scope_write_does_not_prompt_expand(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        scope = EditScope.resolve(tmp_path, "a.py")
        expanded = []
        gate = PermissionGate(
            mode="edit", auto_yes=True, edit_scope=scope,
            scope_prompt_fn=lambda t: expanded.append(t) or "n",
        )
        ok, why = gate.check("fs_write", {"path": "a.py", "content": "x = 2\n"}, is_mutating=True)
        assert ok
        assert not expanded  # no expand prompt for in-scope write

    def test_out_of_scope_write_prompts_expand_and_denies_on_n(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 1\n")
        scope = EditScope.resolve(tmp_path, "a.py")
        gate = PermissionGate(
            mode="edit", auto_yes=True, edit_scope=scope,
            scope_prompt_fn=lambda t: "n",
        )
        ok, why = gate.check("fs_write", {"path": "b.py", "content": "y = 2\n"}, is_mutating=True)
        assert not ok
        assert "out-of-scope" in why or "denied" in why

    def test_always_expands_scope_for_session(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 1\n")
        scope = EditScope.resolve(tmp_path, "a.py")
        gate = PermissionGate(
            mode="edit", auto_yes=True, edit_scope=scope,
            scope_prompt_fn=lambda t: "always",
        )
        ok, _ = gate.check("fs_write", {"path": "b.py", "content": "y = 2\n"}, is_mutating=True)
        assert ok
        # Now b.py is in scope; subsequent write should not prompt.
        assert scope.allows_write("b.py")


class TestDiffPreview:
    def test_diff_preview_rendered_for_fs_write(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("x = 1\n")
        scope = EditScope.resolve(tmp_path, "a.py")
        gate = PermissionGate(
            mode="edit", auto_yes=True, edit_scope=scope,
            scope_prompt_fn=lambda t: "n",
        )
        gate.check("fs_write", {"path": "a.py", "content": "x = 2\n"}, is_mutating=True)
        captured = capsys.readouterr()
        assert "diff preview" in captured.err
        assert "-x = 1" in captured.err or "x = 1" in captured.err
```

4. Run `pytest tests/harness/test_edit_cmd.py tests/harness/test_edit_scope.py tests/harness/test_permissions_modes.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_edit_cmd.py tests/harness/test_edit_scope.py tests/harness/test_permissions_modes.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "@click.command(\"edit\")" voss/harness/cli.py` returns 1.
    - `grep -c "def edit_cmd" voss/harness/cli.py` returns 1.
    - `grep -c "edit_cmd" voss/harness/cli.py` returns at least 2 (decorator + AGENT_COMMANDS).
    - `grep -c "edit_scope" voss/harness/permissions.py` returns at least 2.
    - `grep -c "_render_diff_preview" voss/harness/permissions.py` returns at least 1.
    - `grep -c "_prompt_expand" voss/harness/permissions.py` returns at least 1.
    - `grep -c "difflib" voss/harness/permissions.py` returns at least 1.
    - `pytest tests/harness/test_edit_cmd.py -x` exits 0.
    - `pytest tests/harness/test_edit_scope.py -x` exits 0.
    - `pytest tests/harness/test_permissions_modes.py -x` exits 0 (no regression from Plan 01).
    - `pytest tests/harness/test_cli.py -x` exits 0 (existing CLI test for help/registration).
    - `python -m voss edit --help` output contains "scope".
  </acceptance_criteria>
  <done>voss edit registered, scope-aware gate prompts on out-of-scope writes, "always" persists in-session only, diff preview renders before all mutating writes.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_edit_cmd.py tests/harness/test_edit_scope.py tests/harness/test_permissions_modes.py tests/harness/test_cli.py -x` exits 0.
- Manual: `python -m voss edit voss/harness/sandbox.py` launches a REPL whose banner lists `voss/harness/sandbox.py` and `tests/harness/test_sandbox.py`.
- Manual: in the same REPL, if the agent attempts to write `voss/harness/auth.py`, the prompt asks `expand scope to include voss/harness/auth.py?`.
</verification>

<success_criteria>
- D-01: `voss edit` is a REPL session (reuses `_run_repl`); exits cleanly on /quit, Ctrl-D, EOF.
- D-02: Default scope = `<path>` + sibling test mirror; resolved set is printed in banner.
- D-03: Reads under cwd are unrestricted; only writes pass through scope check.
- D-04: Out-of-scope writes prompt `[y/once/always/n]`; "always" persists for session only (not written to PermissionStore).
- CTRL-08: Diff preview renders before all `fs_write` / `fs_edit` calls.
- CLIH-04: `voss edit <path>` is registered, callable, and documented in help output.
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-04-SUMMARY.md` documenting the EditScope contract, the gate's diff/expand prompt order, and the session-only persistence boundary (so M2 knows not to leak scope into `.voss/sessions/`).
</output>
