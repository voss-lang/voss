"""ContextAllocator unit contract (VOPT-01/02/03/04).

Fixtures are synthetic SimpleNamespace iters shaped like
voss.harness.session.IterationRecord (index/plan/tool_results) — no
provider, no live model, no filesystem dependency: the allocator is pure.

Contract pinned here:
    from voss.harness.context_allocator import ContextAllocator, PackingProfile
    ContextAllocator(token_count=callable)            # injected for purity
    .pack(iter_records, packing_budget, profile) -> list[tuple[dict, dict]]
    .stable_region_hash() -> str                      # SHA-256 of stable replay prefix
    PackingProfile(recent_full_k=8, digest_cutoff_m=20,
                   high_water=0.80, low_water=0.60, enabled=True)
"""
from __future__ import annotations

from types import SimpleNamespace


def _tok(text: str) -> int:
    return max(len(text) // 4, 1)


def _make_iter(i: int, *, path: str | None = None) -> SimpleNamespace:
    args: dict = {"path": path} if path is not None else {}
    return SimpleNamespace(
        index=i,
        plan={
            "rationale": f"work on step {i}",
            "steps": [{"name": "fs_read", "args": dict(args), "why": "look"}],
            "final_when_done": "",
        },
        tool_results=[{"name": "fs_read", "args": dict(args), "result": f"result-{i}: ok"}],
        cache_read_input_tokens=0,
        prompt_tokens=0,
    )


def _iters(n: int) -> list[SimpleNamespace]:
    return [_make_iter(i) for i in range(n)]


def _pair_tokens(pairs) -> int:
    return sum(
        _tok(str(a.get("content", ""))) + _tok(str(u.get("content", "")))
        for a, u in pairs
    )


def _render_text(pairs) -> str:
    return "\n".join(str(m.get("content", "")) for pair in pairs for m in pair)


# ---------------------------------------------------------------------------
# VOPT-01 — pure allocator under a ceiling
# ---------------------------------------------------------------------------


def test_allocator_pure(tmp_path) -> None:
    """VOPT-01: allocator is pure — no provider attribute, no fs writes."""
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(_iters(50), 2_000, PackingProfile())

    assert isinstance(out, list)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in out)
    assert not hasattr(alloc, "provider")
    assert list(tmp_path.iterdir()) == []  # no filesystem writes


def test_pack_50_iters_under_ceiling() -> None:
    """VOPT-01: 50 iters pack under a 10k token ceiling."""
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(_iters(50), 10_000, PackingProfile())

    assert _pair_tokens(out) <= 10_000


def test_pack_respects_tiny_ceiling() -> None:
    """VOPT-01: when reserve leaves almost no space, replay stays under budget."""
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(_iters(50), 1, PackingProfile())

    assert _pair_tokens(out) <= 1


def test_below_threshold_byte_identical() -> None:
    """VOPT-01: <= recent_full_k iters ⇒ output is full replay, byte-for-byte."""
    from voss.harness.agent import _serialize_iter_for_replay
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    iters = _iters(5)
    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(iters, 1_000_000, PackingProfile(recent_full_k=8))

    assert out == [_serialize_iter_for_replay(p) for p in iters]


# ---------------------------------------------------------------------------
# VOPT-02 — tiered rendering (full / digest / folded)
# ---------------------------------------------------------------------------


def test_tier_boundaries_golden_render() -> None:
    """VOPT-02: full tier for last K, one-line digests K..M, fold past M.

    30 iters with the default profile (K=8, M=20) so all three tiers are
    populated: iters 22-29 full, 10-21 digested, 0-9 folded.
    """
    from voss.harness.agent import _serialize_iter_for_replay
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    iters = _iters(30)
    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(iters, 1_000_000, PackingProfile())
    text = _render_text(out)

    # Newest iteration full in every case; last K=8 are the full tier.
    assert out[-1] == _serialize_iter_for_replay(iters[-1])
    assert out[-8:] == [_serialize_iter_for_replay(p) for p in iters[-8:]]
    # Digest tier marker: one-line structural digest `Iter i: <n> tools, ...`.
    assert "tools," in text
    # Fold tier: single "Earlier work" summary block.
    assert "Earlier work" in text
    assert text.count("Earlier work") == 1


