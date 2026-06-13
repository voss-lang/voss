"""MemoryStore: orchestrator over voss_runtime.memory + .voss/memory/ filesystem mirror.

Composition (not subclassing) of voss_runtime types per Req 7 grep gate.
Owned by M8-02 (MEM-03 + MEM-07). Lazy chroma init per Pitfall 4.
"""
from __future__ import annotations

import dataclasses
import fnmatch
import hashlib
import json
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
_VOSS_MEMORY_GITIGNORE = "chroma/\n.locks/\n.tombstones.jsonl\n"


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

        files.sort(key=lambda p: p.stat().st_mtime)
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
        body = (
            "---\n"
            f"id: {path.stem}\n"
            f"related_session: {session_id}\n"
            f"created_at: {ts}\n"
            "---\n\n"
            f"{text}\n"
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
        body = (
            "---\n"
            f"id: {path.stem}\n"
            "status: active\n"
            f"related_session: {session_id}\n"
            f"evidence_turn_idx: {candidate.evidence_turn_idx}\n"
            f"confidence: {candidate.confidence:.2f}\n"
            f"created_at: {ts}\n"
            "---\n\n"
            f"# {candidate.statement}\n\n"
            f"## Evidence\n\n> {candidate.evidence_quote}\n"
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
            return bm25_hits[:top_k]
        try:
            chroma_hits = self._chroma_recall(chroma, query, top_k=recall_k, source=source)
        except Exception as exc:  # noqa: BLE001 — chroma can raise on malformed query
            print(f"memory: chroma recall failed ({exc}); falling back to BM25", file=sys.stderr)
            return bm25_hits[:top_k]
        return self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)

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
