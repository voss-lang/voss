# Phase O4: Reviewer A/B Split — Research

**Researched:** 2026-05-19
**Domain:** Python harness agent orchestration — independent reviewer authoring (A) + independent tiered judgment (B), eval harness reuse, information isolation, O3 verdict interface wiring
**Confidence:** HIGH on existing code surface (read directly, cited file:line); MEDIUM on derived constraints where SPEC.md does not yet exist; LOW on model-selection specifics (discretion area)

---

<user_constraints>
## User Constraints (from O4-CONTEXT.md)

### Locked Decisions
- **Confidence source is an independent reviewer** (OPLAN decision #6), never self-reported (invariant #3).
- **Audit bar = original idea; Reviewer-A re-derives** (decision #13). EM's AC/DoD are worker scaffolding, never the judging bar.
- **Engineers cannot author the verification that gates them** (decisions #14, invariant #5) — Reviewer-A owns tests/eval.
- **A/B split** (decision #15): author ≠ judge. Splitting restores two genuinely independent sources at →Done and un-blinds calibration.
- **AI-card eval gate** (decision #21): the AI domain's second source is an eval harness, not deterministic tests.
- **Residual-2 invariant (must be implemented, not just documented):** Reviewer-B sees the raw idea and has explicit authority to fail a card whose A-verification diverges from the idea.

### Claude's Discretion
- Model selection for A vs. B vs. B-tiers.
- Eval-harness authoring interface for Reviewer-A on AI cards (golden set vs. rubric).
- Exact information-isolation mechanism guaranteeing B has no EM/A memory bleed.

### Deferred Ideas (OUT OF SCOPE)
- Board transition logic beyond the `Reviewer` Protocol O3 already froze (O3 owns it).
- EM dispatch (O5).
- Calibration telemetry (O6 — O4 must emit the data O6 will audit: B-verdict vs. A-verification).
</user_constraints>

---

## Summary

O4 is the phase where the structural cage gets its two independent judgment sources. O3 froze the consumer interface — `ReviewerVerdict` frozen dataclass and the `Reviewer` Protocol live in `voss/harness/board/verdict.py` (no transitive harness imports). O4 must provide two concrete implementations of that `Reviewer` Protocol: Reviewer-A (derives the judging bar from the **original human idea** and authors verification — tests for code, an eval harness for AI cards), and Reviewer-B (independent session/model, tiered fast/strong, renders the confidence verdict the board's gate predicates consume). O4 does not build the board, does not wire the EM dispatch path, and does not design calibration outputs — those are O3, O5, and O6 respectively.

The two critical technical problems are: (1) **eval harness reuse** — `voss/eval/judge.py:judge_run` and `voss/eval/suite.py:TaskSpec`/`load_suite` are M5's offline batch eval; O4 must reuse the `Verdict`/`judge_run` async call surface as an **online** gate call, not the offline `run_suite` runner; and (2) **information isolation** — Reviewer-B must receive `[artifact, acceptance, repo, original_idea]` and nothing from EM's narrative/plan; the isolation mechanism is purely about what gets included in the `messages[]` list passed to `run_turn` (or a single `provider.complete()` call), not about process-level sandboxing.

**Primary recommendation:** Implement both reviewers as `Reviewer` Protocol implementations in `voss/harness/board/reviewer_a.py` and `voss/harness/board/reviewer_b.py`. Reviewer-A is a stateful authoring agent (`run_turn` + independent `EpisodicMemory(capacity=0)` fresh per card, no cross-card bleed). Reviewer-B is a single `provider.complete()` call (not a full agent loop) — one structured prompt with the `[artifact, acceptance, repo, original_idea]` payload, returning a `ReviewerVerdict`-shaped JSON via `response_format=ReviewerVerdict`. Tiering is a model string swap: `fast_model` (default `claude-haiku-3-5` or equivalent) at `InProgress→InReview`, `strong_model` (default `claude-opus-4-5` or `claude-sonnet-4-5`) at `→Done`. The Residual-2 check is a deterministic predicate on the returned `ReviewerVerdict.verdict == "block"` when B explicitly flags A-divergence.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reviewer-A: derive judging bar from original idea | `voss/harness/board/reviewer_a.py` | `voss/eval/judge.py` (Verdict shape) | Agent run (run_turn) with idea as the anchor; no EM narrative. |
| Reviewer-A: author tests for code cards | `voss/harness/board/reviewer_a.py` | `shell_run` (test execution) | A writes a test file, runs it deterministically; the verdict is the exit code. |
| Reviewer-A: author eval harness for AI cards | `voss/harness/board/reviewer_a.py` (orchestrates) | `voss/eval/judge.py:judge_run` (executes) | Reuse M5 judge_run as the online gate; A provides the rubric; no new judge logic. |
| Reviewer-B: independent confidence verdict | `voss/harness/board/reviewer_b.py` | `voss/harness/board/verdict.py:ReviewerVerdict` | Single provider.complete() call, tiered model selection, no EM context in messages[]. |
| Residual-2 invariant enforcement | `voss/harness/board/reviewer_b.py` | `voss/harness/board/verdict.py` | B's system prompt explicitly grants authority; verdict == "block" triggers it. |
| Model selection (tiered B) | `voss/harness/board/reviewer_b.py` | `voss_runtime/_config.py` (`default_model`) | fast_model / strong_model config; injectable for tests. |
| Information isolation | `voss/harness/board/reviewer_b.py` (message construction) | `voss/harness/agent.py:run_turn` (not used for B) | Isolation = message list construction discipline; not process sandboxing. |
| O3 `Reviewer` Protocol implementation | Both reviewer files | `voss/harness/board/verdict.py` (Protocol def) | O3 froze the interface; O4 fills it. |

---

## Standard Stack

No new external packages are required for O4. All dependencies ship with the existing harness.

### Core (all already in pyproject.toml)

| Library | Purpose | Where |
|---------|---------|-------|
| `voss.eval.judge` | `Verdict`, `judge_run`, `JUDGE_SYSTEM` — reused for AI-card eval gate | `voss/eval/judge.py` |
| `voss.eval.suite` | `TaskSpec`, `load_suite` — reused for eval suite loading | `voss/eval/suite.py` |
| `voss.harness.board.verdict` | `ReviewerVerdict`, `Reviewer` Protocol (O3-shipped) | `voss/harness/board/verdict.py` |
| `voss.harness.agent:run_turn` | Reviewer-A authoring loop — same call surface as all other agents | `voss/harness/agent.py:491` |
| `voss_runtime.EpisodicMemory` | Fresh per-card memory for Reviewer-A; `capacity=0` for B (single call) | `voss_runtime/memory/episodic.py` |
| `voss_runtime.providers.base.ModelProvider` | B's tiered `provider.complete()` interface | `voss_runtime/providers/base.py` |
| `pydantic.BaseModel` + `response_format` | Reviewer-B JSON output via structured completion (same as judge_run) | existing dep |

### No new packages needed

O4 is a harness-internal phase. `judge_run` is already the LLM-as-judge call surface. `run_turn` is already the agent loop. No new imports beyond what M5 + O3 shipped.

**Package Legitimacy Audit:** N/A — O4 installs zero new packages.

---

## Architecture Patterns

### System Architecture Diagram

```
CARD arrives at gate (from O3 Board)
        │
        ▼
┌─────────────────────────────┐
│     Reviewer-A              │  ← new (O4)
│  Input: [original_idea,     │
│          repo, artifact]    │
│  Model: any (discretion)    │
│  Memory: fresh EpisodicMem  │
│  Output: VerificationResult │
│    code: test_file + pass?  │
│    ai:   rubric → judge_run │
└──────────────┬──────────────┘
               │ VerificationResult
               ▼
┌─────────────────────────────┐
│     Reviewer-B              │  ← new (O4)
│  Input: [artifact,          │
│          acceptance,        │
│          repo,              │
│          original_idea,     │
│          A_verification]    │
│  Model: fast (intermediate) │
│         strong (→Done)      │
│  single provider.complete() │
│  Output: ReviewerVerdict    │
│    .conf / .verdict / .notes│
│    Residual-2: "block" if   │
│    A diverges from idea     │
└──────────────┬──────────────┘
               │ ReviewerVerdict
               ▼
     O3 Board gate predicate
     (conf_meets_p, etc.)
```

### Recommended Project Structure

```
voss/harness/board/
├── __init__.py           # existing (O3) — O4 adds nothing to public API here
├── verdict.py            # existing (O3) — ReviewerVerdict, Reviewer Protocol
├── machine.py            # existing (O3) — Board, Card
├── gates.py              # existing (O3) — gate predicates
├── tick.py               # existing (O3)
├── errors.py             # existing (O3)
├── stub.py               # existing (O3) — DeterministicReviewerStub
├── reviewer_a.py         # NEW (O4) — Reviewer-A: bar authoring + verification
└── reviewer_b.py         # NEW (O4) — Reviewer-B: independent tiered judgment

tests/harness/board/
├── test_reviewer_a.py    # NEW (O4)
└── test_reviewer_b.py    # NEW (O4)
```

### Pattern 1: Reviewer-B as a Single `provider.complete()` Call

**What:** Reviewer-B does NOT use `run_turn`. It makes one structured completion call with a carefully constructed `messages` list that contains ONLY `[artifact, acceptance, repo, original_idea]` — no EM plan, no A's episodic history.

**Why:** Isolation is achieved by message-list discipline. `run_turn` carries session history and the system prompt; for B, the system prompt IS the isolation mechanism (no EM narrative; explicitly grant Residual-2 authority). Single call = no loop, no context bleed.

**When to use:** Every ReviewerB.review() invocation. Tiering = model string selection before the call.

```python
# Source: voss/eval/judge.py:judge_run (direct analog — same pattern)
async def _call_reviewer_b(
    *,
    provider: ModelProvider,
    model: str,
    artifact: str,
    acceptance: str,
    repo_summary: str,
    original_idea: str,
    a_verification_summary: str,
    tier: Literal["fast", "strong"],
) -> ReviewerVerdict:
    user_msg = (
        f"## Original idea\n{original_idea}\n\n"
        f"## Acceptance criteria\n{acceptance}\n\n"
        f"## Artifact\n{artifact}\n\n"
        f"## Repository context\n{repo_summary}\n\n"
        f"## Reviewer-A verification summary\n{a_verification_summary}\n"
    )
    resp = await provider.complete(
        messages=[
            {"role": "system", "content": REVIEWER_B_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        model=model,
        response_format=ReviewerVerdict,   # pydantic structured output
        temperature=0.0,
    )
    return resp.parsed
```

**Isolation guarantee:** `messages` contains zero EM plan text, zero A's episodic turns — only the 4 declared inputs. Residual-2 authority is declared in `REVIEWER_B_SYSTEM`.

### Pattern 2: Reviewer-A Authoring Loop (run_turn with Fresh Memory)

**What:** Reviewer-A uses `run_turn` (the standard agent loop) with a fresh `EpisodicMemory(capacity=20)` per card review. The task prompt anchors to the **original idea**, not EM's AC. A uses `fs_write`/`shell_run` to author and run tests, or `judge_run` for AI cards.

**When to use:** Every ReviewerA.review() invocation.

```python
# Source: voss/harness/agent.py:491 — standard run_turn call pattern
result = await run_turn(
    _reviewer_a_task(original_idea=card.original_idea, artifact_path=card.artifact),
    tools=make_toolset(cwd, renderer=renderer),
    cwd=cwd,
    renderer=renderer,
    model=model,
    provider=provider,
    history=EpisodicMemory(capacity=20),   # fresh — zero A↔A bleed across cards
    permissions=gate_for_role(reviewer_a_spec, base_gate),
    session_id=str(uuid.uuid4()),           # fresh session — no shared session id
)
```

**Information isolation:** fresh `EpisodicMemory` per card ensures A cannot see prior card context. No EM session id shared.

### Pattern 3: AI-Card Eval Gate (Online reuse of `judge_run`)

**What:** For AI-domain cards, Reviewer-A cannot author deterministic unit tests. Instead, A authors a **rubric** (plain-text PASS/FAIL criteria), then calls `judge_run` with the artifact as `final` and the rubric. The verdict (`Verdict.verdict == "pass"`) is what O3's `eval.score >= threshold` predicate consumes.

**When to use:** Any card with `card.domain == "ai"`.

```python
# Source: voss/eval/judge.py (verified by direct read)
verdict, judge_str = await judge_run(
    provider=provider,
    model=judge_model,
    task_prompt=card.original_idea,   # the idea is the task prompt
    final=artifact_text,
    file_diff=file_diff,
    rubric=a_authored_rubric,         # Reviewer-A's rubric from bar derivation
)
# verdict is Verdict(verdict="pass"|"fail", confidence=float, rationale=str)
```

**Contract with O3:** O3's gate predicate `eval.score >= card.eval_threshold` receives `verdict.confidence` (which is 0.0–1.0 from Verdict) as the score. This is the online-gate reuse contract.

### Pattern 4: ReviewerVerdict shape (O3-frozen, read by O4)

The `ReviewerVerdict` dataclass is **frozen by O3** in `voss/harness/board/verdict.py`. O4 must produce instances of exactly this shape — no new fields, no subclassing.

```python
# Source: O3-SPEC.md REQ-7 (already implemented in board/verdict.py by O3)
@dataclass(frozen=True)
class ReviewerVerdict:
    conf: float                            # 0.0–1.0
    source: Literal["A", "B"]             # "A" for A's deterministic check; "B" for B's LLM verdict
    tier: Literal["fast", "strong"]        # B's tier; "strong" always for A (deterministic)
    verdict: Literal["pass", "fail", "block"]  # "block" = Residual-2 trigger
    notes: str
    evidence_refs: tuple[str, ...]         # paths, test names, or rubric IDs
```

### Pattern 5: Information Isolation via System Prompt + Message Construction

**What:** Reviewer-B's isolation is implemented ENTIRELY by what is placed in `messages[]`. The system prompt explicitly instructs B to judge against `[artifact, acceptance, original_idea]` only, ignores EM narrative, and grants Residual-2 authority.

**Anti-pattern:** Using a separate LLM session/process for isolation is unnecessary and complex. The harness has no multi-process isolation mechanism; isolation is message-list discipline.

```python
REVIEWER_B_SYSTEM = """You are Reviewer-B, an independent judge.

You see ONLY: the original human idea, acceptance criteria, the artifact, and 
the repository context. You do NOT see the Engineering Manager's plans, 
Reviewer-A's reasoning process, or any EM-authored narrative.

You have explicit authority to FAIL (verdict="fail") or BLOCK (verdict="block") 
any card where:
- The artifact does not satisfy the original idea (verdict="fail")
- Reviewer-A's verification diverges from what the original idea requires
  (verdict="block" — Residual-2 invariant)

Return a JSON object matching the ReviewerVerdict schema.
"""
```

### Anti-Patterns to Avoid

- **Sharing EpisodicMemory across A and B:** A and B must have independent memory instances — never pass A's history to B's call or vice versa.
- **Passing EM plan text to B:** B's `messages[]` must contain ONLY `[artifact, acceptance, repo, original_idea, A_verification_summary]`. Never include EM's ticket description, DoD, or plan reasoning.
- **Using `run_suite` (offline batch):** `voss/eval/runner.py:run_suite` is the batch CLI runner — it creates temp git repos, runs full agent sessions, writes JSONL. The O4 eval gate reuses ONLY `judge_run` (single async call). Never call `run_suite` from the board gate path.
- **Using the same model for A and B:** Model diversity between A and B increases independence. If both use the default model, the A/B split is weaker than it appears. At minimum, model is injectable; default B-strong should be the most capable available.
- **Reviewer-B using `run_turn` (multi-turn loop):** A full agent loop for B adds unnecessary latency and context bleed risk. B is a single structured call. A is the agent loop.
- **Storing A's artifacts in shared session state:** A's verification (test file, rubric) belongs in the card's session-tree node payload, not in a module-level cache or shared dict.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM-as-judge call | Custom HTTP client, custom JSON parsing | `voss/eval/judge.py:judge_run` | Already handles ParseError fallback, pydantic structured output, temperature=0. |
| Structured JSON output from B | Ad-hoc regex or `json.loads` | `response_format=ReviewerVerdict` (pydantic) via `provider.complete` | Same pattern as judge_run; validated, typed. |
| Test execution for code cards | Custom subprocess harness | `shell_run` tool (already in `make_toolset`) | Reuse existing sandboxed shell tool; captures exit code and stdout. |
| Per-role PermissionGate | Parallel auth engine | `voss.harness.team:gate_for_role` (O2-shipped) | Already compiles SubagentSpec → PermissionGate; reuse for reviewer_a_spec. |
| Reviewer-B model tier switching | Custom tier manager | model string parameter (caller selects before `provider.complete`) | Tiering is just `model = fast_model if tier == "fast" else strong_model`. |

**Key insight:** O4 is an integration phase. Every hard sub-problem (LLM calls, agent loops, gate derivation, test execution, eval judgment) is solved by existing shipped code. The authoring pattern is how you wire them, not new mechanisms.

---

## Common Pitfalls

### Pitfall 1: Treating `judge_run` as Synchronous

**What goes wrong:** `judge_run` is `async def`. Calling it without `await` (e.g. inside a synchronous `Reviewer.review()` method) silently returns a coroutine object — Python won't error, but the verdict is never computed.

**Why it happens:** The O3 `Reviewer` Protocol's `review()` method may be specified as sync or async. Confirm O3's exact signature in `verdict.py` before implementing.

**How to avoid:** Check whether O3's `Reviewer.review` is `async def` or `def`. If sync, wrap with `asyncio.run()` (only if no running event loop) or make the entire review() path async and update the Protocol.

**Warning signs:** `reviewer.review(card)` returns a coroutine object rather than a `ReviewerVerdict`.

### Pitfall 2: Memory Bleed from Shared `EpisodicMemory`

**What goes wrong:** If Reviewer-A's `EpisodicMemory` instance is reused across cards (e.g., stored on the ReviewerA class), A's judgment of card N will see artifact context from card N-1.

**Why it happens:** Convenience — one instance per reviewer class is natural OO design. But episodic memory is session-scoped, not agent-scoped.

**How to avoid:** Create `EpisodicMemory(capacity=20)` at the start of each `review()` call, not once in `__init__`. Verify with a test: two sequential `review()` calls on different cards; A's second review must not mention the first card's artifact.

**Warning signs:** Reviewer-A rationale references the wrong card's context.

### Pitfall 3: Using `run_suite` Instead of `judge_run` for Online Gate

**What goes wrong:** `voss/eval/runner.py:run_suite` launches full agent sessions in tempdir git repos, runs `k` repetitions, writes JSONL, and calls `judge_run`. Pulling it into the board gate path adds 10–60s latency per gate evaluation and creates filesystem side effects.

**Why it happens:** `judge_run` is nested inside `run_suite` — natural assumption is to call the outer function.

**How to avoid:** Import `from voss.eval.judge import judge_run` directly. Never import `from voss.eval.runner import run_suite` in board reviewer code.

**Warning signs:** A single gate evaluation writes to `.voss/eval/` or creates a tempdir.

### Pitfall 4: Circular Import via `verdict.py`

**What goes wrong:** O3 designed `verdict.py` to import ONLY from `typing` and `dataclasses`. If O4's `reviewer_b.py` imports from `verdict.py` and also from harness modules, and `verdict.py` tries to import from `reviewer_b.py`, a circular import breaks startup.

**Why it happens:** O4 may be tempted to enrich `ReviewerVerdict` or add helpers to `verdict.py`.

**How to avoid:** Never modify `verdict.py`. Reviewer implementations import FROM `verdict.py`; `verdict.py` imports from nothing in harness. The dependency is strictly one-directional.

**Warning signs:** `ImportError: cannot import name 'X' from partially initialized module`.

### Pitfall 5: Residual-2 via Heuristic String Matching

**What goes wrong:** Reviewer-B is instructed to "block if A-verification diverges from idea" but the implementation checks this by looking for keywords like "diverges" in B's rationale text. This is fragile and allows slop to propagate.

**Why it happens:** Verdict is a structured type but the Residual-2 trigger logic is tempting to implement in prose.

**How to avoid:** Residual-2 is expressed as `verdict.verdict == "block"` — a first-class enum value in the structured output. The system prompt instructs B to set `verdict="block"` specifically for divergence. Never parse B's `notes` field to detect Residual-2 — test the `.verdict` field.

**Warning signs:** Tests for Residual-2 do string matching on `verdict.notes` rather than asserting `verdict.verdict == "block"`.

### Pitfall 6: O3 NOT YET EXECUTED — Board Package May Not Exist

**What goes wrong:** O3 has a SPEC, CONTEXT, and DISCUSSION LOG but NO plan files and has not been executed. The `voss/harness/board/` package (including `verdict.py`, `ReviewerVerdict`, and the `Reviewer` Protocol) does NOT exist yet.

**Why it happens:** Research discovered O3 has only SPEC.md + CONTEXT.md + DISCUSSION-LOG.md in its phase directory — no plan files.

**How to avoid:** O4 has a hard dependency on O3. O4 execution MUST be gated behind O3 completion. The O4 plan Wave 0 should include a preflight check: `voss/harness/board/verdict.py` exists and `ReviewerVerdict` imports cleanly.

**Warning signs:** `ModuleNotFoundError: No module named 'voss.harness.board'`.

---

## Runtime State Inventory

Step 2.6 applies: O4 is a greenfield-within-harness phase with no renames or migrations.

**Stored data:** None — O4 adds new files, does not rename existing ones.
**Live service config:** None — no external service configuration.
**OS-registered state:** None.
**Secrets/env vars:** None — model strings are configuration, not secrets.
**Build artifacts:** None — Python source; no compiled artifacts to stale.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python `.venv` | All tests | ✓ | `.venv/bin/python` is the canonical interpreter (memory: voss-python-interpreter) |
| `voss.eval.judge` | AI-card eval gate | ✓ | Shipped in M5; `voss/eval/judge.py` verified present |
| `voss.eval.suite` | TaskSpec schema reference | ✓ | Shipped in M5; `voss/eval/suite.py` verified present |
| `voss.harness.board` | O4's Reviewer Protocol | ✗ (O3 not executed) | Blocked until O3 ships. Wave 0 preflight must check this. |
| `pydantic>=2.6` | `response_format=ReviewerVerdict` | ✓ | In pyproject.toml |
| `voss.harness.team:gate_for_role` | Reviewer-A permission gate | ✓ | Shipped in O2-03 |

**Missing dependencies with no fallback:**
- `voss/harness/board/verdict.py` — O3 must execute before O4 can start.

---

## Key Research Findings

### Finding 1: `voss/eval/judge.py` Contract (VERIFIED by direct read)

`judge_run` signature (file:line `voss/eval/judge.py:29-59`):
```python
async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,      # maps to: original_idea
    final: str,            # maps to: artifact text
    file_diff: str,        # maps to: git diff of artifact changes
    rubric: str,           # maps to: A-authored rubric
) -> tuple[Verdict | None, str]:   # (Verdict, "pass"|"fail"|"skipped")
```

`Verdict` (file:line `voss/eval/judge.py:12-19`):
```python
class Verdict(BaseModel):
    verdict: Literal["pass", "fail"]
    confidence: float   # ge=0.0, le=1.0
    rationale: str
```

**O4 contract note:** `Verdict.confidence` from `judge_run` maps to `ReviewerVerdict.conf` for AI-card gates. O3's predicate `eval.score >= card.eval_threshold` receives this value. `Verdict.verdict == "pass"` ↔ `ReviewerVerdict.verdict == "pass"`. These are distinct types — O4 must translate between them.

### Finding 2: `TaskSpec` shape (VERIFIED by direct read, `voss/eval/suite.py:12-26`)

`TaskSpec` holds `prompt`, `mode`, `rubric`, `judge_inputs`, `provider`, `model`, `auto_approve_edits`, `tools`. For O4's eval gate, only `rubric` and `prompt` are needed — the full TaskSpec loader is only relevant if A needs to load suite fixtures, which is unlikely for the online gate (A authors the rubric directly from the idea).

### Finding 3: O3 `ReviewerVerdict` Shape (ASSUMED — O3 not yet executed)

From O3-SPEC.md REQ-7:
```python
@dataclass(frozen=True)
class ReviewerVerdict:
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]
```

This is the interface O4 must produce. Key difference from `voss/eval/judge.py:Verdict`: `ReviewerVerdict` adds `source`, `tier`, `evidence_refs`, and supports `"block"` as a verdict (the Residual-2 path). **`Verdict` and `ReviewerVerdict` are different types.** Translation is required.

### Finding 4: O3 `Reviewer` Protocol Shape (ASSUMED — O3 not yet executed)

From O3-SPEC.md REQ-7: `class Reviewer(Protocol): def review(self, card: Card) -> ReviewerVerdict: ...`

**Critical unknown:** whether `review` is `async def` or `def`. O3-CONTEXT.md does not specify this. If `review` is sync, the async call to `judge_run` must be bridged with `asyncio.get_event_loop().run_until_complete(...)` or the Protocol must be updated to `async def`. Research strongly recommends the Protocol be `async def review(...)` — the harness is entirely asyncio-based, and sync-wrapping async in an asyncio context raises `RuntimeError: This event loop is already running`.

**Recommendation:** O4 should assume `async def review(self, card: Card) -> ReviewerVerdict` and confirm against the actual O3 `verdict.py` at Wave 0.

### Finding 5: `SubagentSpec` for Reviewers (VERIFIED by direct read, `voss/harness/subagents.py:29-40`)

The `SubagentSpec` dataclass supports `model`, `mode`, `scope`, `budget`, `tools`, `net` (all Optional, O2-shipped). For Reviewer-A and Reviewer-B, the relevant fields:
- `mode="plan"` for Reviewer-A (read artifact + write test — uses `fs_write` + `shell_run`; needs at least `"edit"` mode for test writing)
- `tools=frozenset({"fs", "test"})` for Reviewer-A
- `model=None` for Reviewer-B (model is selected per-tier at call time, not at spec compile time)

Reviewer-A and Reviewer-B must each have entries in the team registry (OTEAM-06 enforcement). From O2-03 summary: compiled registry ids for the strawman are `{ai, backend, em, frontend, ui}` — `reviewer_a` and `reviewer_b` are NOT in the default strawman roster. The `.voss team{}` declaration must add them explicitly (or O4 registers them as defaults in the compiled registry path). This needs clarification at SPEC time.

### Finding 6: Gate for Role (VERIFIED, `voss/harness/team.py:gate_for_role`)

O2-03 shipped `gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate` and `filter_toolset_for_role(spec, base_toolset)`. These are the tools O4 must use when instantiating Reviewer-A's tool surface. For Reviewer-B, no gate is needed (it's a `provider.complete()` call, not a tool-using agent).

### Finding 7: Default Model Config (VERIFIED, `voss_runtime/_config.py:8`)

```python
default_model: str = "claude-sonnet-4-5"
```

The harness default is `claude-sonnet-4-5`. For O4 tiered B:
- `fast_model` (intermediate gate): `claude-haiku-3-5` [ASSUMED — model naming convention, not verified against current Anthropic API]
- `strong_model` (→Done): `claude-opus-4-5` [ASSUMED] or keep `claude-sonnet-4-5` as strong

Both must be injectable via constructor kwargs so tests can use `StubProvider` without hitting model strings. The actual strings are Claude's discretion — what matters is that both are configurable.

### Finding 8: O2 Registration Gap — reviewer_a / reviewer_b not in default roster

From O2-03 SUMMARY: the strawman compiles to registry ids `{ai, backend, em, frontend, ui}`. The ORCHESTRATION-PLAN.md §5 strawman shows `agent reviewer_a { ... }` and `agent reviewer_b { ... }` as team agents (not roster roles). This means:

- `reviewer_a` and `reviewer_b` are **team agents** (declared with `agent reviewer_a { ... }` inside `team{}`), not **roster roles** (`roster engineers { reviewer_a { ... } }`)
- O2's `subagent_spec_from_agent` (not `subagent_spec_from_role`) is the compile path for them
- Their O2-compiled `SubagentSpec` entries should already be in the registry after O2 executes the full strawman
- **Verification needed at O4 Wave 0:** confirm that after O2+O3 execute, `registry.get("reviewer_a")` and `registry.get("reviewer_b")` return non-None specs

---

## Validation Architecture

`nyquist_validation: true` — include.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml [tool.pytest.ini_options]` — `asyncio_mode = "auto"` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/board/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -x -q --ignore=tests/eval --ignore=tests/packaging` |

### Phase Requirements → Test Map

(O4-SPEC.md does not yet exist; requirement IDs below are PROPOSED from CONTEXT.md + OPLAN §2)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORVW-01 | Reviewer-A derives bar from original idea (not EM AC) | unit | `pytest tests/harness/board/test_reviewer_a.py::test_a_uses_original_idea -x` | ❌ Wave 0 |
| ORVW-02 | Reviewer-A authors tests for code cards; exit code is verdict | unit | `pytest tests/harness/board/test_reviewer_a.py::test_a_authors_test_file -x` | ❌ Wave 0 |
| ORVW-03 | Reviewer-A uses judge_run for AI cards (rubric → Verdict) | unit | `pytest tests/harness/board/test_reviewer_a.py::test_a_ai_card_eval -x` | ❌ Wave 0 |
| ORVW-04 | Reviewer-B receives only [artifact, acceptance, repo, original_idea] | unit | `pytest tests/harness/board/test_reviewer_b.py::test_b_message_isolation -x` | ❌ Wave 0 |
| ORVW-05 | Reviewer-B uses fast model at intermediate gate | unit | `pytest tests/harness/board/test_reviewer_b.py::test_b_tier_selection -x` | ❌ Wave 0 |
| ORVW-06 | Reviewer-B uses strong model at →Done | unit | `pytest tests/harness/board/test_reviewer_b.py::test_b_tier_strong -x` | ❌ Wave 0 |
| ORVW-07 | Residual-2: B returns verdict="block" when A-verification diverges from idea | unit | `pytest tests/harness/board/test_reviewer_b.py::test_b_residual_2_block -x` | ❌ Wave 0 |
| ORVW-08 | EpisodicMemory is fresh per Reviewer-A review (no cross-card bleed) | unit | `pytest tests/harness/board/test_reviewer_a.py::test_a_memory_fresh_per_card -x` | ❌ Wave 0 |
| ORVW-09 | Both reviewers implement the O3 Reviewer Protocol | unit | `pytest tests/harness/board/test_reviewer_a.py::test_a_implements_protocol tests/harness/board/test_reviewer_b.py::test_b_implements_protocol -x` | ❌ Wave 0 |
| ORVW-10 | Full board lifecycle with real ReviewerA+B stubs drives card to Done | integration | `pytest tests/harness/board/test_reviewer_integration.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/board/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ tests/eval/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/board/test_reviewer_a.py` — covers ORVW-01..03, ORVW-08, ORVW-09
- [ ] `tests/harness/board/test_reviewer_b.py` — covers ORVW-04..07, ORVW-09
- [ ] `tests/harness/board/test_reviewer_integration.py` — covers ORVW-10
- [ ] Preflight: `voss/harness/board/verdict.py` exists (O3 must be complete first)

---

## Security Domain

`security_enforcement` is not set to false in config — include.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Reviewers use the existing provider auth path (auth.py:resolve); no new auth. |
| V3 Session Management | yes | Fresh EpisodicMemory per review prevents cross-card session leakage; fresh session_id per Reviewer-A run. |
| V4 Access Control | yes | gate_for_role(reviewer_a_spec) enforces per-role permission cap. Reviewer-B makes no fs changes. |
| V5 Input Validation | yes | All external inputs (artifact text, original_idea) are passed as string values in message dicts — no eval, no exec. Pydantic validates B's structured output. |
| V6 Cryptography | no | No cryptographic operations in O4. |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reviewer-B sees EM plan (information leakage) | Information Disclosure | message-list discipline — never add EM context to B's `messages[]` |
| Reviewer-A writes files outside review scope | Elevation of Privilege | `gate_for_role` with `mode="edit"`, scoped to artifact's directory |
| LLM-crafted artifact manipulates B's verdict (prompt injection) | Tampering | temperature=0.0 + structured output format reduces susceptibility; Residual-2 provides a second check |
| Reviewer-A's verdict is self-reported confidence | Spoofing | A produces a deterministic result (test exit code or judge_run result) — not self-assessed confidence; B produces the confidence number |
| A and B share session state | Tampering | EpisodicMemory fresh per review(); no shared session_id |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | O3's `Reviewer.review()` is `async def` (not `def`). | Pitfall 1, Finding 4 | If sync, `judge_run` can't be awaited inside `review()`; need asyncio bridge. |
| A2 | `fast_model` for B-tier = `claude-haiku-3-5` (or equivalent fast model). | Finding 7 | Wrong model string = LiteLLM routing failure; easily fixed if caught at Wave 0. |
| A3 | `strong_model` for B-tier = `claude-opus-4-5` or `claude-sonnet-4-5`. | Finding 7 | Wrong model string = LiteLLM routing failure. |
| A4 | `reviewer_a` and `reviewer_b` are already in the O2-compiled registry as team-agent specs (not roster roles). | Finding 8 | If they're absent, O4 must add a registration step or update the O2 strawman fixture. |
| A5 | `response_format=ReviewerVerdict` works with `provider.complete()` exactly as `response_format=Verdict` works in `judge_run` (pydantic structured output via LiteLLM). | Pattern 1 | If ReviewerVerdict has a field Pydantic/LiteLLM can't serialize (e.g. `tuple`), need custom serialization. |
| A6 | O3's board package exists at execution time (O3 has been executed before O4 starts). | Pitfall 6 | If O3 is skipped or only partially done, O4 imports fail. Hard gate required. |
| A7 | `evidence_refs: tuple[str, ...]` in ReviewerVerdict can be populated with test file paths (for code cards) or rubric hashes (for AI cards). | Finding 3 | If the field semantics are different, evidence_refs may be unused. |

---

## Open Questions

1. **`Reviewer.review()` sync vs async**
   - What we know: O3-SPEC.md says `def review(self, card: Card) -> ReviewerVerdict`. Harness is entirely asyncio.
   - What's unclear: Sync `def` + asyncio context = `RuntimeError: This event loop is already running` if `review` tries to `asyncio.run(judge_run(...))`.
   - Recommendation: Confirm actual O3 `verdict.py` signature at Wave 0. If sync, update the Protocol to `async def` (one-line change, zero backward-compat risk since no O4 impl exists yet). Pin this as a Wave 0 decision gate.

2. **reviewer_a / reviewer_b registry entries: team-agent vs roster-role**
   - What we know: O2's compile path has `subagent_spec_from_agent` for team-agent blocks. The strawman shows them as `agent reviewer_a { ... }`.
   - What's unclear: Did the O2-03 executed code register reviewer_a/reviewer_b in the compiled registry, or are they only in the grammar/AST but never registered because the strawman fixture only covers `team_strawman.voss` parsing?
   - Recommendation: O4 Wave 0 must verify `registry.get("reviewer_a") is not None` against the full compile path. If missing, O4 adds a registration helper or updates the strawman.

3. **Reviewer-A test authoring: shell_run exit code or file-based result**
   - What we know: Reviewer-A uses `shell_run` to run tests. `shell_run` returns stdout/stderr as a string.
   - What's unclear: Does Reviewer-A parse `[exit 0]` / `[exit 1]` from the `shell_run` output envelope, or does it use a different signal?
   - Recommendation: Parse the `[exit N]` suffix that `shell_run` appends (verified pattern in `voss/harness/tools.py`). Exit 0 = `verdict="pass"`, non-zero = `verdict="fail"`.

4. **Card.original_idea field: where does it live in Card?**
   - What we know: O3's `Card` value-object holds `(node_id, column, risk_tier, retry_count, deadline)`. `original_idea` is not in the O3 SPEC.
   - What's unclear: Does `card.original_idea` exist as a field on `Card`, or is it a field on the session-tree node, or is it passed separately as a parameter to `review()`?
   - Recommendation: O4's `review(card: Card)` signature must receive the `original_idea` somehow. Most likely solution: `Card` gains an `original_idea: str` field in O3/O4 (small O3 addendum), OR `review(card, *, original_idea: str)` adds it as a kwarg to the Protocol. Confirm at SPEC.

---

## Sources

### Primary (HIGH confidence — verified by direct read)

- `voss/eval/judge.py` — `Verdict`, `judge_run` contract, `JUDGE_SYSTEM`, ParseError handling (lines 1-59)
- `voss/eval/suite.py` — `TaskSpec`, `load_suite` (lines 1-39)
- `voss/eval/runner.py` — `run_suite` (full file; confirmed NOT appropriate for online gate)
- `voss/harness/subagents.py` — `SubagentSpec`, `SubagentRegistry`, `run_subagent`, `attach_subagent_tool` (lines 1-197)
- `voss/harness/team.py` — `gate_for_role`, `filter_toolset_for_role`, `TOOL_GROUP_ALIASES`, `DEFAULT_ROSTER` (partial read)
- `voss/harness/session_tree.py` — `SessionTreeNode`, `SessionTreeManager.allocate_child` (lines 1-180)
- `voss_runtime/_config.py` — `default_model = "claude-sonnet-4-5"` (line 8)
- `voss/harness/auth.py` — `resolve(role=...)` pattern (line 333-338)
- `.planning/ORCHESTRATION-PLAN.md` — §2 roles, §3 board, §4 cage invariants, §7 residuals, §8 decisions
- `.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md` — SubagentSpec shape, gate_for_role, scope.py reuse
- `.planning/phases/O2-voss-team-spec-roster/O2-01-SUMMARY.md` through `O2-03-SUMMARY.md` — what O2 actually shipped
- `.planning/phases/O3-board-state-machine/O3-SPEC.md` — `ReviewerVerdict`, `Reviewer` Protocol, `Card` shape, board package layout (9 requirements, 14 acceptance criteria)
- `.planning/phases/O3-board-state-machine/O3-CONTEXT.md` — module layout decisions, `verdict.py` import constraint, DeterministicReviewerStub
- `tests/eval/test_judge_verdict.py` — judge_run usage pattern, FakeJudgeProvider pattern (reusable for O4 tests)

### Secondary (MEDIUM confidence — synthesized from O3 SPEC)

- O3-SPEC.md REQ-7: `ReviewerVerdict` exact field names — confirmed from SPEC text, not from executed code
- O3-CONTEXT.md: `verdict.py` lives in `voss/harness/board/verdict.py` and imports only from `typing`, `dataclasses`

### Tertiary (LOW confidence — assumed, flagged)

- Model string `claude-haiku-3-5` for B-fast, `claude-opus-4-5` for B-strong — naming convention from `voss_runtime/_config.py` pattern, not verified against current Anthropic model list

---

## Metadata

**Confidence breakdown:**
- Eval harness contracts (`judge_run`, `Verdict`, `TaskSpec`): HIGH — code read directly
- O2 shipped surface (SubagentSpec, gate_for_role, registry): HIGH — summaries + code read directly
- O3 `ReviewerVerdict`/`Reviewer` Protocol shape: MEDIUM — from SPEC text, not executed code
- Model selection for tiered B: LOW — discretion area, model strings assumed from naming convention
- Reviewer registration in O2 registry: MEDIUM — synthesized from O2 summaries, needs Wave 0 verification
- Open Question #1 (sync vs async Protocol): LOW — SPEC says `def`, harness says asyncio everywhere; contradictory

**Research date:** 2026-05-19
**Valid until:** 2026-06-02 (stable — `judge_run` and `SubagentSpec` are stable shipped code; refresh only if O3 changes `ReviewerVerdict` shape during execution)
