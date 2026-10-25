from __future__ import annotations

import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import logging
from pathlib import Path
import subprocess
import threading
import time

import httpx
import pytest

from tests.harness.review_fakes import choice_body, install_jev
from tests.harness.test_swarm_runtime import _FakeHandle, _git, _spawn_with_result, _write_result
from voss.harness import conventions, decision_review, judgments, swarm_review
from voss.harness.swarm.events import SwarmEventLog
from voss.harness.swarm_runtime import run_cli_member, run_cli_swarm
from voss.harness.swarm_store import CANDIDATE_READY, Role, SwarmStore

SHADOW = "judgments:\n  enabled: true\n  review: shadow\n"
OFF = "judgments:\n  enabled: true\n  review: off\n"
NOT_ENABLED = "judgments:\n  enabled: false\n  review: shadow\n"
GOAL = "owned.py says changed by builder"
ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_KEYS = (
    "swarm_id", "task_id", "attempt_id", "base_revision", "repository", "head", "branch", "worktree", "candidate_head", "candidate_branch", "candidate_worktree",
)


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(judgments.auth, "load_provider_key", lambda env_key: None)
    swarm_review.PENDING.clear()
    yield
    swarm_review.PENDING.clear()


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=choice_body(request))


def _repo(root: Path, config_text: str | None = SHADOW) -> Path:
    root.mkdir()
    _git(["init", "-q"], root)
    _git(["config", "user.email", "test@test"], root)
    _git(["config", "user.name", "test"], root)
    (root / "base.txt").write_text("base\n")
    (root / "owned.py").write_text("# original\n")
    (root / "other.py").write_text("# untouched\n")
    _git(["add", "-A"], root)
    _git(["commit", "-q", "-m", "init"], root)
    if config_text is not None:
        (root / ".voss").mkdir()
        (root / ".voss" / "config.yml").write_text(config_text)
    return root


def _out(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True).stdout.strip()


def _member(repo: Path, edits: dict[str, str], goal: str = GOAL):
    store = SwarmStore(cwd=repo)
    swarm = store.create("ship it", cwd=str(repo), roster=[Role(name="builder-1", agent="codex")])
    task = store.add_task(swarm.id, goal, owned_files=["owned.py"])
    spawn = _spawn_with_result(repo, edits, swarm.id, "builder-1", "done")
    return store, swarm.id, swarm.roster[0], task, spawn


def _run(store, repo, swarm_id, role, task, spawn, *, events=None, after=None, gather=True):
    async def go():
        result = await run_cli_member(
            store, repo, swarm_id, role, task, spawn_fn=spawn, on_event=None if events is None else events.append
        )
        if after is not None:
            after()
        if gather:
            await asyncio.gather(*list(swarm_review.PENDING))
        return result

    return asyncio.run(go())


def _review(repo: Path, swarm_id: str, task_id: str) -> dict:
    return json.loads(decision_review.candidate_review_path(repo, swarm_id, task_id).read_text())


def _reviews_dir(repo: Path, swarm_id: str) -> Path:
    return repo / ".voss" / "swarm" / swarm_id / "reviews"


