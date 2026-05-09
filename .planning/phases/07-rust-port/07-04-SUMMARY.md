---
plan: 07-04
status: complete
date: 2026-05-09
---

# 07-04 — voss-tools (R4) Summary

Wave R4 ports `voss/harness/sandbox.py` (49 LOC) and `voss/harness/tools.py`
(170 LOC) to the Rust `voss-tools` crate. Nine tools registered, sandbox
jail + allowlist persistence in place, and a schemars-vs-pydantic parity
gate locks both the per-tool argument schemas and the D-12 mutating set.

## Tools registered (9)

| name        | mutating | description (verbatim from Python) |
|-------------|----------|------------------------------------|
| fs_read     | no       | Read a UTF-8 text file from the project. Path must be inside cwd. |
| fs_glob     | no       | List files matching a glob pattern, relative to cwd. |
| fs_grep     | no       | Recursively search for a regex pattern. Returns matching lines with file:line. |
| git_status  | no       | Run \`git status --porcelain\`. |
| git_diff    | no       | Run \`git diff\` (unstaged) or \`git diff --cached\` (staged) on optional path. |
| voss_check  | no       | Run \`voss check\` on a .voss file or directory. Returns analyzer diagnostics. |
| fs_write    | yes      | Write text to a file inside cwd. Creates parent dirs. Overwrites existing. |
| fs_edit     | yes      | Replace exact \`old\` text with \`new\` in a file. \`old\` must appear exactly once. Returns line count delta. |
| shell_run   | yes      | Run a shell command from the allowlist. Output truncated to 4KB. |

Mutating set `{fs_write, fs_edit, shell_run}` and read-only set
`{fs_read, fs_glob, fs_grep, git_status, git_diff, voss_check}` are
locked by the `is_mutating_flags_match_d12` test.

## Bridge caching strategy for `voss_check`

Chose **per-tool cached PyBridge via `tokio::sync::OnceCell`**. The
`VossCheck` tool stores `bridge: OnceCell<PyBridge>`; the first
`invoke` discovers and stashes a `PyBridge`, every subsequent call reuses
it. PyBridge itself owns a `Mutex<Option<BridgeChild>>` that lazily spawns
the Python subprocess on first `call`. Net effect: one Python subprocess
per `VossCheck` instance for the lifetime of that tool.

Per-invoke construction was rejected because the Python startup cost
(~150ms cold) on every tool call would be visible in agent loops that
voss_check repeatedly. The OnceCell pattern keeps `VossCheck` cheap to
construct (no I/O) while avoiding multi-spawn.

## Shell timeout test strategy

Chose **parameterized timeout via `ShellRun::with_timeout_secs(t)`
builder**. The test `shell_run_timeout` constructs a `ShellRun` with
`timeout_secs = 1`, runs `python3 -c "import time; time.sleep(5)"`, and
asserts the output contains `<timeout: 1s>`. Production callers
construct via `ShellRun::new(cwd)` which keeps the 30s default.

Rationale: a 30s default is too slow to put in a test loop, and `#[ignore]`
removes the regression-detection value of the test. The builder pattern
mirrors `with_timeout_secs` knobs already common in Rust crates and
keeps the production constructor signature minimal.

## Sandbox jail correction

Initial implementation joined `tail` segments via `PathBuf::from(name)
.join(&tail)` where `tail` started as `PathBuf::new()`. On Unix, joining
an empty `PathBuf` produces a trailing `/` (`"a.txt/"`), which makes
`std::fs::write` fail with `NotFound` because the kernel treats the path
as a directory. Fixed by collecting non-existent components in a
`Vec<OsString>` (in reverse order) and re-pushing them in order onto the
canonicalized existing-ancestor base. `fs_write_then_read` and the rest
of the fs tests now pass.

## Schema parity strictness

Same posture as R3 (Plan/ToolCall):

| Check | enforced |
|-------|----------|
| Property-name set | yes |
| Required-set | yes |
| Description text | no |
| Field-level metadata (default, format, type) | no |

Why: schemars and pydantic both emit the right *structure* (object/required)
but diverge on cosmetic metadata (e.g. pydantic emits `title: "Path"` on
every field; schemars emits `description` only when given a doc-comment).
The dangerous drift class — a field becoming required on one side or a
field added/removed/renamed — is fully covered.

Two specific tools to call out:

- **`git_status`** has zero parameters in Python. Schemars emits
  `{"type": "object", "title": "GitStatusArgs", "properties": {}}` for
  the unit-like `GitStatusArgs` struct (no `required` key). Python emits
  `{"type": "object", "properties": {}, "required": []}`. Both produce
  empty property sets and empty required sets — parity test passes.
- **`git_diff`** uses `staged: bool = false, path: str = ""` in Python →
  required `[]`, properties `{staged, path}`. Rust uses
  `#[serde(default)] staged: bool` and `#[serde(default)] path: String`
  → schemars emits required `[]`, properties `{staged, path}`. Aligned.

## Verification

```
cargo test -p voss-tools --no-fail-fast    # 7 sandbox + 5 fs + 4 shell + 2 schema_parity = 18 pass
.venv/bin/python scripts/dump_python_tool_schemas.py | head -3    # `{"fs_edit": ...`
grep -l 'is_mutating(&self) -> bool { false }' crates/voss-tools/src/{fs_read,fs_glob,fs_grep,git_status,git_diff,voss_check}.rs    # 6 files
grep -l 'is_mutating(&self) -> bool { true }'  crates/voss-tools/src/{fs_write,fs_edit,shell_run}.rs    # 3 files
grep -rn 'pyo3\|cpython' crates/voss-tools/    # no matches
```