def test_packed_tokens_never_exceed_full() -> None:
    """VOPT-02: packed estimate <= full-replay estimate at every history length."""
    from voss.harness.agent import _serialize_iter_for_replay
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    for n in (5, 12, 25, 60):
        iters = _iters(n)
        packed = alloc.pack(iters, 1_000_000, PackingProfile())
        full = [_serialize_iter_for_replay(p) for p in iters]
        assert _pair_tokens(packed) <= _pair_tokens(full), f"history length {n}"


# ---------------------------------------------------------------------------
# VOPT-03 — cache-coherent append-only stable region (pure half)
# ---------------------------------------------------------------------------


def test_stable_region_append_only() -> None:
    """VOPT-03: below high_water, stable region hash unchanged turn-over-turn."""
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    profile = PackingProfile()
    iters = _iters(10)
    hashes = []
    for n in range(1, 11):
        alloc.pack(iters[:n], 1_000_000, profile)  # huge budget: never crosses high_water
        hashes.append(alloc.stable_region_hash())

    assert len(set(hashes)) == 1, f"stable region recompacted below high_water: {hashes}"


def test_recompaction_on_high_water() -> None:
    """VOPT-03: crossing high_water triggers exactly one recompaction.

    Small budget forces estimated usage past high_water as history grows;
    the stable-region hash changes once at the crossing, then settles at
    low_water and stays stable on the immediately following turns.
    """
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    alloc = ContextAllocator(token_count=_tok)
    profile = PackingProfile()
    iters = _iters(60)

    prev = None
    change_turns: list[int] = []
    crossed_at = None
    for n in range(1, 61):
        alloc.pack(iters[:n], 800, profile)
        h = alloc.stable_region_hash()
        if prev is not None and h != prev:
            change_turns.append(n)
        prev = h
        if change_turns and crossed_at is None:
            crossed_at = n
        # Stop two turns after the first crossing: post-recompaction usage
        # sits at low_water, below high_water, so no second change yet.
        if crossed_at is not None and n >= crossed_at + 2:
            break

    assert change_turns, "high_water crossing never triggered a recompaction"
    assert len(change_turns) == 1, f"expected one recompaction at crossing, got {change_turns}"


# ---------------------------------------------------------------------------
# VOPT-04 — eviction pointers on fold
# ---------------------------------------------------------------------------


def test_eviction_pointer_emitted() -> None:
    """VOPT-04: folded iters with file refs emit deduped re-fetch pointers, max 5."""
    from voss.harness.context_allocator import ContextAllocator, PackingProfile

    # 10 old iters (folded under default M=20 with 30 total): foo.py three
    # times (dedup target) plus 7 distinct paths (8 distinct > cap of 5).
    paths = ["foo.py", "foo.py", "foo.py", "a.py", "b.py", "c.py", "d.py", "e.py", "f.py", "g.py"]
    iters = [_make_iter(i, path=paths[i]) for i in range(10)] + [
        _make_iter(i) for i in range(10, 30)
    ]
    alloc = ContextAllocator(token_count=_tok)
    out = alloc.pack(iters, 1_000_000, PackingProfile())
    text = _render_text(out)

    assert "re-fetch" in text
    assert "code_search" in text
    pointer_lines = [ln for ln in text.splitlines() if "re-fetch" in ln]
    pointer_blob = "\n".join(pointer_lines)
    assert pointer_blob.count("foo.py") <= 1, "pointer for foo.py not deduped"
    distinct_mentioned = sum(1 for p in set(paths) if p in pointer_blob)
    assert distinct_mentioned <= 5, f"pointer cap exceeded: {distinct_mentioned} paths"
