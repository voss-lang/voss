"""J3-10 SC1/SC3: one fixed shortlist and responder give one order on every entry point and the tool."""
from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace

import httpx

from voss.harness import cli
from voss.harness.agent import _default_token_count
from voss.harness.code.semantic_index import Candidate
from voss.harness.memory_store import Hit
from voss.harness.server import app as appmod
from voss.harness.session import RunRecord
from voss.harness.tools import attach_code_recall_tool

from .conftest import make_candidates, score_body
from .test_rerank_entrypoints import FakeService, enable

TASK = "fix the retry backoff handling"
FAVORED = [8, 13, 1, 10, 5]
PATHS = ("do", "chat_tui", "chat_plain", "server")
SECTION_ANCHOR = re.compile(r"\n- (\S+) \(score ")
TOOL_ANCHOR = re.compile(r"^\[code\] (\S+) \(score ", re.M)


def _distinct_levels(favored=FAVORED, n=15):
    rank = favored + [i for i in range(n) if i not in favored]
    levels = {}
    for i in range(n):
        w = (n - rank.index(i)) / n
        levels[f"c{i + 1:02d}"] = {"0": 1 - w, "1": 0.0, "2": 0.0, "3": w}
    return levels


def _equal_levels():
    return {f"c{i:02d}": {"0": 0.25, "1": 0.25, "2": 0.25, "3": 0.25} for i in range(1, 16)}


def _run_every_path(tmp_path, monkeypatch, svc):
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    tools: dict = {}
    attach_code_recall_tool(tools, code_index_service=svc)
    tool = tools["code_recall"].descriptor
    outputs: list[tuple[str, str]] = []

    async def run_turn(task, *, code_recall_text=None, **kwargs):
        outputs.append((code_recall_text or "", await tool(query=TASK, top_k=5)))
        return SimpleNamespace(run=RunRecord(id="run", started_at="", ended_at=""), final="", confidence=1.0, cost_usd=0.0)

    def make_turn(recall):
        return cli._run_turn_with_teardown(run_turn(TASK, **recall), None)

    renderer = SimpleNamespace()
    cli._run_turn_cancellable(cli._scoped_turn(tmp_path, TASK, "do", run_turn, make_turn), renderer=renderer)
    asyncio.run(cli._scoped_turn(tmp_path, TASK, "tui", run_turn, make_turn, sidecar_root="chat-root"))
    cli._run_turn_cancellable(
        cli._scoped_turn(tmp_path, TASK, "plain", run_turn, make_turn, sidecar_root="chat-root"), renderer=renderer,
    )
    monkeypatch.setattr(appmod, "run_turn", run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    session = appmod.create_app("token").state.sessions.create(cwd=tmp_path, model="m", provider=object())
    asyncio.run(appmod._run_turn(session, TASK, "plan"))
    errors = []
    while not session.queue.empty():
        errors.append(getattr(session.queue.get_nowait(), "text", ""))
    assert len(outputs) == len(PATHS), [e for e in errors if "[error:" in e]
    return outputs


def _section_anchors(section):
    return SECTION_ANCHOR.findall(section)


def _tool_anchors(output):
    return TOOL_ANCHOR.findall(output)


def _anchor(hit):
    return f"{hit.locator.split(':')[1]}:{hit.line_start}"


def test_fixed_shortlist_gives_one_order_on_every_path_and_the_tool(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    pool = make_candidates(15)
    jev.handler = lambda request: httpx.Response(200, json=score_body(_distinct_levels()))
    outputs = _run_every_path(tmp_path, monkeypatch, FakeService(pool))
    expected_hits = [pool[i].hit for i in FAVORED]
    expected = cli._format_code_recall_section(expected_hits)
    sections = {section for section, _ in outputs}
    assert sections == {expected}
    assert _section_anchors(expected) == [_anchor(h) for h in expected_hits]
    for _, tool_output in outputs:
        assert _tool_anchors(tool_output) == _section_anchors(expected)
    assert len(jev.requests) == 2 * len(PATHS)


def test_equal_distributions_keep_the_pool_order_everywhere(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    pool = make_candidates(15)
    jev.handler = lambda request: httpx.Response(200, json=score_body(_equal_levels()))
    outputs = _run_every_path(tmp_path, monkeypatch, FakeService(pool))
    expected = cli._format_code_recall_section([c.hit for c in pool[:5]])
    assert {section for section, _ in outputs} == {expected}
    for _, tool_output in outputs:
        assert _tool_anchors(tool_output) == [f"pkg/m{i}.py:1" for i in range(5)]


def _long_candidates():
    out = []
    for i in range(6):
        path = "/".join(f"segment_{i}_{n:03d}" for n in range(80)) + f"/m{i}.py"
        text = f"def f{i}():\n" + "    value = compute_something_long(alpha, beta, gamma)\n" * 80
        hit = Hit(source="code", locator=f"code:{path}:000", score=1.0 / (i + 1), excerpt=text[:160], line_start=1, line_end=81)
        out.append(Candidate(hit=hit, path=path, line_start=1, line_end=81, text=text, fresh=True))
    return out


def test_token_cap_holds_after_reordering_on_every_injection_path(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    pool = _long_candidates()
    favored = [5, 2, 4, 0, 3, 1]
    jev.handler = lambda request: httpx.Response(200, json=score_body(_distinct_levels(favored, len(pool))))
    outputs = _run_every_path(tmp_path, monkeypatch, FakeService(pool))
    model = cli.get_config().default_model
    [section] = {section for section, _ in outputs}
    entries = _section_anchors(section)
    assert 0 < len(entries) < 5
    assert entries == [_anchor(pool[i].hit) for i in favored[: len(entries)]]
    assert _default_token_count(section, model=model) <= cli._CODE_RECALL_TOKEN_CAP


def test_kill_switch_restores_the_legacy_output_with_zero_calls(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    svc = FakeService(make_candidates(15))
    outputs = _run_every_path(tmp_path, monkeypatch, svc)
    expected = cli._render_code_recall_text(tmp_path, TASK)
    assert expected == cli._format_code_recall_section(svc.legacy[:5])
    assert {section for section, _ in outputs} == {expected}
    for _, tool_output in outputs:
        assert _tool_anchors(tool_output) == [_anchor(h) for h in svc.legacy[:5]]
    assert jev.requests == [] and svc.candidate_calls == 0
