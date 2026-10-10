"""J3-07 S3.3/D-04/D-12/D-20: pre-turn code recall through _scoped_turn on do and chat."""
from __future__ import annotations

import ast
import asyncio
import inspect
import re
import textwrap
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import mock

import httpx
import pytest

from voss.harness import cli
from voss.harness.agent import _default_token_count
from voss.harness.memory_store import Hit
from voss.harness.session import RunRecord

from .conftest import make_candidates, score_body

TASK = "where is retry backoff handled"
FAVOR_C07 = {f"c{i:02d}": 3 if i == 7 else 0 for i in range(1, 16)}
LINE = re.compile(r"\n- \S+ \(score \d+\.\d\d\)\n  [^\n]*")


class FakeService:
    def __init__(self, pool, *, ready=True):
        self.pool = pool
        self.ready = ready
        self.legacy = [
            Hit(source="code", locator=f"code:legacy/l{i}.py:000", score=0.9 - i / 10, excerpt=f"def legacy_{i}():\n    return {i}", line_start=i + 3)
            for i in range(10)
        ]
        self.candidate_calls = 0

    def is_ready(self):
        return self.ready

    def candidates(self, query):
        self.candidate_calls += 1
        return self.pool

    def query(self, query, top_k=5):
        return self.legacy[:top_k]


def enable(root, mode):
    path = root / ".voss" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"judgments:\n  enabled: true\n  code_recall: {mode}\n")


def fake_run_turn(during=None):
    calls: list[dict] = []

    async def run_turn(task, *, code_recall_text=None, **kwargs):
        calls.append({"code_recall_text": code_recall_text})
        if during is not None:
            await during()
        return SimpleNamespace(run=RunRecord(id="run", started_at="", ended_at=""), final="", confidence=1.0, cost_usd=0.0)

    return run_turn, calls


def _use(monkeypatch, svc):
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)


async def _turn(tmp_path, run_turn, **kw):
    recorded = []

    def make_turn(recall):
        recorded.append(recall)
        return run_turn(TASK, **recall)

    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, make_turn, **kw)
    return result, recorded[0]


def test_format_reproduces_legacy_section_byte_for_byte(tmp_path, monkeypatch):
    svc = FakeService([])
    _use(monkeypatch, svc)
    hits = svc.legacy[:5]
    expected = "## Code Recall\nTask-relevant code (semantic index):" + "".join(
        f"\n- legacy/l{i}.py:{i + 3} (score {0.9 - i / 10:.2f})\n  def legacy_{i}():     return {i}" for i in range(5)
    )
    assert cli._format_code_recall_section(hits) == expected
    assert cli._render_code_recall_text(tmp_path, TASK) == expected


def test_format_stops_before_the_token_cap():
    words = " ".join(f"token{i}" for i in range(40))
    hits = [Hit(source="code", locator=f"code:pkg/f{i}.py:000", score=0.5, excerpt=words, line_start=1) for i in range(60)]
    section = cli._format_code_recall_section(hits)
    entries = section.count("\n- ")
    assert 0 < entries < 60
    model = cli.get_config().default_model
    assert _default_token_count(section, model=model) <= cli._CODE_RECALL_TOKEN_CAP
    assert cli._format_code_recall_section(hits[: entries + 1]) == section


@pytest.mark.parametrize("setup", ["disabled", "killed", "no_key"])
async def test_off_is_byte_identical_and_makes_no_calls(jev, tmp_path, monkeypatch, setup):
    from voss.harness import judgments

    svc = FakeService(make_candidates(15))
    _use(monkeypatch, svc)
    if setup != "disabled":
        enable(tmp_path, "active")
    if setup == "killed":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    if setup == "no_key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
        monkeypatch.setattr(judgments.auth, "load_provider_key", lambda key: None)
    run_turn, _ = fake_run_turn()
    returned = SimpleNamespace(run=None)

    async def turn(**recall):
        return returned

    recorded = []

    def make_turn(recall):
        recorded.append(recall)
        return turn(**recall)

    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, make_turn)
    assert result is returned
    assert recorded == [{"code_recall_text": cli._render_code_recall_text(tmp_path, TASK)}]
    assert recorded[0] == cli._code_recall_kwargs(run_turn, tmp_path, TASK)
    assert jev.requests == [] and svc.candidate_calls == 0


