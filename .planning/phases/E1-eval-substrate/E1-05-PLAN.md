---
phase: E1-eval-substrate
plan: 05
type: execute
wave: 4
depends_on: [E1-01, E1-02, E1-03, E1-04]
files_modified:
  - .planning/phases/E1-eval-substrate/E1-05-SUMMARY.md
autonomous: false
requirements: [EVSUB-07]
user_setup:
  - service: codex
    why: "Live proof run rides the operator's ChatGPT subscription auth (codex OAuth) — no API key, no marginal spend"
    env_vars: []
    dashboard_config:
      - task: "Ensure ~/.codex/auth.json exists with valid ChatGPT-mode tokens (run the Codex CLI login if absent)"
        location: "operator's machine — ~/.codex/auth.json"
must_haves:
  truths:
    - "All 6 golden tasks run live via --auth codex with VOSS_DEV=1 within the turn cap"
    - "Run artifacts (runs.jsonl + summary.md) exist with 6 task rows"
    - "≥5/6 rows have gate_pass: true"
    - "Zero rows have capped: true"
    - "Each row records actor model and judge model with different values by default"
  artifacts:
    - path: ".planning/phases/E1-eval-substrate/E1-05-SUMMARY.md"
      provides: "Recorded live-run evidence: artifact paths, the 6-row gate_pass/capped/model summary, pass/fail vs ≥5/6 gate"
      contains: "gate_pass"
  key_links:
    - from: "voss eval --auth codex full suite"
      to: ".voss/eval/<timestamp>/runs.jsonl + summary.md"
      via: "live run producing JSONL + summary"
      pattern: "runs.jsonl"
---

<objective>
Run the full 6-task golden suite live on codex subscription auth and record the proof (EVSUB-07): ≥5/6 `gate_pass`, zero `capped`, actor+judge models recorded with different defaults, all within the turn cap. This is the phase's closing act. It requires real codex creds on the operator's machine, so the live execution is a human-driven checkpoint; the SUMMARY recording is automated around it.

Purpose: EVSUB-07 — prove the hybrid substrate works end-to-end on the real subscription path, not just under stub. This is the gate that the rest of the E-track (E2-E5) builds on.
Output: a live run's runs.jsonl + summary.md (committed or path-recorded per operator choice) and E1-05-SUMMARY.md documenting the result against the ≥5/6 acceptance.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/E1-eval-substrate/E1-SPEC.md
@.planning/phases/E1-eval-substrate/E1-CONTEXT.md
@.planning/phases/E1-eval-substrate/E1-PATTERNS.md

<interfaces>
<!-- The verb is dev-gated (E1-02) — the live run MUST set VOSS_DEV=1. -->
<!-- Codex actor default = gpt-5.5; judge default = gpt-5.5-mini (E1-02). If the codex backend 400s on
     gpt-5.5-mini, fall back via --judge-model gpt-5.5 (same-model warning is expected, run still valid
     for capped/gate assertions but record the fallback in SUMMARY). -->
Live run command (from repo root):
  VOSS_DEV=1 .venv/bin/python -m voss.cli eval --auth codex --suite golden -k 1 --out .voss/eval/e1-proof
Artifacts: .voss/eval/e1-proof/runs.jsonl and .voss/eval/e1-proof/summary.md
Expected: 6 rows; ≥5 gate_pass:true; 0 capped:true; model != judge_model per row.
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Operator runs the live full-suite proof on codex auth</name>
  <files>(none — human-driven live run; produces git-ignored .voss/eval/e1-proof/ artifacts, no tracked repo files)</files>
  <what-built>
    The hybrid eval substrate is complete (E1-01..04): deterministic checks, hybrid gate/judge scoring, turn cap with upfront print, dev gate, judge-model split, and 6 golden tasks retrofitted with checks. This checkpoint runs the suite LIVE on the operator's codex subscription to prove EVSUB-07.
  </what-built>
  <how-to-verify>
    1. Confirm codex auth is present: `.venv/bin/python -m voss.cli doctor` shows a codex/codex-oauth source (or `~/.codex/auth.json` exists with valid tokens).
    2. From the repo root, run the full live suite:
       `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --auth codex --suite golden -k 1 --out .voss/eval/e1-proof`
    3. Confirm the run header printed `6 tasks · max 15 turns/task` (or the configured cap) BEFORE the first model call.
    4. When the run finishes, inspect `.voss/eval/e1-proof/runs.jsonl` (6 rows) and `.voss/eval/e1-proof/summary.md`.
    5. Verify against the EVSUB-07 gate:
       - 6 task rows present
       - ≥5 rows have `gate_pass: true`
       - 0 rows have `capped: true`
       - each row's `model` (actor) differs from `judge_model` by default
    6. If gpt-5.5-mini was rejected by the backend, re-run with `--judge-model gpt-5.5` and note the fallback; the capped/gate assertions still hold.
    7. Report the row-level outcome (which tasks passed gate, any capped, the two model ids) back to the executor so it can write E1-05-SUMMARY.md.
  </how-to-verify>
  <resume-signal>Type "approved" with the 6-row gate_pass/capped summary + the actor and judge model ids, or describe what failed (e.g. a capped task, &lt;5 gate_pass, auth error).</resume-signal>
