from voss_runtime import ContextScope, SemanticMatcher

SUPPORT_AGENT_PROMPT = "You are a customer support agent for a SaaS product. Be empathetic and clear."

async def handleMessage(userMessage: str) -> str:
    _matcher_1 = SemanticMatcher(
        cases=[('angry, frustrated, or upset customer', 'escalate'), ('refund, money back, cancel subscription', 'refund'), ("can't log in, password reset, account locked", 'auth')],
        threshold=0.55,
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )
    match _matcher_1.match(userMessage):
        case "escalate":
            return escalate(userMessage)
        case "refund":
            return refundFlow(userMessage)
        case "auth":
            return authSupport(userMessage)
        case _:
            async with ContextScope(token_budget=3000) as ctx:
                return await ctx.ask(userMessage)
