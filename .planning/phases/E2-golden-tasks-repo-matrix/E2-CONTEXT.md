# Phase E2: Golden Tasks × Repo Matrix - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning (no SPEC yet — these decisions seed EVGLD-* requirements)

<domain>
## Phase Boundary

E2 runs golden agentic tasks (analyze, plan-only, approved-edit, validation, resume) against **fixture repos in Python, Rust, and TypeScript**, proving the agent's cognition + edits hold across project shapes — not just the single `.voss`-flavored fixture E1 exercises. It is a **consumer of E1's substrate** (TaskSpec + `checks` schema + runner fixture-isolation + hybrid `gate_pass`/judge scoring + turn caps + `VOSS_DEV` gate + JSONL/summary + codex auth at $0). E2 adds the **repo-matrix dimension** and per-language deterministic gates; it does not rebuild the eval engine.

**Note:** No `E2-SPEC.md` exists. These decisions seed the EVGLD-* requirements — run `/gsd-spec-phase E2` to lock them, or `/gsd-plan-phase E2` to plan directly from this CONTEXT.

</domain>

<decisions>
## Implementation Decisions

User delegated: *"apply all of your recommendations and create CONTEXT.md."* The four gray areas are resolved with recommended defaults below; the planner/SPEC may refine within these.

### Fixture repo nature (D-01)
- **Synthetic-minimal, in-repo, hermetic.** Hand-build one tiny repo per language under `tests/eval/fixtures/{python,rust,ts}/`. Each contains: a build/dependency manifest (`pyproject.toml` / `Cargo.toml` / `package.json`+`tsconfig.json`), ONE source module with a known editable function, ONE test the toolchain runs, and just enough structure for `analyze` to produce a meaningful `architecture.md`. Target ≤ ~5 files per fixture.
- **Why:** E-track is internal, on-demand, deterministic-gate-first. Synthetic-minimal gives total control over what "correct cognition + correct edit" means, zero network/vendoring, and fast cargo/tsc/pytest. Plugs straight into E1's runner fixture-isolation (runner copies the fixture per task; checks run in the isolated copy).
- **Rejected:** realistic-small vendored repos (heavier, version-drift, slower, network) — see Deferred.

### Matrix coverage (D-02)
- **Curated ~12 cells, not the full 5×3=15.** Shape-SENSITIVE tasks run on all three languages: **analyze · approved-edit · validation × {py, rust, ts} = 9 cells**. Language-AGNOSTIC tasks proven ONCE (on Python, since they exercise session/planning machinery, not project shape): **plan-only · resume · fetch-summarize = 3 cells**.
- **Why:** the 6 dropped cells (plan-only/resume/fetch-summarize on rust+ts) add no shape-specific signal but triple their cost/maintenance. Concentrate budget where project shape actually changes agent behavior (toolchain, manifest, idioms).
- **Per-language task meaning:** `validation` = run the repo's native test/build (`pytest` / `cargo test` / `npm test`/`tsc`), expect exit 0 — NOT E1's `voss check sample.voss`. `approved-edit` = land a specified function change that then compiles + passes that repo's test.

