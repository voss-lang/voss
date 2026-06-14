"""V23 RED scaffold — pins all eight retrieval-aware ranking/hygiene requirements.

Wave 0 tests-first gate (V23-VALIDATION.md): every later V23 plan turns one or
more of these RED tests GREEN. Tests assert the *post-V23* contract, so most fail
today (feature code absent) and flip green as plans land. A handful are
deliberate always-green regression locks (byte-identical off-path, disable-knob
restores fill, mtime eviction fallback) — these guard the "no behaviour change
unless opted in" constraint and must stay green before AND after the feature.

RED mechanism per requirement:
  - VRNK-01 telemetry  → not-yet-existing `store._record_telemetry` /
                         `store._load_telemetry_compacted`
  - VRNK-02 floors     → post-floor `recall()` returns 0 for a weak/ubiquitous
                         query that today fills
  - VRNK-03 rescore    → telemetry-driven re-ranking (config `memory.rescore`)
                         not yet honoured; off-path byte-identical
  - VRNK-04 eviction   → pin/telemetry-aware eviction order (today mtime-only)
  - VRNK-05 reindex    → `voss memory reindex [--check]` CLI verbs absent
  - VRNK-06 pins       → not-yet-existing `store._load_pins` + pin-aware eviction
  - VRNK-07 cli        → `pin/unpin/list/show` CLI verbs absent
  - VRNK-08            → byte-identical baseline (shared with VRNK-03)

Sidecar contract (gitignored under .voss/memory/, never the memory files):
  - telemetry: .voss/memory/.retrieval.jsonl  (append-only per agent recall)
  - pins:      .voss/memory/.pins.json

Tests import only from voss.harness.memory_store / memory_cli (no reach into
voss_runtime.memory.semantic) per V23-RESEARCH Test Map.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.memory_cli import memory_group
from voss.harness.memory_store import MemoryStore, make_id


@pytest.fixture(autouse=True)
def _no_chroma(monkeypatch: pytest.MonkeyPatch) -> None:
    """BM25-only determinism: skip chroma so recall ordering is reproducible.

    Mirrors tests/harness/test_memory_eviction.py:_no_chroma. The chroma-absent
    reindex test layers `chroma_disabled_env` on top; both collapse to None.
    """
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)


# ---------------------------------------------------------------------------
# seeding / sidecar helpers
# ---------------------------------------------------------------------------


def _store(repo: Path, *, cap_bytes: int = 100 * 1024 * 1024) -> MemoryStore:
    return MemoryStore(repo, cap_bytes=cap_bytes).bind(session_id="s")


def _write_note(store: MemoryStore, stem: str, body: str) -> str:
    """Write a raw note .md (full control over corpus text); return its locator."""
    path = store.root / "notes" / f"{stem}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return make_id("note", stem)


def _write_convention(store: MemoryStore, stem: str, body: str, *, mtime: int) -> Path:
    path = store.root / "conventions" / f"{stem}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    os.utime(path, (mtime, mtime))
    return path


def _telemetry_path(store: MemoryStore) -> Path:
    return store.root / ".retrieval.jsonl"


def _write_telemetry(store: MemoryStore, entries: list[tuple[str, int]]) -> None:
    """Seed the retrieval sidecar: list of (locator, retrieval_count)."""
    lines: list[str] = []
    for locator, count in entries:
        for _ in range(count):
            lines.append(
                json.dumps(
                    {
                        "locator": locator,
                        "ts": "2026-06-13T00:00:00+00:00",
                        "session_id": "s",
                    }
                )
            )
    _telemetry_path(store).write_text("\n".join(lines) + "\n")


def _pins_path(store: MemoryStore) -> Path:
    return store.root / ".pins.json"


def _write_pins(store: MemoryStore, locators: list[str]) -> None:
    _pins_path(store).write_text(json.dumps([{"locator": loc} for loc in locators]))


def _write_memory_config(repo: Path, **kv: object) -> None:
    """Write .voss/config.yml memory section (extends `_load_memory_config`)."""
    body = "memory:\n" + "".join(f"  {k}: {v}\n" for k, v in kv.items())
    (repo / ".voss").mkdir(parents=True, exist_ok=True)
    (repo / ".voss" / "config.yml").write_text(body)


# ===========================================================================
# VRNK-01 — telemetry: agent recall records; CLI does not; memory files immutable
# ===========================================================================


def test_telemetry_recorded_on_agent_recall(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    store.write_turn(role="user", content="postgres partition migration plan", session_id="s", turn_idx=0)

    hits = store.recall("postgres migration", top_k=5)
    assert hits, "setup: agent recall must return ≥1 hit to record"

    # RED: agent path records telemetry to the sidecar (V23-02).
    store._record_telemetry(hits)  # type: ignore[attr-defined]

    assert _telemetry_path(store).exists()
    compacted = store._load_telemetry_compacted()  # type: ignore[attr-defined]
    assert compacted[hits[0].locator]["retrieval_count"] == 1


def test_telemetry_not_recorded_on_cli_recall(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    store.write_turn(role="user", content="rate limiter latency spike", session_id="s", turn_idx=0)

    # A plain recall with no agent-path record call must leave telemetry empty.
    store.recall("rate limiter", top_k=5)

    # RED: compacted-telemetry reader does not exist yet (V23-02).
    compacted = store._load_telemetry_compacted()  # type: ignore[attr-defined]
    assert compacted == {}


def test_recall_does_not_mutate_memory_file_mtime(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    store.write_turn(role="user", content="websocket reconnect idle clients", session_id="s", turn_idx=0)
    mem_file = store.root / "turns" / "s.jsonl"
    before = mem_file.stat()

    hits = store.recall("websocket reconnect", top_k=5)
    # RED: telemetry write targets the sidecar only — never the memory file.
    store._record_telemetry(hits)  # type: ignore[attr-defined]

    after = mem_file.stat()
    assert (after.st_mtime, after.st_size) == (before.st_mtime, before.st_size)


# ===========================================================================
# VRNK-02 — relevance floor: no-match → 0 hits; disable knob restores fill
# ===========================================================================


def test_no_match_query_returns_zero_hits_with_floor(tmp_voss_repo: Path) -> None:
    # BM25-only here (autouse _no_chroma): a query with no token overlap returns
    # 0, not top_k nearest-anything. The chroma absolute floor (0.25) enforces
    # the same when chroma is present. Floors default-on.
    store = _store(tmp_voss_repo)
    _write_note(store, "n0", "database migration rollback\n")
    _write_note(store, "n1", "websocket reconnect handler\n")

    assert store.recall("xylophone quokka zzzznonexistent", top_k=5) == []


def test_bm25_floor_drops_weak_matches(tmp_voss_repo: Path) -> None:
    # One strong multi-term match + one doc touching only the common term. The
    # relative-to-top floor (default 0.1) drops the weak fill before fusion.
    store = _store(tmp_voss_repo)
    strong = _write_note(
        store, "strong", "database migration rollback database migration rollback\n"
    )
    _write_note(store, "weak", "database " + "filler " * 80 + "\n")

    locs = [h.locator for h in store.recall("database migration rollback", top_k=5)]
    assert strong in locs
    assert make_id("note", "weak") not in locs  # below 10% of top → floored out.


def test_floor_disabled_restores_fill(tmp_voss_repo: Path) -> None:
    # Same strong+weak corpus; disabling both floors restores pre-V23 fill so the
    # weak match returns again. Green before AND after the feature (knob lock).
    store = _store(tmp_voss_repo)
    strong = _write_note(
        store, "strong", "database migration rollback database migration rollback\n"
    )
    weak = _write_note(store, "weak", "database " + "filler " * 80 + "\n")

    _write_memory_config(tmp_voss_repo, chroma_floor=0, bm25_floor_ratio=0)

    locs = [h.locator for h in store.recall("database migration rollback", top_k=5)]
    assert strong in locs and weak in locs


# ===========================================================================
# VRNK-03 / VRNK-08 — rescore: deterministic re-rank on; byte-identical off
# ===========================================================================


def test_rescore_deterministic_under_fixture(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    a = _write_note(store, "a", "database migration database migration database\n")
    b = _write_note(store, "b", "database schema\n")

    # Baseline: A outranks B on lexical strength.
    baseline = store.recall("database migration", top_k=5)
    assert [h.locator for h in baseline][:2] == [a, b], "setup: A must lead B pre-rescore"

    # Fixed telemetry strongly favours B; rescore on must lift B to the top.
    _write_telemetry(store, [(b, 8)])
    _write_memory_config(tmp_voss_repo, rescore="true")

    hits = store.recall("database migration", top_k=5)
    assert hits and hits[0].locator == b  # RED today: rescore not honoured → A leads.


def test_rescore_off_byte_identical(tmp_voss_repo: Path) -> None:
    """VRNK-08 baseline lock: default config → recall byte-identical across calls."""
    store = _store(tmp_voss_repo)
    _write_note(store, "a", "database migration plan\n")
    _write_note(store, "b", "database schema notes\n")

    first = store.recall("database migration", top_k=5)
    second = store.recall("database migration", top_k=5)

    fingerprint = lambda hs: [(h.locator, h.score, h.excerpt) for h in hs]
    assert fingerprint(first) == fingerprint(second)


def test_empty_telemetry_rescore_on_is_noop(tmp_voss_repo: Path) -> None:
    """Rescore on but no telemetry → ordering identical to the off path."""
    store = _store(tmp_voss_repo)
    _write_note(store, "a", "database migration plan\n")
    _write_note(store, "b", "database schema notes\n")

    baseline = [h.locator for h in store.recall("database migration", top_k=5)]
    _write_memory_config(tmp_voss_repo, rescore="true")  # no .retrieval.jsonl written
    after = [h.locator for h in store.recall("database migration", top_k=5)]
    assert after == baseline


# ===========================================================================
# VRNK-04 — retrieval-aware eviction: never-retrieved evicts before retrieved
# ===========================================================================


def _seed_two_conventions(store: MemoryStore) -> tuple[Path, Path, str, str]:
    old = _write_convention(store, "old-conv", "c" * 200, mtime=1000)
    new = _write_convention(store, "new-conv", "c" * 200, mtime=2000)
    return old, new, make_id("convention", "old-conv"), make_id("convention", "new-conv")


def test_retrieval_aware_eviction_evicts_never_retrieved_first(tmp_voss_repo: Path) -> None:
    # cap 2560 → conventions quota = 0.10*cap = 256; two 200B files = 400 → evict 1.
    store = _store(tmp_voss_repo, cap_bytes=2560)
    old, new, old_loc, _ = _seed_two_conventions(store)

    # Telemetry marks the OLDER file as recently/frequently retrieved.
    _write_telemetry(store, [(old_loc, 5)])

    store._maybe_evict("conventions")

    # RED today: mtime-only eviction kills the oldest (the retrieved one).
    assert old.exists(), "retrieved-but-old convention must survive"
    assert not new.exists(), "never-retrieved (newer) convention must evict first"


def test_eviction_mtime_fallback_no_sidecar(tmp_voss_repo: Path) -> None:
    """No .retrieval.jsonl → mtime ordering unchanged (oldest evicts). Green lock."""
    store = _store(tmp_voss_repo, cap_bytes=2560)
    old, new, _, _ = _seed_two_conventions(store)

    store._maybe_evict("conventions")

    assert not old.exists()
    assert new.exists()


# ===========================================================================
# VRNK-05 — reindex hygiene: --check detects drift; reindex repairs; chroma-absent
# ===========================================================================


def test_reindex_check_detects_drift(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    path = _write_convention(store, "drifted", "original statement\n", mtime=1000)
    # Hand-edit the mirror so the embedding manifest goes stale.
    path.write_text("edited out-of-band statement\n")

    res = CliRunner().invoke(
        memory_group, ["reindex", "--check", "--cwd", str(tmp_voss_repo)]
    )
    # RED today: no `reindex` verb (exit 2). Post-V23: exit 1 + stale locator listed.
    assert res.exit_code == 1
    assert make_id("convention", "drifted") in res.output


def test_reindex_repairs_then_check_clean(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    path = _write_convention(store, "drifted", "original statement\n", mtime=1000)
    path.write_text("edited out-of-band statement\n")

    runner = CliRunner()
    repair = runner.invoke(memory_group, ["reindex", "--cwd", str(tmp_voss_repo)])
    assert repair.exit_code == 0  # RED today (no verb)

    check = runner.invoke(memory_group, ["reindex", "--check", "--cwd", str(tmp_voss_repo)])
    assert check.exit_code == 0


def test_reindex_chroma_absent_exit_0(tmp_voss_repo: Path, chroma_disabled_env: None) -> None:
    _store(tmp_voss_repo)
    runner = CliRunner()
    check = runner.invoke(memory_group, ["reindex", "--check", "--cwd", str(tmp_voss_repo)])
    repair = runner.invoke(memory_group, ["reindex", "--cwd", str(tmp_voss_repo)])
    # RED today (no verb). Post-V23: both no-op exit 0 with a notice.
    assert check.exit_code == 0
    assert repair.exit_code == 0


# ===========================================================================
# VRNK-06 — pinned tier: always available; survives eviction; cap overflow warns
# ===========================================================================


def test_pinned_memory_always_injected(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    pin_loc = _write_note(store, "pinned", "PINNED ALPHA never matched by recall\n")
    _write_pins(store, [pin_loc])

    # A query that never recalls the pinned note still must surface it via pins.
    assert store.recall("totally unrelated zzqq", top_k=5) == []
    # RED: pin loader absent (V23-06). Full context-injection is manual-only
    # (V23-VALIDATION manual row); unit scope asserts the pin contract.
    pins = store._load_pins()  # type: ignore[attr-defined]
    assert any(p["locator"] == pin_loc for p in pins)


def test_pinned_survives_over_quota_eviction(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo, cap_bytes=2560)
    old, new, old_loc, _ = _seed_two_conventions(store)
    _write_pins(store, [old_loc])  # pin the OLDEST → it must be eviction-exempt.

    store._maybe_evict("conventions")

    # RED today: mtime-only eviction kills the pinned-but-oldest file.
    assert old.exists(), "pinned convention must survive over-quota eviction"
    assert not new.exists()


def test_pin_cap_overflow_warns(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    locs = [_write_note(store, f"p{i}", f"pin body {i}\n") for i in range(60)]
    _write_pins(store, locs)

    # RED: pin loader (with cap/warn semantics) absent (V23-06).
    pins = store._load_pins()  # type: ignore[attr-defined]
    assert len(pins) <= 50  # pin cap enforced on load


# ===========================================================================
# VRNK-07 — CLI verbs: pin / unpin / list --pinned / show
# ===========================================================================


def test_pin_unpin_list_cli(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    loc = _write_note(store, "my-note", "pin me\n")
    runner = CliRunner()

    pinned = runner.invoke(memory_group, ["pin", loc, "--cwd", str(tmp_voss_repo)])
    assert pinned.exit_code == 0  # RED today (no verb)

    listed = runner.invoke(memory_group, ["list", "--pinned", "--cwd", str(tmp_voss_repo)])
    assert loc in listed.output

    runner.invoke(memory_group, ["unpin", loc, "--cwd", str(tmp_voss_repo)])
    after = runner.invoke(memory_group, ["list", "--pinned", "--cwd", str(tmp_voss_repo)])
    assert loc not in after.output


def test_show_displays_telemetry(tmp_voss_repo: Path) -> None:
    store = _store(tmp_voss_repo)
    loc = _write_note(store, "shown", "show body\n")
    _write_telemetry(store, [(loc, 3)])

    res = CliRunner().invoke(memory_group, ["show", loc, "--cwd", str(tmp_voss_repo)])
    # RED today (no verb). Post-V23: prints retrieval_count for the locator.
    assert res.exit_code == 0
    assert "retrieval_count" in res.output


def test_cli_unknown_locator_exits_1(tmp_voss_repo: Path) -> None:
    _store(tmp_voss_repo)
    res = CliRunner().invoke(
        memory_group, ["pin", "note:does-not-exist", "--cwd", str(tmp_voss_repo)]
    )
    # RED today: unknown command → exit 2. Post-V23: unknown locator → exit 1.
    assert res.exit_code == 1


# ===========================================================================
# VRNK-06 (D-09) — global-store pinned dual fusion: V21-gated (expected-fail)
# ===========================================================================


@pytest.mark.xfail(reason="V21 global-store dual fusion not yet merged", strict=False)
def test_pinned_global_store_dual_fusion(tmp_voss_global: Path) -> None:
    from voss.harness.memory_store import make_global_store

    store = make_global_store()
    assert store is not None
    store.bind(session_id="s")
    pin_loc = make_id("note", "global-pin")
    _write_pins(store, [pin_loc])

    pins = store._load_pins()  # type: ignore[attr-defined]
    assert any(p["locator"] == pin_loc for p in pins)
