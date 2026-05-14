"""MemoryStore: orchestrator over voss_runtime.memory + .voss/memory/ filesystem mirror.

Composition (not subclassing) of voss_runtime types per Req 7 grep gate.
Owned by M8-02 (MEM-03 + MEM-07). Lazy chroma init per Pitfall 4.
"""
from __future__ import annotations

import dataclasses
import fnmatch
import json
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import portalocker

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


def make_id(source: str, locator: str, seq: int | None = None) -> str:
    """D-04 composite ID format <source>:<locator>:<seq>."""
    if seq is None:
        return f"{source}:{locator}"
    return f"{source}:{locator}:{seq:03d}"


class MemoryStore:
    def __init__(self, cwd: Path, *, cap_bytes: int = DEFAULT_CAP_BYTES) -> None:
        self.cwd = cwd
        self.cap_bytes = cap_bytes
        self.root = cwd / ".voss" / "memory"
        self._chroma: Optional[SemanticMemory] = None
        self._chroma_unavailable = False
        self._size_cache: dict[str, int] = {}
        self._session_id: Optional[str] = None

    # ------------------------------------------------------------------
    # bind / layout
    # ------------------------------------------------------------------

    def bind(self, *, session_id: str) -> "MemoryStore":
        """Attach a session id; ensures the .voss/memory/ layout exists.

        Pitfall 6: session_id is supplied by the caller from record.id; no
        SessionRecord field dependency. Pitfall 4: chromadb is NOT imported
        here — first call to recall/write lazily probes.
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
            print(f"memory: chroma init failed ({exc}); using keyword fallback", file=sys.stderr)
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

    def _maybe_evict(self, source: str) -> None:
        """M8-06: per-source quota check + oldest-first eviction (D-14/D-16).

        Currently a no-op; M8-03 establishes the call site contract.
        """
        return

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
        with self._lock("turns") as lock:
            if lock is None:
                return
            self._maybe_evict("turns")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                f.write(json.dumps({"ts": ts, "role": role, "content": content, "turn_idx": turn_idx}) + "\n")
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
        with self._lock("ledgers") as lock:
            if lock is None:
                return
            self._maybe_evict("ledgers")
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                f.write(json.dumps({"ts": ts, "session_id": session_id, "run": data}, default=str) + "\n")
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
            self._maybe_evict("notes")
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
            self._maybe_evict("conventions")
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
        chroma = self._maybe_chroma()
        if chroma is not None:
            try:
                return self._chroma_recall(chroma, query, top_k=top_k, source=source)
            except Exception as exc:  # noqa: BLE001 — chroma can raise on malformed query
                print(f"memory: chroma recall failed ({exc}); falling back to keyword", file=sys.stderr)
        return self._keyword_scan(query, top_k=top_k, source=source)

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

    def _keyword_scan(
        self,
        query: str,
        *,
        top_k: int,
        source: str | None,
    ) -> list[Hit]:
        terms = [t.lower() for t in query.split() if t]
        if not terms:
            return []
        wanted_sources = _SOURCES
        if source is not None:
            singular = source.rstrip("s") if source.endswith("s") else source
            wanted_sources = tuple(
                s for s in _SOURCES if s == source or s.rstrip("s") == singular
            )
        tombstoned = self._load_tombstones()
        candidates: list[tuple[float, Hit]] = []
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
                    candidates.extend(
                        self._scan_jsonl(src, path, terms, tombstoned)
                    )
                    continue
                try:
                    text = path.read_text(errors="ignore")
                except OSError:
                    continue
                lower = text.lower()
                score = sum(lower.count(t) for t in terms)
                if score <= 0:
                    continue
                locator = self._locator_from_path(src, path)
                if locator in tombstoned:
                    continue
                candidates.append(
                    (
                        float(score),
                        Hit(
                            source=src.rstrip("s") if src != "ledgers" else "ledger",
                            locator=locator,
                            score=float(score),
                            excerpt=text[:200],
                            session_id=None,
                            ts=None,
                        ),
                    )
                )
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in candidates[:top_k]]

    def _scan_jsonl(
        self,
        src: str,
        path: Path,
        terms: list[str],
        tombstoned: set[str],
    ) -> list[tuple[float, Hit]]:
        """Score JSONL files line-by-line so turn / ledger seq aligns with composite IDs."""
        try:
            raw = path.read_text(errors="ignore")
        except OSError:
            return []
        stem = path.stem
        out: list[tuple[float, Hit]] = []
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
            lower = content.lower()
            score = sum(lower.count(t) for t in terms)
            if score <= 0:
                continue
            out.append(
                (
                    float(score),
                    Hit(
                        source=source_label,
                        locator=locator,
                        score=float(score),
                        excerpt=content[:200],
                        session_id=session_id,
                        ts=rec.get("ts"),
                    ),
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
        lines = ["# Memory store contents", ""]
        total_bytes = 0
        total_files = 0
        tombstoned = self._load_tombstones()
        for src in _SOURCES:
            if source is not None and source != src:
                continue
            src_dir = self.root / src
            if not src_dir.exists():
                lines.append(f"- {src}: 0 files, 0 bytes")
                continue
            files = [p for p in src_dir.rglob("*") if p.is_file()]
            n = len(files)
            size = sum(p.stat().st_size for p in files)
            total_bytes += size
            total_files += n
            lines.append(f"- {src}: {n} files, {size} bytes")
        lines.append("")
        lines.append(f"Total: {total_files} files, {total_bytes} bytes")
        lines.append(f"Tombstoned: {len(tombstoned)} ids")
        return "\n".join(lines) + "\n"

    def vacuum(self) -> int:
        """Compact chroma + delete tombstoned entries; returns bytes reclaimed.

        Owned by M8-06.
        """
        raise NotImplementedError("M8-06")
