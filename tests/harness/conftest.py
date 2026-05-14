"""Shared fixtures for harness tests.

`isolated_state` is autouse — every harness test gets an XDG_STATE_HOME
sandbox pointed at its own tmp_path so session JSON / permission state never
leaks between tests.

`git_repo` is opt-in: tests request it by parameter when they need a real
git tree with one commit (drift tests, ls-files tests).

M8 additions: `tmp_voss_repo`, `pre_m8_architecture_md`, `pre_m8_session_json`,
`fake_session_corpus`, `chroma_disabled_env` — see M8-RESEARCH.md §Validation
Architecture.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


@pytest.fixture(scope="session")
def precompiled_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project = tmp_path_factory.mktemp("voss-m4-project")
    repo_root = Path(__file__).resolve().parents[2]
    source_dir = repo_root / "voss" / "harness" / "agent"
    target_dir = project / "voss" / "harness" / "agent"
    target_dir.mkdir(parents=True)

    for source in sorted(source_dir.glob("*.voss")):
        shutil.copy2(source, target_dir / source.name)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(repo_root)
        if not env.get("PYTHONPATH")
        else f"{repo_root}{os.pathsep}{env['PYTHONPATH']}"
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "voss.cli",
            "compile",
            "voss/harness/agent/",
            "--project-root",
            str(project),
        ],
        cwd=str(project),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return project


@pytest.fixture
def parity_project(precompiled_harness: Path) -> Path:
    (precompiled_harness / "fixture.md").write_text("noop fixture body\n")
    return precompiled_harness


# ---------------------------------------------------------------------------
# M8 fixtures (Project Memory MEM-01)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_voss_repo(tmp_path: Path) -> Path:
    """A tmp project root with .voss/memory/<source>/ subdirs pre-created.

    Layout matches M8-SPEC §Storage Topology. Consumed by Reqs 3/4/5/6/7.
    """
    root = tmp_path
    (root / ".voss").mkdir(parents=True, exist_ok=True)
    mem = root / ".voss" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    for sub in ("turns", "ledgers", "decisions", "conventions", "notes", "chroma", ".locks"):
        (mem / sub).mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def pre_m8_architecture_md(tmp_voss_repo: Path) -> Path:
    """Write a realistic pre-migration .voss/architecture.md.

    Frontmatter shape matches cognition.py:38 ArchitectureFrontmatter
    (git_head, analyzed_at, file_count, analyzer_version). Used by
    test_voss_md_migration to verify byte-identical archive (Req 2(a)).
    """
    arch = tmp_voss_repo / ".voss" / "architecture.md"
    arch.write_text(
        "---\n"
        "git_head: abc123def456\n"
        "analyzed_at: 2026-05-14T10:00:00+00:00\n"
        "file_count: 42\n"
        "analyzer_version: 1\n"
        "---\n\n"
        "# Architecture\n\nThis is fixture content.\n"
    )
    return arch


@pytest.fixture
def pre_m8_session_json(tmp_voss_repo: Path) -> Path:
    """Write a .voss/sessions/<uuid>.json matching the M2 SessionRecord schema (no memory_* fields).

    Used for Pitfall 6 backward-compat tests.
    """
    sessions_dir = tmp_voss_repo / ".voss" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = {
        "id": sid,
        "name": f"session-{sid[:8]}",
        "cwd": str(tmp_voss_repo),
        "model": "claude-sonnet-4-5",
        "started_at": now,
        "updated_at": now,
        "total_cost_usd": 0.0,
        "turns": [],
        "runs": [],
    }
    path = sessions_dir / f"{sid}.json"
    path.write_text(json.dumps(record, indent=2))
    return path


@pytest.fixture
def fake_session_corpus(tmp_voss_repo: Path) -> dict:
    """Seed 5 sessions × (3 turns + 1 ledger + 1 convention + 1 note) + 5 decisions.

    Returns a dict {query: expected_locator} covering all four source types
    (turn / decision / convention / note + ledger). Used by
    `tests/harness/test_recall_eval.py` to verify Req 3 hit-rate floors.
    """
    from types import SimpleNamespace

    from voss.harness.memory_store import MemoryStore, make_id

    store = MemoryStore(tmp_voss_repo).bind(session_id="seed")

    turn_seed = {
        "s1": [
            ("user", "always use snake_case identifiers in Python"),
            ("assistant", "got it; renamed identifiers to snake_case"),
            ("assistant", "tests still pass after rename"),
        ],
        "s2": [
            ("user", "the auth bug was in jwt token refresh handler"),
            ("assistant", "patched refresh handler"),
            ("assistant", "added regression test for jwt"),
        ],
        "s3": [
            ("user", "investigate rate limiter latency spike"),
            ("assistant", "found redis hot key"),
            ("assistant", "rebalanced rate limiter shards"),
        ],
        "s4": [
            ("user", "migrate postgres analytics tables to partitioned schema"),
            ("assistant", "wrote migration script"),
            ("assistant", "rolled out partitioned tables"),
        ],
        "s5": [
            ("user", "websocket reconnect loop is dropping idle clients"),
            ("assistant", "added heartbeat ping every 30s"),
            ("assistant", "verified websocket reconnect stable"),
        ],
    }
    for sid, turns in turn_seed.items():
        for idx, (role, content) in enumerate(turns):
            store.write_turn(role=role, content=content, session_id=sid, turn_idx=idx)

    ledger_blurbs = {
        "s1": "renamed identifiers to snake_case across module",
        "s2": "patched jwt refresh handler in auth.py",
        "s3": "rebalanced redis rate limiter shards",
        "s4": "applied partitioned schema migration to analytics db",
        "s5": "added websocket heartbeat to gateway service",
    }
    for sid, blurb in ledger_blurbs.items():
        run = {
            "id": f"run-{sid}",
            "changed": [f"src/{sid}.py"],
            "diff_summary": blurb,
        }
        store.write_ledger(run, session_id=sid)

    convention_seed = [
        ("s1", "always run mypy before merging Python changes"),
        ("s2", "never store jwt secrets in environment variables"),
        ("s3", "prefer redis pipeline batching for rate limiter writes"),
        ("s4", "use partitioned tables for time-series analytics data"),
        ("s5", "send websocket heartbeat every 30 seconds"),
    ]
    convention_ids: dict[str, str] = {}
    for sid, statement in convention_seed:
        candidate = SimpleNamespace(
            statement=statement,
            confidence=0.9,
            evidence_quote=statement,
            evidence_turn_idx=0,
        )
        path = store.write_convention(candidate, session_id=sid)
        convention_ids[sid] = make_id("convention", path.stem)

    note_seed = {
        "s1": "snake_case Python style note",
        "s2": "jwt rotation runbook tip",
        "s3": "rate limiter latency debug tip",
        "s4": "postgres partitioning checklist",
        "s5": "websocket idle timeout tip",
    }
    note_ids: dict[str, str] = {}
    for sid, text in note_seed.items():
        path = store.write_note(text, session_id=sid)
        note_ids[sid] = make_id("note", path.stem)

    decisions_dir = tmp_voss_repo / ".voss" / "memory" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    decision_seed = {
        "s1": "Adopt snake_case for all new Python identifiers",
        "s2": "Use rotating jwt signing keys with 24h expiry",
        "s3": "Cap redis rate limiter to 100 req/s per tenant",
        "s4": "Partition postgres analytics tables by month",
        "s5": "Drop websocket clients silent for 90 seconds",
    }
    for sid, body in decision_seed.items():
        path = decisions_dir / f"{sid}-decision.md"
        path.write_text(
            "---\n"
            f"id: {sid}-decision\n"
            f"related_session: {sid}\n"
            "---\n\n"
            f"# Decision\n\n{body}\n"
        )

    return {
        "always snake_case identifiers Python": make_id("turn", "s1", seq=0),
        "jwt token refresh handler bug": make_id("turn", "s2", seq=0),
        "rate limiter latency spike investigate": make_id("turn", "s3", seq=0),
        "postgres partitioned schema migration analytics": make_id("turn", "s4", seq=0),
        "websocket reconnect idle clients": make_id("turn", "s5", seq=0),
        "mypy before merging Python": convention_ids["s1"],
        "never store jwt secrets env": convention_ids["s2"],
        "postgres partitioning checklist": note_ids["s4"],
        "websocket idle timeout tip": note_ids["s5"],
        "redis rate limiter shards rebalance": make_id("ledger", "run-s3", seq=0),
    }


@pytest.fixture
def chroma_disabled_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force chromadb to be uninstalled-like for the duration of one test.

    Sets sys.modules["chromadb"] = None so subsequent imports raise
    ImportError. Reloads voss_runtime.memory.semantic if already imported
    so its module-level state is rebuilt under the disabled env.
    """
    import sys as _sys

    monkeypatch.setitem(_sys.modules, "chromadb", None)
    if "voss_runtime.memory.semantic" in _sys.modules:
        import importlib

        importlib.reload(_sys.modules["voss_runtime.memory.semantic"])
