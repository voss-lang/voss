# Voss Language — Product Requirements Document

> ⊘ **SUPERSEDED** — This document is retained as the historical **language PRD** for the `.voss` language. The canonical PRD + architecture doc for Voss is now [`.planning/docs/ORCHESTRATION_LAYERS.md`](.planning/docs/ORCHESTRATION_LAYERS.md) — refer there for current product identity, the six primitives, and the roadmap. The `.voss` spec below remains accurate as the language-layer reference.

**Version:** 0.1 (Inception)  
**Status:** Pre-build  
**Author:** Ben / Wineberry  
**Purpose:** Spec for an AI agent to begin implementation

---

## 1. Overview

Voss is an AI-native programming language that compiles to Python. It introduces a type system, syntax, and runtime primitives designed specifically for probabilistic, context-aware, multi-agent computation — problems that existing languages were never designed to handle and currently require significant boilerplate to address.

The name "Voss" carries no prior language baggage, reads as sharp and minimal, and has a human surname quality consistent with modern language naming conventions (Julia, Ada, Beef).

### Elevator pitch

Every AI application written today manually implements the same five things: confidence checking, token budget management, prompt construction, semantic routing, and agent lifecycle. Voss makes these first-class language constructs. The same program that takes 300 lines of Python boilerplate takes 40 lines of Voss.

### Design philosophy

- **Uncertainty is a value, not a side effect.** Confidence propagates through the type system.
- **Context is a scope, not a string.** The token window is a first-class code construct.
- **Agents are primitives, not patterns.** Spawn, message, and gather agents the way Go handles goroutines.
- **Cost is a constraint, not an afterthought.** Token budgets and latency limits are declared in code, enforced at runtime.
- **Compiles to Python.** The entire Python AI ecosystem (LangChain, OpenAI SDK, vector DBs, etc.) is immediately available. Voss is typed syntax sugar over a powerful runtime library, not a new runtime.

---

## 2. Problem Statement

### What developers do today (the problem)

Every AI application in production manually re-implements the same patterns:

```python
# Typical production AI app — this pattern is everywhere
response = openai_client.chat.completions.create(...)
text = response.choices[0].message.content

# Confidence checking — done by hand, inconsistently
if response.choices[0].finish_reason != "stop":
    return fallback_response()

# Token budget — manually counted before every call
tokens_used = count_tokens(prompt)
if tokens_used > budget:
    prompt = truncate(prompt)  # ad-hoc truncation logic

# Semantic routing — brittle if/else or hardcoded embeddings
if any(word in text for word in ["refund", "cancel", "money back"]):
    return refund_flow()

# Agent orchestration — custom asyncio boilerplate per project
tasks = [asyncio.create_task(agent1()), asyncio.create_task(agent2())]
results = await asyncio.gather(*tasks)

# Memory — gluing together Redis + vector DB + in-memory dict manually
```

None of these patterns are solved at the language level. Every team reimplements them. Every implementation is slightly different. Bugs cluster here.

### What Voss solves

Voss makes the above patterns syntax-level constructs with compiler-enforced semantics. The developer expresses *what they want*; the Voss runtime handles *how to do it*.

---

## 3. Language Specification

### 3.1 File extension

`.voss`

### 3.2 Core type system

#### Probable\<T\>

The fundamental new type. A `probable<T>` is a value of type `T` paired with a confidence score between 0.0 and 1.0. Operations on probable values propagate uncertainty.

```voss
let label: probable<string> = classify(userInput)

# Confidence gate — only executes if confidence >= 0.85
if label @ p >= 0.85 {
    route(label.value)
} else {
    escalate(userInput)
}
```

**Compiler behavior:** If a `probable<T>` value is used in a context expecting `T` without an explicit confidence gate, the compiler emits a warning: `Unguarded probable use — confidence not checked`.

**Generated Python:**
```python
label = ProbableValue(value=classify(user_input), confidence=0.91)
if label.confidence >= 0.85:
    route(label.value)
else:
    escalate(user_input)
```

#### Supported base types

`string`, `int`, `float`, `bool`, `list<T>`, `dict<K,V>`, `agent`, `memory`

All standard types. `probable<T>` wraps any of them.

---

### 3.3 Context blocks (`ctx`)

