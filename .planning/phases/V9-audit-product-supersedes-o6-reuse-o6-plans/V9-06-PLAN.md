---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 06
type: execute
wave: 4
depends_on: ["V9-04"]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [VAUD-SIGNOFF]

must_haves:
  truths:
    - "In voss team run sign-off, approve is unavailable until the human acknowledges the killed-card + misroute diff"
    - "A non-yes acknowledgement aborts sign-off non-zero; the diff is displayed before the prompt"
    - "The acknowledgement is recorded in a NEW .signoff-ack.json governance sidecar (0o600), not a mutation of run-final.json or any node JSON"
    - "A clean run (zero killed, zero misroute) skips the ack gate and proceeds to approve/reject"
    - "voss audit reads back .signoff-ack.json; an approve path is refused when risks exist and the ack is absent"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "_write_signoff_ack sidecar writer + ack gate in team_run_cmd + ack readback in the audit path"
      contains: "_write_signoff_ack"
  key_links:
    - from: "voss/harness/cli.py team_run_cmd"
      to: ".signoff-ack.json"
      via: "_write_signoff_ack after acknowledgement, before approve"
      pattern: "signoff-ack"
---

<objective>
The sign-off forcing function (VAUD-SIGNOFF): make approve unavailable until the operator acknowledges the killed-card + misroute diff, in BOTH `voss team run` sign-off and `voss audit`. The acknowledgement is recorded as a NEW `.signoff-ack.json` governance sidecar — a record alongside the audited data, never a mutation of it (reconciling the hard gate with the read-only-audit constraint).

Purpose: V7 ships a plain approve/reject prompt with no gate. V9 inserts a forced acknowledgement of risk. The ack sidecar mirrors `_persist_run_final`'s 0o600 write pattern; the run data stays frozen.
Output: `_write_signoff_ack` writer + ack gate in `team_run_cmd` + ack readback wired into the audit approve path. Wave-0 `test_signoff_forcing.py` turns GREEN.
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
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-RESEARCH.md

<interfaces>
team_run_cmd sign-off site (voss/harness/cli.py:4106-4120 — AUTHORITATIVE, what V9 wraps):
  click.echo run summary (cards: total/done/blocked/killed/rescope; em_iterations)
  decision = click.prompt("Sign off on this run (approve/reject)", type=click.Choice(["approve","reject"]))
  _persist_run_final(rf, cwd, decision=decision); echo "sign-off recorded"; raise Exit(0)
  rf is a RunFinal with .root_id, .killed_count, etc.  (snapshot.routings carries confidence_hint)

_persist_run_final (cli.py:3979-4000): mkdir parents → write_text(json.dumps(indent=2)) → chmod(0o600);
  root_id comes ONLY from rf.root_id (no user input) — the 0o600 write pattern to copy for _write_signoff_ack.

