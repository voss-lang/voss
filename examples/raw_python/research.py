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
