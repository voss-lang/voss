"""MemoryStore: orchestrator over voss_runtime.memory + .voss/memory/ filesystem mirror.

Composition (not subclassing) of voss_runtime types per Req 7 grep gate.
Owned by M8-02 (MEM-03 + MEM-07). Lazy chroma init per Pitfall 4.
"""
from __future__ import annotations

import dataclasses
import fnmatch
import hashlib
import json
import math
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import portalocker
from rank_bm25 import BM25Okapi

from voss.template_render import render_package_template
from voss_runtime.memory import EpisodicMemory, SemanticMemory, Turn  # noqa: F401  (imported for downstream waves)


SOURCE_QUOTAS = {
    "turns": 0.60,
    "ledgers": 0.20,
    "decisions": 0.10,
    "conventions": 0.10,
}

DEFAULT_CAP_BYTES = 100 * 1024 * 1024

_SOURCES = ("turns", "ledgers", "decisions", "conventions", "notes")
_VOSS_MEMORY_GITIGNORE = "chroma/\n.locks/\n.tombstones.jsonl\n.retrieval.jsonl\n.reindex-manifest.json\n"


@dataclass
class Hit:
    source: str
    locator: str
    score: float
    excerpt: str
    session_id: str | None = None
    ts: str | None = None
    # V19 VSEM-01: code-chunk hits carry file:line locators through RRF fusion.
    # Memory hits leave both None; appended after existing optionals so
    # positional construction at existing call sites is unaffected.
    line_start: int | None = None
    line_end: int | None = None


@dataclass
class _BM25Candidate:
    hit: Hit
    text: str


@dataclass
class ReindexResult:
    """Outcome of MemoryStore.reindex (VRNK-05); the CLI maps this to exit codes.

    ``stale`` = locators whose mirror file drifted from / is missing in the
    manifest. ``reembedded`` = count upserted into chroma (0 for a --check pass).
    ``chroma_available`` = False when chroma is absent (clean no-op, exit 0).
    """

    stale: list[str]
    reembedded: int
    chroma_available: bool


def make_id(source: str, locator: str, seq: int | None = None) -> str:
    """D-04 composite ID format <source>:<locator>:<seq>."""
    if seq is None:
        return f"{source}:{locator}"
    return f"{source}:{locator}:{seq:03d}"


def _repo_id(cwd: Path) -> str:
    """Stable, human-readable repo identifier for provenance metadata."""
    resolved = cwd.resolve()
    digest = hashlib.sha256(str(resolved).encode()).hexdigest()[:8]
    return f"{resolved.name}-{digest}"


def _file_hash(text: str) -> str:
    """sha256 of file text — reindex drift manifest key (mirrors V19 semantic_index)."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _global_memory_root() -> Path | None:
    """Resolve global memory root; return None when HOME is unavailable."""
    voss_home = os.environ.get("VOSS_HOME")
    if voss_home:
        return Path(voss_home).resolve() / "memory"
    try:
        return Path.home() / ".voss" / "memory"
    except RuntimeError:
        return None


def make_global_store() -> "MemoryStore | None":
    """Create the global MemoryStore when enabled and resolvable."""
    from voss.harness.config import get_global_memory_enabled

    try:
        home = Path.home()
    except RuntimeError:
        return None
    if not get_global_memory_enabled():
        return None
    root = _global_memory_root()
    if root is None:
        return None
    return MemoryStore(home, root_override=root)


def _bm25_tokenize(text: str) -> list[str]:
    """Tokenize memory text for lexical recall, including code-like symbols."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    spaced = re.sub(r"[_\-\./\\]+", " ", spaced)
    spaced = re.sub(r"[^\w\s]", " ", spaced)
    return [tok for tok in spaced.lower().split() if tok]


