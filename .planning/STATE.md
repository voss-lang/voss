---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: milestone
status: executing
last_updated: "2026-05-11T20:30:00.000Z"
last_activity: 2026-05-11 — Phase M5 context gathered (7 decision areas: voss eval CLI + JSONL/Markdown artifact under .voss/eval/, 5 golden tasks with per-task temp git fixtures, LLM-as-judge with rubric per task.toml, live-by-default + --stub for hermetic smoke at k=3, wheel-in-tempvenv packaging smoke, measurement-only ship posture).
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# State: Voss

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-05-10)

**Core value:** A developer can give Voss a repo task and get bounded, inspectable, resumable AI coding work, while the most important agent logic is expressible as compiler-checkable `.voss` workflows instead of prompt soup.
**Current focus:** M0 — Scope Lock planning rebaseline from `.vscode/voss_v_0_1_scope_lock.md`.

## Current Position

**Phase:** M5 — Eval and Distribution Prep
**Status:** Context gathered — ready to plan
**Goal:** Measure v0.1 quality and prep package install.
**Last activity:** 2026-05-11 — Phase M5 context gathered (7 decision areas: voss eval CLI + JSONL/Markdown artifact under .voss/eval/, 5 golden tasks with per-task temp git fixtures, LLM-as-judge with rubric per task.toml, live-by-default + --stub for hermetic smoke at k=3, wheel-in-tempvenv packaging smoke, measurement-only ship posture).

## Phase Status

| Phase | Name | Status |
|---|---|---|
| M0 | Scope Lock | Ready to plan |
| M1 | Harness Happy Path | Ready to execute (7 plans) |
| M2 | Project Cognition | Ready to execute (7 plans) |
| M3 | Language Validation | Ready to execute (6 plans, 4 waves) |
| M4 | Voss-authored Harness Loop | Ready to execute (5 plans, 5 waves) |
| M5 | Eval and Distribution Prep | Context gathered — ready to plan |

## Recent Activity

- 2026-05-07 — Project initialized via `/gsd-new-project`.
- 2026-05-07 — Initial runtime/compiler/language roadmap created for phases 1-6.
- 2026-05-09 — Harness and Rust planning added, including a later Rust port.
- 2026-05-10 — Scope lock reframed v0.1 around a harness-led MVP with `.voss` as workflow control layer.
- 2026-05-10 — Roadmap rebaselined to M-prefixed phases M0-M5; Rust deferred until Python harness usage is proven.
- 2026-05-10 — Phase M1 context gathered (4 decision areas: voss edit scope, permission modes, voss doctor, session redaction).
- 2026-05-10 — Phase M1 planned: 7 plans across 3 waves; plan-checker passed after 1 revision (3 blockers + 4 warnings cleared).
- 2026-05-10 — Phase M2 context gathered (4 decision areas: analyze + index lifecycle, cognition file schemas, session move + per-run ledger, context injection on resume).
- 2026-05-11 — Phase M2 planned: 7 plans across 6 waves (M2-00 scaffold + M2-01..06); plan-checker passed after 1 revision (4 blockers + 5 warnings cleared).
- 2026-05-11 — Phase M3 context gathered (4 decision areas: hermetic run + check speed via auto-StubProvider + static check, sample coverage via support memory.episodic + research try/catch + use, slimmed legacy-06 test plan under tests/examples/, framing via README section + sample headers + docs/voss-vs-python.md).
- 2026-05-11 — Phase M3 planned: 6 plans across 4 waves (M3-01 analyzer guard + M3-02 auto-stub + M3-03 coverage fixtures parallel in W0; M3-04 sample extensions W1; M3-05 e2e suite repoint W2; M3-06 speed gate + framing docs W3); plan-checker passed iteration 2 after 1 revision (3 warnings cleared: M3-04 promoted to W1 for M3-02 hook ordering; M3-02 must_haves 4-test alignment; M3-06 D-14 negation phrasing audit).
- 2026-05-11 — Phase M4 context gathered (5 decision areas: pipeline split across loop/router/planner/executor/reviewer.voss with thin .voss control flow only and Python imports compiled functions; voss check + compile extended to walk directories static-only; VOSS_HARNESS=compiled env-flag opt-in with voss/harness/agent.py kept as parity oracle and loud stale-cache failure; per-file `.voss-cache/harness/*.py` artifacts sha-keyed via _manifest.json; M4 success bar = stub-provider real turn end-to-end, live-provider parity deferred to M5).
- 2026-05-11 — Phase M4 planned: 5 plans across 5 waves (M4-01 compiler sub-plan grammar use..as + codegen auto-await W0; M4-02 dir-walk + cache.py + StaleHarnessCacheError + sandbox.write_cache W1; M4-03 5 .voss files + _run_step_loop + ToolEntry.invoke_dict + _resolve_run_turn W2; M4-04 parity test FakeProvider + DOG-07 smoke W3; M4-05 CI gate + README one-liner + doctor cache row W4); plan-checker passed iteration 2 after 1 revision (3 warnings cleared: Open Questions RESOLVED markers, M4-03 stub fallback removed with LOC-floor enforcement 20/8/8/6/12, VALIDATION config.py mismatch reconciled).
- 2026-05-11 — Phase M5 context gathered (7 decision areas: `voss eval` CLI subcommand emitting JSONL + Markdown under `.voss/eval/<timestamp>/`; five golden task fixtures under `tests/eval/golden/NN-slug/` with per-task `task.toml` + isolated temp git repos; LLM-as-judge scorer with rubric per task and JSON-mode `Verdict {verdict, confidence, rationale}`; live-by-default with `--stub` for hermetic smoke at k=3 runs per task; cost from `RunRecord.cost_usd`, confidence from `Plan.confidence`, Pearson r reported; wheel-in-tempvenv packaging smoke in `tests/packaging/` with PyPI publish deferred and README install polish; measurement-only ship posture — no CI threshold gate, human reads report).

## Notes

- Existing `.planning/phases/01-*` through `07-*` directories remain historical planning artifacts unless explicitly archived.
- Next operational step after this rebaseline is to plan M0, then M1.
