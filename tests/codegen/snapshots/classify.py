import asyncio

from voss_runtime import ContextScope

async def classifyIntent(input: str) -> str:
    async with ContextScope(token_budget=4000) as ctx:
        intent: str = await ctx.ask('Classify the intent: ' + input)
    return intent or 'unknown'

async def main():
    result = await classifyIntent('I want to cancel my subscription')
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
