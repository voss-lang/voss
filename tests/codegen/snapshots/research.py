import asyncio

from voss_runtime import BudgetExceededError, ContextScope, VossAgent, gather, run_with_budget

class Researcher(VossAgent):
    system_prompt = "You are a research analyst. Summarize key findings concisely."
    tools = (webSearch,)

    async def run(self, topic: str) -> str:
        async with ContextScope(token_budget=2000) as ctx:
            results = webSearch(topic, max_results=5)
            await ctx.add(results)
            return await ctx.ask('Summarize the key findings on: ' + topic)

class Synthesizer(VossAgent):
    system_prompt = "You synthesize research into executive summaries."

    async def run(self, reports: list[str]) -> str:
        async with ContextScope(token_budget=4000) as ctx:
            await ctx.add(reports)
            return await ctx.ask('Write a unified executive summary of these research reports.')

async def runResearch(company: str) -> str:
    topics = [company + ' market position', company + ' recent news', company + ' competitors', company + ' financials']
    researchers = [Researcher().spawn(t) for t in topics]
    reports: list[str] = await gather(researchers, timeout=60)
    async def _within_primary_():
        synth = Synthesizer().spawn(reports)
        return (await gather([synth]))[0]
    try:
        return await run_with_budget(_within_primary_(), token_limit=5000, latency_ms=10000)
    except BudgetExceededError:
        return '\n---\n'.join(reports)

async def main():
    print(await runResearch('Anthropic'))

if __name__ == "__main__":
    asyncio.run(main())