class MemoryStore:
    def __init__(
        self,
        cwd: Path,
        *,
        cap_bytes: int = DEFAULT_CAP_BYTES,
        root_override: Path | None = None,
    ) -> None:
        self.cwd = cwd
        self.cap_bytes = cap_bytes
        self.root = root_override if root_override is not None else cwd / ".voss" / "memory"
        self._chroma: Optional[SemanticMemory] = None
        self._chroma_unavailable = False
        self._size_cache: dict[str, int] = {}
        self._session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # bind / layout
    # ------------------------------------------------------------------

    def bind(self, *, session_id: str) -> "MemoryStore":
        """Attach a session id; ensures the .voss/memory/ layout exists.

        # Pitfall 6: session_id is supplied by the caller from record.id; no
        # SessionRecord field dependency.
        Pitfall 4: chromadb is NOT imported here — first call to recall/write
        lazily probes.
        """
        self._session_id = session_id
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in _SOURCES:
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        (self.root / "chroma").mkdir(parents=True, exist_ok=True)
        (self.root / ".locks").mkdir(parents=True, exist_ok=True)
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_VOSS_MEMORY_GITIGNORE)
        return self

    # ------------------------------------------------------------------
    # lazy chroma probe + lock + eviction stub
    # ------------------------------------------------------------------

    def _maybe_chroma(self) -> "SemanticMemory | None":
        if self._chroma is not None:
            return self._chroma
        if self._chroma_unavailable:
            return None
        try:
            chroma = SemanticMemory(
                persist_dir=str(self.root / "chroma"),
                collection_name="voss_memory",
            )
        except (ModuleNotFoundError, ImportError):
            self._chroma_unavailable = True
            return None
        except Exception as exc:  # noqa: BLE001 — defensive; chroma init can raise OS/permission errors
            print(f"memory: chroma init failed ({exc}); using BM25 fallback", file=sys.stderr)
            self._chroma_unavailable = True
            return None
        self._chroma = chroma
        return chroma

    @contextmanager
    def _lock(self, source: str):
        """Per-source advisory lock via portalocker; yields None on contention."""
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".locks").mkdir(parents=True, exist_ok=True)
        lock_path = self.root / ".locks" / f"{source}.lock"
        try:
            with portalocker.Lock(
                str(lock_path),
                mode="a",
                flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
                timeout=0,
            ) as fh:
                yield fh
        except portalocker.exceptions.LockException:
            print(f"memory.{source} busy — skipping write", file=sys.stderr)
            yield None

    def _maybe_evict(self, source: str, *, est_bytes: int = 0) -> None:
        """Per-source quota check + oldest-first eviction (D-14/D-16).

        On every write, compute current source bytes; if current + est_bytes
        would exceed the source's quota, delete oldest files (by mtime) until
        under quota OR the source has no more files.

        decisions/ is a mirror of COG-06 output; eviction stays out — see
        M8-06 plan Warning 5.
        """
        if source == "decisions":
            return
        if self.cap_bytes <= 0:
            return

        cfg = self._load_memory_config()
        quota_map = cfg.get("quota_pct", {}) or {}
        quota_pct = quota_map.get(source, SOURCE_QUOTAS.get(source, 0.0))
        if quota_pct <= 0:
            return
        quota_bytes = int(self.cap_bytes * quota_pct)

        source_dir = self.root / source
        if not source_dir.exists():
            return

        files = [p for p in source_dir.rglob("*") if p.is_file()]
        current_bytes = sum(p.stat().st_size for p in files)
        if current_bytes + est_bytes <= quota_bytes:
            self._size_cache[source] = current_bytes
            return

        # VRNK-04 retrieval-aware eviction: drop pinned rows from the candidate
        # set (never deleted, but they still count toward quota bytes), then sort
        # by _eviction_key — never-retrieved/stale evict before recently-retrieved;
        # mtime ascending tie-break. With no telemetry sidecar every file lands in
        # bucket 0 → the sort degrades to the pre-V23 mtime ordering.
        telemetry = self._load_telemetry_compacted()
        pins = self._load_pins()
        files = [f for f in files if self._locator_from_path(source, f) not in pins]
        files.sort(key=lambda p: self._eviction_key(p, telemetry))
        chroma = self._maybe_chroma()
        for oldest in files:
            try:
                size = oldest.stat().st_size
            except OSError:
                size = 0
            if chroma is not None:
                try:
                    chroma._collection.delete(where={"path": str(oldest)})
                except Exception:  # noqa: BLE001
                    pass
            try:
                oldest.unlink(missing_ok=True)
            except OSError:
                continue
            current_bytes -= size
            if current_bytes + est_bytes <= quota_bytes:
                break

        self._size_cache[source] = max(0, current_bytes)

    def _load_memory_config(self) -> dict:
        config_path = self.cwd / ".voss" / "config.yml"
        if not config_path.exists():
            return {}
        try:
            import yaml

            data = yaml.safe_load(config_path.read_text()) or {}
        except Exception:  # noqa: BLE001
            return {}
        memory = data.get("memory") if isinstance(data, dict) else None
        return memory if isinstance(memory, dict) else {}

    # ------------------------------------------------------------------
    # tombstones
    # ------------------------------------------------------------------

    @property
    def _tombstones_path(self) -> Path:
        return self.root / ".tombstones.jsonl"

    def _load_tombstones(self) -> set[str]:
        path = self._tombstones_path
        if not path.exists():
            return set()
        ids: set[str] = set()
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and "id" in rec:
                    ids.add(str(rec["id"]))
        except OSError:
            return set()
        return ids

    # ------------------------------------------------------------------
    # retrieval telemetry (VRNK-01) — sidecar append-log, never memory files
    # ------------------------------------------------------------------

    @property
    def _retrieval_path(self) -> Path:
        return self.root / ".retrieval.jsonl"

    def _record_telemetry(self, hits: list[Hit]) -> None:
        """Append one ``{locator, ts}`` event per hit to ``.retrieval.jsonl``.

        Agent-path only (wired at the ``memory_recall`` tool site); ``recall()``
        itself and every CLI path never call this. Writes ONLY the sidecar —
        never a memory file, so eviction's mtime ordering stays intact (D-01).
        Skip-on-contention (D-03): if the lock is held, drop this batch. Any fs
        error is swallowed so telemetry can never break a recall caller.
        """
        if not hits:
            return
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._lock("retrieval") as lock:
                if lock is None:
                    return
                path = self._retrieval_path
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a") as f:
                    for h in hits:
                        f.write(json.dumps({"locator": h.locator, "ts": ts}) + "\n")
                path.chmod(0o600)
        except OSError:
            return

    def _load_telemetry_compacted(self) -> dict:
        """Fold ``.retrieval.jsonl`` → ``{locator: {retrieval_count, count, last_retrieved}}``.

        Corrupt-line tolerant (template: :meth:`_load_tombstones`). Reads BOTH
        raw event lines ``{locator, ts}`` and post-vacuum compacted lines
        ``{locator, retrieval_count, last_retrieved}`` so a vacuumed file still
        folds (idempotent). ``last_retrieved`` is the max ISO ts — string max is
        correct for fixed-width ISO ``timespec="seconds"`` (D-15). ``retrieval_count``
        is the SPEC field name; ``count`` is an alias the rescore (V23-04) and
        eviction (V23-05) readers consume. Returns ``{}`` on missing/all-corrupt.
        """
        path = self._retrieval_path
        if not path.exists():
            return {}
        try:
            lines = path.read_text().splitlines()
        except OSError:
            return {}
        folded: dict[str, dict] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            locator = rec.get("locator")
            if not locator:
                continue
            if "ts" in rec:  # raw event line
                n = 1
                ts = str(rec.get("ts") or "")
            else:  # compacted line
                raw_n = rec.get("retrieval_count", rec.get("count", 0))
                try:
                    n = int(raw_n)
                except (TypeError, ValueError):
                    continue
                ts = str(rec.get("last_retrieved") or "")
            agg = folded.setdefault(locator, {"count": 0, "last_retrieved": ""})
            agg["count"] += n
            if ts > agg["last_retrieved"]:
                agg["last_retrieved"] = ts
        return {
            loc: {
                "retrieval_count": agg["count"],
                "count": agg["count"],
                "last_retrieved": agg["last_retrieved"],
            }
            for loc, agg in folded.items()
        }

    def _vacuum_telemetry(self) -> None:
        """Rewrite ``.retrieval.jsonl`` to one compacted line per locator.

        Under the retrieval lock (skip-on-contention). Idempotent: re-reading
        after vacuum yields identical counts/timestamps (compacted lines are
        re-foldable by :meth:`_load_telemetry_compacted`).
        """
        path = self._retrieval_path
        if not path.exists():
            return
        try:
            with self._lock("retrieval") as lock:
                if lock is None:
                    return
                compacted = self._load_telemetry_compacted()
                if not compacted:
                    return
                lines = [
                    json.dumps(
                        {
                            "locator": loc,
                            "retrieval_count": agg["retrieval_count"],
                            "last_retrieved": agg["last_retrieved"],
                        }
                    )
                    for loc, agg in compacted.items()
                ]
                tmp = path.with_suffix(path.suffix + ".tmp")
                tmp.write_text("\n".join(lines) + "\n")
                tmp.chmod(0o600)
                os.replace(tmp, path)
        except OSError:
            return

    # ------------------------------------------------------------------
    # writes
    # ------------------------------------------------------------------

    def write_turn(
        self,
        *,
        role: str,
        content: str,
        session_id: str,
        turn_idx: int,
    ) -> None:
        path = self.root / "turns" / f"{session_id}.jsonl"
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        composite_id = make_id("turn", session_id, seq=turn_idx)
        line = json.dumps({"ts": ts, "role": role, "content": content, "turn_idx": turn_idx}) + "\n"
        with self._lock("turns") as lock:
            if lock is None:
                return
            self._maybe_evict("turns", est_bytes=len(line.encode()))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                f.write(line)
            path.chmod(0o600)
        chroma = self._maybe_chroma()
        if chroma is not None:
            chroma.add(
                text=content,
                metadata={
                    "source_type": "turn",
                    "session_id": session_id,
                    "path": str(path),
                    "ts": ts,
                    "tombstoned": False,
                },
                id=composite_id,
            )

    def write_ledger(self, run, *, session_id: str) -> None:
        run_id = (
            getattr(run, "id", None)
            or (run.get("id") if isinstance(run, dict) else None)
            or f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        )
        path = self.root / "ledgers" / f"{run_id}.jsonl"
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        composite_id = make_id("ledger", run_id, seq=0)
        if dataclasses.is_dataclass(run):
            data = dataclasses.asdict(run)
        elif isinstance(run, dict):
            data = run
        else:
            data = {
                k: getattr(run, k)
                for k in ("changed", "inspected", "avoided", "decisions", "goal", "diff_summary")
                if hasattr(run, k)
            }
        text_blob = json.dumps(data, default=str)
        line = json.dumps({"ts": ts, "session_id": session_id, "run": data}, default=str) + "\n"
        with self._lock("ledgers") as lock:
            if lock is None:
                return
            self._maybe_evict("ledgers", est_bytes=len(line.encode()))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                f.write(line)
            path.chmod(0o600)
        chroma = self._maybe_chroma()
        if chroma is not None:
            chroma.add(
                text=text_blob,
                metadata={
                    "source_type": "ledger",
                    "session_id": session_id,
                    "path": str(path),
                    "ts": ts,
                    "tombstoned": False,
                },
                id=composite_id,
            )

    def write_note(self, text: str, *, session_id: str) -> Path:
        from .cognition import reserve_filename, slug

        notes_dir = self.root / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path = reserve_filename(notes_dir, slug(text[:40]))
        composite_id = make_id("note", path.stem)
        body = render_package_template(
            "voss",
            "templates/memory/note.md.jinja",
            {
                "id": path.stem,
                "session_id": session_id,
                "created_at": ts,
                "text": text,
            },
        )
        with self._lock("notes") as lock:
            if lock is None:
                return path
            self._maybe_evict("notes", est_bytes=len(body.encode()))
            path.write_text(body)
            path.chmod(0o600)
        chroma = self._maybe_chroma()
        if chroma is not None:
            chroma.add(
                text=text,
                metadata={
                    "source_type": "note",
                    "session_id": session_id,
                    "path": str(path),
                    "ts": ts,
                    "tombstoned": False,
                },
                id=composite_id,
            )
        return path

    def write_convention(self, candidate, *, session_id: str) -> Path:
        from .cognition import reserve_filename, slug

        conventions_dir = self.root / "conventions"
        conventions_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path = reserve_filename(conventions_dir, slug(candidate.statement[:40]))
        composite_id = make_id("convention", path.stem)
        body = render_package_template(
            "voss",
            "templates/memory/convention.md.jinja",
            {
                "id": path.stem,
                "session_id": session_id,
                "evidence_turn_idx": candidate.evidence_turn_idx,
                "confidence": f"{candidate.confidence:.2f}",
                "created_at": ts,
                "statement": candidate.statement,
                "evidence_quote": candidate.evidence_quote,
            },
        )
        with self._lock("conventions") as lock:
            if lock is None:
                return path
            self._maybe_evict("conventions", est_bytes=len(body.encode()))
            path.write_text(body)
            path.chmod(0o600)
        chroma = self._maybe_chroma()
        if chroma is not None:
            chroma.add(
                text=candidate.statement,
                metadata={
                    "source_type": "convention",
                    "session_id": session_id,
                    "path": str(path),
                    "ts": ts,
                    "tombstoned": False,
                    "evidence_turn_idx": candidate.evidence_turn_idx,
                    "confidence": candidate.confidence,
                },
                id=composite_id,
            )
        return path

    # ------------------------------------------------------------------
    # recall
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        source: str | None = None,
    ) -> list[Hit]:
        recall_k = max(top_k * 3, top_k)
        bm25_hits = self._bm25_recall(query, top_k=recall_k, source=source)
        chroma = self._maybe_chroma()
        if chroma is None:
            fused = bm25_hits[:top_k]
        else:
            try:
                chroma_hits = self._chroma_recall(chroma, query, top_k=recall_k, source=source)
            except Exception as exc:  # noqa: BLE001 — chroma can raise on malformed query
                print(f"memory: chroma recall failed ({exc}); falling back to BM25", file=sys.stderr)
                fused = bm25_hits[:top_k]
            else:
                fused = self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)
        # VRNK-03 rescore hook (config-gated, default OFF). When disabled, `fused`
        # is returned untouched → byte-identical to the pre-V23 path (no extra
        # sort/copy/mutation). Routes BOTH the fused and BM25-only-degraded paths.
        cfg = self._load_memory_config()
        if cfg.get("rescore", False):
            fused = self._rescore(fused, cfg)
        return fused

    @staticmethod
    def _rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60) -> list[Hit]:
        scores: dict[str, float] = {}
        carriers: dict[str, Hit] = {}
        for ranking in rankings:
            for rank, hit in enumerate(ranking, start=1):
                carriers.setdefault(hit.locator, hit)
                scores[hit.locator] = scores.get(hit.locator, 0.0) + (1.0 / (k + rank))

        fused: list[Hit] = []
        for locator, score in scores.items():
            carrier = carriers[locator]
            fused.append(dataclasses.replace(carrier, score=score))

        fused.sort(key=lambda hit: (-hit.score, hit.locator))
        return fused[:top_k]

    def _rescore(self, hits: list[Hit], cfg: dict) -> list[Hit]:
        """Deterministic recency×frequency multiplicative boost (VRNK-03).

        Empty telemetry → input returned unchanged (no-op; SPEC constraint). The
        boost is bounded in ``[1.0, 1 + w_recency + w_freq]`` so similarity still
        dominates ranking (D-13). Missing ``last_retrieved`` → recency 0.0
        (Pitfall 5). Deterministic: same hits + same telemetry → identical output,
        ties broken by locator. Pure — no filesystem writes.
        """
        telemetry = self._load_telemetry_compacted()
        if not telemetry:
            return hits

        def _f(key: str, default: float) -> float:
            try:
                return float(cfg.get(key, default))
            except (TypeError, ValueError):
                return default

        half_life = max(_f("rescore_half_life_days", 7.0), 0.001)
        freq_scale = max(_f("rescore_freq_scale", 10.0), 1.0)
        w_recency = _f("rescore_w_recency", 0.3)
        w_freq = _f("rescore_w_freq", 0.2)
        now = datetime.now(timezone.utc)

        rescored: list[Hit] = []
        for hit in hits:
            entry = telemetry.get(hit.locator)
            if entry is None:
                rescored.append(hit)
                continue
            try:
                count = int(entry.get("count", 0))
            except (TypeError, ValueError):
                count = 0
            last_ts = entry.get("last_retrieved") or ""
            recency = 0.0
            if last_ts:
                try:
                    days_ago = max(
                        0.0,
                        (now - datetime.fromisoformat(last_ts)).total_seconds() / 86400.0,
                    )
                    recency = math.exp(-days_ago / half_life)
                except (ValueError, TypeError):
                    recency = 0.0  # Pitfall 5: corrupt/naive ts → no recency boost
            freq = math.log1p(count) / math.log1p(freq_scale)
            boost = 1.0 + w_recency * recency + w_freq * min(freq, 1.0)
            rescored.append(dataclasses.replace(hit, score=hit.score * boost))
        rescored.sort(key=lambda h: (-h.score, h.locator))
        return rescored

    def _chroma_recall(self, chroma, query, *, top_k, source) -> list[Hit]:
        where: dict[str, object] = {"tombstoned": False}
        if source:
            singular = source.rstrip("s") if source.endswith("s") else source
            where["source_type"] = singular
        result = chroma._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        out: list[Hit] = []
        tombstoned = self._load_tombstones()
        for idx, locator in enumerate(ids):
            if locator in tombstoned:
                continue
            meta = metas[idx] if idx < len(metas) and metas[idx] else {}
            doc = docs[idx] if idx < len(docs) else ""
            dist = dists[idx] if idx < len(dists) else 1.0
            try:
                score = max(0.0, 1.0 - float(dist))
            except (TypeError, ValueError):
                score = 0.0
            out.append(
                Hit(
                    source=meta.get("source_type", "unknown"),
                    locator=locator,
                    score=score,
                    excerpt=(doc or "")[:200],
                    session_id=meta.get("session_id"),
                    ts=meta.get("ts"),
                )
            )

        # VRNK-02 chroma absolute similarity floor (pre-fusion, D-04/D-06):
        # score = max(0.0, 1 - distance); drop hits < chroma_floor (default 0.25,
        # NOT froots' 0.45). chroma_floor=0 disables → all nearest neighbors
        # retained (pre-V23). This is what turns a junk query into 0 hits instead
        # of top_k nearest-anything.
        cfg = self._load_memory_config()
        try:
            chroma_floor = float(cfg.get("chroma_floor", 0.25))
        except (TypeError, ValueError):
            chroma_floor = 0.25
        if chroma_floor > 0:
            out = [h for h in out if h.score >= chroma_floor]
        return out

    def _bm25_corpus(self, source: str | None) -> list[_BM25Candidate]:
        wanted_sources = _SOURCES
        if source is not None:
            singular = source.rstrip("s") if source.endswith("s") else source
            wanted_sources = tuple(
                s for s in _SOURCES if s == source or s.rstrip("s") == singular
            )

        tombstoned = self._load_tombstones()
        candidates: list[_BM25Candidate] = []
        for src in wanted_sources:
            src_dir = self.root / src
            if not src_dir.exists():
                continue
            for path in src_dir.rglob("*"):
                if not path.is_file():
                    continue
                if path.name.startswith(".tombstones"):
                    continue
                if src in ("turns", "ledgers"):
                    candidates.extend(self._bm25_jsonl_candidates(src, path, tombstoned))
                    continue
                try:
                    text = path.read_text(errors="ignore")
                except OSError:
                    continue
                locator = self._locator_from_path(src, path)
                if locator in tombstoned:
                    continue
                source_label = src.rstrip("s") if src != "ledgers" else "ledger"
                candidates.append(
                    _BM25Candidate(
                        hit=Hit(
                            source=source_label,
                            locator=locator,
                            score=0.0,
                            excerpt=text[:200],
                            session_id=None,
                            ts=None,
                        ),
                        text=text,
                    )
                )
        return candidates

    def _bm25_recall(
        self,
        query: str,
        *,
        top_k: int,
        source: str | None,
    ) -> list[Hit]:
        query_tokens = _bm25_tokenize(query)
        if not query_tokens:
            return []

        candidates = self._bm25_corpus(source)
        if not candidates:
            return []

        tokenized_corpus = [_bm25_tokenize(candidate.text) for candidate in candidates]
        if not any(tokenized_corpus):
            return []

        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(query_tokens)
        ranked: list[tuple[float, Hit]] = []
        query_token_set = set(query_tokens)
        for candidate, tokens, score in zip(candidates, tokenized_corpus, scores):
            score_float = float(score)
            if score_float <= 0 and query_token_set.intersection(tokens):
                # rank_bm25 can produce zero/negative IDF for tiny corpora
                # where every query term appears in every document. Keep
                # true lexical matches while still dropping no-overlap rows.
                score_float = float(len(query_token_set.intersection(tokens)))
            if score_float <= 0:
                continue
            ranked.append(
                (
                    score_float,
                    Hit(
                        source=candidate.hit.source,
                        locator=candidate.hit.locator,
                        score=score_float,
                        excerpt=candidate.hit.excerpt,
                        session_id=candidate.hit.session_id,
                        ts=candidate.hit.ts,
                    ),
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)

        # VRNK-02 BM25 relative-to-top floor (pre-fusion, D-05/D-06): drop rows
        # below bm25_floor_ratio of the top score. Guard top > 0 (Pitfall 4 — a
        # zero top would pass everything). ratio=0 disables → pre-V23 fill. The
        # tiny-corpus token-overlap rescue feeds positive scores that compare
        # naturally against the relative cutoff.
        cfg = self._load_memory_config()
        try:
            bm25_floor_ratio = float(cfg.get("bm25_floor_ratio", 0.1))
        except (TypeError, ValueError):
            bm25_floor_ratio = 0.1
        if ranked and ranked[0][0] > 0 and bm25_floor_ratio > 0:
            cutoff = ranked[0][0] * bm25_floor_ratio
            ranked = [(s, h) for s, h in ranked if s >= cutoff]

        return [hit for _, hit in ranked[:top_k]]

    def _bm25_jsonl_candidates(
        self,
        src: str,
        path: Path,
        tombstoned: set[str],
    ) -> list[_BM25Candidate]:
        """Build JSONL candidates line-by-line so locators remain forgettable."""
        try:
            raw = path.read_text(errors="ignore")
        except OSError:
            return []
        stem = path.stem
        out: list[_BM25Candidate] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if src == "turns":
                content = str(rec.get("content", ""))
                seq = int(rec.get("turn_idx", 0))
                source_label = "turn"
                locator = make_id("turn", stem, seq=seq)
                session_id = stem
            else:  # ledgers
                content = json.dumps(rec.get("run", rec), default=str)
                seq = 0
                source_label = "ledger"
                locator = make_id("ledger", stem, seq=seq)
                session_id = rec.get("session_id")
            if locator in tombstoned:
                continue
            out.append(
                _BM25Candidate(
                    hit=Hit(
                        source=source_label,
                        locator=locator,
                        score=0.0,
                        excerpt=content[:200],
                        session_id=session_id,
                        ts=rec.get("ts"),
                    ),
                    text=content,
                )
            )
        return out

    def _locator_from_path(self, source_dir: str, path: Path) -> str:
        """Reconstruct a composite-id-like locator from a per-source on-disk file."""
        stem = path.stem
        if source_dir == "turns":
            return make_id("turn", stem, seq=0)
        if source_dir == "ledgers":
            return make_id("ledger", stem, seq=0)
        if source_dir == "decisions":
            return make_id("decision", str(path.relative_to(self.root.parent)))
        if source_dir == "conventions":
            return make_id("convention", stem)
        if source_dir == "notes":
            return make_id("note", stem)
        return f"{source_dir}:{stem}"

    # ------------------------------------------------------------------
    # forget / summary / vacuum
    # ------------------------------------------------------------------

    def forget(self, pattern: str, *, confirm: bool = False) -> int:
        if "*" in pattern and pattern.strip() == "*" and not confirm:
            return 0
        candidate_ids: set[str] = set()
        for src in _SOURCES:
            src_dir = self.root / src
            if not src_dir.exists():
                continue
            for path in src_dir.rglob("*"):
                if not path.is_file():
                    continue
                if path.name.startswith(".tombstones"):
                    continue
                candidate_ids.add(self._locator_from_path(src, path))
        chroma = self._maybe_chroma()
        if chroma is not None:
            try:
                all_ids = chroma._collection.get().get("ids", [])
                candidate_ids.update(all_ids)
            except Exception:  # noqa: BLE001
                pass
        matched = [cid for cid in candidate_ids if fnmatch.fnmatchcase(cid, pattern)]
        if not matched:
            return 0
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock("forget") as lock:
            if lock is None:
                return 0
            tomb_path = self._tombstones_path
            tomb_path.parent.mkdir(parents=True, exist_ok=True)
            with tomb_path.open("a") as f:
                for mid in matched:
                    f.write(json.dumps({"id": mid, "tombstoned_at": ts}) + "\n")
            tomb_path.chmod(0o600)
        if chroma is not None:
            try:
                chroma._collection.update(
                    ids=matched,
                    metadatas=[{"tombstoned": True} for _ in matched],
                )
            except Exception:  # noqa: BLE001 — chroma update may fail on unknown ids
                pass
        return len(matched)

    def summary(self, *, source: str | None = None) -> str:
        total_bytes = 0
        total_files = 0
        tombstoned = self._load_tombstones()
        sources = []
        for src in _SOURCES:
            if source is not None and source != src:
                continue
            src_dir = self.root / src
            if not src_dir.exists():
                sources.append({"name": src, "files": 0, "bytes": 0})
                continue
            files = [p for p in src_dir.rglob("*") if p.is_file()]
            n = len(files)
            size = sum(p.stat().st_size for p in files)
            total_bytes += size
            total_files += n
            sources.append({"name": src, "files": n, "bytes": size})
        return render_package_template(
            "voss",
            "templates/memory/summary.md.jinja",
            {
                "sources": sources,
                "total_files": total_files,
                "total_bytes": total_bytes,
                "tombstoned_count": len(tombstoned),
            },
        )

    def vacuum(self) -> int:
        """Compact chroma + physically delete tombstoned entries; returns bytes reclaimed.

        Three passes inside per-source advisory locks:
          (i)  JSONL line-level compaction for turns/ and ledgers/ via
               atomic tmp + os.replace.
          (ii) Whole-file deletion for notes/ and conventions/.
          (iii) Chroma row delete via where={"tombstoned": True} (best effort).

        bytes_reclaimed counts only on-disk file shrinkage across .voss/memory/;
        chroma persist_dir reclaim is opaque and excluded.
        """
        bytes_before = self._tree_bytes()
        tomb_ids = self._load_tombstones()
        if not tomb_ids:
            chroma = self._maybe_chroma()
            if chroma is not None:
                try:
                    chroma._collection.delete(where={"tombstoned": True})
                except Exception as exc:  # noqa: BLE001
                    print(f"vacuum: chroma delete failed: {exc}", file=sys.stderr)
            self._vacuum_telemetry()
            return 0

        turn_ids: set[str] = set()
        ledger_ids: set[str] = set()
        note_ids: set[str] = set()
        convention_ids: set[str] = set()
        for cid in tomb_ids:
            head, _, _ = cid.partition(":")
            if head == "turn":
                turn_ids.add(cid)
            elif head == "ledger":
                ledger_ids.add(cid)
            elif head == "note":
                note_ids.add(cid)
            elif head == "convention":
                convention_ids.add(cid)

        # Pass (i): JSONL line-level compaction
        self._vacuum_jsonl("turns", turn_ids, lambda stem, idx: make_id("turn", stem, seq=idx))
        self._vacuum_jsonl("ledgers", ledger_ids, lambda stem, idx: make_id("ledger", stem, seq=idx))

        # Pass (ii): whole-file deletion for notes + conventions
        for cid in note_ids:
            _, _, locator = cid.partition(":")
            if not locator:
                continue
            path = self.root / "notes" / f"{locator}.md"
            if path.exists():
                path.unlink(missing_ok=True)
        for cid in convention_ids:
            _, _, locator = cid.partition(":")
            if not locator:
                continue
            path = self.root / "conventions" / f"{locator}.md"
            if path.exists():
                path.unlink(missing_ok=True)

        # Pass (iii): chroma where-filter delete
        chroma = self._maybe_chroma()
        if chroma is not None:
            try:
                chroma._collection.delete(where={"tombstoned": True})
            except Exception as exc:  # noqa: BLE001
                print(f"vacuum: chroma delete failed: {exc}", file=sys.stderr)

        # Pass (iv): compact retrieval telemetry sidecar (VRNK-01)
        self._vacuum_telemetry()

        # Truncate tombstones index (do not unlink — keeps layout stable)
        self._tombstones_path.write_text("")

        # Refresh size cache
        for src in _SOURCES:
            src_dir = self.root / src
            if not src_dir.exists():
                self._size_cache[src] = 0
                continue
            self._size_cache[src] = sum(
                p.stat().st_size for p in src_dir.rglob("*") if p.is_file()
            )

        bytes_after = self._tree_bytes()
        return max(0, bytes_before - bytes_after)

    def _vacuum_jsonl(self, source: str, id_set: set[str], id_factory) -> None:
        if not id_set:
            return
        src_dir = self.root / source
        if not src_dir.exists():
            return
        with self._lock(source) as lock:
            if lock is None:
                print(
                    f"vacuum: {source} busy; skipping JSONL compaction this pass",
                    file=sys.stderr,
                )
                return
            for jsonl_path in src_dir.rglob("*.jsonl"):
                stem = jsonl_path.stem
                try:
                    lines = jsonl_path.read_text().splitlines()
                except OSError:
                    continue
                kept: list[str] = []
                changed = False
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entry = json.loads(stripped)
                    except json.JSONDecodeError:
                        kept.append(line)
                        continue
                    turn_idx = int(entry.get("turn_idx", 0))
                    composite = id_factory(stem, turn_idx)
                    if composite in id_set:
                        changed = True
                        continue
                    kept.append(line)
                if not changed:
                    continue
                if not kept:
                    jsonl_path.unlink(missing_ok=True)
                    continue
                tmp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
                tmp_path.write_text("\n".join(kept) + "\n")
                tmp_path.chmod(0o600)
                os.replace(tmp_path, jsonl_path)

    def _tree_bytes(self) -> int:
        if not self.root.exists():
            return 0
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    # ------------------------------------------------------------------
    # pins (VRNK-04 eviction exemption + VRNK-06/07 injection/CLI) — COMMITTED
    # sidecar (.pins.json is NOT gitignored, D-02)
    # ------------------------------------------------------------------

    @property
    def _pins_path(self) -> Path:
        return self.root / ".pins.json"

    def _load_pins(self) -> set[str]:
        """Return the set of pinned locators from ``.pins.json``.

        On-disk schema ``{"pins": [{"locator": ..., "pinned_at": ISO}]}``.
        Missing / corrupt / wrong-shape → empty set (eviction proceeds normally).
        Pitfall 6: pinned locators MUST be stored as :meth:`_locator_from_path`
        output so the eviction exemption + injection lookups fire.
        """
        path = self._pins_path
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return set()
        if not isinstance(data, dict):
            return set()
        return {
            e["locator"]
            for e in data.get("pins", [])
            if isinstance(e, dict) and e.get("locator")
        }

    def _save_pins(self, pins) -> None:
        """Persist the committed ``.pins.json``.

        Accepts an iterable of locator strings or of ``{"locator", "pinned_at"}``
        dicts; preserves ``pinned_at`` so VRNK-07 list/show can render it. Pin
        locators MUST come from :meth:`_locator_from_path` (Pitfall 6).
        """
        entries: list[dict] = []
        for p in pins:
            if isinstance(p, dict) and p.get("locator"):
                entries.append(
                    {"locator": p["locator"], "pinned_at": p.get("pinned_at", "")}
                )
            elif isinstance(p, str) and p:
                entries.append({"locator": p, "pinned_at": ""})
        path = self._pins_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"pins": entries}))
        path.chmod(0o600)

    def _eviction_key(self, path: Path, telemetry: dict) -> tuple:
        """Sort key for retrieval-aware eviction (D-15): evict-first → evict-last.

        Bucket 0 (never retrieved, or telemetry without ``last_retrieved``) sorts
        before bucket 1 (retrieved), so cold files go first. Within bucket 1,
        ascending ``last_retrieved`` = stalest first. mtime ascending breaks ties
        in both buckets. Always a 3-tuple so cross-bucket comparison never errors.
        """
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        source = path.parent.name
        locator = self._locator_from_path(source, path)
        entry = telemetry.get(locator)
        if not entry or not entry.get("last_retrieved"):
            return (0, "", mtime)
        return (1, str(entry["last_retrieved"]), mtime)

    # ------------------------------------------------------------------
    # reindex / drift hygiene (VRNK-05) — chroma-only; sha256 manifest of the
    # file-based sources (notes/decisions/conventions, D-10)
    # ------------------------------------------------------------------

    @property
    def _reindex_manifest_path(self) -> Path:
        return self.root / ".reindex-manifest.json"

    def _load_reindex_manifest(self) -> dict:
        """relpath→sha256 manifest; missing/corrupt → {} (everything stale, D-11)."""
        path = self._reindex_manifest_path
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_reindex_manifest(self, data: dict) -> None:
        path = self._reindex_manifest_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=0, sort_keys=True))
        path.chmod(0o600)

    def _file_based_sources(self) -> list[Path]:
        """Files under notes/ decisions/ conventions/ only (turns/ledgers excluded, D-10)."""
        out: list[Path] = []
        for src in ("notes", "decisions", "conventions"):
            src_dir = self.root / src
            if not src_dir.exists():
                continue
            for p in src_dir.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    out.append(p)
        return out

    def reindex(self, *, check: bool = False) -> ReindexResult:
        """Detect/repair chroma drift of the file-based mirror (VRNK-05).

        ``check=True`` is read-only: returns the stale/missing locator list (sha256
        vs manifest) WITHOUT re-embedding or writing the manifest. ``check=False``
        upserts each stale file into chroma (idempotent — upsert, NOT add) and
        rewrites the manifest, returning the re-embedded count. Chroma absent →
        a clean no-op (``chroma_available=False``); never raises.
        """
        chroma = self._maybe_chroma()
        if chroma is None:
            return ReindexResult(stale=[], reembedded=0, chroma_available=False)

        manifest = self._load_reindex_manifest()
        current: dict[str, str] = {}
        stale: list[tuple[Path, str, str, str]] = []  # (path, locator, text, src)
        for path in self._file_based_sources():
            rel = str(path.relative_to(self.root))
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            digest = _file_hash(text)
            current[rel] = digest
            if manifest.get(rel) != digest:
                src = path.parent.name
                locator = self._locator_from_path(src, path)
                stale.append((path, locator, text, src))

        stale_locators = [loc for _, loc, _, _ in stale]
        if check:
            return ReindexResult(stale=stale_locators, reembedded=0, chroma_available=True)

        reembedded = 0
        for path, locator, text, src in stale:
            source_type = "ledger" if src == "ledgers" else src.rstrip("s")
            try:
                chroma._collection.upsert(
                    ids=[locator],
                    documents=[text],
                    metadatas=[
                        {
                            "source_type": source_type,
                            "path": str(path),
                            "tombstoned": False,
                        }
                    ],
                )
                reembedded += 1
            except Exception as exc:  # noqa: BLE001 — one bad embed must not abort the pass
                print(f"reindex: upsert failed for {locator}: {exc}", file=sys.stderr)
        self._save_reindex_manifest(current)
        return ReindexResult(
            stale=stale_locators, reembedded=reembedded, chroma_available=True
        )

    # ------------------------------------------------------------------
    # pinned-tier injection text (VRNK-06) — always-injected, capped block
    # ------------------------------------------------------------------

    def _read_pinned_body(self, locator: str) -> str | None:
        """Resolve a pinned locator to its full on-disk memory body (D-08)."""
        prefix, _, rest = locator.partition(":")
        if not rest:
            return None
        sub = {"note": "notes", "convention": "conventions", "decision": "decisions"}.get(
            prefix
        )
        if sub is None:
            return None
        if prefix == "decision":
            path = self.root.parent / rest
        else:
            path = self.root / sub / f"{rest}.md"
        if not path.exists():
            return None
        try:
            return path.read_text(errors="ignore")
        except OSError:
            return None

    def render_pinned_memory_text(self, *, model: str) -> str:
        """Assemble the always-injected pinned-memory block (VRNK-06, D-07/D-08).

        Full body per pin (no excerpt truncation). Each item soft-capped to
        ``pin_item_cap_tokens`` (~200); the tier capped at ``pin_cap_tokens``
        (~500) keeping newest-pinned (``pinned_at`` desc) on overflow, dropping
        the oldest and warning once. Returns "" when there are no pins. Token
        accounting via the V18/V19 counter. Project store only — the global-store
        project-priority merge (D-09) lands post-V21.
        """
        # D-09 TODO(post-V21): merge global_store pins here; project pins win on
        # overflow. The V23-01 global xfail test un-xfails once V21 is merged.
        path = self._pins_path
        if not path.exists():
            return ""
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return ""
        raw = data.get("pins", []) if isinstance(data, dict) else []
        entries = [e for e in raw if isinstance(e, dict) and e.get("locator")]
        if not entries:
            return ""
        # Newest-pinned first so overflow drops the oldest (D-08).
        entries.sort(key=lambda e: str(e.get("pinned_at", "")), reverse=True)

        from voss.harness.agent import _default_token_count  # lazy: avoid import cycle

        cfg = self._load_memory_config()

        def _intcfg(key: str, default: int) -> int:
            try:
                return int(cfg.get(key, default))
            except (TypeError, ValueError):
                return default

        tier_cap = _intcfg("pin_cap_tokens", 500)
        item_cap = _intcfg("pin_item_cap_tokens", 200)

        kept: list[str] = []
        used = 0
        dropped = 0
        for idx, entry in enumerate(entries):
            body = self._read_pinned_body(entry["locator"])
            if not body:
                continue
            body = body.strip()
            if _default_token_count(body, model=model) > item_cap:
                body = body[: item_cap * 4].rstrip() + " …"  # per-item soft cap
            item_tokens = _default_token_count(body, model=model)
            if kept and used + item_tokens > tier_cap:
                dropped = len(entries) - idx  # remaining (oldest) all dropped
                break
            kept.append(body)
            used += item_tokens
        if dropped:
            print(
                f"memory: pinned tier over {tier_cap} tok — dropped {dropped} oldest pin(s)",
                file=sys.stderr,
            )
        if not kept:
            return ""
        return "## Pinned memory\n" + "\n\n".join(f"- {b}" for b in kept)
