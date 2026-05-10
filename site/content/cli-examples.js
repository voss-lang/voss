// Hero examples mirrored from /Voss/examples/raw_python/.
// Once the Voss compiler ships, swap these for the .voss source.

export const cliExamples = [
  {
    id: "classify",
    label: "Classify",
    blurb: "Confidence-gated intent classification.",
    command: "voss run classify.py",
    lang: "python",
    code: `from voss_runtime import ContextScope, ProbableValue

async def classify_intent(user_input: str) -> str:
    async with ContextScope(token_budget=1000) as ctx:
        await ctx.add(f"Classify the intent: {user_input}")
        intent: ProbableValue = await ctx.ask(
            "Return only the intent label.",
            return_type=ProbableValue,
        )
        if intent @ 0.80:
            return intent.value
        return "unknown"
`,
  },
  {
    id: "support",
    label: "Support",
    blurb: "Semantic routing for a support inbox.",
    command: "voss run support.py",
    lang: "python",
    code: `from voss_runtime import ContextScope, SemanticMatcher

matcher = SemanticMatcher(
    cases=[
        ("angry, frustrated, or upset customer", "escalate"),
        ("refund, money back, cancel subscription", "refund"),
        ("can't log in, password reset, account locked", "auth"),
    ],
    threshold=0.55,
)

async def handle_message(msg: str) -> str:
    label = matcher.match(msg)
    if label == "escalate": return await escalate(msg)
    if label == "refund":   return await refund_flow(msg)
    if label == "auth":     return await auth_support(msg)
    async with ContextScope(token_budget=3000) as ctx:
        await ctx.add("system: You are a customer support agent.")
        return await ctx.ask(msg)
`,
  },
  {
    id: "research",
    label: "Research",
    blurb: "Parallel agents with timeout and graceful fallback.",
    command: "voss run research.py",
    lang: "python",
    code: `from voss_runtime import ContextScope, VossAgent, gather, run_with_budget
from voss_runtime.exceptions import BudgetExceededError

class Researcher(VossAgent):
    system_prompt = "You are a research analyst."

    async def run(self, topic: str) -> str:
        async with ContextScope(token_budget=2000) as ctx:
            await ctx.add("\\n".join(web_search(topic, max_results=5)))
            return await ctx.ask(f"Summarize key findings on: {topic}")

async def run_research(company: str) -> str:
    topics = [f"{company} market", f"{company} news", f"{company} comps"]
    workers = [Researcher().spawn(t) for t in topics]
    reports = [r for r in await gather(workers, timeout=60) if r]
    try:
        synth = Synthesizer().spawn(reports)
        return await run_with_budget(synth.result(), token_limit=5000)
    except BudgetExceededError:
        return "\\n---\\n".join(reports)
`,
  },
];
