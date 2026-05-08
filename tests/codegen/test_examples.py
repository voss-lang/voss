from __future__ import annotations

import ast
import asyncio
import importlib
import json
import sys
from pathlib import Path

import pytest

from voss import analyze, generate_python, parse

from tests.codegen.helpers import (
    assert_allowed_imports,
    fake_analysis,
    load_module_from_path,
    load_module_with_globals,
    write_generated_module,
)


EXAMPLES = Path(__file__).resolve().parents[1] / "parser" / "examples"


class FakeIndexBuilder:
    model = "fake-embedding-model"

    def build_cases(self, cases):
        embeddings = (
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        )
        return [
            {
                "label": label,
                "description": description,
                "embedding": embeddings[i],
            }
            for i, (description, label) in enumerate(cases)
        ]


class _FakeMatrix:
    def __init__(self, rows):
        self.rows = [list(row) for row in rows]

    def __getitem__(self, index):
        return self.rows[index]

    def __matmul__(self, vector):
        return [
            sum(left * right for left, right in zip(row, vector))
            for row in self.rows
        ]


class _FakeNumpy:
    float32 = "float32"

    @staticmethod
    def asarray(rows, dtype=None):
        return _FakeMatrix(rows)


def _read_example(name: str) -> str:
    path = EXAMPLES / name
    assert path.exists(), (
        f"missing parser example {path}; Phase 4 contract gate was bypassed"
    )
    return path.read_text()


def _compile_example(tmp_path: Path, name: str, *, analysis=None):
    source = _read_example(f"{name}.voss")
    program = parse(source, file=f"{name}.voss")
    if analysis is None:
        analysis = analyze(
            program,
            source_path=f"{name}.voss",
            project_root=tmp_path,
            cache_dir=".voss-cache",
            emit_indexes=False,
            index_builder=FakeIndexBuilder(),
        )
    return generate_python(
        program,
        source_path=f"{name}.voss",
        analysis=analysis,
        cache_dir=tmp_path / ".voss-cache",
        project_root=tmp_path,
    )


def _load_generated(tmp_path: Path, name: str, source: str):
    path = write_generated_module(tmp_path, name, source)
    return load_module_from_path(path, f"generated_{name}")


def _configure_stub(default_response: str):
    import voss_runtime
    from voss_runtime import configure
    from voss_runtime.providers.stub import StubProvider

    stub = StubProvider(default_response=default_response)
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    return stub


def _stub_encode(self, texts):
    out = []
    for text in texts:
        lower = text.lower()
        if any(w in lower for w in ("angry", "furious", "frustrat", "upset")):
            out.append([1.0, 0.0, 0.0])
        elif any(w in lower for w in ("refund", "money", "cancel")):
            out.append([0.0, 1.0, 0.0])
        elif any(w in lower for w in ("log in", "password", "locked", "auth")):
            out.append([0.0, 0.0, 1.0])
        else:
            out.append([0.1, 0.1, 0.1])
    return _FakeMatrix(out)


def _write_support_manifest(tmp_path: Path) -> Path:
    cache = tmp_path / ".voss-cache"
    cache.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 1,
        "program": "support",
        "model": "fake-embedding-model",
        "matches": [
            {
                "match_id": "match_7_5",
                "threshold": 0.55,
                "cases": [
                    {
                        "label": "escalate",
                        "description": "angry, frustrated, or upset customer",
                        "embedding": [1.0, 0.0, 0.0],
                    },
                    {
                        "label": "refund",
                        "description": "refund, money back, cancel subscription",
                        "embedding": [0.0, 1.0, 0.0],
                    },
                    {
                        "label": "auth",
                        "description": "can't log in, password reset, account locked",
                        "embedding": [0.0, 0.0, 1.0],
                    },
                ],
            }
        ],
    }
    path = cache / "support.idx"
    path.write_text(json.dumps(manifest))
    return path


def _load_raw_support_with_stubbed_encoder(monkeypatch):
    import voss_runtime.semantic as semantic_module
    from voss_runtime.semantic import SemanticMatcher

    monkeypatch.setattr(SemanticMatcher, "_encode", _stub_encode)
    monkeypatch.setattr(semantic_module, "_numpy", lambda: _FakeNumpy)
    sys.modules.pop("examples.raw_python.support", None)
    return importlib.import_module("examples.raw_python.support")


def _install_support_helpers(module):
    def escalate(msg: str) -> str:
        return f"[escalated] {msg}"

    def refund_flow(msg: str) -> str:
        return f"[refund flow] {msg}"

    def auth_support(msg: str) -> str:
        return f"[auth support] {msg}"

    module.escalate = escalate
    module.refundFlow = refund_flow
    module.authSupport = auth_support