def test_shadow_assesses_candidate_commit_once(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed by builder\n"})

    result = _run(store, repo, swarm_id, role, task, spawn)

    assert len(seen) == 1
    state = json.loads(seen[0].content)["state"]
    assert state["criteria"] == [{"id": "AC-1", "text": GOAL}]
    assert state["checks"] == [{"name": "scope", "status": "passed"}]
    assert "owned.py" in state["diff"]
    review = _review(repo, swarm_id, task.id)
    assert len(review["receipts"]) == 1
    receipt = review["receipts"][0]
    assert receipt["purpose"] == "review.requirements"
    assert receipt["mode"] == "shadow"
    assert receipt["status"] == "answered"
    assert receipt["detail"]["candidate"] == {
        "kind": "commit", "head": result.candidate_head, "touched_paths": ["owned.py"],
    }
    assert review["judgments_cost_usd"] == receipt["cost_usd"]


def test_ownership_violation_fails_scope_check_and_keeps_candidate(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# legit\n", "other.py": "# OUT OF SCOPE\n"})

    result = _run(store, repo, swarm_id, role, task, spawn)

    assert result.violations == ["other.py"]
    assert json.loads(seen[0].content)["state"]["checks"] == [{"name": "scope", "status": "failed"}]
    assert _out(["show", f"{result.candidate_head}:other.py"], repo) == "# untouched"
    assert _out(["show", f"{result.candidate_head}:owned.py"], repo) == "# legit"


def test_review_runs_after_candidate_is_recorded_and_emitted(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    events: list[dict] = []
    observed: list[tuple] = []

    def handler(request):
        observed.append((
            SwarmStore(cwd=repo).replay(swarm_id).task(task.id).state,
            any(e["type"] == "swarm.candidate_ready" and e["task_id"] == task.id for e in list(events)),
        ))
        return _ok(request)

    install_jev(monkeypatch, handler)
    _run(store, repo, swarm_id, role, task, spawn, events=events)

    assert observed == [(CANDIDATE_READY, True)]


def test_swarm_with_two_candidates_writes_two_reviews(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store = SwarmStore(cwd=repo)
    swarm = store.create(
        "mixed", cwd=str(repo), roster=[Role(name="builder-1", agent="codex"), Role(name="builder-2", agent="codex")]
    )
    ta = store.add_task(swarm.id, "A", owned_files=["owned.py"])
    tb = store.add_task(swarm.id, "B", owned_files=["other.py"])

    def spawn(argv, cwd):
        (cwd / ("owned.py" if cwd.name == "builder-1" else "other.py")).write_text(f"# by {cwd.name}\n")
        _write_result(repo, swarm.id, cwd.name, f"{cwd.name} done")
        return _FakeHandle(0)

    async def go():
        await run_cli_swarm(store, repo, swarm.id, spawn_fn=spawn)
        await asyncio.gather(*list(swarm_review.PENDING))

    asyncio.run(go())

    assert len(seen) == 2
    assert sorted(p.name for p in _reviews_dir(repo, swarm.id).iterdir()) == sorted([f"{ta.id}.json", f"{tb.id}.json"])
    for t in (ta, tb):
        assert len(_review(repo, swarm.id, t.id)["receipts"]) == 1


def test_member_without_candidate_is_not_reviewed(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {})

    result = _run(store, repo, swarm_id, role, task, spawn)

    assert result.candidate_ready is False
    assert seen == []
    assert not _reviews_dir(repo, swarm_id).exists()


def test_already_candidate_ready_task_is_not_reviewed_again(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    _run(store, repo, swarm_id, role, task, spawn)
    path = decision_review.candidate_review_path(repo, swarm_id, task.id)
    before = path.read_text()

    _run(store, repo, swarm_id, role, task, spawn)

    assert len(seen) == 1
    assert path.read_text() == before


@pytest.mark.parametrize("case", ["review_off", "not_enabled", "killed"])
def test_zero_calls_and_nothing_scheduled_when_off(tmp_path, monkeypatch, case):
    seen = install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj", {"review_off": OFF, "not_enabled": NOT_ENABLED, "killed": SHADOW}[case])
    if case == "killed":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    scheduled: list[int] = []

    result = _run(store, repo, swarm_id, role, task, spawn, after=lambda: scheduled.append(len(swarm_review.PENDING)))

    assert result.candidate_ready is True
    assert scheduled == [0]
    assert seen == []
    assert not _reviews_dir(repo, swarm_id).exists()


def test_no_key_is_checked_only_in_the_worker_thread(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    monkeypatch.delenv("TYPESAFE_API_KEY")
    keychain_threads: list[threading.Thread] = []

    def lookup(env_key):
        keychain_threads.append(threading.current_thread())
        return None

    monkeypatch.setattr(judgments.auth, "load_provider_key", lookup)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    at_schedule: list[tuple] = []

    _run(
        store, repo, swarm_id, role, task, spawn,
        after=lambda: at_schedule.append((len(swarm_review.PENDING), threading.current_thread())),
    )

    assert at_schedule[0][0] == 1
    loop_thread = at_schedule[0][1]
    assert keychain_threads
    assert loop_thread not in keychain_threads
    assert seen == []
    assert not _reviews_dir(repo, swarm_id).exists()


def _hold(monkeypatch, gate: threading.Event, result=None):
    real = judgments.review_mode

    def held(cwd):
        gate.wait(5)
        return real(cwd) if result is None else result

    monkeypatch.setattr(judgments, "review_mode", held)


def test_kill_switch_set_after_scheduling_makes_zero_calls(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    gate = threading.Event()
    _hold(monkeypatch, gate)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    scheduled: list[int] = []

    def kill():
        scheduled.append(len(swarm_review.PENDING))
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
        gate.set()

    _run(store, repo, swarm_id, role, task, spawn, after=kill)

    assert scheduled == [1]
    assert seen == []
    assert not _reviews_dir(repo, swarm_id).exists()


def test_kill_switch_inside_assess_records_disabled_receipt(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, _ok)
    gate = threading.Event()
    _hold(monkeypatch, gate, result="shadow")
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})

    def kill():
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
        gate.set()

    _run(store, repo, swarm_id, role, task, spawn, after=kill)

    assert seen == []
    receipts = _review(repo, swarm_id, task.id)["receipts"]
    assert len(receipts) == 1
    assert receipts[0]["status"] == "disabled"
    assert receipts[0]["fallback_reason"] == "disabled"


def test_jev_http_error_becomes_receipt_and_member_result_is_unchanged(tmp_path, monkeypatch):
    seen = install_jev(monkeypatch, lambda request: httpx.Response(500))
    results = {}
    for name, text in (("off", OFF), ("shadow", SHADOW)):
        repo = _repo(tmp_path / name, text)
        store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
        results[name] = _normalize([asdict(_run(store, repo, swarm_id, role, task, spawn))])
        if name == "shadow":
            receipt = _review(repo, swarm_id, task.id)["receipts"][0]

    assert results["off"] == results["shadow"]
    assert len(seen) == 1
    assert receipt["status"] == "unavailable"
    assert receipt["fallback_reason"] == "unavailable"


def test_invalid_jev_body_becomes_receipt(tmp_path, monkeypatch):
    install_jev(monkeypatch, lambda request: httpx.Response(200, json={"bogus": True}))
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})

    result = _run(store, repo, swarm_id, role, task, spawn)

    assert result.candidate_ready is True
    assert _review(repo, swarm_id, task.id)["receipts"][0]["status"] == "invalid_response"


def test_jev_timeout_becomes_receipt(tmp_path, monkeypatch):
    async def slow(request):
        await asyncio.sleep(2)
        return _ok(request)

    install_jev(monkeypatch, slow, timeout_ms=50)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})

    _run(store, repo, swarm_id, role, task, spawn)

    assert _review(repo, swarm_id, task.id)["receipts"][0]["fallback_reason"] == "timeout"


def test_slow_jev_does_not_delay_the_member(tmp_path, monkeypatch):
    async def slow(request):
        await asyncio.sleep(1.5)
        return _ok(request)

    install_jev(monkeypatch, slow)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    timing: dict = {}

    async def go():
        start = time.monotonic()
        await run_cli_member(store, repo, swarm_id, role, task, spawn_fn=spawn)
        timing["member"] = time.monotonic() - start
        timing["pending"] = len(swarm_review.PENDING)
        await asyncio.gather(*list(swarm_review.PENDING))

    asyncio.run(go())

    assert timing["member"] < 1
    assert timing["pending"] == 1
    assert _review(repo, swarm_id, task.id)["receipts"][0]["status"] == "answered"


def test_collection_error_only_warns(tmp_path, monkeypatch, caplog):
    seen = install_jev(monkeypatch, _ok)

    def boom(repo, ref):
        raise ValueError("secret detail")

    monkeypatch.setattr(decision_review, "collect_commit", boom)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})

    with caplog.at_level(logging.WARNING, logger="voss.harness.swarm_review"):
        result = _run(store, repo, swarm_id, role, task, spawn)

    assert result.candidate_ready is True
    warnings = [r.getMessage() for r in caplog.records if r.name == "voss.harness.swarm_review"]
    assert len(warnings) == 1
    assert task.id in warnings[0] and "ValueError" in warnings[0]
    assert GOAL not in warnings[0] and "secret detail" not in warnings[0]
    assert seen == []
    assert not _reviews_dir(repo, swarm_id).exists()