Misroute definition (V9-RESEARCH Assumption A2, Claude's discretion): a routing with
  confidence_hint is not None AND confidence_hint < 0.7. The rf does not directly carry routings;
  load them read-only via voss.harness.audit (build_audit_report / load_audit_snapshot) — those imports
  are allowed in cli.py — OR derive misroute_count from rf if it exposes it. Prefer reading the just-loaded
  snapshot via load_audit_snapshot(cwd, run_id=rf.root_id).routings to count confidence_hint < 0.7.

.signoff-ack.json schema (V9-RESEARCH A1): {"ack_ts": iso, "killed_count": int, "misroute_count": int}
  at .voss/sessions/<root_id>/.signoff-ack.json
audit approve readback (V9-RESEARCH Open Q #2/#3): voss audit checks for .signoff-ack.json;
  when killed_count>0 or misroutes present AND ack absent → refuse approve with a clear message.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add _write_signoff_ack and gate team_run_cmd's approve behind a forced acknowledgement</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py:4092-4120 (the team_run_cmd tail: rf load, summary echo, the plain approve/reject prompt to gate) — self-extension analog
    - voss/harness/cli.py:3979-4000 (_persist_run_final — the 0o600 mkdir+write+chmod pattern to copy)
    - voss/harness/audit/load.py (load_audit_snapshot(cwd, run_id=rf.root_id).routings — confidence_hint for misroute count; read-only)
    - V9-PATTERNS.md "Sign-off forcing function in team_run_cmd" (existing prompt, V9 gate, _write_signoff_ack excerpts lines 430-481) + "0o600 Sidecar Write Pattern" + Pitfall 5 (clean run must skip the ack gate, no empty-diff prompt)
    - tests/harness/audit/test_signoff_forcing.py (Wave-0 RED tests)
  </read_first>
  <action>
    Add a module-level `_write_signoff_ack(cwd: Path, root_id: str, *, killed_count: int, misroute_count: int) -> Path` mirroring `_persist_run_final`: `run_dir = cwd/".voss"/"sessions"/root_id`; `mkdir(parents=True, exist_ok=True)`; write `{"ack_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "killed_count": killed_count, "misroute_count": misroute_count}` to `run_dir/".signoff-ack.json"` via `write_text(json.dumps(..., indent=2))`; `chmod(0o600)`; return the path. root_id comes ONLY from `rf.root_id` (no user input → no traversal). In `team_run_cmd`, BEFORE the existing approve/reject prompt (cli.py:4114): compute `killed_count = rf.killed_count` and `misroute_count` by loading `load_audit_snapshot(cwd, run_id=rf.root_id).routings` and counting `r.confidence_hint is not None and r.confidence_hint < 0.7` (read-only; import load_audit_snapshot locally). When `killed_count > 0 or misroute_count > 0`: echo a risk summary line + the killed-card / misroute items, then `ack = click.prompt("Acknowledge killed/misroute risks? Type 'yes' to continue")`; if `ack.strip().lower() != "yes"` echo "Sign-off aborted — acknowledgement required." to stderr and `raise click.exceptions.Exit(1)`; on "yes" call `_write_signoff_ack(cwd, rf.root_id, killed_count=killed_count, misroute_count=misroute_count)`. When BOTH counts are 0 (Pitfall 5): SKIP the ack prompt entirely (do not prompt for an empty diff) and proceed to the existing approve/reject prompt. The `.signoff-ack.json` is a NEW file — do NOT modify `_persist_run_final` to fold the ack into run-final.json. Keep the existing approve/reject prompt + `_persist_run_final(rf, cwd, decision=decision)` + Exit(0) flow intact after the gate.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `_write_signoff_ack(tmp, "rootX", killed_count=1, misroute_count=2)` creates `.voss/sessions/rootX/.signoff-ack.json` with those counts + an `ack_ts`; mode 0o600.
    - Writing the ack creates/modifies NEITHER `run-final.json` NOR any node JSON (the ack-is-new-file test passes).
    - team_run_cmd (CliRunner, simulated non-"yes" ack input when killed/misroute present) exits non-zero with an "acknowledg" message; with "yes" it proceeds to approve/reject.
    - A clean run (0 killed, 0 misroute) does NOT prompt for an ack (Pitfall 5).
    - `.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py -x` exits 0.
  </acceptance_criteria>
  <done>team_run_cmd gates approve behind a forced acknowledgement; ack written to a new 0o600 .signoff-ack.json; clean runs skip the gate; run data untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Wire ack readback into voss audit (refuse approve when risks exist and ack absent)</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py audit_cmd (added in V9-04) — the command to extend with an approve readback path
    - voss/harness/audit/report.py (build_audit_report → report.signoff_ack from .signoff-ack.json; report.snapshot.routings + killed cards for risk presence)
    - V9-RESEARCH.md Open Q #2/#3 (recommendation: an interactive forcing-function display in audit that reads the ack; refuse approve when risks exist and ack absent) + Assumption A4
    - tests/harness/audit/test_signoff_forcing.py (any audit-side approve-readback test)
  </read_first>
  <action>
    Extend `audit_cmd` (or add an `--approve` flag handled within it) so that when the operator requests approval of an audited run: read `report.signoff_ack` (from `.signoff-ack.json` via build_audit_report); compute whether risks exist (killed cards present OR a routing with `confidence_hint < 0.7`); if risks exist AND `report.signoff_ack is None`, echo a clear message instructing the operator that acknowledgement is required (e.g. "approve refused: killed-card/misroute risks unacknowledged — run `voss team run` sign-off to acknowledge") to stderr and `raise SystemExit(1)`. When the ack is present (or no risks), permit approval (record-only echo; do NOT mutate audited run data — approval recording, if any, writes only to the governance sidecar already present). Keep the default (no `--approve`) path purely read-only rendering from V9-04 unchanged. Choose the flag form per RESEARCH A4 (a `--approve` flag on `audit_cmd` is acceptable; do not add a separate subgroup unless the test demands it).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py tests/harness/audit/test_audit_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `voss audit <run_with_kills> --approve` with NO `.signoff-ack.json` present → exit non-zero with a message naming acknowledgement.
    - `voss audit <run_with_kills> --approve` WITH a `.signoff-ack.json` present → permitted (no refusal).
    - The default `voss audit` (no `--approve`) path remains read-only and unchanged (test_audit_cli.py still green).
    - `.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py tests/harness/audit/test_audit_cli.py -x` exits 0.
  </acceptance_criteria>
  <done>voss audit reads back the ack; approve refused when risks exist and ack absent; default render path unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator ack input → governance record | The "yes" acknowledgement is operator input that authorizes approve |
| .signoff-ack.json write → run directory | The ONLY new write into the run dir; must not touch audited data |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-06-01 | Elevation of Privilege | bypassing the forcing function (approve without ack) | mitigate | team_run_cmd aborts non-zero on any non-"yes"; voss audit --approve refuses when risks exist and ack absent — the gate is the security control |
| T-V9-06-02 | Tampering | ack write mutating audited run data | mitigate | `.signoff-ack.json` is a NEW file; _persist_run_final + node JSONs untouched; the ack-is-new-file test asserts this; frozen-schema diff gate in V9-07 confirms zero drift |
| T-V9-06-03 | Tampering | path traversal via root_id on ack write | mitigate | root_id sourced ONLY from rf.root_id (a SessionTreeNode UUID), never user input (same control as T-V7-05); 0o600 perms |
| T-V9-06-04 | Tampering | .signoff-ack.json write race (two processes) | accept | Single-operator interactive flow; low risk. 0o600 perms limit exposure; atomic-rename not warranted for a solo-dev governance record |
| T-V9-06-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies; stdlib + click (existing) only |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py -x` — VAUD-SIGNOFF green.
- `.venv/bin/python -m pytest tests/harness/audit/test_audit_cli.py -x` — audit CLI still green (no regression from the --approve path).
- The ack-is-new-file test confirms run-final.json + node JSONs untouched.
</verification>

<success_criteria>
- team_run_cmd gates approve behind a forced killed/misroute acknowledgement; clean runs skip the gate.
- Ack recorded in a new 0o600 .signoff-ack.json; audited run data untouched.
- voss audit reads back the ack and refuses approve when risks exist and ack absent.
- test_signoff_forcing.py green; audit CLI tests preserved.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-06-SUMMARY.md` when done.
</output>