The `ctx` block defines an execution scope in which a token budget is enforced. Variables included in the block are automatically managed to fit within the budget. The compiler statically estimates token usage and warns when a code path likely exceeds the declared budget.

```voss
ctx(budget: 4000 tokens) {
    let summary = summarize(longDocument)   # auto-compressed if needed
    let answer: probable<string> = ask("What is the key risk?")
    yield answer
}
```

**Semantics:**
- Variables brought into a `ctx` block are passed to the underlying model call automatically.
- If a variable exceeds the remaining token budget, the runtime applies the variable's declared compression strategy (`summarize` by default, configurable).
- `yield` inside a `ctx` block returns the value and closes the context scope.
- Token budget is tracked at runtime; a `BudgetExceededError` is raised if the hard limit is hit without a fallback.

**Generated Python:**
```python
with ContextScope(token_budget=4000) as ctx:
    summary = ctx.add(summarize(long_document))
    answer = ctx.ask("What is the key risk?", return_type=ProbableValue)
    return answer
```

---

### 3.4 Budget-aware execution (`within`)

```voss
within budget(tokens: 2000, latency: 500ms, cost: $0.02) {
    result = deepReason(problem)
} fallback {
    result = quickAnswer(problem)
}
```

**Semantics:**
- The `within` block monitors execution in real time.
- If any constraint is exceeded, execution is immediately redirected to the `fallback` block.
- The `fallback` block receives the original inputs; it does not receive partial results from the primary block.
- At least one of `tokens`, `latency`, or `cost` must be specified. All three are optional individually.

**Generated Python:**
```python
with BudgetScope(token_limit=2000, latency_ms=500, cost_usd=0.02) as budget:
    try:
        result = deep_reason(problem)
        budget.check()
    except BudgetExceededError:
        result = quick_answer(problem)
```

---

### 3.5 Semantic pattern matching (`match`)

Standard `match` uses structural equality. Voss adds `similar()` as a match predicate that uses embedding cosine similarity at runtime. The embedding index is generated at compile time.

```voss
match userInput {
    case similar("user is expressing frustration or anger") => escalate()
    case similar("user wants a refund or money back") => refundFlow()
    case similar("user has a billing question") => billingSupport()
    case _ => generalResponse()
}
```

**Semantics:**
- Each `similar()` string is embedded at compile time and stored in a compiled index.
- At runtime, `userInput` is embedded and compared against the index.
- The case with the highest similarity score above a threshold (default: 0.75, configurable) is selected.
- If no case exceeds the threshold, the `_` wildcard case is used.
- Cases are evaluated in order; first match above threshold wins (not highest score).

**Configuration:**
```voss
@match_threshold(0.80)
match userInput { ... }
```

**Generated Python:**
```python
_matcher = SemanticMatcher([
    ("user is expressing frustration or anger", "escalate"),
    ("user wants a refund or money back", "refund_flow"),
    ("user has a billing question", "billing_support"),
], threshold=0.75)

match _matcher.match(user_input):
    case "escalate": escalate()
    case "refund_flow": refund_flow()
    case "billing_support": billing_support()
    case _: general_response()
```

---

### 3.6 Agent concurrency

Agents are first-class primitives. Spawning an agent is a single expression. Agents communicate via typed channels.

```voss
# Define an agent
agent Researcher(topic: string) -> Report {
    system: "You are a research assistant. Be thorough and cite sources."
    tools: [webSearch, readURL]
    
    let findings = search(topic)
    return Report(content: findings)
}

# Spawn multiple agents in parallel
let topics = ["market size", "competitors", "regulations"]
let agents = topics.map(t => spawn Researcher(t))

# Gather results — blocks until all complete
let reports: list<Report> = gather(agents, timeout: 30s)
```

**Semantics:**
- `spawn` creates an agent and returns an `AgentHandle`.
- `gather(handles)` blocks until all agents complete or timeout is reached.
- `gather` with a timeout returns completed results; failed/timed-out agents return `null` in their slot.
- Agents can message each other via channels: `channel.send(value)` / `channel.recv()`.

**Agent options:**
```voss
agent MyAgent(input: string) -> string {
    system: "..."           # System prompt (required)
    tools: [tool1, tool2]   # Available tools (optional)
    model: "claude-sonnet"  # Model override (optional, defaults to config)
    retries: 3              # Auto-retry on failure (optional, default: 1)
    memory: episodic        # Memory scope (optional)
}
```

