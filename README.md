# Voss

A language for confidence-aware, budget-bounded LLM programs. Voss makes probabilistic values, context windows, and per-call budgets first-class so that AI-augmented code is auditable and predictable instead of vibes-based.

## What is .voss

.voss is an **AI workflow control** layer that compiles to readable Python. It is a complement to Python, not a replacement: write your data structures, business logic, and integrations in Python as usual, and reach for .voss when you need first-class control over LLM-shaped concerns.

First-class primitives:

- Probable values + confidence gates: `let intent: probable<string> = ask(...)` with `if intent @ p >= 0.80 { ... }`
- Context budgets: `ctx(budget: 4000 tokens) { include ... yield ask(...) }` and `within budget(tokens: N, latency: Ts) { ... } fallback { ... }`
- Semantic routing: `match userMessage { case similar("angry customer") => ... case _ => ... }`
- Agents, spawn, gather: `spawn Researcher(topic)` + `gather(researchers, timeout: 60s)`
- Memory primitives: `memory.episodic(capacity: N turns)`, `memory.semantic(source: "...")`, `memory.working(capacity: N)`
- Recovery + imports: `try { ... } catch e { ... }` and `use voss_runtime::tools::tool`

See the [`samples/`](samples/) directory for the three canonical programs, and [`docs/voss-vs-python.md`](docs/voss-vs-python.md) for side-by-side comparisons against the raw-Python equivalents.

## Install

```bash
pip install -e ".[dev]"
```

Not on PyPI yet. Python 3.11+ required.

If you want to opt into the compiled harness with `VOSS_HARNESS=compiled`, eagerly populate the local harness cache after install. The default Python harness path works without this step.

```bash
voss compile voss/harness/agent/
```

## Quickstart

The runtime exposes `ProbableValue`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent`, `gather`, `@tool`, and the three memory primitives. See:

- [`examples/raw_python/classify.py`](examples/raw_python/classify.py) — PRD §7.1, confidence-gated classification
- [`examples/raw_python/support.py`](examples/raw_python/support.py) — PRD §7.2, semantic routing + ContextScope fallback
- [`examples/raw_python/research.py`](examples/raw_python/research.py) — PRD §7.3, agent swarm with `gather` + `run_with_budget` fallback

```python
import asyncio
from voss_runtime import ContextScope, ProbableValue

async def classify(text: str) -> str:
    async with ContextScope(token_budget=1000) as ctx:
        await ctx.add(f"Classify: {text}")
        intent: ProbableValue = await ctx.ask(
            "Return only the intent label.", return_type=ProbableValue
        )
        return intent.value if intent @ 0.80 else "unknown"

print(asyncio.run(classify("I want to cancel my subscription")))
```

## Tests

Default (stub providers, hermetic, fast):

```bash
pytest -q -m "not live"
```

With coverage:

```bash
pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing
```

Live mode (real Anthropic / OpenAI / Ollama — requires API keys + Ollama service):

```bash
pytest -q -m live
```

Live mode runs nightly in CI; stub mode runs on every PR.

## Project Docs

- [PRD.md](PRD.md) — full language specification
- [docs/voss-vs-python.md](docs/voss-vs-python.md) — side-by-side .voss vs raw Python with LOC counts
- [.planning/PROJECT.md](.planning/PROJECT.md) — core value, constraints
- [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) — RUN/GRAM/ANLY/GEN/CLI requirements
- [.planning/ROADMAP.md](.planning/ROADMAP.md) — six-phase delivery plan
