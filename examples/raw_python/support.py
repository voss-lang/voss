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
