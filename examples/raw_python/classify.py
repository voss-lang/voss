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
