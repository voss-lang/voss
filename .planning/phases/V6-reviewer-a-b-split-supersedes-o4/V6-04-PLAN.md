---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 04
type: execute
wave: 3
depends_on: [V6-01, V6-03]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [VREV-10]
must_haves:
  truths:
    - "`voss review` with no arg prints the latest run's per-card A verification + B verdict + final outcome and exits 0"
    - "`voss review <run_id>` prints that run's per-card review and exits 0"
    - "`voss review <unknown_run_id>` exits non-zero and writes an error to stderr"
    - "The command is read-only from persisted .review.json sidecars — no live Board/SessionTreeManager constructed"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "review_cmd click command + _latest_root_id helper + AGENT_COMMANDS registration"
      contains: "review_cmd"
  key_links:
    - from: "voss/harness/cli.py"
      to: ".voss/sessions/<run_id>/*.review.json"
      via: "review_cmd globs and reads sidecar JSON written by V6-03"
      pattern: "review.json"
    - from: "voss/harness/cli.py AGENT_COMMANDS"
      to: "review_cmd"
      via: "tuple registration so `voss review` is dispatched"
      pattern: "review_cmd"
---

<objective>
Ship the read-only `voss review <run_id>` CLI (VREV-10) that surfaces persisted review artifacts per card without re-running review. It mirrors the `sessions_cmd` read-only-from-persisted pattern (NOT `voss board`, which does not exist yet — V5 unshipped), discovers the latest root dir by mtime when no `run_id` is given, reads the `.review.json` sidecars written by V6-03, renders per-card A verification + B verdict + final outcome, and matches `voss board`'s exit-code convention (0 on success, non-zero + stderr on unknown run).

Purpose: Make review outcomes inspectable from the persisted artifacts; close the last V6 deliverable gap.
Output: `review_cmd` + `_latest_root_id` in `cli.py`, registered in `AGENT_COMMANDS`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-PATTERNS.md

<interfaces>
<!-- Extracted from V6-PATTERNS.md "cli.py" section + V6-RESEARCH.md Q5/Pitfall 1. -->

cli.py sessions_cmd (L2437) — the read-only-from-persisted template:
  @click.command("sessions"); reads from store; click.echo; no live manager.
cli.py AGENT_COMMANDS (L3777) tuple — contains sessions_cmd (L3785); register() (L3810) loops + adds each cmd to the group.

CRITICAL (Pitfall 1): `voss board` / `board_cmd` does NOT exist (V5 unshipped). Mirror `sessions_cmd`, do NOT import board_cmd.

Sidecar layout (written by V6-03): .voss/sessions/<root_id>/<node_id>.review.json
  keys: a_verification {test_path_or_rubric, result, notes} | null,
        b_verdict {conf, source, tier, verdict, notes, evidence_refs, domain_inferred} | null,
        final_outcome "Done"|"Blocked"
  run_id == root_id == the subdir name under .voss/sessions/

