# Phase V2: Principles Layer - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct from V2-SPEC.md (discuss-phase skipped — ambiguity 0.153, decisions locked in spec; SPEC interview log already contains the researcher scout)

<spec_lock>
## Locked Requirements (from V2-SPEC.md — MUST read before planning)

`.planning/phases/V2-principles-layer/V2-SPEC.md` locks 6 requirements:
VPRIN-01 (loader), VPRIN-03 (immutable + no control-flow coupling), VPRIN-04 (system-prompt
injection), VPRIN-05 (six shipped defaults), VPRIN-06 (additive override + explicit disable),
VPRIN-07 (`voss principles show`).

Deferred OUT of V2: VPRIN-02 (`principles{}` grammar block) → V10; VPRIN-08 (audit recording of
active principles) → V9. Do NOT plan these.

The 8 SPEC Acceptance Criteria are the verification bar — do not re-derive WHAT/WHY here.
</spec_lock>

<domain>
## Phase Boundary

Make engineering principles first-class: a `.voss/principles.yml` (key→string map, with six
shipped defaults) compiles to an immutable `PrinciplesConfig` and injects as one distinct,
~1k-token-capped ordered block into the agent system prompt via the EXISTING
`_compose_system_blocks` seam — so `voss do`/`voss chat` (and current subagents) carry the
team's culture as opaque text, with NO control flow branching on any individual principle.
Plus `voss principles show`. Genuinely new surface (no principles plumbing exists today).
</domain>

<decisions>
## Implementation Decisions (the HOW the SPEC's "next step" flagged)

### D-01 — Config object: frozen, mirrors TeamConfig
- New module `voss/harness/principles.py` housing `PrinciplesConfig` as
  `@dataclass(frozen=True, slots=True)` — same pattern as `voss/harness/team.py`'s `TeamConfig`
  (frozen=True, slots=True). Store principles as an immutable ordered mapping (e.g. a
  `tuple[tuple[str, str], ...]` of (key, text) pairs, or a frozen mapping) so mutation raises
  and order is stable for injection + `show`.
- VPRIN-03 immutability acceptance ("mutation raises") satisfied by `frozen=True`.

### D-02 — Loader: YAML key→string, reuse existing stack, loud on malformed
- `.voss/principles.yml` is a flat YAML `key: "string"` map (plus an optional top-level
  `disable: [keys]` list — see D-04). Load via the existing YAML/pydantic stack already used for
  `.voss/` config — NO new third-party deps.
- A malformed file (bad YAML, non-string value where a string is expected) raises a clear,
  NON-silent error (a `VossPrinciplesConfigError`-style exception mirroring
  `VossTeamConfigError`), not a silent fallback to defaults.

### D-03 — Injection: new ordered block in the cacheable static prefix
- Add a `principles_text` (or equivalent) parameter to `_compose_system_blocks`
  (`agent.py:318`) and insert it as its OWN distinct block in the returned blocks list,
  inside the CACHE-01 static cacheable prefix (principles are static per run, like cognition).
- Suggested slot: adjacent to the cognition/project-index culture blocks (exact ordinal is
  planner's discretion, but it MUST be a separate labeled block, e.g. a `## Principles` heading,
  not merged into cognition or VOSS.md).
- Role-specific EM/reviewer/tester contexts are NOT wired here — they inherit this same block as
  V3/V6/V7 build them (SPEC out-of-scope). V2 wires only the current `voss do`/`voss chat`/subagent path.

### D-04 — Merge semantics: additive override + explicit disable
- Active set = defaults, then project file layered ON TOP by key:
  - project key not in defaults → ADDS it;
  - project key matching a default → REPLACES that default's string;
  - a default is REMOVED only when explicitly disabled — either its value set to `null`, OR its
    key listed in a top-level `disable: [keys]` list.
- Non-disabled defaults always remain active. No project file at all → the six defaults are the active set.

### D-05 — Token cap: ~1k, mirror cognition's overflow pattern
- The injected principles block respects a ~1k-token hard cap. On overflow: truncate (drop
  lowest-priority principles last/first per a deterministic rule) AND emit a renderer overflow
  event mirroring cognition's `cognition_overflow` — new event name e.g. `principles_overflow`.
- Reuse the same token-count helper `_compose_cognition_prompt` (`agent.py:79`,
  `COGNITION_BUDGET_TOKENS=6000`) uses; define `PRINCIPLES_BUDGET_TOKENS ≈ 1000`.

