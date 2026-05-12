# Voss vs raw Python

.voss compiles to readable Python. The three canonical samples in [`samples/`](../samples/) are paired below with the hand-written Python equivalents in [`examples/raw_python/`](../examples/raw_python/). Each .voss program makes LLM-shaped concerns explicit (confidence gates, token budgets, semantic routing, agent fan-out, episodic memory, try/catch fallback) where raw Python leaves them implicit or scattered. See the [README](../README.md) for higher-level framing.

## Classify

The .voss program declares the classifier's return type as `probable<string>` and gates use of `intent.value` on `@ p >= 0.80` — the confidence threshold is a syntactic construct, not a magic number buried in an `if`. Raw Python achieves the same behavior with `ContextScope` + `ProbableValue` + the `@` operator, but the surrounding ceremony (async context manager, explicit `return_type=ProbableValue`, manual `await ctx.add`) dilutes the intent.

`samples/classify.voss`:

```voss
# classify.voss
# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.
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

`examples/raw_python/classify.py`:

```python
"""PRD §7.1 — probabilistic classification, hand-written in Python."""
from __future__ import annotations
import asyncio
from voss_runtime import ContextScope, ProbableValue

async def classify_intent(user_input: str) -> str:
    async with ContextScope(token_budget=1000) as ctx:
        await ctx.add(f"Classify the intent: {user_input}")
        intent: ProbableValue = await ctx.ask(
            "Return only the intent label.", return_type=ProbableValue,
        )
        if intent @ 0.80:
            return intent.value
        return "unknown"

if __name__ == "__main__":
    result = asyncio.run(classify_intent("I want to cancel my subscription"))
    print(result)
```

## Support

The .voss program expresses semantic routing as a `match` with `case similar(...)` branches; the runtime embedding work, threshold, and case labels are inferred by the compiler. It declares episodic memory at module scope (`let tickets: memory.episodic(capacity: 50 turns)`) and uses `tickets.last(6)` inside a `ctx(budget: 3000 tokens) { ... }` block. Raw Python has to wire up `SemanticMatcher(cases=..., threshold=...)`, dispatch labels with an if-ladder, construct `EpisodicMemory(capacity=50)` itself, manually call `tickets.add` at function entry, and feed `tickets.last(6)` into a `ContextScope` it also constructed by hand.

`samples/support.voss`:

```voss
# support.voss
# support.voss — prompt block, match similar (semantic routing), ctx(budget: N tokens), memory.episodic.
prompt SupportAgent {
    "You are a customer support agent for a SaaS product. Be empathetic and clear."
}

let tickets: memory.episodic(capacity: 50 turns)

fn handleMessage(userMessage: string) -> string {
    tickets.add(userMessage, role: "user")
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
                include tickets.last(6)
                yield ask(userMessage)
            }
        }
    }
}
```

`examples/raw_python/support.py`:

```python
"""PRD §7.2 — customer support: semantic routing + ctx blocks + prompt classes (raw Python)."""
from __future__ import annotations
import asyncio
from voss_runtime import ContextScope, EpisodicMemory, SemanticMatcher

SUPPORT_SYSTEM_PROMPT = (
    "You are a customer support agent for a SaaS product. Be empathetic and clear."
)

tickets = EpisodicMemory(capacity=50)

matcher = SemanticMatcher(
    cases=[
        ("angry, frustrated, or upset customer", "escalate"),
        ("refund, money back, cancel subscription", "refund"),
        ("can't log in, password reset, account locked", "auth"),
    ],
    threshold=0.55,
)

async def escalate(msg: str) -> str:
    return f"[escalated] {msg}"

async def refund_flow(msg: str) -> str:
    return f"[refund flow] {msg}"

async def auth_support(msg: str) -> str:
    return f"[auth support] {msg}"