**Generated Python:**
```python
class ResearcherAgent(VossAgent):
    system_prompt = "You are a research assistant..."
    tools = [web_search, read_url]
    
    async def run(self, topic: str) -> Report:
        findings = await self.search(topic)
        return Report(content=findings)

handles = [ResearcherAgent().spawn(t) for t in topics]
reports = await gather(handles, timeout=30)
```

---

### 3.7 Memory primitives

Three built-in memory stores, declared as variable types:

```voss
# Episodic — stores conversation turns, auto-summarized when full
let history: memory.episodic(capacity: 20 turns)

# Semantic — vector store for retrieval
let knowledge: memory.semantic(source: "./docs/", model: "text-embedding-3-small")

# Working — in-context scratch pad, cleared after each ctx block
let notes: memory.working
```

**Usage:**
```voss
history.add(userMessage)
let relevant = knowledge.retrieve(query, top_k: 5)
notes.set("key", value)
```

**Functions can declare memory requirements in their signature:**
```voss
fn answerQuestion(q: string, history: memory.episodic, kb: memory.semantic) -> string {
    let context = kb.retrieve(q, top_k: 3)
    ctx(budget: 3000 tokens) {
        include history.last(5)
        include context
        yield ask(q)
    }
}
```

---

### 3.8 Tool annotation

Any Voss function annotated with `@tool` automatically generates its schema for model tool-calling. No separate schema definition required.

```voss
@tool
fn searchWeb(query: string, max_results: int = 5) -> list<SearchResult> {
    # implementation
}
```

**Generated at compile time:** A JSON schema manifest compatible with OpenAI and Anthropic tool-calling APIs. The schema is derived from the function signature and inline docstring.

---

### 3.9 Prompt inheritance

System prompts are defined as classes with inheritance.

```voss
prompt BaseAssistant {
    "You are a helpful, harmless assistant. Always be concise."
}

prompt SupportAgent extends BaseAssistant {
    "You specialize in customer support for a SaaS product.
     Always acknowledge the user's frustration before problem-solving."
}

prompt EscalationAgent extends SupportAgent {
    "You handle escalated cases. You have authority to offer refunds up to $50."
}
```

---

### 3.10 Standard operators summary

| Operator | Meaning |
|---|---|
| `@ p >= 0.85` | Confidence gate on a `probable<T>` |
| `spawn Agent(args)` | Spawn an agent, return `AgentHandle` |
| `gather(handles)` | Await all agents, return results |
| `similar("...")` | Semantic similarity predicate in match |
| `yield` | Return from a `ctx` block |
| `include` | Bring a variable into the current context scope |
| `@tool` | Annotate a function as a model-callable tool |
| `@match_threshold(n)` | Override similarity threshold for a match block |

---

## 4. Compiler Architecture

### 4.1 Pipeline

```
.voss source
    │
    ▼
Lexer (tokenizer)
    │  produces: token stream
    ▼
Parser (Lark grammar)
    │  produces: concrete syntax tree
    ▼
AST transformer
    │  produces: Voss AST (dataclasses)
    ▼
Semantic analyzer
    │  - type checking
    │  - confidence gate warnings
    │  - token budget estimation
    │  - embedding index generation (for semantic match)
    ▼
Python codegen
    │  produces: .py file importing voss_runtime
    ▼
Output: runnable Python
```

### 4.2 Technology choices

| Component | Technology | Rationale |
|---|---|---|
| Parser generator | Lark (Python) | Fast to prototype, pure Python, good error messages |
| Grammar format | Lark EBNF | Readable, well-documented |
| AST representation | Python dataclasses | Simple, typed, easy to walk |
| Codegen | String templates / ast module | ast module for correctness, string for readability |
| Embedding generation (compile-time) | sentence-transformers | Local, no API key needed at compile time |
| CLI | Click (Python) | Standard, clean |
| Editor support (later) | Tree-sitter | Syntax highlighting in Neovim/VSCode |

### 4.3 Directory structure

