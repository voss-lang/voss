---
phase: M2
plan: 06
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/cli.py (drift hint in _run_repl + sessions_cmd --all/--global + doctor cognition rows + project_policy wired into PermissionGate construction in _run_repl + do_cmd)
  - voss/harness/permissions.py (project_policy field on PermissionGate + first-clause deny check + module docstring extended with Project-level layering section)
  - tests/harness/test_cli.py (TestSessionsListing × 2, TestDoctorCognitionRows × 1, TestProjectPolicyLayering × 3)
  - tests/harness/test_repl_cognition.py (test_drift_hint_printed_non_blocking unskipped)
tests_added: 7 (2 sessions + 1 doctor + 3 permissions + 1 drift)
tests_total: 222 passed + 2 skipped
---

# M2-06 Summary · Drift Hint · Sessions --all · Doctor Cognition Rows · Permissions Layering

Closes the M2 loose ends. After this plan: cognition is **visible** (drift +
doctor) and **enforceable** (`.voss/permissions.yml` deny rules).

## 1. Drift hint (D-04)

Inserted in `_run_repl`, immediately after the banner block / auth-detail /
resumed-turns echo. T-M2-22 mitigation: wrapped in `try/except (OSError,
ValueError)` so malformed frontmatter cannot crash REPL boot — failure is
logged via `click.echo(err=True)` and the loop continues.

```python
if bundle.initialized and bundle.architecture_frontmatter:
    try:
        drift = cognition_mod.drift_check(cwd, bundle.architecture_frontmatter)
    except (OSError, ValueError) as exc:
        click.echo(f"drift check failed: {exc}", err=True)
    else:
        if drift.is_stale:
            click.echo(
                f"  cognition stale ({drift.reason}) — /analyze to refresh"
            )
```

Output example: `  cognition stale (30d old) — /analyze to refresh`.

**Non-blocking**: hint precedes the prompt loop; REPL continues regardless.

## 2. `voss sessions --all` (D-11)

```python
@click.command("sessions")
@click.option(
    "--all",
    "--global",
    "include_legacy",
    is_flag=True,
    help="Include legacy sessions from ~/.local/state/voss/sessions/.",
)
def sessions_cmd(include_legacy: bool) -> None:
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    ...
    for r in records:
        tag = "[legacy] " if getattr(r, "_legacy", False) else ""
        click.echo(f"  {tag}{r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}")
```

Output rows:
- Cwd-scoped: `  abc12345  2026-05-10T...  claude-test                  (empty)`
- Legacy:     `  [legacy] 999aaaaa  2026-05-10T...  claude-test                  (empty)`

Default (no flag): cwd-scoped only. `--all` (alias `--global`) merges legacy
XDG-dir sessions in.

## 3. `voss doctor` cognition rows (D-12)

Appended **after** the existing 7-check block, **before** the exit-code
computation. Uses M1's `f"  {label:<20}: {value}"` layout (20-char left-padded
label, colon, space, value).

```
  .voss/ initialized  : yes|no
  cognition staleness : fresh | stale (<reason>) | n/a | error (<exc>)
  legacy sessions     : 0 | N (read-only via voss sessions --all)
```

Reads `cognition_mod.load(cwd)` directly (independent of diagnostics module's
Check pipeline so the layout matches exactly). Drift check wrapped in same
try/except as the REPL hint.

Manual sanity (no `.voss/`, empty legacy dir):
```
  .voss/ initialized  : no
  cognition staleness : n/a
  legacy sessions     : 0
```

## 4. Permissions.yml layering precedence (deny-wins)

### Docstring extension (`voss/harness/permissions.py`)

```
Project-level layering (.voss/permissions.yml, added in M2)
-----------------------------------------------------------
When .voss/permissions.yml is loaded into a PermissionsConfig and attached
to the gate, its rules layer on top of the session mode:

  - deny (project) ALWAYS wins, even in mode=auto.
  - allow (project) is recorded but does NOT expand session-mode
    permissions (a project allow does not auto-approve a tool that the
    session mode would have prompted for).

This mirrors M1's "least-privilege wins" stance.
```