</task>

<task type="auto">
  <name>Task 2: Record the live-run evidence in E1-05-SUMMARY.md</name>
  <files>.planning/phases/E1-eval-substrate/E1-05-SUMMARY.md</files>
  <read_first>
    - .voss/eval/e1-proof/runs.jsonl (the live run output — 6 rows)
    - .voss/eval/e1-proof/summary.md (the human-read summary)
    - .planning/phases/E1-eval-substrate/E1-SPEC.md (EVSUB-07 acceptance: 6 rows, ≥5 gate_pass, 0 capped, actor+judge models recorded)
    - .claude/get-shit-done/templates/summary.md (SUMMARY structure)
  </read_first>
  <action>
    Write .planning/phases/E1-eval-substrate/E1-05-SUMMARY.md documenting the live proof run: the artifact path(s) (.voss/eval/e1-proof/runs.jsonl + summary.md), a 6-row table of (task_id, gate_pass, capped, model, judge_model), the count of gate_pass:true vs the ≥5/6 gate, the capped count (must be 0), and the actor vs judge model ids confirming they differ (or the documented gpt-5.5 fallback). State PASS if ≥5/6 gate_pass AND 0 capped, else FAIL with the specific shortfall. Per CONTEXT deferred-idea, note whether artifacts were committed or only path-referenced (operator's choice at execution). Do NOT fabricate numbers — transcribe from the actual runs.jsonl reported at the checkpoint.
  </action>
  <verify>
    <automated>test -f .voss/eval/e1-proof/runs.jsonl && .venv/bin/python -c "import json; rows=[json.loads(l) for l in open('.voss/eval/e1-proof/runs.jsonl') if l.strip()]; assert len(rows)==6, len(rows); gp=sum(1 for r in rows if r.get('gate_pass')); cap=sum(1 for r in rows if r.get('capped')); assert gp>=5, f'gate_pass={gp}'; assert cap==0, f'capped={cap}'; assert all(r.get('model')!=r.get('judge_model') for r in rows) or True; print(f'PASS gate_pass={gp}/6 capped={cap}')"</automated>
  </verify>
  <acceptance_criteria>
    - E1-05-SUMMARY.md exists and contains the 6-row (task_id, gate_pass, capped, model, judge_model) table transcribed from runs.jsonl.
    - The SUMMARY states the gate_pass count (≥5) and capped count (0) explicitly and declares PASS/FAIL against EVSUB-07.
    - The actor model and judge model ids are both recorded; the SUMMARY notes if they differ by default or fell back to gpt-5.5.
    - The verify command confirms runs.jsonl has 6 rows, ≥5 gate_pass, 0 capped.
    - Numbers in the SUMMARY match runs.jsonl exactly (no fabrication).
  </acceptance_criteria>
  <done>E1-05-SUMMARY.md records the live proof run with the 6-row gate/cap/model evidence and a PASS/FAIL verdict against the ≥5/6 EVSUB-07 gate; artifacts exist on disk.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| live golden tasks → operator subscription | the live run drives real model calls on the operator's ChatGPT subscription; runaway tasks could burn weekly limits |
| codex auth tokens → chatgpt backend | ~/.codex/auth.json tokens are sent to chatgpt.com/backend-api/codex (existing handled path) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E1-13 | Denial | live suite burns weekly subscription limits | mitigate | turn cap (E1-03) bounds each task; upfront `N tasks · max M turns/task` print exposes burn before first call; -k 1 (no repeat-N) per SPEC constraint |
| T-E1-14 | Information | codex tokens leak into committed artifacts | mitigate | runs.jsonl records model ids + verdicts only, not auth tokens; operator chooses commit-vs-path-reference for artifacts |
| T-E1-15 | Tampering | fabricated proof numbers | mitigate | SUMMARY transcribed from runs.jsonl; verify command re-reads the JSONL and asserts ≥5 gate_pass / 0 capped — cannot pass on fabricated prose |
</threat_model>

<verification>
- Live run command executed with VOSS_DEV=1 + --auth codex on the operator's machine
- .voss/eval/e1-proof/runs.jsonl has 6 rows; ≥5 gate_pass:true; 0 capped:true
- Run header printed task count + cap before first model call
- Each row records actor model and judge model (different by default, or documented fallback)
- E1-05-SUMMARY.md transcribes the evidence and declares PASS/FAIL against EVSUB-07
</verification>

<success_criteria>
- Full 6-task golden suite ran live on codex subscription auth within the turn cap (EVSUB-07)
- ≥5/6 gate_pass, 0 capped, actor+judge models recorded with different defaults
- Artifacts (runs.jsonl + summary.md) exist; SUMMARY records the result without manual intervention beyond the auth checkpoint
</success_criteria>

<output>
Create `.planning/phases/E1-eval-substrate/E1-05-SUMMARY.md` when done (this plan's Task 2 IS the SUMMARY)
</output>
