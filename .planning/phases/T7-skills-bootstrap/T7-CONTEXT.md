# Phase T7: Skills Bootstrap - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship 6 ready-to-use skills so the existing skill registry "isn't just a hook." The registry, slash surface (`/skill`, `/skills`), and CLI surface (`voss skill run`, `voss skills`) already exist and are LOCKED — T7 adds entries + handlers, it does **not** redesign the registry or add a `.voss`-skill execution path.

The 6 skills (from ROADMAP.md §"Phase T7" / punch-list):
- **SKL-01 `rename-symbol`** — anchor + scope-aware rename across the repo.
- **SKL-02 `add-test`** — locate a public function, generate a unit test, plant a failing assertion.
- **SKL-03 `summarize-diff`** — pipe `git diff` → PR description.
- **SKL-04 `port-py-to-voss`** — Python → `.voss` for the classify/support/research sample shapes.
- **SKL-05 `audit-cognition`** — re-run analyze against drift; propose a one-paragraph `architecture.md` update (proposes, never writes).
- **SKL-06 `voss-lint-as-skill`** — wraps `voss check` with structured JSON diagnostics. Foundation for M11.

**In scope:**
- 6 `SkillEntry` registrations in `default_skill_registry()` + one Python handler module per skill under `voss/harness/skills/<id>.py` (mirrors the existing `skills/analyze.py` reference pattern).
- Standalone test suite `tests/skills/` — `fixtures/<skill>/` seed repos + `test_skills_smoke.py` with deterministic hermetic assertions. Decoupled from M5's golden suite.
- Companion `.voss` artifacts for the 4 agentic skills under `voss/harness/skills/voss/<id>.voss`, each passing `voss check` in CI (the "composability demonstration" deliverable).
- `voss skills` lists 7 entries (existing `analyze` + 6 new) on a fresh install.

**Out of scope (deferred / explicitly rejected):**
- Any change to the skill registry contract (`SkillEntry` shape, `SkillHandler` signature, `handler -> None`) — LOCKED by prior M-phase work.
- A `.voss`-skill loader / bridge that executes `.voss` files as skills — rejected for T7 (would reopen the locked registry). Agentic skills run as Python; their `.voss` companions are `voss check`-validated demonstrations only, not the exec path.
- Hard 1:1 pairing with M5's golden eval suite, and adding fixtures into `tests/eval/golden/` — rejected. T7's suite is standalone and T7 ships independently of M5 (M5 is `status: verifying`).
- LLM-as-judge scoring for skill verification — rejected for T7 (non-hermetic). T7 uses deterministic assertions.
- M11 marketplace work, M15 — unblocked by SKL-06's JSON contract but not required.

</domain>

<decisions>
## Implementation Decisions

### Eval / verification strategy
- **D-01:** Skill verification lives in a **standalone** `tests/skills/` suite — `tests/skills/fixtures/<skill>/` (seed repo + expected artifacts) and `tests/skills/test_skills_smoke.py`. **Decoupled from M5's golden suite** — no shared `tests/eval/golden/` dir, no M5 hard-dependency. T7 ships independently. May borrow M5's `task.toml` schema + rubric *shape* (M5-CONTEXT D-05/D-07) where natural, but does not depend on M5 being shipped.
- **D-02:** Verification is **deterministic + hermetic** — no LLM-as-judge. Each fixture asserts concrete post-conditions: exit 0, no permission escalation, and skill-specific checks:
  - `rename-symbol` → `git diff` == expected patch
  - `add-test` → `pytest --collect-only` finds the new test
  - `summarize-diff` → output non-empty + has PR-ish sections
  - `voss-lint` → emitted JSON validates against the frozen schema + contains known seeded findings
  - `port-py-to-voss` → `voss check` exits 0 on the generated `.voss`
  - `audit-cognition` → a proposal block is emitted, **no write** to `architecture.md`
- **D-03:** Agentic skills run under a **stub provider** in tests so output shape is assertable without live creds (keeps CI hermetic/fast).

