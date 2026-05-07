# Phase 1: Runtime Library - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `voss_runtime` as a standalone, pip-installable Python package implementing every primitive Voss will codegen against: `ProbableValue[T]`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent` + `AgentHandle` + `gather()`, `EpisodicMemory`, `SemanticMemory`, `WorkingMemory`, `@tool`, plus a multi-provider model abstraction.

The runtime must be exercisable today via hand-written Python — the PRD §7 examples can be expressed in raw Python using only `voss_runtime`, and they execute correctly. No compiler exists yet; this phase locks runtime semantics before any syntax work begins.

**In scope (RUN-01..11):** all classes, multi-provider abstraction, `@tool` schema generation, full pytest suite.

**Out of scope:** Lark grammar, AST, transformer, semantic analysis, codegen, CLI, Linguist tooling, end-to-end `.voss` example execution. Those land in later phases.

</domain>

<decisions>
## Implementation Decisions

### Provider Abstraction
- **D-01:** Multi-provider abstraction is built on **LiteLLM** as the backbone. Voss exposes a `ModelProvider` protocol; the default implementation delegates to LiteLLM (`litellm.completion` / `litellm.acompletion`) so Anthropic, OpenAI, and Ollama all work through one unified surface. Users may register a custom `ModelProvider` if they want to bypass LiteLLM for a specific model.
- **D-02:** **No streaming** in v1 runtime. All model calls return full responses synchronously (or via `await` for async). Streaming primitive deferred — keeps `ContextScope`/`BudgetScope` semantics tractable.
- **D-03:** Provider config = **env vars + `voss_runtime.configure(...)` overrides**. Standard env (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_HOST`) plus a global `configure(default_model="claude-sonnet-4-5", ...)` for project-level defaults. Per-call kwargs (`model=`, `api_key=`) always override.
- **D-04:** **Cost tracking is on by default.** LiteLLM's per-call `response.usage` + cost is exposed via `BudgetScope.cost_so_far` and `BudgetScope.tokens_so_far`. Required to enforce `cost: $0.02` budgets meaningfully.
- **D-05:** v1 runtime test matrix gates on **all three providers** (Anthropic, OpenAI, Ollama). Live-mode CI must pass against each. Stub-mode CI is the default; live mode is opt-in (see test strategy).

### Token Counting & Budget Enforcement
- **D-06:** Token counting uses **`litellm.token_counter(model=..., text=...)`**. Single API, dispatches per-provider under the hood (tiktoken for OpenAI, Anthropic SDK count for Claude, etc.). No bespoke per-provider branching in our code.
- **D-07:** `ContextScope` counts tokens **per `ctx.add()` call** and triggers compression immediately when the running total would exceed budget. Predictable, fast feedback, fewer surprises at `ctx.ask()` time.
- **D-08:** `BudgetScope` enforces latency via **`asyncio.wait_for(coro, timeout=ms/1000)`**. On `asyncio.TimeoutError`, cancel the primary block and raise `BudgetExceededError(reason="latency")`. The compiler's `within/fallback` codegen catches this and routes to the fallback block.
- **D-09:** When `BudgetExceededError` is raised inside a `BudgetScope` and **no `fallback` is registered, it propagates to the caller** as a normal Python exception. Voss `try/catch` (Phase 4 codegen) lets users handle it explicitly.

### Agent Output Typing
- **D-10:** Agent return types are parsed via **Pydantic + provider-native structured outputs**. LiteLLM's `response_format=<PydanticModel>` (under the hood: Anthropic tool-use, OpenAI `response_format`, Ollama JSON mode) returns a validated Pydantic instance.
- **D-11:** Voss class types (`class Report { content: string }`) **codegen to Pydantic `BaseModel` subclasses** in Phase 4. Phase 1 runtime exposes a `VossModel = pydantic.BaseModel` alias and the hand-written PRD §7 examples use Pydantic models directly. This keeps runtime ↔ codegen contract clean: agent return types are always `BaseModel` subclasses.
- **D-12:** Parse/validation failures consume the agent's **`retries=` budget** (default 1). After retries exhausted: raise. API errors and parse errors share one budget — simpler mental model.
- **D-13:** `@tool` schema generation reads **`inspect.signature` + `typing.get_type_hints` + first-line docstring**. Complex argument types are auto-converted to Pydantic field schemas. Output schema is OpenAI/Anthropic tool-format compatible. No explicit Pydantic model required for tool args, but accepted if provided.

### Test Strategy
- **D-14:** Default test mode is **`StubProvider`** — a deterministic in-memory `ModelProvider` returning canned responses keyed by prompt fingerprint. Fast, free, hermetic. CI runs in stub mode by default (`pytest`).
- **D-15:** Live-mode tests run via **`pytest -m live`**. Hits real Anthropic, OpenAI, and Ollama. Run nightly and on release branches; not on every PR.
- **D-16:** **Ollama in CI uses a GitHub Actions service container** (`ollama/ollama` image) pulling a small model (`llama3.2:1b` or similar). Free, real local-provider coverage in the live job.
- **D-17:** Coverage gate: **≥90% line coverage on pure logic** (`ProbableValue`, `BudgetScope` math, `SemanticMatcher` matching, memory data structures). LLM-touching code paths (provider abstraction, agent run loop, ctx.ask) get smoke tests + stub-driven behavior tests; not held to the same numeric bar.
- **D-18:** Compression strategy is verified with a **stub summarizer**: a deterministic `summarize` callable that shrinks input by a known ratio. Tests assert `ContextScope` invokes summarization at the right moment and final token count fits budget. Real-LLM summarization quality is validated manually, not in unit tests.

### Claude's Discretion
- Internal package layout under `voss_runtime/` (file split per class vs. logical grouping) — match PRD §4.3 as starting point, refine as code lands.
- Specific stub provider response format (dict, callable, fixture file) — pick whatever yields cleanest test code; document in test README.
- Exception class hierarchy beyond `BudgetExceededError` — define as needed (`ProviderError`, `ParseError`, etc.) following standard Python conventions.
- Channel API surface for inter-agent messaging (PRD §3.6 mentions `channel.send/recv`) — design within the agent runtime; minimal v1 implementation acceptable.
- Working memory eviction policy when crossing ctx boundaries — implement per PRD §3.7 ("cleared after each ctx block"); details left to implementer.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `PRD.md` §3 — Full language specification for every construct the runtime backs (`probable<T>`, `ctx`, `within/fallback`, `match similar`, agent primitives, memory primitives, `@tool`, `prompt`, operator summary)
- `PRD.md` §5 — Runtime library specification with class signatures (`ProbableValue`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent`, memory classes) — these are the contracts to implement
- `PRD.md` §7 — Three example programs that must run as hand-written Python against the runtime (validates semantics)
- `PRD.md` §13 — Build-order mandate: runtime first, compiler later
- `.planning/PROJECT.md` — Core value, constraints, key decisions (multi-provider, asyncio, Python 3.11+)
- `.planning/REQUIREMENTS.md` — RUN-01..11 acceptance criteria
- `.planning/ROADMAP.md` Phase 1 — Goal and success criteria