Latest-root discovery (V6-PATTERNS Example 4):
  roots = [d for d in sessions_dir.iterdir() if d.is_dir()]; max(roots, key=lambda d: d.stat().st_mtime).name
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement review_cmd + _latest_root_id, register in AGENT_COMMANDS</name>
  <read_first>
    - voss/harness/cli.py (sessions_cmd at L2437; AGENT_COMMANDS tuple at L3777, sessions_cmd entry L3785; register() at L3810)
    - V6-PATTERNS.md "cli.py — review_cmd + AGENT_COMMANDS" section (exact review_cmd body, _latest_root_id helper, registration line)
    - V6-RESEARCH.md Q5 + Pitfall 1 (voss board absent — mirror sessions_cmd; exit-code convention)
    - tests/harness/board/test_review_cli.py (RED scaffold from V6-01 this satisfies — CliRunner, unknown-run, no-sessions, existing-run cases)
  </read_first>
  <behavior>
    - review_cmd([]) with at least one session dir → discovers latest root by mtime → prints each card's A verification + B verdict + final outcome → exit 0
    - review_cmd([known_run_id]) → prints that run's sidecars → exit 0
    - review_cmd([unknown_run_id]) → click.echo("unknown run_id: ...", err=True) + raise SystemExit(1)
    - review_cmd([]) with no .voss/sessions dirs → error to stderr + non-zero exit
    - run with a known root that has no .review.json sidecars → benign message, exit 0 (the run exists)
    - No live Board / SessionTreeManager / provider constructed anywhere in the command
  </behavior>
  <action>
    In `voss/harness/cli.py`:
    (1) Add module-level helper `_latest_root_id(sessions_dir: Path) -> str | None` (V6-PATTERNS Example 4): list `sessions_dir` subdirs, return the name of the max-by-mtime dir, or None (guard `OSError`/empty).
    (2) Add `@click.command("review")` with `@click.argument("run_id", required=False)` → `review_cmd(run_id)`. Body: `cwd = Path.cwd()`; `sessions_dir = cwd/".voss"/"sessions"`; if `run_id is None`: `run_id = _latest_root_id(sessions_dir)`, and if still None → `click.echo("(no review runs found)", err=True)` + `raise SystemExit(1)`. Resolve `sidecar_dir = sessions_dir/run_id`; if not `sidecar_dir.is_dir()` → `click.echo(f"unknown run_id: {run_id}", err=True)` + `raise SystemExit(1)`. Glob `sorted(sidecar_dir.glob("*.review.json"))`; if empty → benign `click.echo("(no review artifacts for this run)")` + return (exit 0). For each sidecar: `json.loads(path.read_text())` and render per card (a `_render_review_card(node_id, data)` helper or inline) — show A verification (test/rubric + result), B verdict (verdict/conf/tier/domain_inferred/evidence_refs/notes), and final_outcome. Plain text, ordered by card, matching `sessions_cmd` echo style (D-12). Guard malformed/oversized sidecar JSON: wrap the per-file `json.loads` so a single corrupt sidecar prints a warning line and continues rather than crashing the whole command.
    (3) Register `review_cmd` in the `AGENT_COMMANDS` tuple (alongside `sessions_cmd`) so `register()` adds it to the group.
    Mirror `sessions_cmd` — do NOT import or reference a nonexistent `board_cmd` (Pitfall 1).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_review_cli.py -x 2>&1 | tail -6</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'def review_cmd' voss/harness/cli.py` and `grep -q '_latest_root_id' voss/harness/cli.py` both succeed
    - `grep -q 'review_cmd' voss/harness/cli.py` shows review_cmd present in the AGENT_COMMANDS tuple region (registered)
    - `grep -c 'board_cmd' voss/harness/cli.py` returns 0 (no nonexistent board command referenced)
    - `.venv/bin/python -m pytest tests/harness/board/test_review_cli.py -x` exits 0 (unknown-run non-zero+stderr, no-sessions non-zero, existing-run exit 0)
    - `.venv/bin/python -c "from voss.harness.cli import review_cmd"` exits 0 (importable)
  </acceptance_criteria>
  <done>`voss review` is registered and read-only from `.review.json` sidecars; latest-run default works; unknown run exits non-zero with stderr; the CLI test file is green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `<run_id>` arg → filesystem path under .voss/sessions/ | User-supplied run_id is joined onto the sessions dir to resolve a sidecar directory |
| persisted .review.json → CLI render | On-disk JSON (possibly stale/corrupt) is parsed and printed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V6-04-01 | Tampering | path traversal via `run_id` (e.g. `../../etc`) | mitigate | `run_id` resolves to `sessions_dir / run_id` and is gated by `sidecar_dir.is_dir()` + a `*.review.json` glob confined to that dir; only `.review.json` files under `.voss/sessions/<run_id>/` are read. A traversal target without matching sidecars yields the unknown-run / no-artifacts path (non-zero or benign), never reads outside the glob. Acceptance covers the unknown-run exit. |
| T-V6-04-02 | Denial | malformed/oversized sidecar JSON crashing the command | mitigate | Per-file `json.loads` wrapped — a corrupt sidecar prints a warning and the loop continues; one bad file does not abort the whole review render |
| T-V6-04-03 | Information Disclosure | rendering sidecar contents | accept | Read-only display of artifacts the user already owns (0o600, same user); no new exposure |
| T-V6-04-SC | Tampering | npm/pip/cargo installs | mitigate | Zero new dependencies (click already present); no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_review_cli.py -x` exits 0.
- `.venv/bin/python -c "from voss.harness.cli import review_cmd"` succeeds (importable + registered).
- Manual (V6-VALIDATION manual-only): after a board run, `voss review` renders per-card A verification + B verdict legibly.
</verification>

<success_criteria>
- `voss review` (no arg) → latest run per-card A+B + final, exit 0 (VREV-10).
- `voss review <run_id>` → that run, exit 0; unknown run → non-zero + stderr.
- Read-only from `.review.json`; no live Board/manager/provider constructed.
- Mirrors `sessions_cmd`; no reference to a nonexistent `board_cmd`.
</success_criteria>

<output>
Create `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-04-SUMMARY.md` when done.
</output>
