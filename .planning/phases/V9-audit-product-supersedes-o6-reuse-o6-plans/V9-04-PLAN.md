---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 04
type: execute
wave: 3
depends_on: ["V9-03"]
files_modified:
  - voss/harness/audit/render.py
  - voss/harness/audit/__init__.py
  - voss/harness/cli.py
autonomous: true
requirements: [VAUD-01, VAUD-02, VAUD-08]

must_haves:
  truths:
    - "voss audit (no arg) renders the latest run and exits 0; voss audit <run_id> renders that run"
    - "An unknown run_id exits non-zero with stderr; a traversal run_id (.. or /) is rejected before any FS touch"
    - "render_json produces deterministic output (sort_keys); two renders of identical persisted data are byte-identical"
    - "render_markdown emits one header per PRD §9 section; missing sections render explicit _none_"
    - "audit_cmd is registered in AGENT_COMMANDS"
  artifacts:
    - path: "voss/harness/audit/render.py"
      provides: "render_text + render_markdown + render_json deterministic exporters"
      contains: "def render_json"
    - path: "voss/harness/cli.py"
      provides: "audit_cmd read-only CLI registered in AGENT_COMMANDS"
      contains: "audit_cmd"
  key_links:
    - from: "voss/harness/cli.py audit_cmd"
      to: "voss.harness.audit.report.build_audit_report + render.*"
      via: "import + call (no live Board/Manager)"
      pattern: "build_audit_report"
    - from: "voss/harness/cli.py AGENT_COMMANDS"
      to: "audit_cmd"
      via: "tuple membership"
      pattern: "audit_cmd"
---

<objective>
Ship the user-facing surface: the deterministic Markdown/JSON renderer (`render.py`), the package exports (`__init__.py`), and the `voss audit` CLI command wired into `AGENT_COMMANDS` (`cli.py`). After this wave a developer can run `voss audit` and get a complete, deterministic, exportable audit.

Purpose: VAUD-01 (CLI) + VAUD-08 (export) + the rendering half of VAUD-02. The CLI mirrors `review_cmd`/`board_cmd` exactly — read-only, optional run_id, latest default, traversal-guarded, no live Board/Manager.
Output: New `render.py`, updated `__init__.py` exports, `audit_cmd` in `cli.py` + AGENT_COMMANDS. Wave-0 `test_audit_render.py` + `test_audit_cli.py` turn GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-SPEC.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-PATTERNS.md
@.planning/docs/ORCHESTRATION_LAYERS.md

<interfaces>
From V9-03 (now landed):
  voss/harness/audit/report.py: build_audit_report(cwd, run_id=None, calibration=None) -> AuditReport
From V9-02:
  voss/harness/audit/model.py: AuditReport (run_id, idea, principles, team_config, snapshot,
    review_sidecars, run_final, signoff_ack, calibration, sections_missing, unsupported_claims)

CLI analogs (voss/harness/cli.py — AUTHORITATIVE):
  review_cmd (2487-2518): @click.command("review"), @click.argument("run_id", required=False),
    cwd = Path.cwd(); sessions_dir; run_id None → _latest_root_id; unknown → echo(...,err=True)+SystemExit(1)
  board_cmd decorators (3847-3855): @click.option("--cwd","cwd_str",default=".",type=click.Path(file_okay=False))
  _latest_root_id(sessions_dir) -> str | None  (2451-2459)
  AGENT_COMMANDS tuple (4163-4197) — currently ends with board_cmd
  Path-traversal guard analog: voss/harness/board/cli_view.py lines 97-116 (reject "/","\\","..";
    resolved candidate.parent must equal sessions_dir.resolve())

Determinism helpers (V9-PATTERNS "render.py"): json.dumps(data, sort_keys=True, indent=2);
  recursive _to_dict over dataclasses.asdict (tuples→lists; document the coercion).
