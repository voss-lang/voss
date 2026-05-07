# Voss

A language for confidence-aware, budget-bounded LLM programs. Voss makes probabilistic values, context windows, and per-call budgets first-class so that AI-augmented code is auditable and predictable instead of vibes-based.

> **Phase 1 status:** runtime library shipped. The compiler does not yet exist — `.voss` source files are not parsed today. The three PRD §7 examples run as raw Python against `voss_runtime`. See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for the path to a full compiler.

## Install

```bash
pip install -e ".[dev]"
```

Not on PyPI yet. Python 3.11+ required.

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
- [.planning/PROJECT.md](.planning/PROJECT.md) — core value, constraints
- [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) — RUN/GRAM/ANLY/GEN/CLI requirements
- [.planning/ROADMAP.md](.planning/ROADMAP.md) — six-phase delivery plan