def test_gate_error_only_warns_and_schedules_nothing(tmp_path, monkeypatch, caplog):
    seen = install_jev(monkeypatch, _ok)

    def boom(cwd):
        raise RuntimeError("bad config")

    monkeypatch.setattr(conventions, "_load_judgments_review", boom)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    scheduled: list[int] = []

    with caplog.at_level(logging.WARNING, logger="voss.harness.swarm_review"):
        result = _run(store, repo, swarm_id, role, task, spawn, after=lambda: scheduled.append(len(swarm_review.PENDING)))

    assert result.candidate_ready is True
    assert scheduled == [0]
    warnings = [r.getMessage() for r in caplog.records if r.name == "voss.harness.swarm_review"]
    assert len(warnings) == 1
    assert task.id in warnings[0] and "RuntimeError" in warnings[0]
    assert seen == []


def test_review_in_flight_finishes_when_asyncio_run_shuts_down(tmp_path, monkeypatch, caplog, capsys):
    async def slow(request):
        await asyncio.sleep(0.5)
        return _ok(request)

    install_jev(monkeypatch, slow)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})

    with caplog.at_level(logging.DEBUG):
        _run(store, repo, swarm_id, role, task, spawn, gather=False)

    receipts = _review(repo, swarm_id, task.id)["receipts"]
    assert len(receipts) == 1
    assert receipts[0]["status"] == "answered"
    assert "Task was destroyed but it is pending" not in caplog.text
    assert "Task was destroyed but it is pending" not in capsys.readouterr().err