async def test_off_with_empty_section_passes_no_kwargs(jev, tmp_path, monkeypatch):
    _use(monkeypatch, FakeService(make_candidates(15), ready=False))
    run_turn, calls = fake_run_turn()
    _, recall = await _turn(tmp_path, run_turn)
    assert recall == {} and calls == [{"code_recall_text": None}]


async def test_active_injects_reranked_pool_in_legacy_format(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    pool = make_candidates(15)
    _use(monkeypatch, FakeService(pool))
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))
    run_turn, _ = fake_run_turn()
    _, recall = await _turn(tmp_path, run_turn)
    text = recall["code_recall_text"]
    assert text == cli._format_code_recall_section([pool[i].hit for i in (6, 0, 1, 2, 3)])
    assert text.split("\n")[2].startswith("- pkg/m6.py:1 (score ")
    assert len(LINE.findall(text)) == text.count("\n- ") <= 5
    assert len(jev.requests) == 1


async def test_shadow_injects_legacy_section_without_waiting(jev, tmp_path, monkeypatch):
    enable(tmp_path, "shadow")
    svc = FakeService(make_candidates(15))
    _use(monkeypatch, svc)
    gate = asyncio.Event()

    async def blocked(request):
        await gate.wait()
        return httpx.Response(200, json=score_body(FAVOR_C07))

    jev.handler = blocked
    run_turn, _ = fake_run_turn()
    result, recall = await asyncio.wait_for(_turn(tmp_path, run_turn), timeout=1.0)
    assert recall == {"code_recall_text": cli._format_code_recall_section(svc.legacy[:5])}
    [receipt] = result.run.judgment_receipts
    assert receipt["mode"] == "shadow" and receipt["status"] in ("answered", "cancelled")


async def test_not_ready_index_injects_nothing_and_calls_nothing(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15), ready=False)
    _use(monkeypatch, svc)
    run_turn, _ = fake_run_turn()
    result, recall = await _turn(tmp_path, run_turn)
    assert recall == {}
    assert jev.requests == [] and svc.candidate_calls == 0
    assert result.run.judgment_receipts == []


