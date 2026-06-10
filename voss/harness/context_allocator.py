"""V18 budget-aware context allocator (VOPT-01/02/03/04).

Pure transformer: packs the variable replay region of the agent message
list under a token ceiling using three age tiers —

  FULL   — the last ``recent_full_k`` iterations, rendered by delegating
           to ``agent._serialize_iter_for_replay`` (byte-identical to the
           pre-V18 replay; preserves redaction + 400-char caps).
  DIGEST — iterations between the fold boundary and the FULL tier, one
           ``[digest] Iter i: ...`` structural line each (mirrors the
           rider digest format at agent.py:418-427).
  FOLD   — everything older, collapsed into a single "Earlier work
           summary" pair carrying deduped, capped re-fetch pointers to
           the existing M10 code-intel surfaces (no retrieval call).

Purity: no model client, no filesystem, no second tokenizer — token
estimation is injected as a callable (the caller binds
``functools.partial(_default_token_count, model=...)``).

Cache coherence (VOPT-03): the FOLD region is the *stable region*. It is
frozen across pack() calls and rewritten only when the packed estimate
crosses ``high_water * packing_budget`` (recompaction), at which point
digests are absorbed into the fold until the estimate drops to
``low_water * packing_budget``. Below high-water the fold pairs are
returned verbatim turn-over-turn, so ``stable_region_hash()`` is
append-only-stable between recompactions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

_POINTER_CAP = 5
_SNIPPET_CAP = 120


@dataclass
class PackingProfile:
    recent_full_k: int = 8
    digest_cutoff_m: int = 20
    high_water: float = 0.80
    low_water: float = 0.60
    enabled: bool = True


def _full_renderer():
    # Lazy import: agent.py will import ContextAllocator (Plan 03 seam),
    # so a module-level import here would create a cycle. The FULL tier
    # must delegate — not re-implement — to keep redaction + caps and the
    # below-threshold byte-identity guarantee (RESEARCH Pitfall 2).
    from voss.harness.agent import _serialize_iter_for_replay

    return _serialize_iter_for_replay


def _build_eviction_pointer(tr: dict) -> str | None:
    args = tr.get("args") or {}
    if not isinstance(args, dict):
        return None
    path = args.get("path") or args.get("file")
    if path:
        return f'↻ re-fetch via code_search("{path}")'
    symbol = args.get("pattern") or args.get("symbol")
    if symbol:
        return f'↻ re-fetch via find_definition("{symbol}")'
    return None


class ContextAllocator:
    """Budget-aware packer for the iteration-replay message region."""

    def __init__(self, token_count: Callable[[str], int]):
        self._token_count = token_count
        # Stable region: frozen FOLD pairs + how many leading iters they
        # consumed. Rewritten only on recompaction (hysteresis).
        self._stable_pairs: list[tuple[dict, dict]] = []
        self._stable_upto: int = 0
        self._initialized: bool = False
        self._recompactions: int = 0

    # -- rendering -----------------------------------------------------

    def _pair_tokens(self, pair: tuple[dict, dict]) -> int:
        return sum(self._token_count(str(m.get("content", ""))) for m in pair)

    def _estimate(self, pairs: list[tuple[dict, dict]]) -> int:
        return sum(self._pair_tokens(p) for p in pairs)

    def _fit_to_budget(
        self,
        pairs: list[tuple[dict, dict]],
        iters: list[Any],
        packing_budget: int,
    ) -> list[tuple[dict, dict]]:
        """Hard final guard: never return a replay region over budget."""
        if packing_budget <= 0:
            return []
        if self._estimate(pairs) <= packing_budget:
            return pairs

        serialize = _full_renderer()
        suffix: list[tuple[dict, dict]] = []
        for iter_rec in reversed(iters):
            pair = serialize(iter_rec)
            candidate = [pair, *suffix]
            if self._estimate(candidate) <= packing_budget:
                suffix = candidate
            elif suffix:
                break
        if suffix:
            return suffix

        latest_digest = self._render_iter_digest(iters[-1:][0]) if iters else None
        if latest_digest is not None and self._pair_tokens(latest_digest) <= packing_budget:
            return [latest_digest]

        minimal = (
            {
                "role": "assistant",
                "content": f"[context omitted] {len(iters)} prior iterations omitted to fit token budget.",
            },
            {"role": "user", "content": "(prior iterations omitted)"},
        )
        if self._pair_tokens(minimal) <= packing_budget:
            return [minimal]
        return []

    def _render_iter_digest(self, iter_rec: Any) -> tuple[dict, dict]:
        plan = iter_rec.plan or {}
        step_count = len(plan.get("steps", []) or [])
        tool_count = len(iter_rec.tool_results or [])
        snippet_src = plan.get("final_when_done") or plan.get("rationale") or ""
        snippet = snippet_src.replace("\n", " ")[:_SNIPPET_CAP]
        assistant_msg = {
            "role": "assistant",
            "content": f"[digest] Iter {iter_rec.index}: {step_count} steps, "
            f"{tool_count} tools, {snippet}",
        }
        user_msg = {"role": "user", "content": f"(iteration {iter_rec.index} digested)"}
        digest_pair = (assistant_msg, user_msg)
        # Pitfall 4: a digest must never cost more than the full rendering
        # it replaces — fall back to full for degenerate tiny iterations.
        full_pair = _full_renderer()(iter_rec)
        if self._pair_tokens(digest_pair) > self._pair_tokens(full_pair):
            return full_pair
        return digest_pair

    def _render_fold_summary(self, iter_recs: list[Any]) -> list[tuple[dict, dict]]:
        if not iter_recs:
            return []
        first, last = iter_recs[0].index, iter_recs[-1].index
        tool_names: dict[str, None] = {}
        pointers: dict[str, None] = {}
        for ir in iter_recs:
            for tr in ir.tool_results or []:
                name = tr.get("name", "")
                if name:
                    tool_names.setdefault(name, None)
                ptr = _build_eviction_pointer(tr)
                if ptr is not None:
                    pointers.setdefault(ptr, None)
        lines = [
            f"Earlier work summary: iterations {first}-{last} "
            f"({len(iter_recs)} iterations); tools used: "
            f"{', '.join(tool_names) or 'none'}."
        ]
        lines.extend(list(pointers)[:_POINTER_CAP])
        assistant_msg = {"role": "assistant", "content": "\n".join(lines)}
        user_msg = {
            "role": "user",
            "content": f"({len(iter_recs)} earlier iterations folded)",
        }
        fold_pairs = [(assistant_msg, user_msg)]
        # Pitfall 4: never let the fold cost more than the full pairs it folds.
        full_pairs = [_full_renderer()(ir) for ir in iter_recs]
        if self._estimate(fold_pairs) > self._estimate(full_pairs):
            return full_pairs
        return fold_pairs

    # -- packing -------------------------------------------------------

    def _assemble(
        self,
        iters: list[Any],
        fold_pairs: list[tuple[dict, dict]],
        fold_upto: int,
        recent_full_k: int,
    ) -> list[tuple[dict, dict]]:
        full_start = len(iters) - recent_full_k
        serialize = _full_renderer()
        pairs = list(fold_pairs)
        pairs.extend(self._render_iter_digest(p) for p in iters[fold_upto:full_start])
        pairs.extend(serialize(p) for p in iters[full_start:])
        return pairs

    def pack(
        self,
        iter_records: list[Any],
        packing_budget: int,
        profile: PackingProfile,
    ) -> list[tuple[dict, dict]]:
        n = len(iter_records)
        serialize = _full_renderer()
        if not profile.enabled:
            # No-op below threshold: verbatim full replay, byte-identical.
            return [serialize(p) for p in iter_records]
        if n <= profile.recent_full_k:
            full_pairs = [serialize(p) for p in iter_records]
            return self._fit_to_budget(full_pairs, iter_records, packing_budget)

        if not self._initialized:
            # First packing call seeds the fold boundary age-based; this
            # is the baseline the stable-region hash is measured against.
            fold_upto = max(0, n - profile.digest_cutoff_m)
            self._stable_pairs = self._render_fold_summary(iter_records[:fold_upto])
            self._stable_upto = fold_upto
            self._initialized = True

        pairs = self._assemble(
            iter_records, self._stable_pairs, self._stable_upto, profile.recent_full_k
        )
        est = self._estimate(pairs)
        high = profile.high_water * packing_budget
        if est < high and est <= packing_budget:
            # Below high-water: hold the frozen fold (append-only stable
            # region); only the digest/full tail slides.
            return self._fit_to_budget(pairs, iter_records, packing_budget)

        # Recompaction: re-fold age-based, then absorb digests oldest-first
        # until the estimate drops to the low-water target (hysteresis).
        target = min(profile.low_water * packing_budget, packing_budget)
        fold_upto = max(self._stable_upto, n - profile.digest_cutoff_m, 0)
        max_fold = n - profile.recent_full_k  # the newest K are never folded
        while True:
            fold_pairs = self._render_fold_summary(iter_records[:fold_upto])
            pairs = self._assemble(
                iter_records, fold_pairs, fold_upto, profile.recent_full_k
            )
            est = self._estimate(pairs)
            if est <= target or fold_upto >= max_fold:
                break
            fold_upto += 1
        self._stable_pairs = fold_pairs
        self._stable_upto = fold_upto
        self._recompactions += 1
        return self._fit_to_budget(pairs, iter_records, packing_budget)

    def stable_region_hash(self) -> str:
        """SHA-256 of the frozen stable-region pairs (change == recompaction)."""
        flat = [msg for pair in self._stable_pairs for msg in pair]
        return hashlib.sha256(
            json.dumps(flat, sort_keys=True).encode()
        ).hexdigest()
