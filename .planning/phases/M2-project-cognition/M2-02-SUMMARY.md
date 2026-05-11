---
phase: M2
plan: 02
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/session.py (per-cwd storage + RunRecord dataclass + extended docstring)
  - voss/harness/recorder.py (new)
  - voss/harness/cli.py (sessions_cmd + resume_cmd pass cwd=)
  - tests/harness/test_session.py (per-cwd tests + signature updates)
  - tests/harness/test_session_redaction.py (TestRunRecordRedaction class)
  - tests/harness/test_recorder.py (5 stubs unskipped)
  - tests/harness/test_happy_path_integration.py (signature updates)
tests_added: 13 (6 session + 2 redaction + 5 recorder)
tests_total: 192 passed + 11 skipped
---

# M2-02 Summary: Per-cwd Sessions + RunRecord + Mechanical Recorder

Wave 1 ships the structural changes every later M2 plan sits on top of.
COG-05 hard cut completed; COG-08 mechanical half done.

## 1. `voss/harness/session.py` public API after migration

| Name                              | Signature                                                    | Change |
|-----------------------------------|--------------------------------------------------------------|--------|
| `_sessions_dir(cwd)`              | `Path -> Path` → `(cwd / ".voss" / "sessions").resolve()`     | NEW |
| `_legacy_state_dir()`             | `() -> Path` → `$XDG_STATE_HOME/voss/sessions/`               | NEW |
| `_state_dir()`                    | —                                                            | DELETED |
| `session_path(id, cwd=None)`      | `(str, Path | None) -> Path`                                  | cwd added |
| `save(record, history)`           | unchanged signature; reads cwd from `record.cwd` internally   | now writes to per-cwd dir |
| `load(name_or_id, cwd=None)`      | scans per-cwd → falls back to legacy; tags legacy hits `_legacy=True` | cwd added |
| `list_sessions(cwd, *, include_legacy=False)` | per-cwd only by default; with flag extends to legacy | sig change |
| `delete(id, cwd=None)`            | refuses to delete legacy files (returns False)               | cwd added |

### Legacy fallback resolution order

```
load(id, cwd):
  1. scan <cwd>/.voss/sessions/*.json     ← writable, primary
  2. scan <legacy>/voss/sessions/*.json   ← read-only, fallback
  match by id prefix OR name; ambiguous → ValueError
  legacy hits → setattr(record, "_legacy", True)
```

`save()` writes ONLY to (1). Legacy dir never written under any path — the
D-10 hard cut.

### Backward-compat: missing `runs` field

`_hydrate(data)` filters to `_SESSION_FIELDS` then `setdefault("turns", [])`
+ `setdefault("runs", [])`. M1 sessions (no `runs` key) load with
`runs=[]`. Pitfall 7 closed.

## 2. `RunRecord` — 16-field dataclass

Field order matters; redaction test asserts `len(dataclasses.fields(RunRecord)) == 16`.

| # | Field          | Type            | Default              |
|---|----------------|-----------------|----------------------|
| 1 | id             | str             | (required)           |
| 2 | started_at     | str             | (required)           |
| 3 | ended_at       | str             | (required)           |
| 4 | goal           | str             | ""                   |
| 5 | plan           | dict \| None    | None                 |
| 6 | inspected      | list[str]       | []                   |
| 7 | changed        | list[str]       | []                   |
| 8 | avoided        | list[dict]      | []                   |
| 9 | assumptions    | list[str]       | []                   |
| 10 | decisions     | list[dict]      | []                   |
| 11 | risks         | list[str]       | []                   |
| 12 | validation    | list[dict]      | []                   |
| 13 | failures      | list[dict]      | []                   |
| 14 | diff_summary  | str             | ""                   |
| 15 | follow_ups    | list[str]       | []                   |
| 16 | cost_usd      | float           | 0.0                  |

Mutable defaults via `field(default_factory=...)`. Non-frozen so M2-03 can
populate semantic fields via `RunRecorder.absorb`.

## 3. `voss/harness/recorder.py` — RunRecorder collaborator