### D-06 — `voss principles show`: click group → AGENT_COMMANDS
- Add a `principles` click group with a `show` subcommand, registered in the `AGENT_COMMANDS`
  tuple (`cli.py:3672`, same pattern as `memory_group`/`mcp_group`).
- `show` exits 0 and prints every active (merged) principle with its source label
  (`default` vs `project`). Provide a `--json` path (project convention is JSON-first).

### D-07 — No-control-flow-branching guard test (VPRIN-03 constraint)
- A guard test asserts no harness/agent code path conditionals on individual principle
  keys/strings (principles are opaque injected text). Treat principles strings as data only.

### Six shipped defaults (VPRIN-05 — exact strings, from PRD §"Default Principles")
```yaml
diff: "Make the smallest diff that solves the task."
evidence: "No factual claim without evidence."
tests: "Tests prove behavior, not coverage theater."
scope: "Do not edit outside assigned scope."
review: "Review intent and correctness before style."
reversibility: "Prefer reversible changes unless the user approves risk."
```

### Claude's Discretion (lock at planning)
- Exact module layout (`principles.py` fns), the precise injection ordinal in the blocks list,
  the truncation priority rule, `show` table formatting, and where defaults live (constant in
  `principles.py` vs a shipped `.voss/principles.default.yml`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec / PRD
- `.planning/phases/V2-principles-layer/V2-SPEC.md` — LOCKED requirements (VPRIN-01/03/04/05/06/07) + 8 acceptance criteria. Read first.
- `.planning/docs/ORCHESTRATION_LAYERS.md` §"Phase 2: Principles Layer" — PRD PRIN-01..08 table + the six default-principle strings (§"Default Principles").
- `.planning/ROADMAP.md` §"Phase V2" — VPRIN mapping + cross-cutting constraints.

### The injection seam + precedent to mirror
- `voss/harness/agent.py` — `_compose_system_blocks` (L318, add the principles block param);
  `_compose_cognition_prompt` (L79) + `COGNITION_BUDGET_TOKENS=6000` (L53) — the cap/truncate/overflow-event pattern to mirror at ~1k.
- `voss/harness/team.py` — `TeamConfig` `@dataclass(frozen=True, slots=True)` (L211) + `VossTeamConfigError` (L33) — frozen-config + loud-error precedent for `PrinciplesConfig`.
- `voss/harness/cli.py` — `AGENT_COMMANDS` tuple (L3672) + click group pattern (`memory_group`, `mcp_group`) — register `voss principles show` here.
- `voss/harness/config.py` — existing `.voss/` YAML load stack to reuse (no new deps).

### Frozen — must NOT change (schema-freeze constraint)
- `voss/harness/session.py` `RunRecord`/`SessionRecord`, `voss_runtime/budget.py` `BudgetScope` — zero field
  changes (O1/V4 redaction invariant); the redaction test must stay green. Audit recording of
  principles is V9, not V2.

### Tests to extend
- `tests/harness/test_*` for agent context composition + cli; add principles loader/merge/injection/guard tests.
</canonical_refs>

<code_context>
## Reusable Assets / Integration Points

- `_compose_system_blocks` already assembles ordered cacheable blocks (cognition, VOSS.md,
  project index) — principles = one more ordered block, exact precedent (SPEC background).
- `_compose_cognition_prompt` already enforces a 6k cap, truncates on overflow, emits
  `cognition_overflow` via the renderer — copy this shape at ~1k for principles.
- `TeamConfig` (frozen=True, slots=True) + `VossTeamConfigError` = the frozen-config + clear-error
  template for `PrinciplesConfig`.
- `AGENT_COMMANDS` click-group registration = where `voss principles` attaches (V1-02 used the same tuple for `voss capabilities`).
</code_context>

<specifics>
## Specific Ideas

- Principles are OPAQUE TEXT — data, never branched on (guard test enforces).
- Injected block is a distinct labeled section in the static prefix; ≤ ~1k tokens; overflow → truncate + renderer warning.
- Defaults always active unless explicitly disabled (null value or `disable:` list).
- `show` prints merged set + per-principle source (default vs project); JSON-first.
</specifics>

<deferred>
## Deferred Ideas

- `principles { ... }` `.voss` grammar block + `team{}` nesting (VPRIN-02) → V10.
- Audit recording of active principles (VPRIN-08) → V9 (owns audit surface; avoids touching frozen RunRecord).
- Role-specific EM/reviewer/tester context injection → inherited as V3/V6/V7 build those roles.
</deferred>

---

*Phase: V2-principles-layer*
*Context derived 2026-06-06 directly from V2-SPEC.md (discuss-phase skipped per low ambiguity)*