### Authoring substrate
- **D-04:** All 6 runtime handlers are **Python** modules `voss/harness/skills/<id>.py`, following the existing `skills/analyze.py` `run(*, cwd, provider, history, record, renderer, tools, gate)` pattern. No `.voss`-skill execution path is added (registry stays locked).
- **D-05:** The 4 agentic skills (`summarize-diff`, `add-test`, `port-py-to-voss`, `audit-cognition`) **also ship a companion `.voss` artifact** at `voss/harness/skills/voss/<id>.voss` that `voss check` must pass in CI — this is the roadmap's "Python with a `.voss` lint pass demonstrating composability" deliverable. The `.voss` files are dogfood demonstrations, **not** the runtime exec path.
- **D-06:** The 2 deterministic skills (`rename-symbol`, `voss-lint-as-skill`) are **Python-only**, no `.voss` companion — the language adds nothing to a mechanical operation.

### Deterministic vs agentic split
- **D-07:** **Agentic** (invokes an LLM turn via `run_turn`): `summarize-diff`, `add-test`, `port-py-to-voss`, `audit-cognition`.
- **D-08:** **Deterministic** (no provider call at all): `rename-symbol`, `voss-lint-as-skill`. These must run with zero LLM dependency.

### Mutating classification + permission posture
- **D-09:** `mutating: true` → `rename-symbol`, `add-test`, `port-py-to-voss`. They write **through the existing `fs_edit` / `fs_write` tools**, so the standard permission gate + mode rules apply — **no skill-level permission escalation or bypass**. In `plan` mode the write path refuses cleanly (no escalation); `edit`/`auto` proceed under normal approval. Matches `analyze.py` and the T5 D-12 explicit-deny precedent.
- **D-10:** `mutating: false` → `summarize-diff`, `voss-lint-as-skill`, `audit-cognition`. Read-only. `audit-cognition` emits a proposal block and **never writes** `architecture.md` (the human/another flow applies it).
- **D-11:** Skills never re-implement or bypass the central tool permission layer — all mutation goes through the existing gated tools.

### Output contract
- **D-12:** Per-skill output convention (printed via renderer/stdout — `SkillHandler` returns `None`, contract stays locked):
  - `voss-lint-as-skill` → **stable JSON diagnostics schema** (e.g. `{version, findings:[{file,line,rule,severity,msg}]}`). This is the **M11 contract** — schema documented and asserted in `tests/skills/`. Treat the schema as frozen once written.
  - `summarize-diff` → **structured markdown** with stable sections (`## Title`, `## Summary`, `## Changes`) — PR-ready.
  - `rename-symbol`, `add-test`, `port-py-to-voss` → human-readable text; the meaningful effect is the file mutation itself.
  - `audit-cognition` → human-readable proposal block (no write).
- **D-13:** No uniform JSON envelope across all skills (rejected as over-engineered for human-facing skills).

### Claude's Discretion
- Symbol-scoping engine for `rename-symbol` (AST vs anchor+grep heuristic) — researcher/planner choose, grounded in existing `fs_grep`/`fs_edit` tools.
- Test-framework detection for `add-test` (pytest assumed given the repo; planner confirms).
- Exact `.voss` companion shape for the 4 agentic skills (must `voss check`-pass; expressiveness left to planner using existing `samples/*.voss` + `voss/harness/agent/*.voss` as references).
- Which `voss check` diagnostic fields map into SKL-06's frozen JSON schema — planner designs the schema; constraint: stable + M11-consumable.
- Drift-detection mechanism reuse for `audit-cognition` (reuse `cognition.*` drift APIs from M2).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope (requirements source — no locked SPEC.md or REQUIREMENTS.md entries; SKL-01..06 are "proposed")
- `.planning/ROADMAP.md` §"Phase T7 — Skills Bootstrap *(v0.2)*" (~line 948) — goal, SKL-01..06 definitions, success criteria, cross-cutting constraints.
- `.planning/notes/daily-driver-punch-list.md` §"Phase T7 — Skills Bootstrap" (~line 319) — fuller SKL-01..06 wording + "Capabilities" (`voss skills` lists 6+, eval-fixture intent).

