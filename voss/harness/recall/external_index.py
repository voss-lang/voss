"""External-source recall index skeleton.

Mirrors code/semantic_index.py with heading-boundary markdown chunking and
per-source isolation under .voss-cache/recall/<name>/.
"""
from __future__ import annotations

import dataclasses
import json
import re
import sys
import threading
from pathlib import Path

from voss.harness.code.semantic_index import _split_oversize, _file_hash, _effective_embedding_model
from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize

_MD_SUFFIXES = {".md", ".markdown"}
_ATX_HEADING = re.compile(r"^(#{1,6})\s")
_FENCE_START = re.compile(r"^\s*(?:```|~~~)")


def extract_md_chunks(content: str) -> list[tuple[int, int, str]]:
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    headings: list[tuple[int, int]] = []
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        if _FENCE_START.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _ATX_HEADING.match(line)
        if match:
            headings.append((idx, len(match.group(1))))

    if not headings:
        return _split_oversize(1, total_lines, lines)

    chunks: list[tuple[int, int, str]] = []
    first_heading_line = headings[0][0]
    if first_heading_line > 1:
        chunks.extend(_split_oversize(1, first_heading_line - 1, lines))

    for pos, (start, level) in enumerate(headings):
        end = total_lines
        for next_start, next_level in headings[pos + 1 :]:
            if next_level <= level:
                end = next_start - 1
                break
        chunks.extend(_split_oversize(start, end, lines))
    return chunks


