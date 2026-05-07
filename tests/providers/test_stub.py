from __future__ import annotations

from pydantic import BaseModel

from voss_runtime.providers.stub import StubProvider


class _Person(BaseModel):
    name: str
    age: int


async def test_default_response_when_no_match():
    p = StubProvider(default_response="hi-default")
    out = await p.complete(messages=[{"role": "user", "content": "anything"}], model="m")
    assert out.text == "hi-default"
    assert out.cost_usd == 0.0
    assert out.raw == {"stub": True}


async def test_response_keyed_by_fingerprint():
    messages = [{"role": "user", "content": "hello"}]
    fp = StubProvider.fingerprint(messages)
    p = StubProvider(responses={fp: "matched"})
    out = await p.complete(messages=messages, model="m")
    assert out.text == "matched"


async def test_pydantic_response_format_roundtrip():
    messages = [{"role": "user", "content": "who"}]
    fp = StubProvider.fingerprint(messages)
    p = StubProvider(responses={fp: {"name": "Ada", "age": 36}})
    out = await p.complete(messages=messages, model="m", response_format=_Person)
    assert isinstance(out.parsed, _Person)
    assert out.parsed.name == "Ada"
    assert out.parsed.age == 36
    # text is the JSON form of the parsed model
    assert _Person.model_validate_json(out.text) == out.parsed


async def test_calls_capture_history():
    p = StubProvider()
    await p.complete(messages=[{"role": "user", "content": "a"}], model="m1")
    await p.complete(messages=[{"role": "user", "content": "b"}], model="m2")
    assert len(p.calls) == 2
    assert p.calls[0]["model"] == "m1"
    assert p.calls[1]["model"] == "m2"
    assert p.calls[1]["messages"] == [{"role": "user", "content": "b"}]


def test_default_summarizer_shrinks_text():
    p = StubProvider()
    text = "x" * 1000
    out = p.summarizer(text, 10)
    # max(target*4, 16) = 40
    assert len(out) == 40
    out2 = p.summarizer(text, 1)
    assert len(out2) == 16