```
voss/
├── voss/
│   ├── __init__.py
│   ├── lexer.py           # Token definitions
│   ├── grammar.lark       # Full Lark grammar
│   ├── parser.py          # Lark parser setup
│   ├── ast_nodes.py       # Dataclass AST node definitions
│   ├── transformer.py     # Lark tree → Voss AST
│   ├── analyzer.py        # Semantic analysis + type checking
│   ├── codegen.py         # AST → Python source
│   └── cli.py             # voss compile / voss run commands
├── voss_runtime/
│   ├── __init__.py
│   ├── probable.py        # ProbableValue[T] class
│   ├── context.py         # ContextScope, BudgetScope
│   ├── semantic.py        # SemanticMatcher (embedding-based)
│   ├── agent.py           # VossAgent base class, AgentHandle
│   ├── memory.py          # EpisodicMemory, SemanticMemory, WorkingMemory
│   └── tools.py           # @tool schema generator
├── tests/
│   ├── test_parser.py
│   ├── test_codegen.py
│   └── test_runtime/
├── examples/
│   ├── hello_voss.voss
│   ├── customer_support.voss
│   └── research_swarm.voss
├── pyproject.toml
└── README.md
```

---

## 5. Runtime Library Specification

The runtime library (`voss_runtime`) is a standard Python package installed as a dependency. It is the *actual implementation* — the compiler just generates calls into it.

### 5.1 `ProbableValue[T]`

```python
@dataclass
class ProbableValue(Generic[T]):
    value: T
    confidence: float  # 0.0 - 1.0
    
    def gate(self, threshold: float) -> Optional[T]:
        """Return value if confidence >= threshold, else None."""
    
    def __matmul__(self, threshold: float) -> bool:
        """Supports `value @ 0.85` syntax via operator overload."""
```

### 5.2 `ContextScope`

```python
class ContextScope:
    def __init__(self, token_budget: int, model: str = None):
        ...
    
    def add(self, content: Any, compression: str = "summarize") -> Any:
        """Add content to context, compressing if over budget."""
    
    def ask(self, prompt: str, return_type: type = str) -> Any:
        """Execute a model call with current context contents."""
    
    def __enter__(self) -> "ContextScope": ...
    def __exit__(self, *args): ...
```

### 5.3 `BudgetScope`

```python
class BudgetScope:
    def __init__(self, token_limit: int = None, latency_ms: int = None, cost_usd: float = None):
        ...
    
    def check(self):
        """Raise BudgetExceededError if any constraint is violated."""
```

### 5.4 `SemanticMatcher`

```python
class SemanticMatcher:
    def __init__(self, cases: list[tuple[str, str]], threshold: float = 0.75, model: str = "all-MiniLM-L6-v2"):
        """cases: list of (description, label) pairs. Embeddings computed on init."""
    
    def match(self, input_text: str) -> Optional[str]:
        """Return label of best-matching case above threshold, or None."""
```

### 5.5 `VossAgent`

```python
class VossAgent(ABC):
    system_prompt: str
    tools: list = []
    model: str = "claude-sonnet-4-5"
    retries: int = 1
    
    def spawn(self, *args, **kwargs) -> "AgentHandle":
        """Create and start the agent as an async task."""
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> Any: ...

class AgentHandle:
    async def result(self) -> Any: ...
    async def cancel(self): ...

async def gather(handles: list[AgentHandle], timeout: float = None) -> list[Any]: ...
```

### 5.6 Memory classes

```python
class EpisodicMemory:
    def __init__(self, capacity: int = 20):  # capacity in turns
        ...
    def add(self, message: str, role: str = "user"): ...
    def last(self, n: int) -> list[dict]: ...
    def summarize(self) -> str: ...

class SemanticMemory:
    def __init__(self, source: str = None, model: str = "text-embedding-3-small"):
        ...
    def add(self, text: str, metadata: dict = None): ...
    def retrieve(self, query: str, top_k: int = 5) -> list[str]: ...

class WorkingMemory:
    def set(self, key: str, value: Any): ...
    def get(self, key: str) -> Any: ...
    def clear(self): ...
```

---

## 6. CLI Specification

```bash
# Compile a .voss file to Python
voss compile myprogram.voss
# Output: myprogram.py (importable, or runnable directly)

# Compile and run
voss run myprogram.voss

# Compile with options
voss compile myprogram.voss --output dist/myprogram.py --verbose

# Check/lint without compiling
voss check myprogram.voss

# Initialize a new Voss project
voss init my-project

# Show AST (debug)
voss ast myprogram.voss
```

---

## 7. Example Programs

### 7.1 Minimal — probabilistic classification