class ExternalSourceIndex:
    def __init__(self, cwd: Path, source: dict) -> None:
        self.cwd = Path(cwd).resolve()
        self.source = dict(source)
        self._name = str(self.source.get("name", "")).strip()
        self._glob = str(self.source.get("glob", "**/*.md") or "**/*.md")
        self._cache_dir = self.cwd / ".voss-cache" / "recall" / self._name
        sanitized = re.sub(r"[^a-z0-9_]", "_", self._name.lower())
        self._collection_name = f"voss_recall_{sanitized}"
        self._sem = None
        self._unavailable = False
        self._bm25 = None
        self._bm25_chunks: list[tuple[str, str, str, int, int]] = []

    def _source_root(self) -> Path | None:
        raw = str(self.source.get("path", "")).strip()
        if not raw:
            return None
        root = Path(raw).expanduser()
        if not root.is_absolute():
            root = self.cwd / root
        root = root.resolve()
        if not root.exists():
            print(f"external recall: source path missing ({root})", file=sys.stderr)
            return None
        return root

    def _iter_source_files(self) -> list[tuple[Path, str]]:
        root = self._source_root()
        if root is None:
            return []
        if root.is_file():
            return [(root, root.name)] if root.suffix.lower() in _MD_SUFFIXES else []

        resolved_root = root.resolve()
        files: list[tuple[Path, str]] = []
        try:
            candidates = list(root.rglob(self._glob))
        except OSError as exc:
            print(f"external recall: cannot scan {root} ({exc})", file=sys.stderr)
            return []
        for path in candidates:
            try:
                if not path.is_file() or path.suffix.lower() not in _MD_SUFFIXES:
                    continue
                resolved = path.resolve()
                if not resolved.is_relative_to(resolved_root):
                    continue
                rel = str(path.relative_to(root))
            except (OSError, ValueError):
                continue
            files.append((path, rel))
        files.sort(key=lambda item: item[1])
        return files

    def _manifest_path(self) -> Path:
        return self._cache_dir / "semantic-manifest.json"

    def _load_manifest(self) -> dict:
        try:
            return json.loads(self._manifest_path().read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_manifest(self, data: dict) -> None:
        path = self._manifest_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=0, sort_keys=True))

    def _maybe_semantic(self):
        if self._sem is not None:
            return self._sem
        if self._unavailable:
            return None
        try:
            from voss_runtime.memory.semantic import SemanticMemory

            sem = SemanticMemory(
                persist_dir=str(self._cache_dir / "chroma"),
                collection_name=self._collection_name,
            )
        except (ModuleNotFoundError, ImportError):
            self._unavailable = True
            return None
        except Exception as exc:  # noqa: BLE001 - Chroma can fail for local-state reasons
            print(
                f"external recall: chroma init failed ({exc}); using BM25 fallback",
                file=sys.stderr,
            )
            self._unavailable = True
            return None
        self._sem = sem
        return sem

    def _drop_collection(self, sem) -> None:
        try:
            sem._client.delete_collection(self._collection_name)
        except Exception:  # noqa: BLE001 - collection may not exist yet
            pass
        sem._collection = sem._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=sem._embedding_function(),
        )

    def build(self) -> None:
        files = self._iter_source_files()
        manifest = self._load_manifest()
        current_model = _effective_embedding_model()
        sem = self._maybe_semantic()
        if manifest.get("embedding_model") and manifest["embedding_model"] != current_model:
            if sem is not None:
                self._drop_collection(sem)
            manifest = {}
        file_entries: dict[str, dict] = manifest.setdefault("files", {})

        all_chunks: list[tuple[str, str, str, int, int]] = []
        seen: set[str] = set()
        for path, rel in files:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            digest = _file_hash(content)
            seen.add(rel)
            chunks = [
                (start, end, text)
                for start, end, text in extract_md_chunks(content)
                if text.strip()
            ]
            ids = [f"{self._name}:{rel}:{idx:03d}" for idx in range(len(chunks))]
            all_chunks.extend(
                (cid, text, rel, start, end)
                for cid, (start, end, text) in zip(ids, chunks)
            )

            entry = file_entries.get(rel)
            if entry and entry.get("hash") == digest:
                continue

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

        for rel in [rel for rel in file_entries if rel not in seen]:
            old = file_entries.pop(rel)
            if sem is not None and old.get("chunk_ids"):
                sem._collection.delete(ids=old["chunk_ids"])

        manifest["embedding_model"] = current_model
        if sem is not None:
            try:
                sem._collection.modify(metadata={"embedding_model": current_model})
            except Exception:  # noqa: BLE001 - metadata is best-effort
                pass
        self._set_bm25_corpus(all_chunks)
        self._save_manifest(manifest)

    def _set_bm25_corpus(self, chunks: list[tuple[str, str, str, int, int]]) -> None:
        from rank_bm25 import BM25Okapi

        self._bm25_chunks = chunks
        if chunks:
            self._bm25 = BM25Okapi([_bm25_tokenize(text) for _, text, _, _, _ in chunks])
        else:
            self._bm25 = None

    def _ensure_bm25(self) -> None:
        if self._bm25 is not None or self._bm25_chunks:
            return
        chunks: list[tuple[str, str, str, int, int]] = []
        for path, rel in self._iter_source_files():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            extracted = [
                (start, end, text)
                for start, end, text in extract_md_chunks(content)
                if text.strip()
            ]
            chunks.extend(
                (f"{self._name}:{rel}:{idx:03d}", text, rel, start, end)
                for idx, (start, end, text) in enumerate(extracted)
            )
        self._set_bm25_corpus(chunks)

    def query(self, query: str, top_k: int = 5) -> list[Hit]:
        recall_k = max(top_k * 3, top_k)
        bm25_hits = self._bm25_query(query, recall_k)
        sem = self._maybe_semantic()
        if sem is None:
            return [
                dataclasses.replace(h, source=f"{self._name}[degraded]")
                for h in bm25_hits[:top_k]
            ]
        try:
            chroma_hits = self._chroma_query(sem, query, recall_k)
        except Exception as exc:  # noqa: BLE001 - chroma can raise on malformed query
            print(
                f"external recall: chroma query failed ({exc}); falling back to BM25",
                file=sys.stderr,
            )
            return bm25_hits[:top_k]
        return MemoryStore._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)

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
                score_float = float(len(query_token_set.intersection(_bm25_tokenize(chunk[1]))))
            if score_float <= 0:
                continue
            ranked.append((score_float, chunk))
        ranked.sort(key=lambda pair: -pair[0])
        return [
            Hit(
                source=self._name,
                locator=cid,
                score=score,
                excerpt=text.replace("\n", " ")[:160],
                line_start=start,
                line_end=end,
            )
            for score, (cid, text, _rel, start, end) in ranked[:top_k]
        ]

    def _chroma_query(self, sem, query: str, top_k: int) -> list[Hit]:
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
                    source=self._name,
                    locator=locator,
                    score=1.0 / (1.0 + float(dist)),
                    excerpt=(doc or "").replace("\n", " ")[:160],
                    line_start=(meta or {}).get("line_start"),
                    line_end=(meta or {}).get("line_end"),
                )
            )
        return hits


class ExternalRecallService:
    def __init__(self, cwd: Path, session_id: str | None = None) -> None:
        self.cwd = Path(cwd).resolve()
        self._session_id = session_id
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            from voss.harness.config import get_recall_sources

            sources = get_recall_sources()
        except ValueError as exc:
            print(f"external recall: invalid config ({exc}); disabling sources", file=sys.stderr)
            sources = []
        self._indices = [ExternalSourceIndex(self.cwd, source) for source in sources]

    def ensure_background_build(self) -> None:
        if not self._indices or self._thread is not None:
            return
        t = threading.Thread(target=self._build_loop, daemon=True)
        self._thread = t
        t.start()

    def _build_loop(self) -> None:
        try:
            for index in self._indices:
                index.build()
        except Exception as exc:  # noqa: BLE001 - build failure degrades, never crashes a session
            print(
                f"external recall: background build failed ({exc}); recall degrades to BM25",
                file=sys.stderr,
            )
        finally:
            self._ready.set()

    def is_ready(self) -> bool:
        return self._ready.is_set()

    def build_all(self) -> None:
        for index in self._indices:
            index.build()
        self._ready.set()

    def query_all(self, query: str, top_k: int = 5) -> list[list[Hit]]:
        if not self._ready.is_set():
            return [index._bm25_query(query, top_k) for index in self._indices]
        return [index.query(query, top_k=top_k) for index in self._indices]