async def test_degraded_candidates_fall_back_to_legacy_section(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(None)
    _use(monkeypatch, svc)
    run_turn, _ = fake_run_turn()
    _, recall = await _turn(tmp_path, run_turn)
    assert recall == {"code_recall_text": cli._format_code_recall_section(svc.legacy[:5])}
    assert jev.requests == []


async def test_active_fallback_injects_legacy_section(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    _use(monkeypatch, svc)
    jev.handler = lambda request: httpx.Response(500)
    run_turn, _ = fake_run_turn()
    _, recall = await _turn(tmp_path, run_turn)
    assert recall == {"code_recall_text": cli._format_code_recall_section(svc.legacy[:5])}


def _scoped_calls(fn):
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_scoped_turn"]
    cancellable = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_run_turn_cancellable"
        and n.args and isinstance(n.args[0], ast.Call) and getattr(n.args[0].func, "id", None) == "_scoped_turn"
    ]
    awaited = [n for n in ast.walk(tree) if isinstance(n, ast.Await) and n.value in calls]
    return tree, calls, cancellable, awaited


def _sidecar_root(call):
    return next((ast.unparse(k.value) for k in call.keywords if k.arg == "sidecar_root"), None)


def test_do_routes_through_scoped_turn_without_sidecar():
    tree, calls, cancellable, _ = _scoped_calls(cli.do_cmd.callback)
    assert len(calls) == 1 and [c.args[0] for c in cancellable] == calls
    assert _sidecar_root(calls[0]) is None
    assert "_code_recall_kwargs" not in ast.unparse(tree)


def test_chat_tui_and_plain_route_through_scoped_turn_with_chat_root_sidecar():
    tree, calls, cancellable, awaited = _scoped_calls(cli._run_repl)
    assert len(calls) == 2 and len(cancellable) == 1 and len(awaited) == 1
    assert [_sidecar_root(c) for c in calls] == ["_chat_root.id", "_chat_root.id"]
    for call in calls:
        make_turn = call.args[4]
        assert isinstance(make_turn, ast.Lambda)
        assert not any(isinstance(n, ast.Await) for n in ast.walk(make_turn))
        assert getattr(make_turn.body.func, "id", None) == "_run_turn_with_teardown"
    assert "_code_recall_kwargs" not in ast.unparse(tree)


def test_do_off_sends_byte_identical_code_recall_text(jev, tmp_path, monkeypatch):
    svc = FakeService(make_candidates(15))
    _use(monkeypatch, svc)
    captured = []

    async def run_turn(task, *, code_recall_text=None, **kwargs):
        captured.append(code_recall_text)
        return SimpleNamespace(final="done", confidence=1.0, cost_usd=0.0, run=None)

    class Renderer:
        def banner(self, **_kwargs):
            return None

        def show_user(self, _text):
            return None

        def show_final(self, *_args, **_kwargs):
            return None

    async def no_mcp(tools, cwd):
        return None

    auth = SimpleNamespace(source="stub", detail="ok")
    bundle = SimpleNamespace(initialized=False, permissions=None, safety=None, load_errors=[])
    with ExitStack() as stack:
        patch = lambda name, **kw: stack.enter_context(mock.patch.object(cli, name, **kw))
        patch("_resolve_default_model")
        patch("_resolve_auth_or_die", return_value=(auth, object()))
        patch("_apply_boot_model", side_effect=lambda provider, user_explicit=None, auth_source=None: provider)
        patch("_emit_harness_boot_telemetry")
        patch("make_renderer", return_value=Renderer())
        patch("make_toolset", return_value={})
        patch("_get_net_session", return_value=None)
        patch("_render_project_index_text", return_value="")
        patch("PermissionGate", return_value=object())
        patch("_wire_tui_permissions_if_textual")
        patch("attach_subagent_tool")
        patch("default_subagent_registry", return_value=object())
        patch("_git_status", return_value="clean")
        patch("_resolve_run_turn", return_value=run_turn)
        patch("make_global_store", return_value=object(), create=True)
        patch("attach_memory_tools")
        stack.enter_context(mock.patch.object(cli.voss_md, "ensure_migrated"))
        stack.enter_context(mock.patch.object(cli.voss_md, "read_and_inject", return_value=""))
        stack.enter_context(mock.patch.object(cli.cognition_mod, "load", return_value=bundle))
        stack.enter_context(mock.patch.object(cli.PermissionStore, "load", return_value=object()))
        stack.enter_context(mock.patch.object(cli.session_store.SessionRecord, "new", return_value=SimpleNamespace(id="sess-1", runs=[])))
        stack.enter_context(mock.patch.object(cli.conventions, "run_on_clean_exit"))
        stack.enter_context(mock.patch.object(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True)))
        stack.enter_context(mock.patch("voss.harness.tools.attach_mcp_tools", no_mcp))
        cli.do_cmd.callback(
            task=(TASK,), model=None, cwd_str=str(tmp_path), json_mode=False, plain=True, no_unicode=False,
            mode="plan", yes_to_all=False, allow_net=None, auth_pref="auto", no_pack=False,
        )
        expected = cli._render_code_recall_text(tmp_path, TASK)
    assert expected and captured == [expected]
    assert jev.requests == [] and svc.candidate_calls == 0