@pytest.mark.asyncio
async def test_classify_example_compiles_and_matches_raw_python(tmp_path):
    from examples.raw_python.classify import classify_intent
    from voss_runtime import reset_config

    result = _compile_example(tmp_path, "classify")
    ast.parse(result.source)
    module = _load_generated(tmp_path, "classify", result.source)

    _configure_stub("cancel_subscription")
    try:
        generated = await module.classifyIntent("I want to cancel my subscription")
        raw = await classify_intent("I want to cancel my subscription")
    finally:
        reset_config()

    assert generated == "cancel_subscription"
    assert generated == raw


@pytest.mark.asyncio
async def test_classify_low_confidence_matches_raw_python(tmp_path):
    from examples.raw_python.classify import classify_intent
    from voss_runtime import reset_config

    result = _compile_example(tmp_path, "classify")
    module = _load_generated(tmp_path, "classify_low_confidence", result.source)

    _configure_stub("")
    try:
        generated = await module.classifyIntent("I want to cancel my subscription")
        raw = await classify_intent("I want to cancel my subscription")
    finally:
        reset_config()

    assert generated == "unknown"
    assert generated == raw


@pytest.mark.asyncio
async def test_support_example_compiles_and_routes_with_fake_manifest(
    tmp_path, monkeypatch
):
    import voss_runtime.semantic as semantic_module
    from voss_runtime import reset_config
    from voss_runtime.semantic import SemanticMatcher

    manifest_path = _write_support_manifest(tmp_path)
    result = _compile_example(
        tmp_path, "support", analysis=fake_analysis(manifest_path)
    )
    ast.parse(result.source)
    monkeypatch.setattr(SemanticMatcher, "_encode", _stub_encode)
    monkeypatch.setattr(semantic_module, "_numpy", lambda: _FakeNumpy)
    module = _load_generated(tmp_path, "support", result.source)
    _install_support_helpers(module)
    raw_support = _load_raw_support_with_stubbed_encoder(monkeypatch)

    _configure_stub("Pricing info here")
    try:
        cases = (
            "I'm so angry, fix it",
            "Can I get a refund?",
            "I can't log in",
        )
        for message in cases:
            assert await module.handleMessage(message) == await raw_support.handle_message(
                message
            )
        generic = "What pricing tiers do you have?"
        assert await module.handleMessage(generic) == "Pricing info here"
    finally:
        reset_config()


@pytest.mark.asyncio
async def test_research_example_compiles_and_matches_raw_python_happy_path(tmp_path):
    from examples.raw_python import research as raw_research
    from voss_runtime import reset_config

    result = _compile_example(tmp_path, "research")
    ast.parse(result.source)
    path = write_generated_module(tmp_path, "research", result.source)
    module = load_module_with_globals(
        path, "generated_research", {"webSearch": raw_research.web_search}
    )

    _configure_stub("STUB SUMMARY")
    try:
        generated = await module.runResearch("Anthropic")
        raw = await raw_research.run_research("Anthropic")
    finally:
        reset_config()

    assert isinstance(generated, str)
    assert generated
    assert isinstance(raw, str)
    assert raw


@pytest.mark.asyncio
async def test_research_example_timeout_fallback_matches_raw_python(
    tmp_path, monkeypatch
):
    from examples.raw_python import research as raw_research
    from voss_runtime import reset_config
    from voss_runtime.budget import run_with_budget as orig_run_with_budget

    result = _compile_example(tmp_path, "research")
    path = write_generated_module(tmp_path, "research_timeout", result.source)
    module = load_module_with_globals(
        path,
        "generated_research_timeout",
        {"webSearch": raw_research.web_search},
    )

    async def slow_run(self, reports):
        await asyncio.sleep(1)
        return "should not appear"

    def short_budget(coro, **kwargs):
        return orig_run_with_budget(
            coro, token_limit=kwargs.get("token_limit"), latency_ms=50
        )

    monkeypatch.setattr(module.Synthesizer, "run", slow_run)
    monkeypatch.setattr(module, "run_with_budget", short_budget)

    _configure_stub("STUB SUMMARY")
    try:
        result_value = await module.runResearch("Anthropic")
    finally:
        reset_config()

    assert result_value == "\n---\n".join(["STUB SUMMARY"] * 4)


def test_generated_examples_have_allowed_imports_only(tmp_path):
    support_manifest = _write_support_manifest(tmp_path)
    generated = (
        _compile_example(tmp_path, "classify").source,
        _compile_example(
            tmp_path, "support", analysis=fake_analysis(support_manifest)
        ).source,
        _compile_example(tmp_path, "research").source,
    )

    for source in generated:
        assert_allowed_imports(source)