PRD §9 section list: .planning/docs/ORCHESTRATION_LAYERS.md §9 (15 sections).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create render.py — deterministic render_text / render_markdown / render_json</name>
  <files>voss/harness/audit/render.py</files>
  <behavior>
    - render_json(report) → json.loads-able; deterministic (two calls byte-identical); tuples serialized as lists.
    - render_markdown(report) → one `##` header per PRD §9 section; missing sections render `_none_`.
    - render_text(report) → stable plain-text; two calls identical.
    - No datetime.now()/random/mtime in any render output (purity → determinism).
  </behavior>
  <read_first>
    - voss/harness/audit/model.py (AuditReport fields to render)
    - voss/harness/audit/report.py (what build_audit_report exposes, incl. unsupported_claims + sections_missing)
    - voss/harness/board/cli_view.py:148-157 (section-by-section emit analog) + voss/harness/cli.py:2462-2484 (_render_review_card text analog)
    - voss/harness/cli.py:3998 (json.dumps(data, indent=2) stdlib pattern)
    - .planning/docs/ORCHESTRATION_LAYERS.md §9 (the 15 section names + order — render headers map 1:1)
    - V9-PATTERNS.md "voss/harness/audit/render.py (new)" (render_text/render_json/_to_dict/render_markdown excerpts lines 298-345) + Landmine 5 (asdict tuple→list)
    - tests/harness/audit/test_audit_render.py (Wave-0 RED tests)
  </read_first>
  <action>
    Create `voss/harness/audit/render.py`. Module docstring notes purity/determinism and the documented "JSON round-trip yields lists where AuditReport uses tuples". Implement `_to_dict(obj)` recursive helper: dataclass → `{k: _to_dict(v) for k,v in dataclasses.asdict(obj).items()}`, list/tuple → `[_to_dict(x) for x in obj]`, else passthrough. `render_json(report) -> str`: `json.dumps(_to_dict(report), sort_keys=True, indent=2)`. `render_markdown(report) -> str`: emit a `## §N <SectionName>` header for EACH of the 15 PRD §9 sections in fixed order; populate from the corresponding AuditReport field; for sections in `report.sections_missing` (and the always-none diff_summary/tests_evals) render the body as `_none_`; for §10/§11 render Reviewer-A and Reviewer-B in SEPARATE subsections; tag unsupported EM claims (those in `report.unsupported_claims`) inline with `[UNSUPPORTED CLAIM]`. `render_text(report) -> str`: a compact plain-text variant for the default `--format text`. All three sort any iterated collections by a stable key (node id, section order) — no mtime/now/random. Stdlib only; `from voss.harness.audit.model import AuditReport` is the only project import (no board/em/cli).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py -x` exits 0 (markdown headers, json round-trip, determinism, text-stable all green).
    - `json.loads(render_json(report))` succeeds and is a dict carrying `run_id`/`idea`/nested snapshot.
    - Two `render_json` / `render_text` calls on the same tree are byte-identical.
    - `render_markdown` output contains `_none_` for diff_summary and tests_evals.
    - `grep -v '^#' voss/harness/audit/render.py | grep -c "voss.harness.board\|voss.harness.em\|voss.harness.cli"` returns 0.
  </acceptance_criteria>
  <done>render.py emits deterministic text/markdown/json; missing sections render _none_; reviewers separated; import-clean.</done>
</task>

<task type="auto">
  <name>Task 2: Update __init__.py exports + add audit_cmd to cli.py and AGENT_COMMANDS</name>
  <files>voss/harness/audit/__init__.py, voss/harness/cli.py</files>
  <read_first>
    - voss/harness/audit/__init__.py (current exports — add AuditReport, CalibrationReport, build_audit_report, render_* ; the docstring still says "O6 audit product" — update to V9 — cosmetic per RESEARCH)
    - voss/harness/cli.py:2487-2518 (review_cmd — copy structure VERBATIM as the audit_cmd template) + :2451-2459 (_latest_root_id) + :3847-3855 (board_cmd --cwd option) + :4163-4197 (AGENT_COMMANDS)
    - voss/harness/board/cli_view.py:97-116 (path-traversal guard to copy for run_id)
    - V9-PATTERNS.md "voss/harness/cli.py — audit_cmd" (signature, traversal guard, AGENT_COMMANDS excerpts lines 147-219)
    - tests/harness/audit/test_audit_cli.py (Wave-0 RED tests this task must satisfy)
  </read_first>
  <action>
    In `__init__.py`: add imports/`__all__` entries for `AuditReport`, `CalibrationReport` (from `.model`), `build_audit_report` (from `.report`), and `render_text`/`render_markdown`/`render_json` (from `.render`). Update the docstring "O6 audit product" → "V9 audit product". In `cli.py`: define `audit_cmd` modeled VERBATIM on `review_cmd` — `@click.command("audit")`, `@click.argument("run_id", required=False)`, `@click.option("--cwd","cwd_str",default=".",type=click.Path(file_okay=False))`, `@click.option("--format","fmt",type=click.Choice(["text","json","markdown"]),default="text")`, `@click.option("--output","output_path",default=None,type=click.Path())`. Body: resolve `cwd`; `sessions_dir = cwd/".voss"/"sessions"`; when `run_id` is None → `_latest_root_id(sessions_dir)`, if still None echo "(no runs found)" to stderr + `SystemExit(1)`. When `run_id` is provided, apply the traversal guard (reject if `"/" in run_id or "\\" in run_id or ".." in run_id`; resolve candidate and require `candidate.parent == sessions_dir.resolve()`) — echo invalid + `SystemExit(1)` BEFORE any FS read. If `run_dir` not a dir → echo `f"unknown run_id: {run_id}"` to stderr + `SystemExit(1)`. Otherwise call `build_audit_report(cwd, run_id=run_id, calibration=compute_calibration(sessions_dir))` — import `build_audit_report` and the render functions from `voss.harness.audit`, and `compute_calibration` from `voss.harness.audit.calibration` if V9-05 has landed; if calibration is not yet available, pass `calibration=None` (build_audit_report tolerates None). Select renderer by `fmt` (text→render_text, json→render_json, markdown→render_markdown). When `output_path` is set, write the rendered string to that file; else `click.echo` it. `raise click.exceptions.Exit(0)` on success. Register `audit_cmd` in the `AGENT_COMMANDS` tuple (add after `board_cmd`). Keep the import of audit symbols LOCAL to `audit_cmd` (function-body import) to avoid import-cycle/startup cost, mirroring how team_run_cmd imports its deps.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_audit_cli.py -x && .venv/bin/python -c "from voss.harness.cli import audit_cmd, AGENT_COMMANDS; assert audit_cmd in AGENT_COMMANDS"</automated>
  </verify>
  <acceptance_criteria>
    - `voss audit` (CliRunner, `--cwd <fixture>`) exits 0 and renders the latest run; `voss audit <run_id>` renders that run.
    - Unknown run_id → exit_code != 0 with "unknown" in output (stderr).
    - run_id `"../escape"` → exit_code != 0, rejected before any FS read (traversal guard).
    - `--format json` output parses via `json.loads`; two invocations on identical data → identical stdout (determinism).
    - `audit_cmd in AGENT_COMMANDS` is True; `voss --help` (or the registered group) lists `audit`.
    - `.venv/bin/python -m pytest tests/harness/audit/test_audit_cli.py -x` exits 0.
  </acceptance_criteria>
  <done>__init__.py exports the V9 surface; audit_cmd registered in AGENT_COMMANDS, read-only, traversal-guarded, format/output options; CLI tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI arg run_id → filesystem path | run_id is user-supplied and joined to sessions_dir — primary path-traversal surface |
| audited run data → stdout/--output file | Rendered audit may carry recorder content; must not leak secrets beyond what is persisted |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-04-01 | Spoofing/Tampering | path traversal via `run_id` | mitigate | Reject run_id containing `/`,`\\`,`..` and require resolved candidate.parent == sessions_dir.resolve() BEFORE any FS read (cli_view.py guard copied) |
| T-V9-04-02 | Information Disclosure | render leaking secrets/tokens from recorder events | mitigate | render only serializes the already-redacted persisted fields (recorder redaction is upstream, guarded by test_session_redaction.py); render adds no new field extraction beyond persisted data |
| T-V9-04-03 | Tampering | audit_cmd writing to audited run data | mitigate | audit_cmd is read-only; only `--output` writes, and only to the caller-named path outside the audited run dir by default |
| T-V9-04-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies; stdlib + click (existing) only |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py tests/harness/audit/test_audit_cli.py -x` — VAUD-01/08 + render half of VAUD-02 green.
- `.venv/bin/python -m pytest tests/harness/audit/ -x -k "not calibration and not signoff"` — loader+report+render+cli green, 37 baseline preserved.
- Import-clean grep gate for render.py returns 0.
</verification>

<success_criteria>
- render.py: deterministic text/markdown/json; missing sections _none_; reviewers separated; unsupported-claim tags.
- audit_cmd: read-only, optional run_id, latest default, traversal-guarded, --format/--output, registered in AGENT_COMMANDS.
- __init__.py exports the V9 surface.
- test_audit_render.py + test_audit_cli.py green; baseline preserved.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-04-SUMMARY.md` when done.
</output>
