---
phase: E2-golden-tasks-repo-matrix
plan: 09
type: execute
wave: 3
depends_on: ["E2-05", "E2-06", "E2-07", "E2-08"]
files_modified:
  - tests/eval/test_matrix_stub.py
autonomous: false
requirements: [EVGLD-07]
user_setup:
  - service: codex
    why: "Live matrix proof run rides the ChatGPT subscription via voss --auth codex at $0; gated AFTER E1-05 establishes a working golden baseline"
    env_vars:
      - name: VOSS_DEV
        source: "Set VOSS_DEV=1 in the shell to unlock the internal eval verb (E1-02 gate)"
must_haves:
  truths:
    - "The full 12-cell matrix runs green under --stub --suite matrix (returncode 0, 12 rows) on a machine with all toolchains present"
    - "Every matrix cell's JSONL row carries the required field set (E1 schema)"
    - "A live-proof note documents the exact codex-auth command + acceptance (>=9/12 gate_pass, 0 capped), gated behind E1-05, recorded in the SUMMARY"
    - "The golden suite's 66 tests remain green; golden/ stays pristine (matrix is a separate --suite)"
  artifacts:
    - path: "tests/eval/test_matrix_stub.py"
      provides: "Full 12-cell stub-run integration test (test_full_matrix_stub_run) now active (fixtures + task.tomls present)"
      contains: "test_full_matrix_stub_run"
  key_links:
    - from: "tests/eval/test_matrix_stub.py"
      to: "voss/eval/runner.py run_suite(suite='matrix')"
      via: "subprocess voss eval --stub --suite matrix over all 12 cells"
      pattern: "--suite.*matrix"
---

<objective>
Close out E2: prove the assembled 12-cell matrix runs green end-to-end in stub mode (EVGLD-07), and document the manual live-proof run that the developer executes on codex auth (gated after E1-05). By this wave all fixtures (02/03/04), task.tomls (05/06/07), and runner infra (08) exist — plan-01's skip-guarded stub cells and `test_full_matrix_stub_run` now activate.

Purpose: A green hermetic matrix run is the automated phase gate; the live run is the human-verified product proof that the agent's cognition + edits hold across py/rust/ts shapes. The live run is NOT in the automated loop (subscription-gated, turn-capped).
Output: matrix stub suite green; a documented live-proof procedure + recorded result in the SUMMARY.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-RESEARCH.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-VALIDATION.md
@.planning/phases/E1-eval-substrate/E1-SPEC.md