```voss
# classify.voss
fn classifyIntent(input: string) -> string {
    let intent: probable<string> = ask("Classify the intent: " + input)
    
    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "unknown"
    }
}

let result = classifyIntent("I want to cancel my subscription")
print(result)
```

### 7.2 Semantic routing — customer support

```voss
# support.voss
prompt SupportAgent {
    "You are a customer support agent for a SaaS product. Be empathetic and clear."
}

fn handleMessage(userMessage: string) -> string {
    match userMessage {
        case similar("angry, frustrated, or upset customer") => {
            return escalate(userMessage)
        }
        case similar("refund, money back, cancel subscription") => {
            return refundFlow(userMessage)
        }
        case similar("can't log in, password reset, account locked") => {
            return authSupport(userMessage)
        }
        case _ => {
            ctx(budget: 3000 tokens) {
                yield ask(userMessage)
            }
        }
    }
}
```

### 7.3 Agent swarm — research pipeline

```voss
# research.voss
agent Researcher(topic: string) -> string {
    system: "You are a research analyst. Summarize key findings concisely."
    tools: [webSearch]
    
    ctx(budget: 2000 tokens) {
        let results = webSearch(topic, max_results: 5)
        include results
        yield ask("Summarize the key findings on: " + topic)
    }
}

agent Synthesizer(reports: list<string>) -> string {
    system: "You synthesize research into executive summaries."
    
    ctx(budget: 4000 tokens) {
        include reports
        yield ask("Write a unified executive summary of these research reports.")
    }
}

fn runResearch(company: string) -> string {
    let topics = [
        company + " market position",
        company + " recent news",
        company + " competitors",
        company + " financials"
    ]
    
    let researchers = topics.map(t => spawn Researcher(t))
    let reports: list<string> = gather(researchers, timeout: 60s)
    
    within budget(tokens: 5000, latency: 10s) {
        let synth = spawn Synthesizer(reports)
        return gather([synth])[0]
    } fallback {
        return reports.join("\n---\n")
    }
}

print(runResearch("Anthropic"))
```

### 7.4 Memory-augmented assistant

```voss
# assistant.voss
let history: memory.episodic(capacity: 20 turns)
let kb: memory.semantic(source: "./knowledge_base/")

fn chat(userMessage: string) -> string {
    history.add(userMessage, role: "user")
    
    let relevant = kb.retrieve(userMessage, top_k: 3)
    
    ctx(budget: 4000 tokens) {
        include history.last(6)
        include relevant
        
        let response: probable<string> = ask(userMessage)
        history.add(response.value, role: "assistant")
        yield response.value
    }
}
```

---

## 8. Build Phases

### Phase 1 — Runtime library (Week 1–2)

Build and test `voss_runtime` as a standalone Python package. All functionality working via direct Python calls (no compiler yet). This is the foundation everything else stands on.

Deliverables:
- `ProbableValue[T]` with confidence gating
- `ContextScope` with token tracking and basic compression
- `BudgetScope` with token + latency enforcement
- `SemanticMatcher` with sentence-transformers backend
- `VossAgent` base class + `AgentHandle` + `gather()`
- `EpisodicMemory`, `SemanticMemory` (using chromadb locally), `WorkingMemory`
- Full test suite
- Example programs written in raw Python using the runtime

### Phase 2 — Parser + grammar (Week 2–3)

Build the Lark grammar and parser for the full language syntax. Focus on correctness; codegen comes next.

Deliverables:
- Complete `grammar.lark` covering all constructs
- Parser returning a valid Lark tree for all example programs
- AST node dataclasses for all language constructs
- Lark tree → Voss AST transformer
- Parser test suite (round-trip: parse every example program without error)

### Phase 3 — Semantic analysis (Week 3)

Walk the AST and validate semantics before codegen.

Deliverables:
- Type checker (catches `probable<T>` used without confidence gate)
- Token budget estimator (warns when a `ctx` block likely overflows)
- Embedding index generator (pre-computes embeddings for all `similar()` cases)
- Warning/error output with line numbers and suggestions

### Phase 4 — Codegen (Week 4)

Transform the AST into valid Python source importing `voss_runtime`.

Deliverables:
- Full codegen pass for all language constructs
- Generated Python is readable (not minified)
- All example programs compile and run correctly
- Codegen test suite (compile → run → verify output)

