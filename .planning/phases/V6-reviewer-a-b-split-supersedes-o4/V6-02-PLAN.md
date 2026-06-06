---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 02
type: execute
wave: 1
depends_on: [V6-01]
files_modified:
  - voss/harness/board/verdict.py
  - voss/harness/board/reviewer_b.py
  - voss/harness/board/reviewer_a.py
autonomous: true
requirements: [VREV-06]
must_haves:
  truths:
    - "ReviewerVerdict carries a 7th defaulted field domain_inferred ∈ {code,ai,docs,unknown}"
    - "Existing keyword construction of ReviewerVerdict still works (additive, no breakage)"
    - "Reviewer-B populates domain_inferred from the LLM output, clamped to the allowed set; garbage → unknown"
    - "Reviewer-A defaults domain_inferred (unknown, or a trivial card.domain map) without re-running"
  artifacts:
    - path: "voss/harness/board/verdict.py"
      provides: "7-field ReviewerVerdict with defaulted domain_inferred (last field)"
      contains: "domain_inferred: Literal"
    - path: "voss/harness/board/reviewer_b.py"
      provides: "_ReviewerBOutput.domain_inferred + _to_verdict clamp to allowed set"
      contains: "domain_inferred"
  key_links:
    - from: "voss/harness/board/reviewer_b.py"
      to: "voss/harness/board/verdict.py"
      via: "_to_verdict constructs ReviewerVerdict(domain_inferred=clamped)"
      pattern: "domain_inferred="
---

<objective>
Add the inferred-domain field to the board-local verdict contract (VREV-06). This is a leaf, low-risk, additive change: one defaulted field on `ReviewerVerdict`, B populates it (clamped), A defaults it. No board wiring, no persistence, no CLI — purely the verdict data contract and its two producers.

Purpose: Carries the inferred domain (`code`/`ai`/`docs`/`unknown`) on every verdict so persistence (V6-03) and the CLI (V6-04) can surface it. Additive-and-defaulted so every existing construction is untouched (V6-CONTEXT D-06/D-07/D-08).
Output: `verdict.py` 7-field; `reviewer_b.py` populates+clamps; `reviewer_a.py` defaults.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-PATTERNS.md

<interfaces>
<!-- Extracted from V6-PATTERNS.md (read directly from source). -->

Current ReviewerVerdict (voss/harness/board/verdict.py L13-30) — frozen+slots, 6 fields:
  conf: float; source: Literal["A","B"]; tier: Literal["fast","strong"];
  verdict: Literal["pass","fail","block"]; notes: str; evidence_refs: tuple[str, ...]
  Imports (L1-10): `from typing import Literal, Protocol, runtime_checkable` — Literal ALREADY imported.
  Module docstring asserts a zero-transitive-harness-import contract (only stdlib imports allowed).

Current _ReviewerBOutput (voss/harness/board/reviewer_b.py L34-40) — pydantic, extra="ignore":
  conf: float; verdict: Literal["pass","fail","block"]; notes: str; evidence_refs: list[str] = []