### Field + check order

```python
@dataclass
class PermissionGate:
    ...
    project_policy: Optional[PermissionsConfig] = None  # .voss/permissions.yml

def check(self, tool_name, args, *, is_mutating=False) -> tuple[bool, str]:
    # 0. Project deny (NEW — first clause)
    if self.project_policy is not None:
        if tool_name in self.project_policy.tool_policy.deny:
            return False, "denied by .voss/permissions.yml"
    # 1. Mode-tier structural denial
    # 2. CTRL-08 diff preview
    # 3. Scope check
    # 4. Within-mode prompt or auto-yes
```

### Wiring

`_run_repl` (chat / edit / resume) and `do_cmd` both pass
`project_policy=bundle.permissions if bundle.initialized else None` into the
PermissionGate constructor. Missing `.voss/` → `project_policy=None` →
gate behaves exactly as M1.

### Tests asserting precedence

| Test | Setup | Expectation |
|------|-------|-------------|
| `test_project_policy_deny_wins`              | mode=auto + deny=[shell_run] | `(False, "denied by .voss/permissions.yml")` |
| `test_project_policy_allow_does_not_expand`  | mode=plan + allow=[shell_run] | mode-plan structural denial still wins for mutating tools |
| `test_no_project_policy_unchanged`           | mode=auto + project_policy=None | gate behaves like M1 (`auto_yes=True` → allowed) |

## 5. M2-VALIDATION.md test coverage status

All originally-skipped M2 placeholders are now live:

- `test_voss_gitignore_autogenerated` — unskipped in M2-04
- `test_analyze_invokes_natural_language_route` / `test_analyze_emits_project_root_gitignore_append` — covered in M2-04 (functions inlined)
- `test_architecture_md_frontmatter_well_formed` / `test_analyze_writes_architecture_md` — unskipped in M2-04
- `test_cognition_status_line_tty` / `test_cognition_loaded_ndjson_event` / `test_cognition_overflow_truncates_constraints` — unskipped in M2-05
- `test_turn_injects_cognition` / `test_resume_injects_prior_run_context` — unskipped in M2-05
- `test_drift_hint_printed_non_blocking` / `test_doctor_cognition_rows` / `test_sessions_cwd_scoped` / `test_sessions_all_includes_legacy` — unskipped in M2-06

Remaining 2 skipped tests are placeholders for **post-M2** work (not in M2-VALIDATION):
- `test_analyze_writes_project_json` (placeholder — same scope already covered by `test_init_voss_stubs_creates_valid_files`; will retire on cleanup pass)
- `test_doctor_cognition_rows` Wave-4 placeholder in `test_cli.py` (the real implementation replaced it under a new class; this top-level stub can also retire).

Suite: **222 passed + 2 skipped** (was 215 + 4 after M2-05).

## 6. Threat dispositions

| Threat   | Disposition |
|----------|-------------|
| T-M2-21 | Mitigate — only deny rules short-circuit to auto-deny; allow does NOT expand mode (project allow cannot override session intent upward). |
| T-M2-22 | Mitigate — drift_check call wrapped in `try/except (OSError, ValueError)` in both REPL banner and doctor command; failure logs + proceeds. |
| T-M2-23 | Accept — legacy session count is non-sensitive; row already documents the read-only XDG location. |

## 7. M2 phase ready for /gsd-verify-work

- COG-01 .. COG-08 all observably satisfied across plans M2-01 .. M2-06.
- Cognition layer: load → inject → render → enforce → diagnose end-to-end.
- All success criteria from M2-CONTEXT.md fired:
  1. `/analyze` creates `.voss/` (M2-04)
  2. Cognition auto-injected into every turn (M2-05)
  3. Drift detected + surfaced non-blockingly (M2-06)
  4. Plans + decisions persisted to `.voss/plans/` + `.voss/decisions/` (M2-03 / M2-04)
  5. Repeated sessions improve from stored project context (M2-05 prior_context rehydration)
  6. `.voss/permissions.yml` deny rules enforced (M2-06)
