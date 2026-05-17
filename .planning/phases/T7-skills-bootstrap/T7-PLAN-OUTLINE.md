---
phase: T7
slug: skills-bootstrap
type: plan-outline
created: 2026-05-17
---

# Phase T7 — Skills Bootstrap — Plan Outline

> Manifest for chunked per-plan detailing. Drives `/gsd:execute-phase` spawns.
> Every SKL-01..06 requirement maps to >=1 plan. Wave order is forced by shared
> file ownership of `voss/harness/skill_registry.py` and
> `tests/skills/test_skills_smoke.py` (every skill plan edits both).

| Plan ID | Objective | Wave | Depends On | Requirements |
|---------|-----------|------|------------|--------------|
| T7-01 | **Test scaffold + shared seam.** Create `tests/skills/` package (`__init__.py`, `conftest.py` with `isolated_state` autouse + `git_repo`/`seed_git_repo` helper + module-level `FakeProvider` copied from `test_agent_integration.py:30-102`), `tests/skills/test_skills_smoke.py` with 7 `pytest.fail("not yet")` stubs (one per SKL-01..06 + `test_registry_count`), all 6 `tests/skills/fixtures/<skill>/` seed-repo dirs (RESEARCH §"Wave 0 Gaps"), the `voss/harness/skills/voss/` directory, and the `voss check voss/harness/skills/voss/` step inserted into the `stub` job of `.github/workflows/ci.yml` (after line 48). No `skill_registry.py` edit, no handler modules — pure seam so per-skill plans can run against a known harness. Satisfies VALIDATION Dimension 8 (every downstream task gets an automated verify or a Wave 0 dependency). | 1 | — | SKL-01, SKL-02, SKL-03, SKL-04, SKL-05, SKL-06 |
| T7-02 | **Deterministic skills (Python-only, no `.voss`).** Implement SKL-01 `rename-symbol` (`voss/harness/skills/rename_symbol.py`: anchor + `fs_grep`/`fs_edit` heuristic per RESEARCH discretion call; explicit `gate.check("fs_edit", ..., is_mutating=True)` before every mutating invoke — landmine #3/Pitfall 2; `plan` mode refuses cleanly, no escalation per D-09/D-11) and SKL-06 `voss-lint-as-skill` (`voss/harness/skills/voss_lint_as_skill.py`: direct `voss.parser.parse()` + `voss.analyzer.analyze()` path, inline `rglob("*.voss")`, NO private `voss/cli.py` helper imports — Pitfall 7; emit the FROZEN M11 JSON schema `{version, findings:[{file,line,col,rule,severity,msg,hint}]}` per D-12 via `click.echo(json.dumps(...))`). Register both as `SkillEntry`s in `default_skill_registry()` (`mutating=True` / `mutating=False` per D-09/D-10). Turn `test_rename_symbol`, `test_voss_lint`, and `test_registry_count` (asserts 7 entries) green. No `.voss` companions (D-06). | 2 | T7-01 | SKL-01, SKL-06 |
| T7-03 | **Read-only agentic skills + `.voss` companions.** Implement SKL-03 `summarize-diff` (`summarize_diff.py`: `run_turn` via `asyncio.run`, agent calls `git_diff`, emits structured markdown `## Title`/`## Summary`/`## Changes` per D-12; `mutating=False`) and SKL-05 `audit-cognition` (`audit_cognition.py`: `cognition.load()` + `drift_check()` preamble per PATTERNS, prompt forbids file writes + emits `PROPOSAL:` block, `mutating=False`, asserts `architecture.md`/`VOSS.md` unchanged post-run — D-10/Pitfall 3). Author companions `voss/harness/skills/voss/summarize-diff.voss` + `audit-cognition.voss` (both must pass `voss check` — Pitfall 5; `fn` + `ctx(budget)` + `yield ask()` fallback shape). Register both `SkillEntry`s. Turn `test_summarize_diff` + `test_audit_cognition` green under `FakeProvider`. | 3 | T7-01, T7-02 | SKL-03, SKL-05 |
| T7-04 | **Mutating agentic skills + `.voss` companions.** Implement SKL-02 `add-test` (`add_test.py`: `run_turn`, agent locates a public fn and writes a pytest test with a failing assertion via `fs_write` to `tests/test_<module>.py`; pytest framework confirmed per RESEARCH discretion; `mutating=True`) and SKL-04 `port-py-to-voss` (`port_py_to_voss.py`: `run_turn`, agent translates an input Python file to `.voss` using classify/support/research sample shapes, writes via `fs_write`; `mutating=True`; `args[0]` = source path). Author companions `voss/harness/skills/voss/add-test.voss` + `port-py-to-voss.voss` (`voss check`-pass; port companion models `research.voss` shape per PATTERNS). Register both `SkillEntry`s. Turn `test_add_test` (`pytest --collect-only` finds new test) + `test_port_py_to_voss` (`voss check` exits 0 on generated `.voss`) green under `FakeProvider`. All mutation through gated `fs_write`/`fs_edit`, no escalation (D-09/D-11). | 4 | T7-01, T7-02, T7-03 | SKL-02, SKL-04 |

## Wave Dependency Notes

- **Wave 1 (T7-01):** Standalone foundation. Creates the entire `tests/skills/`
  seam + `voss/harness/skills/voss/` dir + CI gate. Touches `tests/skills/*`
  and `.github/workflows/ci.yml` only — zero overlap with skill plans, so it
  is the sole Wave 1 plan and a hard dependency for all others.
- **Serialized Waves 2→3→4 (file-ownership forced):** Every skill plan must
  edit two shared files — `voss/harness/skill_registry.py` (the single
  `default_skill_registry()` integration point, RESEARCH §"Pattern 1") and
  `tests/skills/test_skills_smoke.py` (turning its stub assertions green).
  Per the planner wave algorithm, `files_modified` overlap on these two files
  forces strict serialization: T7-02 (W2) → T7-03 (W3) → T7-04 (W4). The 6
  handler modules are independent (RESEARCH §"Architecture"), but the registry
  + smoke-test files are the contention points, so plans cannot run in
  parallel even though their handler logic is decoupled.
- **Grouping rationale:** Skills grouped by determinism + mutation posture so
  each plan is a coherent ~2-skill unit a single planner run can fully detail:
  T7-02 = the 2 deterministic Python-only skills (D-06, no `.voss`); T7-03 =
  the 2 read-only agentic skills (D-10); T7-04 = the 2 mutating agentic skills
  (D-09). T7-02 ahead of the agentic plans because it also lands the
  `test_registry_count` smoke guard (Pitfall 6) and is provider-free, giving
  the fastest hermetic green signal before the `run_turn`/`FakeProvider`
  surface is exercised.
- **Requirement coverage:** SKL-01 (T7-02), SKL-02 (T7-04), SKL-03 (T7-03),
  SKL-04 (T7-04), SKL-05 (T7-03), SKL-06 (T7-02). T7-01 lists all six because
  its scaffold (per-skill fixtures + stub tests + `.voss` dir + CI gate) is a
  prerequisite for verifying every one. All 6 IDs appear in >=2 plans.
- **Security gate:** Each per-plan PLAN.md must carry a `<threat_model>` block.
  Core T7 invariant — skills never bypass the central permission gate;
  deterministic mutating SKL-01 must call `gate.check(..., is_mutating=True)`
  before each write and refuse cleanly in `plan` mode (RESEARCH landmine #3,
  Pitfall 2, T5 D-12 precedent). No new packages → no slopcheck / package
  legitimacy checkpoint needed (RESEARCH §"Package Legitimacy Audit").

## OUTLINE COMPLETE

Total plans: 4 (T7-01 through T7-04) across 4 waves.
