---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: milestone
status: executing
last_updated: "2026-05-15T00:00:00Z"
last_activity: 2026-05-15 — T2 CONTEXT.md captured. 8 implementation decisions across DiffModal wiring (tool-side hunks), gather error semantics (return_exceptions=True), BatchRecord nested under T1 IterationRecord, harness.toml `[agent]` section locked for T1+T2 co-location, fs_edit retained alongside fs_edit_many, fs_read_many 30KB per-file cap, mid-batch cancel via gather, batch.* telemetry symmetric with iteration.*. SPEC.md (6 reqs PAR-01..06) + CONTEXT.md both locked. Ready for /gsd-plan-phase T2.
progress:
  total_phases: 8
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

**Phase:** M6 — npm Wrapper
**Status:** Plans ready to execute. 5 PLAN.md files across 4 waves verified by gsd-plan-checker (iteration 2 of 3, all blockers + warning resolved). RESEARCH.md, PATTERNS.md, VALIDATION.md all in place.
**Goal:** Publish `voss` as an npm package vendoring pinned Python 3.12 (python-build-standalone) + the v0.1 wheel via esbuild-pattern optionalDependencies across 5 platforms.
**Critical research finding:** Unscoped `voss` npm name is TAKEN (registered April 2023). D-12 fallback OPERATIVE — main package = `@voss/cli`. M6-01 must create `@voss` org as first BLOCKING human task.
**Next move:** `/gsd-execute-phase M6` (Wave 1 = M6-01 pauses at Task 0 human-action checkpoint for npm org + token creation). `/clear` recommended before execute for fresh context window.
**Rust status:** `crates/` frozen-spike — kept in source control, not on v0.1 ship path. Do not edit. Resurrect on dogfood signal only.
**Last activity:** 2026-05-13 — M6 plans created and verified. Wave structure: 1 (M6-01 names+scaffold), 2 (M6-02 shim || M6-03 build scripts), 3 (M6-04 release workflow), 4 (M6-05 smoke + README). All 5 NPM-01..05 requirements covered. Three [BLOCKING] human-action gates (org creation, site-packages size-budget verify before publish fan-out, v0.1.0 release approval).

## Phase Status

| Phase | Name | Status |
|---|---|---|
| M0 | Scope Lock | Ready to plan |
| M1 | Harness Happy Path | Ready to execute (7 plans) |
| M2 | Project Cognition | Ready to execute (7 plans) |
| M3 | Language Validation | Ready to execute (6 plans, 4 waves) |
| M4 | Voss-authored Harness Loop | Complete (5 plans, 5 waves) |
| M5 | Eval and Distribution Prep | 6/6 plans summarized (M5-01..M5-06). |
| M6 | npm Wrapper | Plans ready to execute (5 plans, 4 waves, verified iteration 2/3). |
| M7 | SDK Polish | Plans ready to execute (6 plans, 6 waves, verified iter 2/3 PASS clean). |

## Recent Activity