Current _to_verdict success branch (reviewer_b.py L167-174): keyword ReviewerVerdict construction.
Parse-fail branch (L159-166): keyword construction → domain_inferred defaults automatically.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add domain_inferred (7th, defaulted) to ReviewerVerdict</name>
  <read_first>
    - voss/harness/board/verdict.py (full file — frozen+slots dataclass + import block + zero-import contract docstring)
    - V6-PATTERNS.md "verdict.py" section (exact 7th-field line + import constraint)
    - tests/harness/board/test_domain_inferred.py (the RED scaffold from V6-01 this satisfies)
    - tests/harness/board/test_verdict.py (the updated 7-field invariant)
  </read_first>
  <behavior>
    - Constructing ReviewerVerdict without domain_inferred yields domain_inferred == "unknown" (default)
    - fields(ReviewerVerdict) is exactly {conf, source, tier, verdict, notes, evidence_refs, domain_inferred}
    - The dataclass stays frozen+slots; no positional construction breaks (no new non-defaulted field)
    - verdict.py still imports only stdlib (no voss.* import added)
  </behavior>
  <action>
    Append `domain_inferred: Literal["code", "ai", "docs", "unknown"] = "unknown"` as the LAST field of `ReviewerVerdict` in `voss/harness/board/verdict.py` (per V6-CONTEXT D-06). It MUST be last — a defaulted field cannot precede the existing non-defaulted fields on a slots dataclass (Pitfall 4: `TypeError: non-default argument follows default argument`). `Literal` is already imported (D-08) — add NO new imports; do not import anything from `voss.*` (preserve the zero-transitive-harness-import contract). No other change to the file.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_verdict.py tests/harness/board/test_domain_inferred.py::TestDomainInferred::test_7th_field_exists_with_default tests/harness/board/test_domain_inferred.py -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'domain_inferred: Literal\["code", "ai", "docs", "unknown"\] = "unknown"' voss/harness/board/verdict.py` succeeds
    - `domain_inferred` is the final field in the `ReviewerVerdict` class body
    - `.venv/bin/python -m pytest tests/harness/board/test_verdict.py -x` exits 0 (7-field invariant now green)
    - `grep -v '^#' voss/harness/board/verdict.py | grep -c 'import voss\|from voss\|from \.' ` returns 0 (zero-transitive-harness-import contract intact)
  </acceptance_criteria>
  <done>ReviewerVerdict is 7-field with a defaulted domain_inferred; test_verdict.py 7-field invariant is green; zero-import contract preserved.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: B populates domain_inferred (clamped); A defaults it</name>
  <read_first>
    - voss/harness/board/reviewer_b.py (_ReviewerBOutput L34-40, _to_verdict L147-174 — both branches)
    - voss/harness/board/reviewer_a.py (_verdict_from_test_exit, _verdict_from_judge, exception fallback — all keyword ReviewerVerdict constructions)
    - V6-PATTERNS.md "reviewer_b.py" + "reviewer_a.py" sections (exact clamp constant + kwarg pattern)
    - tests/harness/board/test_domain_inferred.py (B-populates RED assertions; FakeReviewerBProvider analog)
    - tests/harness/board/test_reviewer_b.py (FakeReviewerBProvider fixture pattern)
  </read_first>
  <behavior>
    - A B verdict whose LLM output names a valid domain (e.g. "code") carries domain_inferred == "code"
    - A B verdict whose LLM output names garbage/unknown domain is clamped to domain_inferred == "unknown"
    - The parse-fail (None) B branch yields domain_inferred == "unknown" (default, no crash)
    - Reviewer-A verdicts carry domain_inferred == "unknown" by default (or a trivial card.domain → code/ai map), with no extra LLM/test call
  </behavior>
  <action>
    Reviewer-B (`reviewer_b.py`):
    (1) Add `domain_inferred: str = "unknown"` to `_ReviewerBOutput` (string type — clamped downstream, `extra="ignore"` keeps unknown LLM keys harmless).
    (2) Insert module-level constant `_ALLOWED_DOMAINS: frozenset[str] = frozenset({"code", "ai", "docs", "unknown"})` before `_to_verdict`.
    (3) In `_to_verdict`'s success branch, compute `domain = parsed.domain_inferred if parsed.domain_inferred in _ALLOWED_DOMAINS else "unknown"` and pass `domain_inferred=domain` as a kwarg to the `ReviewerVerdict(...)` construction. Leave the parse-fail branch unchanged (it keyword-constructs without the field → defaults to "unknown").
    Reviewer-A (`reviewer_a.py`):
    (4) A defaults the field. Either leave all existing keyword `ReviewerVerdict(...)` constructions unchanged (default "unknown" applies automatically — sufficient per D-07) OR add a trivial `card.domain → {"code","ai"}` map (`_DOMAIN_MAP = {"code":"code","ai":"ai"}`, `getattr(card,"domain","")`, fallback "unknown") and pass `domain_inferred=` on the constructions. Do NOT make A run any extra test/LLM call to infer the domain — A defaults, it does not investigate.
    Extend the B-populates test in `test_domain_inferred.py` (from V6-01) so it drives a fake-provider B verdict and asserts both the valid-domain and garbage→unknown clamp paths.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_domain_inferred.py tests/harness/board/test_reviewer_b.py tests/harness/board/test_reviewer_a.py -x 2>&1 | tail -6</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q '_ALLOWED_DOMAINS' voss/harness/board/reviewer_b.py` succeeds and the set literal is exactly `{"code", "ai", "docs", "unknown"}`
    - `grep -q 'domain_inferred=' voss/harness/board/reviewer_b.py` succeeds (B passes the kwarg)
    - `.venv/bin/python -m pytest tests/harness/board/test_domain_inferred.py -x` exits 0 (B-populates + clamp tests green)
    - `.venv/bin/python -m pytest tests/harness/board/test_reviewer_a.py tests/harness/board/test_reviewer_b.py -x` exits 0 (no O4 reviewer regression)
  </acceptance_criteria>
  <done>B populates domain_inferred clamped to the allowed set (garbage→unknown, parse-fail→unknown); A defaults it; existing O4 reviewer tests stay green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM output → ReviewerVerdict.domain_inferred | Reviewer-B's LLM produces a free-form `domain_inferred` string that must be constrained to the enum before it becomes a verdict value |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V6-02-01 | Tampering | LLM-controlled `domain_inferred` value | mitigate | `_to_verdict` clamps to `_ALLOWED_DOMAINS` frozenset; any value outside {code,ai,docs,unknown} → "unknown". LLM cannot inject arbitrary domain strings into the verdict (the ASVS L1 Input-Validation control noted in V6-RESEARCH Security Domain). |
| T-V6-02-02 | Tampering | breaking the zero-transitive-harness-import contract on verdict.py | mitigate | Acceptance grep asserts no `voss.*` / relative import added; `Literal` already present, no new import needed |
| T-V6-02-SC | Tampering | npm/pip/cargo installs | mitigate | Zero new dependencies (pydantic + dataclasses already present); no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_verdict.py tests/harness/board/test_domain_inferred.py -x` exits 0.
- `.venv/bin/python -m pytest tests/harness/board/ -q` shows no regression in the O4 reviewer tests (`test_reviewer_a.py`, `test_reviewer_b.py`, `test_stub.py`, `test_critic_loop.py`).
- `domain_inferred` from a B verdict is always one of {code,ai,docs,unknown}.
</verification>

<success_criteria>
- ReviewerVerdict is 7-field; `domain_inferred` defaulted, additive, last field.
- B populates and clamps; A defaults; parse-fail defaults to unknown.
- Zero-transitive-harness-import contract on verdict.py intact.
- No frozen record (RunRecord/SessionRecord/BudgetScope) touched.
</success_criteria>

<output>
Create `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-02-SUMMARY.md` when done.
</output>