### Library Documentation (fetch via context7 during planning/research)
- LiteLLM — provider abstraction, `litellm.completion`, `litellm.token_counter`, structured outputs via `response_format`, cost tracking via `response.usage`
- Pydantic v2 — `BaseModel`, structured-output integration, JSON schema generation
- ChromaDB — local persistent client, collection API for `SemanticMemory`
- sentence-transformers — `SentenceTransformer("all-MiniLM-L6-v2")` for compile-time embeds (also reusable at runtime if user opts out of OpenAI embeddings)
- pytest + pytest-asyncio — async test fixtures, marker config for `-m live`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
None — greenfield. No prior code to lean on.

### Established Patterns
None yet. Phase 1 establishes them:
- Async-first runtime (asyncio everywhere model I/O is involved)
- `ModelProvider` protocol as the single seam for provider work
- Pydantic as the typing boundary between Voss and Python
- Stub-first testability (every external dependency mockable via injectable provider)

### Integration Points
- Runtime is a standalone pip package. Phase 4 codegen will emit Python that does `from voss_runtime import ...`. The class names and signatures established in Phase 1 are the API contract for codegen — keep them stable.
- `.voss-cache/` (Phase 3) will store compile-time embedding indexes; runtime `SemanticMatcher.from_index(path)` should be able to load them. Design the index file format here so Phase 3 can write what Phase 1 reads.

</code_context>

<specifics>
## Specific Ideas

- Default model = `claude-sonnet-4-5` (PRD §9 decision; carry forward).
- Compile-time embeddings model = `sentence-transformers/all-MiniLM-L6-v2` (local, no API key).
- Runtime `SemanticMemory` default embedding model = `text-embedding-3-small` (OpenAI), per PRD §5.6 — but configurable; users with no OpenAI key should be able to fall back to local sentence-transformers via config.
- `ProbableValue.__matmul__` overloads `@` so `value @ 0.85` returns a `bool` matching the spec's confidence-gate syntax.
- `gather(handles, timeout=N)` returns `None` in slots whose agent timed out or raised, mirroring PRD §3.6 semantics.

</specifics>

<deferred>
## Deferred Ideas

- **Streaming model output** — useful for UX but complicates budget enforcement; revisit post-v1 once core semantics are battle-tested.
- **Distributed/multi-process agents** — explicitly out of scope per PROJECT.md.
- **Public PyPI publication + onboarding polish** — Phase 5 ships an installable package locally; PyPI launch is a v2 milestone.
- **Custom (non-LiteLLM) provider plug-ins for esoteric models** — `ModelProvider` protocol leaves the door open, but no extra implementations beyond the LiteLLM-backed default in v1.
- **Compression strategies beyond summarize** — middle-out truncation, semantic chunk drop, etc. PRD §3.3 says "summarize by default, configurable"; v1 ships summarize only.
- **Channel API for richer inter-agent messaging** — minimal `channel.send/recv` only in v1; pub/sub, fan-out, persistent channels deferred.

</deferred>

---

*Phase: 1-Runtime Library*
*Context gathered: 2026-05-07*
