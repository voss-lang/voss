import pytest

from voss.harness import judgments
from voss_runtime.judgments import ChoiceResult, NoulResult, ScoreResult

pytestmark = pytest.mark.live


async def test_live_synthetic_smoke():
    if judgments.is_killed():
        pytest.skip(judgments.KILLED_MESSAGE)
    found = judgments.resolve_api_key()
    if found is None:
        pytest.skip("TYPESAFE_API_KEY not configured (env or keychain)")
    state, questions = judgments.demo_request()
    async with judgments.make_client(found[0]) as client:
        result = await client.evaluate(state, questions)
    assert len(result.answers) == 3
    assert {type(answer) for answer in result.answers.values()} == {ChoiceResult, ScoreResult, NoulResult}
    assert result.model and result.input_tokens > 0 and result.latency_ms > 0
    assert 1 <= result.attempts <= 2
    print(f"jev smoke: model={result.model} in={result.input_tokens} out={result.output_tokens} latency_ms={result.latency_ms:.0f} cost_usd~{result.cost_usd_estimate:.8f}")