- 2026-05-15 — Phase T3 context gathered (4 decision areas, 16 decisions D-01..D-16: MCP subsystem shape — 3-file layout + lazy-on-first-call + new `voss/harness/lifecycle.py` reap hook + mcp.yml schema with env-interp/{cwd}/timeout/env-allowlist; httpx + tool plumbing — single shared AsyncClient in new `voss/harness/net.py` NetSession + flat `web_search.py` BraveBackend + `make_toolset(cwd, *, net=None)` backward-compatible kwarg; permission gate — `is_network` stored on ToolEntry + net-check before mode-tier in `PermissionGate.check` + MCP scope applied at registration time + tool-result-string denial UX; CLI + telemetry — `voss mcp {list,call}` argparse subparser + `--arg key=value` JSON-typed + `redact_url` pure helper in telemetry.py wrapped by NetSession + `NetSession.acquire(tool_name)` rate-limit site). Open questions for researcher: locate existing teardown hook before adding lifecycle.py, pin MCP `destructiveHint` protocol version, source Codex launcher path.
- 2026-05-15 — Phase T3 SPEC.md authored (7 reqs NET-01..NET-07, ambiguity 0.13, 13 acceptance criteria, 10-item out-of-scope list). 5 Socratic rounds: web_fetch (1MB cap, 30s timeout, HTTP GET only), web_search (Brave only, env-key opt-in), MCP stdio client (Codex pattern lift, filesystem ref server only in CI), allow_net gate, query-stripped URL telemetry, per-tool token bucket (web_fetch 30/min, web_search 10/min, MCP unlimited), streaming OUT.
- 2026-05-15 — Phase T2 planned (6 plans across 5 waves: T2-01 BatchRecord + recorder API, T2-02 max_parallel_reads config, T2-03 partition scheduler + BatchInvariantError + telemetry, T2-04 fs_edit_many atomic multi-edit, T2-05 fs_read_many bundle, T2-06 micro-benchmark + human-verify checkpoint); plan-checker passed iter 1/3 with 1 blocker (VALIDATION map numbering misalignment — fixed by orchestrator) + 3 advisory warnings (T2-02 T1-04 hedging, 5-wave vs 4-wave, T2-06 Plan import path) shipped as-is.
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
- 2026-05-12 — Phase M4 completed all five waves. DOG-01..08 are covered by the five authored `.voss` harness files, `voss check/compile voss/harness/agent/`, cache freshness validation, compiled backend parity/smoke tests, CI gate, README eager-compile one-liner, and `voss doctor` harness-cache row.
- 2026-05-11 — Phase M5 context gathered (7 decision areas: `voss eval` CLI subcommand emitting JSONL + Markdown under `.voss/eval/<timestamp>/`; five golden task fixtures under `tests/eval/golden/NN-slug/` with per-task `task.toml` + isolated temp git repos; LLM-as-judge scorer with rubric per task and JSON-mode `Verdict {verdict, confidence, rationale}`; live-by-default with `--stub` for hermetic smoke at k=3 runs per task; cost from `RunRecord.cost_usd`, confidence from `Plan.confidence`, Pearson r reported; wheel-in-tempvenv packaging smoke in `tests/packaging/` with PyPI publish deferred and README install polish; measurement-only ship posture — no CI threshold gate, human reads report).
- 2026-05-12 — Roadmap extended with M6 npm Wrapper phase. Goal: publish `voss` as an npm package that vendors a pinned Python interpreter + the v0.1 wheel so JS-ecosystem developers can `npm i -g voss` (or `npx voss`) without managing Python. Pattern: pyright-style bundled-Python distribution; npm package vendors the same wheel M5 verifies — no JS reimplementation. NPM-01..05 added to REQUIREMENTS.md (total v0.1 reqs 54 → 59). Cross-cutting: Python source unchanged, DIST-01 stays deferred, Windows enters v0.1 only via npm with optional drop to mac+linux if vendoring proves expensive.
- 2026-05-12 — SDK contract landed: `docs/sdk.md` + expanded `voss.harness.__all__` (8 symbols) + stability docstrings on `voss_runtime` and `voss.harness` + `tests/packaging/test_public_api.py` pinning both `__all__` sets against drift. Four known public-API gaps filed as v0.2 candidate phase M7 — SDK Polish (SDK-01 Renderer protocol, SDK-02 tool_entry_from_callable, SDK-03 read-only SessionView, SDK-04 RuntimeConfig.from_toml, SDK-05 stable provider registration). Not committed to a v0.1 milestone; lands when embedder demand surfaces.
- 2026-05-13 — M7 SDK Polish promoted from v0.2 candidate to formal v0.1 phase. SDK-01..05 moved into REQUIREMENTS.md active section + traceability row; ROADMAP.md gets full M7 phase block (goal, required surface sketch, capabilities, 5 success criteria, cross-cutting constraints). Total v0.1 reqs 59 → 64. Phase is pure promote-existing-internals — no new behavior, only renames + re-exports + docstrings + test_public_api.py regression entries. Ordering preference: M7 before v0.1.0 publish for surface stability; falls back to 0.1.1 minor bump if M6 ships first (pre-1.0 minor breaks allowed per docs/sdk.md).
- 2026-05-13 — M7 context + plans landed. CONTEXT.md captures 26 base decisions D-01..D-26 (synthesized from ROADMAP M7 block + REQUIREMENTS SDK-01..05 + scouted internals; user declined interactive discuss-phase given scope tightness). RESEARCH.md (gsd-phase-researcher HIGH confidence) surfaced 7 corrections + 5 resolved open questions; CONTEXT refined with R-01..R-13 lock-in (notably: Renderer has 11 methods not 9; factory delegates to existing @tool decorator; sync callables get async-shim wrap; SessionRecord.runs is list[dict] so view_session uses defensive .get(); SDK-05 is ATOMIC — kwarg + ModelProvider isinstance validation + register_provider re-export + 10-callsite audit all in one wave; 6-wave structure with waves 1-4 parallel, wave 5 sequential after 4, wave 6 integration depends on all). 6 PLAN.md files + M7-PATTERNS.md (10 reusable patterns). gsd-plan-checker iter 2/3 PASS clean — iter 1 raised 4 blockers (all in M7-06 Task 2 — the M7 success contract test_sdk_embedding.py) + 5 warnings; planner revision resolved all with deterministic FORBIDDEN_PRIVATE_PATHS allowlist replacing comment-scanning, UUID-fixture provider names replacing hardcoded names, noqa-pinned public-API imports + live-imports test defending against linter strip, positive-registration evidence cross-linked between test 5 (raise-on-duplicate) and test 7 (end-to-end embedding), and a checkpoint:phase-final wrapper on the pytest -x acceptance gate.

## Notes

- Existing `.planning/phases/01-*` through `07-*` directories remain historical planning artifacts unless explicitly archived.
- Next operational step after this rebaseline is to plan M0, then M1.