```
class RunRecorder:
    @classmethod start() -> RunRecorder
    observe(tool_name, args, result, *, ok) -> None
    absorb(semantics, plan=None) -> None     # M2-03 stub
    finalize(cwd, cost_usd) -> RunRecord
```

### Observation rules by tool category

| Category set       | Tools                              | Behavior on observe(ok=True) |
|--------------------|------------------------------------|------------------------------|
| `INSPECT_TOOLS`    | fs_read, fs_glob, fs_grep          | append `args.path` (or `args.pattern`) to `inspected` |
| `CHANGE_TOOLS`     | fs_write, fs_edit                  | append `args.path` to `changed` |
| `VALIDATE_TOOLS`   | shell_run, voss_check              | parse `[exit N]` prefix; append `{cmd, exit, summary[:160]}` to `validation` |
| (other)            | git_status, git_diff, unknown       | no-op |

On `ok=False`: append `{tool, error[:200]}` to `failures` regardless of category.

`finalize` truncates `git diff --stat` output at 4096 chars; subprocess has
5s timeout; failure → empty `diff_summary`. T-M2-08 closed.

### Semantic-field stubs (M2-03 wires)

`absorb(semantics, plan)` copies `goal / avoided / assumptions / decisions /
risks / follow_ups` from `semantics` and `plan.model_dump()` into the
recorder. Signature is the contract M2-03 fills.

## 4. Extended redaction CI (D-17 + T-M2-05 + T-M2-07)

`tests/harness/test_session_redaction.py` adds `TestRunRecordRedaction`:

| Test                                      | Locks |
|-------------------------------------------|-------|
| `test_run_record_top_level_keys`          | `set(asdict(rec).keys())` equals the 16 named fields; `len(fields(RunRecord)) == 16`. Any future field addition breaks this. |
| `test_run_record_no_secret_patterns`      | Build SessionRecord with one RunRecord in `runs`; save; full JSON text scanned for `("sk-ant-", "sk-proj-", "Bearer ", "oauth_token", "access_token", "Authorization")`. None may appear. |

Also: `test_saved_json_has_exactly_schema_keys` extended to include `"runs"`
in the expected top-level allowlist.

M1 `test_module_docstring_mentions_redaction_guarantee` still passes — the
"Redaction guarantee" string survives; M2 paragraph appended after it.

## 5. Threat dispositions

| Threat   | Disposition                                                  |
|----------|--------------------------------------------------------------|
| T-M2-05  | Mitigated by RunRecord schema-allowlist + 6-pattern scan + SUMMARY_TRUNC=160 / FAILURE_TRUNC=200. |
| T-M2-06  | `_hydrate` uses `setdefault` for missing keys; load() try/except per file. |
| T-M2-07  | `runs: list[dict]` items themselves serialize via `asdict(RunRecord(...))` whose allowlist is locked. |
| T-M2-08  | `_git_diff_stat` timeout=5; failure → "" not raise. |

## 6. Verification

- `pytest tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_recorder.py tests/harness/test_cli.py -x` → 0 failures.
- Full suite: **192 passed + 11 skipped** (was 179 + 16 after M2-01).
- `len(fields(RunRecord)) == 16` ✓
- `grep -cE '\b_state_dir\b' voss/harness/session.py` → 0 (old helper deleted)
- Manual: `python -c "from voss.harness.recorder import RunRecorder; r=RunRecorder.start(); r.observe('shell_run', {'cmd':'pytest'}, '[exit 1]\nbad', ok=True); assert r.validation[0]['exit']==1"` → exits 0.

## 7. Handoff to M2-03

- `RunRecorder.absorb(semantics, plan)` is the integration point for the
  privileged `record_run` closing call.
- `SessionRecord.runs.append(asdict(run_record))` is where M2-03 writes the
  per-turn record after the user-visible final answer renders.
- Decision/plans markdown writers in M2-03 use `cognition.slug()` +
  `cognition.reserve_filename()` from M2-01.

Subagents used (opus, sequential): Task 1 first (session.py + RunRecord),
then Task 2 (recorder + 5 tests). Sequential because Task 2 imports
`RunRecord` from Task 1's output.
