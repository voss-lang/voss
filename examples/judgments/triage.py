import asyncio
import sys

from voss_runtime import ChoiceQuestion, judge, to_probable


async def triage(text: str) -> str:
    res = await judge(text, {"route": ChoiceQuestion(
        "Which support queue should handle this request?",
        {"billing": "Payment, refund, or invoice issue.", "other": "Anything else."},
    )})
    p = to_probable(res.answers["route"])
    return p.value if p @ 0.80 else "unknown"


if __name__ == "__main__":
    print(asyncio.run(triage(sys.argv[1])))