### Locked registry + skill surface (T7 builds on these, does not modify)
- `voss/harness/skill_registry.py` — `SkillEntry(id, description, handler, mutating)`, `SkillRegistry`, `default_skill_registry()`. The `analyze` registration is the template.
- `voss/harness/skills/analyze.py` — reference handler module: `run(*, cwd, provider, history, record, renderer, tools, gate)` signature, staged-write + gated-tool pattern.
- `voss/harness/cli.py` §§ `_print_skills` (~464), `_skill`/`_skills` slash handlers (~866-875), `SlashCommand` registrations (~955-956), `skills_cmd`/`skill_group`/`skill_run_cmd` (~1769-1810) — the invocation surfaces T7 skills must work through.

### Verification shape borrowed (not depended on)
- `.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md` D-05/D-07 — `task.toml` + `fixture/` per-task shape, copied/adapted into `tests/skills/`. M5 itself is NOT a T7 dependency.

### Permission/mutation precedent
- `.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md` D-12 — edit-mode explicit deny-set / no permission escalation for mutating operations.

### `.voss` companion references (composability artifacts must `voss check`-pass)
- `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` — the sample shapes `port-py-to-voss` targets, and reference `.voss` style.
- `voss/harness/agent/loop.voss`, `voss/harness/agent/executor.voss`, `voss/harness/agent/reviewer.voss` — dogfood `.voss` precedent for agentic-workflow expression.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SkillEntry` / `default_skill_registry()` (`voss/harness/skill_registry.py`): register 6 new entries here; this is the single integration point.
- `voss/harness/skills/analyze.py`: copy its module shape (`run(*, cwd, provider, history, record, renderer, tools, gate)`, gated-tool writes, agent `run_turn` usage) for the agentic skills.
- Existing gated tools `fs_read`/`fs_glob`/`fs_grep`/`fs_edit`/`fs_write` + `voss check`: skills compose these — `voss-lint` wraps `voss check`; mutating skills write via `fs_edit`/`fs_write`.
- `cognition.*` + `voss_md` (used by `analyze.py`): drift APIs reusable by `audit-cognition`.

### Established Patterns
- Skill handler returns `None`; all output via `renderer`/stdout; all mutation via gated tools (no direct filesystem writes, no permission bypass).
- `voss skills` / `/skills` enumerate `registry.entries()` — adding entries is sufficient for discoverability (no extra wiring).
- Agentic skills drive the agent through `run_turn` (see `analyze.py`); stub-provider parity is the test seam (M4/M5 precedent).

### Integration Points
- `default_skill_registry()` in `voss/harness/skill_registry.py` — the one place new `SkillEntry`s are registered.
- New package contents under `voss/harness/skills/` (Python handlers) and `voss/harness/skills/voss/` (`.voss` companions).
- New `tests/skills/` test package (new; no existing skill tests — `tests/` has none matching `*skill*`).
- CI must add a `voss check` pass over `voss/harness/skills/voss/*.voss`.

</code_context>

<specifics>
## Specific Ideas

- voss-lint JSON shape sketch from discussion: `{version, findings:[{file,line,rule,severity,msg}]}` — treat as the frozen M11 contract once finalized.
- summarize-diff markdown sections: `## Title`, `## Summary`, `## Changes`.
- audit-cognition must emit a *proposal* block, explicitly NOT writing `architecture.md`.
- `voss skills` should show 7 entries post-T7 (existing `analyze` + 6 new).

</specifics>

<deferred>
## Deferred Ideas

- `.voss`-skill execution path / loader (registry executing `.voss` files as skills) — explicitly deferred; would reopen the locked registry contract. Revisit if dogfood signal warrants.
- Hard 1:1 M5 golden-suite pairing + LLM-judge skill scoring — deferred; revisit after M5 ships/verifies and enough eval history exists.
- M11 (lint-as-skill consumer / structured-diagnostics platform) and M15 (marketplace) — unblocked by SKL-06's JSON contract but out of T7 scope.
- Uniform cross-skill JSON output envelope — considered and rejected for T7; could be revisited if M15 marketplace needs it.

None of these were scope creep — discussion stayed within the phase domain.

</deferred>

---

*Phase: T7-skills-bootstrap*
*Context gathered: 2026-05-17*