### Phase 5 — CLI + packaging (Week 4–5)

```
pip install voss
voss compile myprogram.voss && python myprogram.py
```

Deliverables:
- `voss compile`, `voss run`, `voss check`, `voss init` commands
- `pyproject.toml` with correct dependencies
- Published to PyPI (or installable from GitHub)
- README with quickstart

### Phase 6 — Editor support (Post-v1)

- Tree-sitter grammar for syntax highlighting
- VSCode extension (syntax highlighting + basic snippets)
- LSP server for type errors inline (stretch goal)

---

## 9. Technical Constraints and Decisions

### Decided

| Decision | Choice | Rationale |
|---|---|---|
| Compilation target | Python | AI ecosystem, no new runtime needed |
| Parser generator | Lark | Fast to prototype, pure Python |
| Default model | claude-sonnet-4-5 | Best capability/cost ratio; user-configurable |
| Embedding model (semantic match) | all-MiniLM-L6-v2 via sentence-transformers | Local, fast, no API key at compile time |
| Vector store (semantic memory) | ChromaDB (local) | Zero-config local vector store, upgradeable |
| Python version | 3.11+ | Match-statement support required |
| Async model | asyncio | Standard; agents use `async/await` under the hood |

### Open questions (agent should flag these, not decide)

1. **Model provider abstraction** — should the runtime support multiple providers (OpenAI, Anthropic, Ollama) via a unified interface, or Anthropic-only for v1?
2. **Compiled index storage** — where should compile-time embedding indexes be stored? Alongside the `.py` file, or in a separate `.voss-cache/` directory?
3. **Error handling syntax** — should Voss have its own `try/catch` equivalent, or inherit Python's? The `within/fallback` pattern covers the AI-specific case but not general exceptions.
4. **Import system** — how should multi-file Voss programs import each other? Mirror Python's `import` or design something new?

---

## 10. Success Metrics (v1)

- The three example programs in Section 7 compile and run correctly end-to-end
- A non-trivial customer support bot (semantic routing + episodic memory + agent escalation) can be written in under 60 lines of Voss
- `pip install voss` works on macOS and Linux
- Compiler produces readable, debuggable Python output (not minified)
- `voss check` catches unguarded `probable<T>` usage with line numbers

---

## 11. Out of Scope (v1)

- Native compilation (LLVM, Wasm)
- Voss-to-TypeScript or any target other than Python
- Standard library beyond AI primitives (no file I/O, HTTP, etc. — use Python interop)
- Package manager (use pip)
- Debugger
- LSP / language server
- Concurrency beyond asyncio (no multi-process, no distributed agents)
- Fine-tuning or training integrations

---

## 12. Dependencies

```toml
[project]
name = "voss"
requires-python = ">=3.11"
dependencies = [
    "lark>=1.1.9",           # Parser generator
    "anthropic>=0.25.0",     # Default model provider
    "openai>=1.0.0",         # Optional provider
    "sentence-transformers>=2.7.0",  # Compile-time embeddings
    "chromadb>=0.5.0",       # Local vector store for semantic memory
    "click>=8.1.0",          # CLI
    "rich>=13.0.0",          # Terminal output formatting
]
```

---

## 13. Agent Instructions

**If you are an AI agent reading this document, here is your build order:**

1. Create the repository structure from Section 4.3 exactly.
2. Implement `voss_runtime` (Section 5) completely before touching the compiler. Write tests. Make sure the runtime works with direct Python calls using the example programs in Section 7 rewritten as raw Python.
3. Write the Lark grammar (`grammar.lark`) for the full syntax in Section 3. Start with the simplest construct (`probable<T>` and confidence gates) and add constructs incrementally.
4. Build the transformer (Lark tree → AST nodes) and verify it parses all example programs.
5. Build semantic analysis — type checker and confidence gate warnings.
6. Build codegen — emit Python that imports `voss_runtime` and calls the correct classes.
7. Wire everything together in the CLI.
8. Verify all example programs in Section 7 compile and run.

**Flag the open questions in Section 9 before making architectural decisions that affect them.** Default choices in the absence of guidance: multi-provider support via abstraction layer, compiled indexes in `.voss-cache/`, inherit Python exceptions with `within/fallback` for AI-specific cases, Python-style `import` for multi-file programs.