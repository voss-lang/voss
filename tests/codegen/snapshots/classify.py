import asyncio

from voss_runtime import ContextScope, ProbableValue

async def classifyIntent(input: str) -> str:
    async with ContextScope(token_budget=4000) as ctx:
        intent: ProbableValue = await ctx.ask('Classify the intent: ' + input, return_type=ProbableValue)
    if intent.confidence >= 0.8:
        return intent.value
    else:
        return 'unknown'

async def main():
    result = await classifyIntent('I want to cancel my subscription')
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