def test_review_queued_behind_busy_executor_still_runs_at_shutdown(tmp_path, monkeypatch):
    install_jev(monkeypatch, _ok)
    repo = _repo(tmp_path / "proj")
    store, swarm_id, role, task, spawn = _member(repo, {"owned.py": "# changed\n"})
    release = threading.Event()

    class HoldExecutor(list):
        def append(self, event):
            super().append(event)
            if event["type"] == "swarm.candidate_ready":
                asyncio.get_running_loop().run_in_executor(None, release.wait, 5)
                threading.Timer(0.3, release.set).start()

    async def go():
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1))
        return await run_cli_member(store, repo, swarm_id, role, task, spawn_fn=spawn, on_event=HoldExecutor().append)

    asyncio.run(go())

    assert _review(repo, swarm_id, task.id)["receipts"][0]["status"] == "answered"


def _normalize(items: list[dict]) -> list[dict]:
    labels: dict[str, str] = {}

    def label(key, value):
        if key not in PLACEHOLDER_KEYS or value is None:
            return value
        if value not in labels:
            labels[value] = f"<{key}#{len(labels) + 1}>"
        return labels[value]

    return [{k: label(k, v) for k, v in item.items()} for item in items]


def _identity_scenario(root: Path, config_text: str) -> tuple[dict, list[str], list[list[dict]]]:
    repo = _repo(root, config_text)
    setup_head = _out(["rev-parse", "HEAD"], repo)
    store = SwarmStore(cwd=repo)
    swarm = store.create(
        "ship it", cwd=str(repo), roster=[Role(name="builder-1", agent="codex"), Role(name="builder-2", agent="codex")]
    )
    tasks = [
        store.add_task(swarm.id, "owned.py says builder-1", owned_files=["owned.py"]),
        store.add_task(swarm.id, "other.py says builder-2", owned_files=["other.py"]),
    ]

    def spawn(argv, cwd):
        (cwd / ("owned.py" if cwd.name == "builder-1" else "other.py")).write_text(f"# by {cwd.name}\n")
        if cwd.name == "builder-2":
            (cwd / "base.txt").write_text("out of scope\n")
        _write_result(repo, swarm.id, cwd.name, f"{cwd.name} done")
        return _FakeHandle(0)

    events: list[dict] = []

    async def go():
        results = await run_cli_swarm(store, repo, swarm.id, spawn_fn=spawn, on_event=events.append)
        await asyncio.gather(*list(swarm_review.PENDING))
        return results

    results = asyncio.run(go())
    replayed = SwarmStore(cwd=repo)
    timeline = replayed.replay_timeline(swarm.id)
    swarm_dir = repo / ".voss" / "swarm" / swarm.id
    files = sorted(str(p.relative_to(swarm_dir)) for p in swarm_dir.rglob("*") if p.is_file())
    observed = {
        "events": _normalize(events),
        "results": _normalize([asdict(r) for r in results]),
        "states": [t.state for t in replayed.replay(swarm.id).tasks],
        "timeline": [timeline[t.id] for t in tasks],
        "log": [e["type"] for e in SwarmEventLog(repo).read_events(swarm.id)],
        "head_unchanged": _out(["rev-parse", "HEAD"], repo) == setup_head,
        "branches": len(_out(["branch", "--list", "swarm/*"], repo).splitlines()),
        "heads_match": [_out(["rev-parse", r.candidate_branch], repo) == r.candidate_head for r in results],
        "worktrees": [_out(["status", "--porcelain"], Path(r.candidate_worktree)) for r in results],
        "main": _out(["status", "--porcelain", "--", ".", ":(exclude).voss"], repo),
        "bus": [f for f in files if not f.startswith("reviews/")],
    }
    reviews = [f for f in files if f.startswith("reviews/")]
    paths = [decision_review.candidate_review_path(repo, swarm.id, t.id) for t in tasks]
    for task, path in zip(tasks, paths):
        if path.exists():
            link = json.loads(path.read_text())["task_review"]
            candidate = next(e for e in events if e['type'] == 'swarm.candidate_ready' and e['task_id'] == task.id)
            assert (link['swarm_id'], link['task_id'], link['attempt_id'], link['candidate_revision']) == (swarm.id, task.id, candidate['attempt_id'], candidate['head'])
            assert link['criteria_source'] == 'task_goal' and link['criteria'][0]['text'] == task.goal
            assert candidate['repository'] == str(repo)
    receipts = [json.loads(path.read_text())["receipts"] for path in paths if path.exists()]
    return observed, reviews, receipts


