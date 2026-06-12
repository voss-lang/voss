"""CodeIndex: semantic code memory over the M10 lexical index (V19 VSEM-01/02).

Symbol-aware chunks from the M10 SQLite symbols table, a content-hash manifest
for incremental (never-full) reindex, a `voss_code` Chroma collection via the
reused SemanticMemory wrapper, and RRF(BM25+vector) query that degrades to
BM25-only when Chroma is absent.

Consume-not-modify boundary: the M10 db is opened read-only (SELECT only).
All artifacts live under `cwd/.voss-cache/code/` (derived cache — safe to rm).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sqlite3
import sys
import threading
from pathlib import Path

from voss.harness.code.index import LANGUAGE_EXTS, _discover_files, _get_db_path
from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize
from voss_runtime.memory import SemanticMemory  # noqa: F401  (lazy use in _maybe_semantic)

# MiniLM max_seq_length=256 tokens (~512 chars); 800-char regions sub-split
# so no chunk silently truncates in the embedding window (Pitfall 5).
_MAX_CHUNK_CHARS = 800


def _chunk_id(rel_path: str, seq: int) -> str:
    """D-04 composite id: the `code:` prefix can never collide with turn:/note: ids."""
    return f"code:{rel_path}:{seq:03d}"


def _split_oversize(
    start: int, end: int, lines: list[str], max_chars: int = _MAX_CHUNK_CHARS
) -> list[tuple[int, int, str]]:
    text = "".join(lines[start - 1 : end])
    if len(text) <= max_chars:
        return [(start, end, text)]
    step = max(1, (end - start + 1) // 2)
    mid = start + step
    return _split_oversize(start, mid, lines, max_chars) + _split_oversize(
        mid + 1, end, lines, max_chars
    )


def extract_chunks(db_path: Path, file_path: str, content: str) -> list[tuple[int, int, str]]:
    """(start_line, end_line, chunk_text) regions for one file, split on M10
    symbol boundaries: chunk = [symbol_start, next_symbol_start), preamble
    before the first symbol is its own chunk, zero-symbol files are one
    whole-file chunk (Pitfall 6)."""
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    starts: list[int] = []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                """SELECT s.line FROM symbols s
                   JOIN files f ON s.file_id = f.id
                   WHERE f.path = ? ORDER BY s.line""",
                (file_path,),
            ).fetchall()
        finally:
            conn.close()
        starts = sorted({int(r[0]) for r in rows if r[0] and 1 <= int(r[0]) <= total_lines})
    except sqlite3.Error:
        starts = []  # missing/unreadable M10 db → whole-file chunk

    if not starts:
        return _split_oversize(1, total_lines, lines)

    boundaries = starts + [total_lines + 1]
    chunks: list[tuple[int, int, str]] = []
    for i, start in enumerate(boundaries[:-1]):
        end = boundaries[i + 1] - 1
        chunks.extend(_split_oversize(start, end, lines))
    if starts[0] > 1:
        chunks = _split_oversize(1, starts[0] - 1, lines) + chunks
    return chunks


def _file_hash(content: str) -> str:
    # Identical call to M10 build_index so manifests stay consistent with files.hash.
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


def _effective_embedding_model() -> str:
    """The model name SemanticMemory._embedding_function would resolve to —
    tracked in the manifest so a model swap drops + rebuilds (Pitfall 1)."""
    from voss_runtime._config import get_config

    cfg = get_config()
    requested = cfg.default_embedding_model
    if requested.startswith("text-embedding-") and not os.environ.get("OPENAI_API_KEY"):
        requested = cfg.local_embedding_model
    return requested


def _manifest_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / "semantic-manifest.json"


def _load_manifest(cwd: Path) -> dict:
    path = _manifest_path(cwd)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(cwd: Path, data: dict) -> None:
    path = _manifest_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))


class CodeIndex:
    """Incremental semantic index over repo code chunks.

    One SemanticMemory (one Chroma client) per instance (Pitfall 3). All
    sentence-transformers cold-load happens lazily inside _maybe_semantic —
    never at import/__init__ (Pitfall 2; V19-03 runs build on a worker thread).
    """

    def __init__(self, cwd: Path) -> None:
        self.cwd = Path(cwd).resolve()
        self._sem: SemanticMemory | None = None
        self._unavailable = False
        self._bm25 = None
        # (chunk_id, text, rel_path, line_start, line_end) for the FULL current chunk set
        self._bm25_chunks: list[tuple[str, str, str, int, int]] = []

    # -- lazy chroma probe (mirror of MemoryStore._maybe_chroma) -----------

    def _maybe_semantic(self) -> "SemanticMemory | None":
        if self._sem is not None:
            return self._sem
        if self._unavailable:
            return None
        try:
            sem = SemanticMemory(
                persist_dir=str(self.cwd / ".voss-cache" / "code" / "chroma"),
                collection_name="voss_code",
            )
        except (ModuleNotFoundError, ImportError):
            self._unavailable = True
            return None
        except Exception as exc:  # noqa: BLE001 — defensive; chroma init can raise OS/permission errors
            print(f"code index: chroma init failed ({exc}); using BM25 fallback", file=sys.stderr)
            self._unavailable = True
            return None
        self._sem = sem
        return sem

    # -- manifest -----------------------------------------------------------

    def _load_manifest(self) -> dict:
        return _load_manifest(self.cwd)

    def _save_manifest(self, data: dict) -> None:
        _save_manifest(self.cwd, data)

    def _drop_collection(self, sem: "SemanticMemory") -> None:
        """Pitfall 1: embedding-model swap invalidates every stored vector."""
        try:
            sem._client.delete_collection("voss_code")
        except Exception:  # noqa: BLE001 — collection may not exist yet
            pass
        sem._collection = sem._client.get_or_create_collection(
            name="voss_code",
            embedding_function=sem._embedding_function(),
        )

    # -- build / incremental reindex ----------------------------------------

    def build(self, session_id: str | None = None) -> None:
        """Full-or-incremental build into the voss_code collection.

        Hash-unchanged files are skipped entirely (zero embedding calls —
        VSEM-02). `session_id` is accepted now so V19-06 can thread it into
        the enrichment ledger without a signature change.
        """
        cwd = self.cwd
        db_path = _get_db_path(cwd)
        files = sorted(
            (f for f in _discover_files(cwd) if f.suffix.lower() in LANGUAGE_EXTS),
            key=lambda p: str(p.relative_to(cwd)),
        )

        manifest = self._load_manifest()
        current_model = _effective_embedding_model()
        sem = self._maybe_semantic()
        if (
            manifest.get("embedding_model")
            and manifest["embedding_model"] != current_model
        ):
            if sem is not None:
                self._drop_collection(sem)
            manifest = {}  # every hash invalid → full re-embed
        file_entries: dict[str, dict] = manifest.setdefault("files", {})

        all_chunks: list[tuple[str, str, str, int, int]] = []
        seen: set[str] = set()
        for f in files:
            try:
                rel = str(f.relative_to(cwd))
                content = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            digest = _file_hash(content)
            seen.add(rel)

            chunks = [
                (start, end, text)
                for start, end, text in extract_chunks(db_path, rel, content)
                if text.strip()
            ]
            ids = [_chunk_id(rel, i) for i in range(len(chunks))]
            all_chunks.extend(
                (cid, text, rel, start, end)
                for cid, (start, end, text) in zip(ids, chunks)
            )

            entry = file_entries.get(rel)
            if entry and entry.get("hash") == digest:
                continue  # unchanged → zero embeds

            if sem is not None:
                old_ids = list(entry.get("chunk_ids", [])) if entry else []
                stale = [cid for cid in old_ids if cid not in set(ids)]
                if stale:
                    sem._collection.delete(ids=stale)
                if ids:
                    sem._collection.upsert(
                        documents=[text for _, _, text in chunks],
                        ids=ids,
                        metadatas=[
                            {"path": rel, "line_start": start, "line_end": end}
                            for start, end, _ in chunks
                        ],
                    )
            file_entries[rel] = {"hash": digest, "chunk_ids": ids}

        # Files deleted from the repo: purge their chunks.
        for rel in [r for r in file_entries if r not in seen]:
            old = file_entries.pop(rel)
            if sem is not None and old.get("chunk_ids"):
                sem._collection.delete(ids=old["chunk_ids"])

        manifest["embedding_model"] = current_model
        if sem is not None:
            try:
                sem._collection.modify(metadata={"embedding_model": current_model})
            except Exception:  # noqa: BLE001 — metadata tag is best-effort
                pass

        # Pitfall 4: BM25 rebuilt from the FULL current chunk set, never the delta.
        self._set_bm25_corpus(all_chunks)
        self._save_manifest(manifest)

    # -- BM25 ----------------------------------------------------------------

    def _set_bm25_corpus(self, chunks: list[tuple[str, str, str, int, int]]) -> None:
        from rank_bm25 import BM25Okapi

        self._bm25_chunks = chunks
        if chunks:
            self._bm25 = BM25Okapi([_bm25_tokenize(text) for _, text, _, _, _ in chunks])
        else:
            self._bm25 = None

    def _ensure_bm25(self) -> None:
        """Lazy corpus for query-before-build callers (no embedding involved)."""
        if self._bm25 is not None or self._bm25_chunks:
            return
        cwd = self.cwd
        db_path = _get_db_path(cwd)
        chunks: list[tuple[str, str, str, int, int]] = []
        for f in _discover_files(cwd):
            if f.suffix.lower() not in LANGUAGE_EXTS:
                continue
            try:
                rel = str(f.relative_to(cwd))
                content = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            extracted = [
                (start, end, text)
                for start, end, text in extract_chunks(db_path, rel, content)
                if text.strip()
            ]
            chunks.extend(
                (_chunk_id(rel, i), text, rel, start, end)
                for i, (start, end, text) in enumerate(extracted)
            )
        self._set_bm25_corpus(chunks)

    def _bm25_query(self, query: str, top_k: int) -> list[Hit]:
        self._ensure_bm25()
        if self._bm25 is None:
            return []
        tokens = _bm25_tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        query_token_set = set(tokens)
        ranked: list[tuple[float, tuple[str, str, str, int, int]]] = []
        for chunk, score in zip(self._bm25_chunks, scores):
            score_float = float(score)
            if score_float <= 0 and query_token_set.intersection(_bm25_tokenize(chunk[1])):
                # rank_bm25 zero/negative IDF on tiny corpora — keep true
                # lexical matches (mirror of memory_store._bm25_recall guard).
                score_float = float(len(query_token_set.intersection(_bm25_tokenize(chunk[1]))))
            if score_float <= 0:
                continue
            ranked.append((score_float, chunk))
        ranked.sort(key=lambda pair: -pair[0])
        return [
            Hit(
                source="code",
                locator=cid,
                score=score,
                excerpt=text.replace("\n", " ")[:160],
                line_start=start,
                line_end=end,
            )
            for score, (cid, text, _rel, start, end) in ranked[:top_k]
        ]

    # -- query ----------------------------------------------------------------

    def query(self, query: str, top_k: int = 5) -> list[Hit]:
        """RRF(BM25+vector) Hits with file:line; BM25-only when Chroma absent."""
        recall_k = max(top_k * 3, top_k)
        bm25_hits = self._bm25_query(query, recall_k)
        sem = self._maybe_semantic()
        if sem is None:
            return [
                dataclasses.replace(h, source="code[degraded]")
                for h in bm25_hits[:top_k]
            ]
        try:
            chroma_hits = self._chroma_query(sem, query, recall_k)
        except Exception as exc:  # noqa: BLE001 — chroma can raise on malformed query
            print(f"code index: chroma query failed ({exc}); falling back to BM25", file=sys.stderr)
            return bm25_hits[:top_k]
        return MemoryStore._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)

    def _chroma_query(self, sem: "SemanticMemory", query: str, top_k: int) -> list[Hit]:
        result = sem._collection.query(query_texts=[query], n_results=top_k)
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        hits: list[Hit] = []
        for idx, locator in enumerate(ids):
            doc = docs[idx] if idx < len(docs) else ""
            meta = metas[idx] if idx < len(metas) else {}
            dist = dists[idx] if idx < len(dists) else 0.0
            hits.append(
                Hit(
                    source="code",
                    locator=locator,
                    score=1.0 / (1.0 + float(dist)),
                    excerpt=(doc or "").replace("\n", " ")[:160],
                    line_start=(meta or {}).get("line_start"),
                    line_end=(meta or {}).get("line_end"),
                )
            )
        return hits


class CodeIndexService:
    """Daemon-thread wrapper: session start never blocks on the index build.

    The sentence-transformers cold-load (Pitfall 2) happens inside build(),
    which only ever runs on daemon threads spawned here. One CodeIndex (one
    Chroma client) per service instance (Pitfall 3).
    """

    def __init__(self, cwd: Path, session_id: str | None = None) -> None:
        self._code_index = CodeIndex(cwd)
        self._session_id = session_id
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._rehash_lock = threading.Lock()

    def ensure_background_build(self) -> None:
        if self._thread is not None:
            return
        t = threading.Thread(target=self._build_loop, daemon=True)
        self._thread = t
        t.start()

    def _build_loop(self) -> None:
        try:
            self._code_index.build(session_id=self._session_id)
        except Exception as exc:  # noqa: BLE001 — build failure degrades, never crashes the session
            print(
                f"code index: background build failed ({exc}); recall degrades to BM25",
                file=sys.stderr,
            )
        finally:
            self._ready.set()  # always flip ready (degraded if failed)

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def query(self, query: str, top_k: int = 5) -> list[Hit]:
        if not self._ready.is_set():
            # Mid-build: BM25-only. Never touch the embedding path here — a
            # chroma query would block behind the in-flight build's embeds.
            hits = self._code_index._bm25_query(query, top_k)
            return [dataclasses.replace(h, source="code[degraded]") for h in hits]
        return self._code_index.query(query, top_k=top_k)

    def queue_rehash(self, path) -> None:
        """D-13 trigger #2: off-thread targeted re-hash after a file mutation.

        Not ready → no-op (the in-flight full build already covers the file).
        The manifest hash-skip means a build pass re-embeds exactly the
        changed path's chunks. Never blocks the caller.
        """
        if not self._ready.is_set():
            return

        def _rehash() -> None:
            try:
                with self._rehash_lock:
                    self._code_index.build(session_id=self._session_id)
            except Exception as exc:  # noqa: BLE001 — re-hash failure must not surface to the write path
                print(f"code index: targeted re-hash failed ({exc})", file=sys.stderr)

        threading.Thread(target=_rehash, daemon=True).start()
