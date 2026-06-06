"""Tier 2 #4 (schema-return half): the `task` tool returns schema-validated
JSON from a subagent, reusing the smol pick + run_subagent path."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from voss.harness import roles, subagents
from voss.harness.subagents import attach_subagent_tool, validate_subagent_json

_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "score": {"type": "integer"}},
    "required": ["answer", "score"],
    "additionalProperties": False,
}


def _attach(monkeypatch, tools: dict, final: str) -> dict:
    captured: dict = {}

    async def fake_run_subagent(**kw):
        captured["task"] = kw["task"]
        captured["provider"] = kw["provider"]
        return final

    monkeypatch.setattr(subagents, "run_subagent", fake_run_subagent)
    attach_subagent_tool(
        tools,
        registry=object(),
        cwd=Path("."),
        renderer=object(),
        provider="parent",
        model=lambda: "default-model",
        gate=object(),
        cognition=None,
    )
    return captured


# ---- validate_subagent_json (pure) ----------------------------------------


class TestValidate:
    def test_valid_returns_canonical(self) -> None:
        out = validate_subagent_json('{"answer": "hi", "score": 3}', _SCHEMA)
        assert json.loads(out) == {"answer": "hi", "score": 3}

    def test_fenced_json_extracted(self) -> None:
        out = validate_subagent_json('```json\n{"answer":"x","score":1}\n```', _SCHEMA)
        assert json.loads(out) == {"answer": "x", "score": 1}

    def test_non_json_errors(self) -> None:
        out = validate_subagent_json("not json at all", _SCHEMA)
        assert "did not return valid JSON" in out

    def test_schema_violation_errors(self) -> None:
        out = validate_subagent_json('{"answer": "x"}', _SCHEMA)  # missing score
        assert "schema validation failed" in out

    def test_malformed_schema_errors(self) -> None:
        out = validate_subagent_json('{"a": 1}', {"type": "not-a-type"})
        assert "invalid schema" in out


# ---- task tool (wiring) ----------------------------------------------------


class TestTaskTool:
    def test_schema_validated_return(self, monkeypatch) -> None:
        monkeypatch.setattr(roles, "build_role_provider", lambda role, **kw: None)
        tools: dict = {}
        cap = _attach(monkeypatch, tools, final='{"answer": "ok", "score": 9}')
        out = asyncio.run(tools["task"].invoke(agent="x", task="do it", schema=_SCHEMA))
        assert json.loads(out) == {"answer": "ok", "score": 9}
        # schema instruction injected into the subagent prompt
        assert "JSON Schema" in cap["task"]

    def test_no_schema_returns_raw(self, monkeypatch) -> None:
        monkeypatch.setattr(roles, "build_role_provider", lambda role, **kw: None)
        tools: dict = {}
        _attach(monkeypatch, tools, final="free-form answer")
        out = asyncio.run(tools["task"].invoke(agent="x", task="do it"))
        assert out == "free-form answer"

    def test_task_uses_smol_when_configured(self, monkeypatch) -> None:
        monkeypatch.setattr(
            roles,
            "build_role_provider",
            lambda role, **kw: ("smol-provider", "smol-model") if role == "smol" else None,
        )
        tools: dict = {}
        cap = _attach(monkeypatch, tools, final='{"answer": "a", "score": 1}')
        asyncio.run(tools["task"].invoke(agent="x", task="t", schema=_SCHEMA))
        assert cap["provider"] == "smol-provider"

    def test_registered_as_mutating(self, monkeypatch) -> None:
        monkeypatch.setattr(roles, "build_role_provider", lambda role, **kw: None)
        tools: dict = {}
        _attach(monkeypatch, tools, final="x")
        assert tools["task"].is_mutating is True
