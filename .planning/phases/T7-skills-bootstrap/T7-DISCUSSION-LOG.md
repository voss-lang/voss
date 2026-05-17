# Phase T7: Skills Bootstrap - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** T7-skills-bootstrap
**Areas discussed:** M5 eval-pairing scope, Verification strategy, Authoring substrate, Deterministic vs agentic split / mutating + permissions, Output contract

**Phase resolution note:** `gsd-sdk query init.phase-op T7` returned `phase_found: false` (the SDK resolver does not parse table-only / non-sequential T-phases — T1–T6 fail identically despite having dirs). Followed the established T-phase convention: dir `.planning/phases/T7-skills-bootstrap/`, files `T7-*`. No SPEC.md; SKL-01..06 are "proposed" in ROADMAP.md/punch-list, not locked in REQUIREMENTS.md.

---

## M5 eval-pairing scope

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone tests/skills/ suite | T7 ships own fixtures + runner, decoupled from M5; borrow task.toml/rubric shape only; no M5 dependency | ✓ |
| Extend M5 golden suite (+6 fixtures) | Add 06..11 into tests/eval/golden/, true 1:1 pairing, hard dependency on M5 shipping first | |
| Subset pairing only | Only 3 loosely-mapped skills get M5 fixtures; rest standalone | |

**User's choice:** Standalone tests/skills/ suite
**Notes:** M5 is `status: verifying`, and its golden tasks (analyze/plan/edit/validation/resume) do not map to rename/add-test/summarize-diff. A hard M5 coupling was judged fragile; T7 must ship independently.

---

## Verification strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic assertions | exit 0 + no escalation + skill-specific post-conditions; stub provider for agentic; hermetic/fast/CI-safe | ✓ |
| LLM-judge (M5-style) | Plain-text rubric + LLM verdict; needs creds, non-hermetic, flaky | |
| Hybrid per skill | Deterministic skills assert; agentic skills judged | |

**User's choice:** Deterministic assertions
**Notes:** Preview locked per-skill post-conditions, incl. audit-cognition emitting a proposal block with **no write** to architecture.md, and port-py-to-voss verified via `voss check` exit 0.

---

## Authoring substrate (.voss vs Python)

| Option | Description | Selected |
|--------|-------------|----------|
| Python handlers + companion .voss lint artifact | All 6 handlers Python; agentic skills also ship skills/voss/<id>.voss that `voss check` passes in CI; deterministic skills Python-only | ✓ |
| Real .voss execution for agentic skills | Agentic skills run as executed .voss via a new registry bridge — reopens the locked registry | |
| All Python, defer .voss entirely | No .voss artifacts; constraint explicitly noted unmet | |

**User's choice:** Python handlers + companion .voss lint artifact
**Notes:** Registry only executes Python `SkillHandler` callables and is LOCKED; the `.voss` companions are `voss check`-validated composability demonstrations, not the exec path.

---

## Deterministic vs agentic split / mutating + permissions

| Option | Description | Selected |
|--------|-------------|----------|
| Mutating skills go through normal tool gate | rename/add-test/port = mutating:true via fs_edit/fs_write → existing gate; summarize/voss-lint/audit = mutating:false; skills never bypass permission layer | ✓ |
| Skills declare + self-enforce mode | Each skill checks ctx mode itself, hard-refuses in plan mode independent of the gate | |

**User's choice:** Mutating skills go through normal tool gate
**Notes:** Agentic = summarize-diff, add-test, port-py-to-voss, audit-cognition. Deterministic (no provider) = rename-symbol, voss-lint. audit-cognition is mutating:false (proposes, never writes). Matches analyze.py + T5 D-12.

---

## Output contract (text vs structured)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-skill: JSON where machine-consumed, text otherwise | voss-lint → frozen JSON schema (M11 contract, schema-tested); summarize-diff → structured markdown; others → human text + file effects | ✓ |
| Uniform JSON envelope for all 6 | Common {skill,status,summary,artifacts,details} envelope for every skill | |
| Freeform text; voss-lint structured later | All freeform; defer SKL-06 JSON to M11 | |

**User's choice:** Per-skill: JSON where machine-consumed, text otherwise
**Notes:** SkillHandler returns None (output is a print convention via renderer/stdout, registry stays locked). voss-lint JSON schema treated as frozen M11 contract once written.

---

## Claude's Discretion

- `rename-symbol` symbol-scoping engine (AST vs anchor+grep), grounded in existing `fs_grep`/`fs_edit`.
- `add-test` test-framework detection (pytest assumed; planner confirms).
- Exact `.voss` companion shapes for the 4 agentic skills (must `voss check`-pass).
- Field mapping from `voss check` diagnostics into SKL-06's frozen JSON schema.
- Drift-detection API reuse for `audit-cognition` (`cognition.*` from M2).

## Deferred Ideas

- `.voss`-skill execution path / loader — would reopen the locked registry; revisit on dogfood signal.
- Hard 1:1 M5 golden-suite pairing + LLM-judge skill scoring — revisit after M5 ships.
- M11 (lint-as-skill consumer) / M15 (marketplace) — unblocked by SKL-06 JSON contract, out of T7 scope.
- Uniform cross-skill JSON output envelope — rejected for T7; revisit if M15 needs it.