async def handle_message(user_message: str) -> str:
    tickets.add(user_message, role="user")
    label = matcher.match(user_message)
    if label == "escalate":   return await escalate(user_message)
    if label == "refund":     return await refund_flow(user_message)
    if label == "auth":       return await auth_support(user_message)
    async with ContextScope(token_budget=3000) as ctx:
        await ctx.add(f"system: {SUPPORT_SYSTEM_PROMPT}")
        await ctx.add(tickets.last(6))
        return await ctx.ask(user_message)

if __name__ == "__main__":
    print(asyncio.run(handle_message("I am furious, fix this NOW")))
```

## Research

The .voss program uses `agent` blocks with declarative `system:` and `tools:` fields, `spawn` to launch parallel researchers, `gather(..., timeout: 60s)` to await them, and a `within budget(tokens: ..., latency: ...) { ... } fallback { ... }` block to bound the synthesizer with an explicit fallback path. A `try { ... } catch e { ... }` block wraps the web search call so a failing tool degrades to an `"web search unavailable"` context line instead of an exception. Raw Python builds the same shape from `VossAgent` subclasses, `asyncio.gather`-equivalent helpers, `run_with_budget`, manual `try`/`except Exception`, and an explicit `except BudgetExceededError` fallback — readable, but the control structure is buried in plumbing.

`samples/research.voss`:

```voss
# research.voss
# research.voss — agent, spawn, gather, ctx(budget: N tokens), within/fallback, try/catch, use.

use voss_runtime::tools::tool

agent Researcher(topic: string) -> string {
    system: "You are a research analyst. Summarize key findings concisely."
    tools: [webSearch]

    ctx(budget: 2000 tokens) {
        try {
            let results = webSearch(topic, max_results: 5)
            include results
        } catch e {
            include "web search unavailable"
        }
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

`examples/raw_python/research.py`:

```python
"""PRD §7.3 — research swarm: agents, spawn, gather, within/fallback (raw Python)."""
from __future__ import annotations

import asyncio

from voss_runtime import (
    ContextScope,
    VossAgent,
    gather,
    run_with_budget,
    tool,
)
from voss_runtime.exceptions import BudgetExceededError


@tool
def web_search(query: str, max_results: int = 5) -> list[str]:
    """Search the web for the given query and return top results."""
    return [f"result-{i} for {query}" for i in range(max_results)]


class Researcher(VossAgent):
    system_prompt = "You are a research analyst. Summarize key findings concisely."
    tools = (web_search,)

    async def run(self, topic: str) -> str:
        async with ContextScope(token_budget=2000) as ctx:
            try:
                results = web_search(topic, max_results=5)
                await ctx.add("\n".join(results))
            except Exception:
                await ctx.add("web search unavailable")
            return await ctx.ask(f"Summarize the key findings on: {topic}")


class Synthesizer(VossAgent):
    system_prompt = "You synthesize research into executive summaries."

    async def run(self, reports: list[str]) -> str:
        async with ContextScope(token_budget=4000) as ctx:
            await ctx.add("\n---\n".join(reports))
            return await ctx.ask(
                "Write a unified executive summary of these research reports."
            )


async def run_research(company: str) -> str:
    topics = [
        f"{company} market position",
        f"{company} recent news",
        f"{company} competitors",
        f"{company} financials",
    ]
    researchers = [Researcher().spawn(t) for t in topics]
    reports = await gather(researchers, timeout=60)
    reports = [r for r in reports if r is not None]
    try:
        synth = Synthesizer().spawn(reports)
        return await run_with_budget(
            synth.result(), token_limit=5000, latency_ms=10_000
        )
    except BudgetExceededError:
        return "\n---\n".join(reports)


if __name__ == "__main__":
    print(asyncio.run(run_research("Anthropic")))
```

## Line counts

| Sample | .voss | raw Python |
| --- | --- | --- |
| classify | 14 | 18 |
| support | 28 | 42 |
| research | 49 | 67 |

Regenerate with `wc -l samples/*.voss examples/raw_python/*.py`.