def _assert_identical(tmp_path, monkeypatch, handler) -> list:
    seen = install_jev(monkeypatch, handler)
    off, off_reviews, _ = _identity_scenario(tmp_path / "a", OFF)
    assert seen == []
    shadow, shadow_reviews, receipts = _identity_scenario(tmp_path / "b", SHADOW)

    assert off == shadow
    assert off["head_unchanged"] is True
    assert off["branches"] == 2
    assert off["heads_match"] == [True, True]
    assert off["worktrees"] == ["", ""]
    assert off["main"] == ""
    assert [r["violations"] for r in off["results"]] == [[], ["base.txt"]]
    assert off_reviews == []
    assert len(shadow_reviews) == 2
    assert [len(r) for r in receipts] == [1, 1]
    assert len(seen) == 2
    return [r[0] for r in receipts]


def test_identical_swarm_behavior(tmp_path, monkeypatch):
    receipts = _assert_identical(tmp_path, monkeypatch, _ok)

    assert [r["status"] for r in receipts] == ["answered", "answered"]


def test_identical_with_jev_failing(tmp_path, monkeypatch):
    receipts = _assert_identical(tmp_path, monkeypatch, lambda request: httpx.Response(500))

    assert [r["fallback_reason"] for r in receipts] == ["unavailable", "unavailable"]


def _names(tree: ast.AST) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.alias):
            found.add(node.asname or node.name)
    return found


def test_hook_boundary():
    tree = ast.parse((ROOT / "voss/harness/swarm_review.py").read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules += [node.module or ""] + [f"{node.module or ''}.{a.name}" for a in node.names]
    assert not [m for m in modules if m.endswith(("gates", "swarm_store", "server"))]
    assert not _names(tree) & {"ReviewerVerdict", "SwarmStore", "on_event", "_emit"}
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    assert not [c for c in called if c.startswith("mark_") or c in {"record_gate_decision", "add_task"}]

    runtime = ast.parse((ROOT / "voss/harness/swarm_runtime.py").read_text())
    calls = [
        n for n in ast.walk(runtime)
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "schedule_candidate_review"
    ]
    assert len(calls) == 1
    member = next(n for n in runtime.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_cli_member")
    assert member.lineno <= calls[0].lineno <= member.end_lineno
    literals = {
        n.value: n.lineno for n in ast.walk(member)
        if isinstance(n, ast.Constant) and n.value in ("swarm.candidate_ready", "swarm.worker_done")
    }
    assert literals["swarm.candidate_ready"] < calls[0].lineno < literals["swarm.worker_done"]