<interfaces>
<!-- The stub-run surface. All cells exist by this wave. -->
CLI: VOSS_DEV=1 voss eval --stub --suite matrix [-k 1] [--out DIR] [--auth none]
CLI (live): VOSS_DEV=1 voss eval --suite matrix --auth codex --require-all-toolchains
run_suite(suite="matrix", ...) → writes .voss/eval/<run>/runs.jsonl + summary.md
12 cell ids: py-01-analyze py-02-plan-only py-03-approved-edit py-04-validation py-05-resume py-06-fetch-summarize
             rust-01-analyze rust-03-approved-edit rust-04-validation
             ts-01-analyze ts-03-approved-edit ts-04-validation
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Activate + verify the full 12-cell matrix stub run (EVGLD-07)</name>
  <files>tests/eval/test_matrix_stub.py (verify-only; plus any minor task.toml/fixture fix surfaced by the real stub run)</files>
  <read_first>
    - tests/eval/test_matrix_stub.py (plan-01 scaffold — test_matrix_cell_stub parametrized over 12 ids + test_full_matrix_stub_run, both skip-guarded on missing matrix dir; now the dir exists so they activate)
    - tests/eval/test_voss_eval_stub.py lines 11-31 (REQUIRED_FIELDS sentinel) + lines 207-227 (parametrized golden stub pattern the matrix test mirrors)
    - E2-RESEARCH.md §Validation Architecture lines 686-694 (EVGLD-08/full-stub-run row) + Hermetic vs Live boundary lines 690-694
    - E2-VALIDATION.md lines 47-57 (per-task map: matrix stub end-to-end row)
  </read_first>
  <action>
    Run the full matrix under stub to confirm the assembled suite is green. Execute `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --stub --suite matrix --auth none -k 1 --out /tmp/e2-matrix-stub` and confirm returncode 0 with 12 JSONL rows. If any cell fails to load or run, fix the offending task.toml/fixture (do NOT weaken the test). Confirm the plan-01 stub tests now pass with the matrix present: `test_matrix_cell_stub` (12 parametrized) + `test_full_matrix_stub_run`. If plan-01 left those tests skip-guarded on `tests/eval/matrix` existence, they auto-activate; verify they are no longer skipped (the dir now exists). Also confirm the preflight line prints `toolchains: pyOK rustOK tsOK` on this all-toolchains-present machine (RESEARCH Environment Availability: all three present). Do NOT modify golden/ or the 66 existing tests. This task is purely integration verification + any minor task.toml/fixture fix surfaced by the real stub run.
  </action>
  <verify>
    <automated>VOSS_DEV=1 .venv/bin/python -m voss.cli eval --stub --suite matrix --auth none -k 1 --out /tmp/e2-matrix-stub && test $(wc -l < /tmp/e2-matrix-stub/runs.jsonl) -eq 12 && .venv/bin/python -m pytest tests/eval/ -q</automated>
  </verify>
  <done>Full 12-cell matrix runs green under stub (12 rows); all matrix tests active and passing; full tests/eval/ suite green; preflight shows all toolchains present; golden/ untouched.</done>
  <acceptance_criteria>
    - `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --stub --suite matrix --auth none -k 1 --out /tmp/e2-matrix-stub` exits 0 and `/tmp/e2-matrix-stub/runs.jsonl` has 12 lines
    - `.venv/bin/python -m pytest tests/eval/test_matrix_stub.py -q` passes with 0 skipped (matrix dir present → all parametrized cells active)
    - `.venv/bin/python -m pytest tests/eval/ -q` is fully green (existing 66 + all matrix tests: suite, runner, stub, summary)
    - Preflight printed all-present: the stub run stdout contains `toolchains:` and `OK` for py/rust/ts (no MISSING on this machine)
    - golden/ pristine: `git status --porcelain tests/eval/golden` shows no changes
  </acceptance_criteria>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 2: Live matrix proof run on codex auth (manual, gated after E1-05)</name>
  <files>(none — out-of-band live run; artifacts land under git-ignored .voss/eval/, no tracked repo files modified)</files>
  <read_first>
    - .planning/phases/E1-eval-substrate/E1-SPEC.md (Requirement 7 live-proof contract — E2's live run is gated AFTER E1-05's golden baseline)
    - E2-RESEARCH.md §E1/E2 Dependency Boundary lines 547-549 (E2 live run gated after E1-05; sequencing convention, not code dep) + Assumptions A1/A2 lines 772-773 (cognition reliability + cargo 120s)
    - E2-VALIDATION.md lines 73-76 (Manual-Only Verifications: live cognition + edit correctness per language)
  </read_first>
  <action>
    Pause for the developer to run the live matrix proof on codex subscription auth per the &lt;how-to-verify&gt; steps, AFTER confirming E1-05's golden live run has passed (>=5/6 gate_pass). If E1-05 has not passed, the developer records this checkpoint as DEFERRED in E2-09-SUMMARY.md (matching the V9-07 deferred-human-verify precedent) and does NOT attempt the live run — the stub gate (Task 1) is sufficient for phase completion. This is an out-of-band human action; nothing is auto-executed. Record the run path, gate_pass count, and per-cell observations in the SUMMARY.
  </action>
  <verify>Human types "approved" with the gate_pass count (e.g. "approved 11/12"), or "deferred — E1-05 pending", or describes failures. No automated gate — this is the manual product proof.</verify>
  <done>Live codex-auth matrix run recorded with >=9/12 gate_pass + 0 capped + 0 skipped, OR recorded DEFERRED pending E1-05; result captured in E2-09-SUMMARY.md.</done>
  <what-built>
    The 12-cell repo-shape matrix is assembled and green in stub mode. The live proof run drives the actual agent against all 12 cells on subscription auth, proving cognition + edits hold across Python, Rust, and TypeScript project shapes (D-04). This is the product-level proof the E-track exists for.

    DEPENDENCY GATE: This live run MUST NOT run until E1-05 (the golden live proof run) has established a working baseline of >=5/6 gate_pass on the golden suite. E1-05 is a separate, still-unexecuted plan. If E1-05 has not yet passed, record this checkpoint as DEFERRED — the stub gate (Task 1) is sufficient for phase completion; the live proof can close in a later session once E1-05 lands.
  </what-built>
  <how-to-verify>
    PRECONDITION: confirm E1-05 has passed (golden live run >=5/6 gate_pass, 0 capped). If not, mark DEFERRED and stop here.

    1. Ensure all three toolchains are present (this machine: py/rust/node all verified). Run with the strict flag so a missing toolchain fails fast rather than silently skipping the proof:
       `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite matrix --auth codex --require-all-toolchains -k 1 --out .voss/eval/e2-live-proof`
    2. Confirm the preflight line prints `toolchains: pyOK rustOK tsOK` before the first model call.
    3. Let the run complete within the per-task turn cap (E1 max_turns=15). No runaway — the cap + subscription auth keep spend at $0 marginal.
    4. Inspect `.voss/eval/e2-live-proof/summary.md` and `runs.jsonl`. ACCEPTANCE: 12 task rows; at least 9/12 with `gate_pass: true`; zero `capped` rows; zero `skipped` rows (all toolchains present); the analyze cells' architecture.md named the language-correct manifest (cognition gate held); the approved-edit cells landed the rename and kept the repo green.
    5. Record the run path + the gate_pass count + any per-cell observations in E2-09-SUMMARY.md.
  </how-to-verify>
  <resume-signal>Type "approved" with the gate_pass count (e.g. "approved 11/12"), or "deferred — E1-05 pending", or describe failures.</resume-signal>
  <acceptance_criteria>
    - PRECONDITION confirmed: E1-05 golden live run passed (>=5/6 gate_pass) — OR checkpoint recorded DEFERRED
    - If run: 12 task rows; >=9/12 gate_pass: true; 0 capped; 0 skipped (all toolchains present, --require-all-toolchains used)
    - Cognition held: analyze cells' architecture.md named the language-correct manifest token
    - Result (gate_pass count or DEFERRED) recorded in E2-09-SUMMARY.md
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| live run → subscription auth | The live proof rides codex auth at $0 marginal; turn cap + require-all flag bound spend and prevent silent-skip masquerading as proof |
| stub run → hermetic | The stub gate makes zero model calls; cmd checks (cargo/npm/pytest) execute only in isolated fixture copies |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-22 | Denial | runaway live run burning subscription | mitigate | E1 max_turns=15 cap per task (unchanged); the live run is single-k, manual, turn-capped; --require-all-toolchains fails fast pre-model on misconfiguration. |
| T-E2-23 | Spoofing | live proof passing via silent toolchain skip | mitigate | `--require-all-toolchains` forces a hard failure if any toolchain is absent, so the proof cannot pass with skipped cells; acceptance requires zero skipped rows. |
| T-E2-24 | Tampering | cmd checks executing in repo root during live run | mitigate | run_suite always uses `_prepare_fixture` temp isolation; cargo/npm/pytest run only in the per-task copy (E1 contract). |
| T-E2-SC | Tampering | npm/pip/cargo installs | n/a | No package installs; the live run only executes the committed fixtures' offline test commands. |
</threat_model>

<verification>
- Automated phase gate (Task 1): full 12-cell stub run green, all tests/eval/ green, golden/ pristine.
- Manual product proof (Task 2): live codex-auth run >=9/12 gate_pass, 0 capped, 0 skipped — OR recorded DEFERRED pending E1-05.
</verification>

<success_criteria>
- EVGLD-07 satisfied: matrix stub-run green (12 rows) + a documented/executed (or DEFERRED) live-proof procedure
- Full tests/eval/ suite green; golden suite + its 66 tests unaffected
- Live run gated behind E1-05; bounded by turn cap + require-all flag
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-09-SUMMARY.md` when done
</output>