### Toolchain strategy (D-03)
- **Require-present + explicit recorded skip (never silent).** Default run: a missing language toolchain records its cells as `skipped: toolchain-absent` and surfaces that in `summary.md` — the run continues for available languages. A `--require-all-toolchains` strict flag fails the run if any of python/rust/node is missing (used for the canonical proof run). A **preflight prints which toolchains are present before the first model call** (mirrors E1's upfront run-size print).
- **Why:** matches E1's "no silent caps" ethos and the E-track's anti-false-green mission — a skipped language must read as skipped, never as green. Containerizing is heavier than the internal/on-demand posture wants (see Deferred).

### Cognition-proof depth (D-04)
- **Both behavioral AND cognition gates** (reusing E1's `checks` types — cmd-exits-0 / file-exists / file-contains):
  - **Behavioral:** the toolchain build/test exits 0 (`gate_pass`) AND the specific edit landed (file-contains the new identifier, file-absent the old) — for approved-edit/validation cells.
  - **Cognition:** the `analyze` cell asserts `architecture.md` names the language-correct tooling via file-contains (Rust → `Cargo.toml`/`cargo`; TS → `package.json`/`tsconfig`; Python → `pyproject`/`pytest`).
- **Why:** defeats lucky-edit / shape-blind false-green — the entire reason the E-track exists. Deterministic-first; the LLM-judge scores quality on top (E1 hybrid model).

### Claude's Discretion (planner)
- Exact fixture file contents + the specific editable function/test per language.
- Cell IDs / task.toml naming convention (extend the `tests/eval/golden/NN-name` pattern with a language axis, e.g. `golden/rust/03-approved-edit/`).
- Whether the matrix is encoded as separate task.toml dirs vs a parametrized suite over a shared task body.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Substrate E2 consumes (E1 — read first)
- `.planning/phases/E1-eval-substrate/E1-SPEC.md` — the `checks` schema (cmd-exit-0/file-exists/file-contains), hybrid `gate_pass`+judge result plumbing, turn caps, `VOSS_DEV` gate, judge-model split. E2 reuses ALL of it per language.
- `.planning/phases/E1-eval-substrate/E1-CONTEXT.md` — E1 implementation decisions (check executor shape, cap defaults, dev-gate wiring).
- `.planning/notes/e-track-eval-decisions.md` — E-track posture: internal-only, $0 subscription auth, hybrid scoring, runtime-surface × repo-shape axis, M5 supersession. Open Q (line ~52): relationship to existing `tests/e2e/`.

### Eval engine (reuse, do not rebuild)
- `voss/eval/suite.py` — pydantic `TaskSpec` + `load_suite` (E1 adds `checks`; E2 fixtures are TaskSpecs)
- `voss/eval/runner.py` — fixture isolation (copies fixture per task), stub/live providers, `auth.resolve(role=...)`, `_run_checks`, `runs.jsonl` writer (`_append_row`)
- `voss/eval/judge.py` — `Verdict` + `judge_run`; `voss/eval/summary.py` — summary.md (gate-pass + judge columns)
- `tests/eval/golden/{01-analyze,02-plan-only,03-approved-edit,04-validation,05-resume,06-fetch-summarize}/task.toml` — the task-type templates E2 instantiates per language

### Roadmap
- `.planning/ROADMAP.md` §"### Phase E2" (~line 2348) + E-track intro (~line 2319) + build order (E1→E2; line 2321 note: V18-05's gate consumes E1 not M5)

*EVGLD-* requirements are TBD — no REQUIREMENTS.md/SPEC entries yet; this CONTEXT is the seed.*

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- E1 `checks` schema (cmd-exits-0 / file-exists / file-contains) — E2's per-language gates ARE these check types (e.g. `cargo test` exit 0; `architecture.md` contains `Cargo.toml`).
- `voss/eval/runner.py` fixture isolation — copies the task's fixture dir before running; E2 fixtures drop into this unchanged (the matrix is just more fixtures + checks).
- `TaskSpec` (`voss/eval/suite.py`, `extra="forbid"`) — E2 task.tomls are TaskSpecs with per-language `checks`.
- Existing 6 golden `task.toml` files — templates for the 5 task TYPES; E2 instantiates the shape-sensitive ones per language.
- E1 `max_turns` cap + upfront run-size print — E2 preflight extends this with toolchain availability.

### Established Patterns
- **Hybrid scoring:** deterministic `gate_pass` decides pass/fail; judge scores quality. E2 inherits — per-language gates are deterministic.
- **No silent caps (E1) → no silent skips (E2):** a skipped language/toolchain must be recorded + surfaced, never absent-as-green.
- **Internal-only, $0:** subscription auth (`--auth codex`), `VOSS_DEV=1` gate; per-run turn cap so the matrix can't eat weekly sub limits.

### Integration Points
- New fixtures: `tests/eval/fixtures/{python,rust,ts}/` (or `tests/eval/golden/<lang>/<task>/`).
- New per-language `checks` in task.tomls — consumed by E1's `_run_checks`.
- Toolchain preflight — extends the runner's run-header print (`N tasks · max M turns · toolchains: py✓ rust✓ ts✗`).
- `summary.md` — gains per-language rows + a `skipped` column.

</code_context>

<specifics>
## Specific Ideas

- `validation` per language = the repo's NATIVE check: `pytest` / `cargo test` / `npm test` (or `tsc --noEmit` + node test), expect exit 0. This is the toolchain gate, distinct from E1's `.voss`-specific `voss check`.
- `approved-edit` per language = a concretely specified change (e.g. rename/replace one function) that must (a) land — file-contains new, file-absent old, and (b) keep the repo green under its toolchain.
- `analyze` cognition check = `architecture.md` file-contains the language-correct build/test tooling token.
- Keep each synthetic fixture trivially auditable (≤ ~5 files) so a human can confirm the "correct" outcome at a glance.

</specifics>

<deferred>
## Deferred Ideas

- **Full 5×3=15 matrix** — adding plan-only/resume/fetch-summarize on rust+ts. Only if those tasks prove shape-sensitive in practice.
- **Realistic vendored small repos** — representative real-world projects instead of synthetic-minimal. Heavier (version pinning, network, slower); revisit if synthetic fixtures miss real-shape behaviors.
- **Containerized toolchains** — hermetic py+rust+node via a container image instead of host toolchains. Only if host-toolchain variance becomes a problem; conflicts with the lightweight internal/on-demand posture.
- **More languages** (Go, Java) — E2 locks py/rust/ts; others are a later matrix expansion.
- **`tests/e2e/` relationship** (E-track open Q) — whether to graduate existing pytest e2e into the E-track or keep both layers. Cross-E-track, not E2-specific.

None of the above is scope creep into E2 — all are explicitly downstream.

</deferred>

---

*Phase: E2-golden-tasks-repo-matrix*
*Context gathered: 2026-06-10*
