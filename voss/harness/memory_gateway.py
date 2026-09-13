"""Keep retained memory in Laravel and session history in the Python store."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voss.template_render import render_package_template

from .memory_api_client import (
    MemoryApiClient,
    MemoryApiConfigurationError,
)
from .memory_store import Hit, MemoryStore


_HISTORY_SOURCES = frozenset({"turn", "turns", "ledger", "ledgers"})
_RETAINED_SOURCES = frozenset({"note", "notes", "convention", "conventions", "decision", "decisions"})
_KINDS = frozenset({"note", "convention", "decision"})
_SOURCE_TO_KIND = {
    "note": "note",
    "notes": "note",
    "convention": "convention",
    "conventions": "convention",
    "decision": "decision",
    "decisions": "decision",
}
_KIND_TO_SOURCE = {"note": "notes", "convention": "conventions", "decision": "decisions"}
_HISTORY_SOURCE_TO_STORE = {"turn": "turn", "turns": "turns", "ledger": "ledger", "ledgers": "ledgers"}
_HISTORY_PREFIXES = frozenset({"turn", "ledger"})


class MemoryGatewayError(RuntimeError):
    """A selected-backend operation is unavailable or invalid."""


class MemoryGatewayConfigurationError(MemoryGatewayError):
    """The project has an invalid retained-memory backend configuration."""


@dataclass(frozen=True)
class SavedMemoryReference:
    """A remote locator, not a filesystem path."""

    id: str
    project_id: str
    kind: str

    @property
    def locator(self) -> str:
        return f"memory:{self.project_id}:{self.id}"

    @property
    def name(self) -> str:
        return self.locator

    @property
    def display(self) -> str:
        return self.locator

    def __str__(self) -> str:
        return self.locator


class MemoryGateway:
    backend = "laravel"
    uses_remote = True

    def __init__(
        self,
        legacy_store: MemoryStore,
        remote_client: MemoryApiClient,
        project_id: str,
        *,
        session_id: str | None = None,
    ) -> None:
        self.legacy_store = legacy_store
        self.remote_client = remote_client
        self.project_id = MemoryApiClient.validate_project_id(project_id)
        self._session_id = session_id

    @property
    def cwd(self) -> Path:
        return self.legacy_store.cwd

    @property
    def root(self) -> Path:
        return self.legacy_store.root

    def bind(self, *, session_id: str) -> "MemoryGateway":
        self._session_id = session_id
        self.legacy_store.bind(session_id=session_id)
        return self

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        source: str | None = None,
    ) -> list[Hit]:
        if not isinstance(query, str) or not query.strip():
            return []
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        top_k = min(top_k, 50)
        recall_k = max(top_k * 3, top_k)

        source_key = source.strip().lower() if isinstance(source, str) else None
        if source_key is not None and source_key not in (_HISTORY_SOURCES | _RETAINED_SOURCES):
            raise ValueError(f"unknown memory source: {source}")

        legacy_hits: list[Hit] = []
        remote_hits: list[Hit] = []
        if source_key is None:
            legacy_hits = self._recall_history(query, top_k=recall_k)
            remote_hits = self._recall_remote(query, top_k=recall_k)
        elif source_key in _HISTORY_SOURCES:
            legacy_hits = self._legacy_recall(
                query,
                top_k=recall_k,
                source=_HISTORY_SOURCE_TO_STORE[source_key],
            )
        else:
            remote_hits = self._recall_remote(
                query,
                top_k=recall_k,
                kind=_SOURCE_TO_KIND[source_key],
            )

        rankings = [ranking for ranking in (legacy_hits, remote_hits) if ranking]
        if not rankings:
            return []
        if len(rankings) == 1:
            return rankings[0][:top_k]
        return MemoryStore._rrf_merge(rankings, top_k=top_k)

    def write_note(self, text: str, *, session_id: str | None = None) -> SavedMemoryReference:
        sid = session_id if session_id is not None else self._session_id
        provenance: dict[str, Any] = {}
        if sid is not None:
            provenance["session_id"] = sid
        record = self.remote_client.create_memory(
            self.project_id,
            "note",
            text,
            provenance=provenance or None,
            idempotency_key=uuid.uuid4().hex,
        )
        return self._saved_reference(record, kind="note")

    def write_convention(
        self,
        candidate: Any,
        *,
        session_id: str | None = None,
    ) -> SavedMemoryReference:
        sid = session_id if session_id is not None else self._session_id
        statement = getattr(candidate, "statement", None)
        if statement is None and isinstance(candidate, Mapping):
            statement = candidate.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("convention statement must be a nonempty string")
        provenance: dict[str, Any] = {}
        if sid is not None:
            provenance["session_id"] = sid
        for key in ("evidence_turn_idx", "confidence", "evidence_quote"):
            value = getattr(candidate, key, None)
            if value is None and isinstance(candidate, Mapping):
                value = candidate.get(key)
            if value is not None:
                provenance[key] = value
        record = self.remote_client.create_memory(
            self.project_id,
            "convention",
            statement,
            provenance=provenance or None,
            idempotency_key=uuid.uuid4().hex,
        )
        return self._saved_reference(record, kind="convention")

    def render_pinned_memory_text(self, *, model: str) -> str:
        entries = self._remote_pins()
        if not entries:
            return ""

        cfg = self._memory_config()
        tier_cap = self._positive_int(cfg.get("pin_cap_tokens"), 500)
        item_cap = self._positive_int(cfg.get("pin_item_cap_tokens"), 200)
        try:
            from voss.harness.agent import _default_token_count
        except (ImportError, AttributeError):
            _default_token_count = lambda text, *, model: len(text.split())

        entries.sort(key=lambda row: (row[0], row[1]), reverse=True)
        kept: list[str] = []
        used = 0
        dropped = 0
        for index, (_, locator, raw_body) in enumerate(entries):
            body = raw_body.strip()
            if not body:
                continue
            if _default_token_count(body, model=model) > item_cap:
                body = body[: item_cap * 4].rstrip() + " …"
            item_tokens = _default_token_count(body, model=model)
            if kept and used + item_tokens > tier_cap:
                dropped = len(entries) - index
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
        return "## Pinned memory\n" + "\n\n".join(f"- {body}" for body in kept)

    def _record_telemetry(self, hits: list[Hit]) -> None:
        history_hits = [hit for hit in hits if not hit.locator.startswith("memory:")]
        if not history_hits:
            return
        self.legacy_store._record_telemetry(history_hits)

    def summary(self, *, source: str | None = None) -> str:
        source_key = source.strip().lower() if isinstance(source, str) else None
        if source_key is not None and source_key not in (_HISTORY_SOURCES | _RETAINED_SOURCES):
            raise ValueError(f"unknown memory source: {source}")
        if source_key in _HISTORY_SOURCES:
            return self.legacy_store.summary(source=_HISTORY_SOURCE_TO_STORE[source_key])

        remote = self._list_remote_memories(
            kind=_SOURCE_TO_KIND[source_key] if source_key in _RETAINED_SOURCES else None
        )
        sources = self._history_summary_sources()
        if source_key in _RETAINED_SOURCES:
            sources = []
        for kind in ("note", "convention", "decision"):
            if source_key is not None and _SOURCE_TO_KIND[source_key] != kind:
                continue
            records = [
                record
                for record in remote
                if self._is_active_record(record) and self._record_kind(record) == kind
            ]
            sources.append(
                {
                    "name": _KIND_TO_SOURCE[kind],
                    "files": len(records),
                    "bytes": sum(len(str(record.get("body", "")).encode("utf-8")) for record in records),
                }
            )
        total_files = sum(int(item["files"]) for item in sources)
        total_bytes = sum(int(item["bytes"]) for item in sources)
        rendered = render_package_template(
            "voss",
            "templates/memory/summary.md.jinja",
            {
                "sources": sources,
                "total_files": total_files,
                "total_bytes": total_bytes,
                "tombstoned_count": 0,
            },
        )
        return f"Backend: laravel (project {self.project_id})\n{rendered}"

    def forget(self, pattern: str, *, confirm: bool = False) -> int:
        del confirm
        parts = pattern.split(":", 2) if isinstance(pattern, str) else []
        if len(parts) != 3 or parts[0] != "memory" or parts[1] != self.project_id or not parts[2]:
            raise NotImplementedError(
                "Laravel memory forget supports only an exact memory:<project>:<id> locator"
            )
        if "*" in pattern or "?" in pattern or "[" in pattern:
            raise NotImplementedError("Laravel memory forget does not support wildcard locators")
        record = self.remote_client.get_memory(self.project_id, parts[2])
        revision = record.get("revision")
        if not isinstance(revision, int):
            raise MemoryGatewayError("Laravel memory response omitted a valid revision")
        self.remote_client.delete_memory(
            self.project_id,
            parts[2],
            expected_revision=revision,
            idempotency_key=uuid.uuid4().hex,
        )
        return 1

    def _recall_history(self, query: str, *, top_k: int) -> list[Hit]:
        rankings = [
            self._legacy_recall(query, top_k=top_k, source="turns"),
            self._legacy_recall(query, top_k=top_k, source="ledgers"),
        ]
        rankings = [ranking for ranking in rankings if ranking]
        if not rankings:
            return []
        if len(rankings) == 1:
            return rankings[0]
        return MemoryStore._rrf_merge(rankings, top_k=top_k)

    def _legacy_recall(self, query: str, *, top_k: int, source: str) -> list[Hit]:
        hits = self.legacy_store.recall(query, top_k=top_k, source=source)
        wanted = "turn" if source.startswith("turn") else "ledger"
        return [hit for hit in hits if self._history_hit_source(hit) == wanted]

    def _recall_remote(
        self,
        query: str,
        *,
        top_k: int,
        kind: str | None = None,
    ) -> list[Hit]:
        records = self.remote_client.search(
            self.project_id,
            query,
            kinds=[kind] if kind else None,
            top_k=min(top_k, 50),
        )
        return [self._remote_hit(record) for record in records if self._is_active_record(record)]

    def _remote_hit(self, record: Mapping[str, Any]) -> Hit:
        kind = self._record_kind(record)
        memory_id = str(record.get("id", ""))
        body = str(record.get("body", ""))
        try:
            score = float(record.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            provenance = {}
        session_id = provenance.get("session_id")
        if session_id is not None:
            session_id = str(session_id)
        hit = Hit(
            source=_KIND_TO_SOURCE.get(kind, f"{kind}s"),
            locator=f"memory:{self.project_id}:{memory_id}",
            score=score,
            excerpt=body[:200],
            session_id=session_id,
            ts=(
                str(record.get("created_at") or record.get("updated_at"))
                if record.get("created_at") or record.get("updated_at")
                else None
            ),
        )
        return hit

    def _list_remote_memories(self, *, kind: str | None = None, pinned: bool | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(1000):
            raw = self.remote_client.list_memories(
                self.project_id,
                kind=kind,
                pinned=pinned,
                limit=100,
                cursor=cursor,
            )
            if not isinstance(raw, Mapping):
                raise MemoryGatewayError("Laravel memory list response was invalid")
            page = raw.get("data")
            next_cursor = raw.get("next_cursor")
            if not isinstance(page, list) or any(not isinstance(item, dict) for item in page):
                raise MemoryGatewayError("Laravel memory list response was invalid")
            if next_cursor is not None and (not isinstance(next_cursor, str) or not next_cursor):
                raise MemoryGatewayError("Laravel memory list cursor was invalid")
            rows.extend(page)
            if not next_cursor:
                return rows
            next_cursor = str(next_cursor)
            if next_cursor == cursor:
                raise MemoryGatewayError("Laravel memory list cursor did not advance")
            cursor = next_cursor
        raise MemoryGatewayError("Laravel memory list exceeded the page limit")

    def _remote_pins(self) -> list[tuple[str, str, str]]:
        records = self._list_remote_memories(pinned=True)
        entries: list[tuple[str, str, str]] = []
        for record in records:
            if not self._is_active_record(record) or not record.get("pinned"):
                continue
            memory_id = str(record.get("id", ""))
            if not memory_id:
                continue
            body = record.get("body")
            if not isinstance(body, str) or not body.strip():
                continue
            locator = f"memory:{self.project_id}:{memory_id}"
            stamp = str(record.get("pinned_at") or record.get("updated_at") or record.get("created_at") or "")
            entries.append((stamp, locator, body))
        return entries

    def _history_summary_sources(self) -> list[dict[str, Any]]:
        root = self.legacy_store.root
        sources: list[dict[str, Any]] = []
        for source in ("turns", "ledgers"):
            src_dir = root / source
            files = [path for path in src_dir.rglob("*") if path.is_file()] if src_dir.exists() else []
            sources.append(
                {
                    "name": source,
                    "files": len(files),
                    "bytes": sum(path.stat().st_size for path in files),
                }
            )
        return sources

    def _memory_config(self) -> dict[str, Any]:
        value = self.legacy_store._load_memory_config()
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _record_kind(record: Mapping[str, Any]) -> str:
        kind = str(record.get("kind", "")).lower()
        return kind.rstrip("s")

    @classmethod
    def _is_active_record(cls, record: Mapping[str, Any]) -> bool:
        return cls._record_kind(record) in _KINDS and record.get("status", "active") == "active"

    @staticmethod
    def _history_hit_source(hit: Hit) -> str | None:
        source = (hit.source or "").removesuffix("[degraded]").lower()
        if source == "turns":
            return "turn"
        if source == "ledgers":
            return "ledger"
        if source in _HISTORY_PREFIXES:
            return source
        return None

    def _saved_reference(self, record: Mapping[str, Any], *, kind: str) -> SavedMemoryReference:
        memory_id = record.get("id")
        if not isinstance(memory_id, str) or not memory_id:
            raise MemoryGatewayError("Laravel memory response omitted an id")
        return SavedMemoryReference(
            id=memory_id,
            project_id=self.project_id,
            kind=kind,
        )


def _load_project_memory_config(cwd: Path) -> dict[str, Any]:
    path = Path(cwd) / ".voss" / "config.yml"
    try:
        contents = path.read_text()
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise MemoryGatewayConfigurationError("unable to read .voss/config.yml") from exc
    try:
        import yaml
    except ImportError as exc:
        raise MemoryGatewayConfigurationError("YAML support is required for memory configuration") from exc
    try:
        data = yaml.safe_load(contents)
    except yaml.YAMLError as exc:
        raise MemoryGatewayConfigurationError("unable to read .voss/config.yml") from exc
    if not isinstance(data, dict):
        if data is None:
            return {}
        raise MemoryGatewayConfigurationError(".voss/config.yml must contain a mapping")
    memory = data.get("memory")
    if memory is None:
        return {}
    if not isinstance(memory, dict):
        raise MemoryGatewayConfigurationError(".voss/config.yml memory section must be a mapping")
    return dict(memory)


def open_memory_store(cwd: Path, *, session_id: str | None = None):
    """Construct the selected project store, defaulting to legacy behavior."""
    root = Path(cwd).resolve()
    config = _load_project_memory_config(root)
    raw_backend = config.get("retained_backend", "legacy")
    if not isinstance(raw_backend, str) or not raw_backend.strip():
        raise MemoryGatewayConfigurationError(
            "memory.retained_backend must be 'legacy' or 'laravel'"
        )
    backend = raw_backend.strip().lower()
    if backend == "legacy":
        store = MemoryStore(root)
        return store.bind(session_id=session_id) if session_id is not None else store
    if backend != "laravel":
        raise MemoryGatewayConfigurationError(
            "memory.retained_backend must be 'legacy' or 'laravel'"
        )

    project_id = config.get("service_project")
    if not isinstance(project_id, str) or not project_id.strip():
        raise MemoryGatewayConfigurationError(
            "memory.service_project is required when Laravel retained memory is enabled"
        )
    try:
        project_id = MemoryApiClient.validate_project_id(project_id.strip())
    except ValueError as exc:
        raise MemoryGatewayConfigurationError(str(exc)) from exc
    try:
        remote_client = MemoryApiClient.from_env()
    except MemoryApiConfigurationError as exc:
        raise MemoryGatewayConfigurationError(str(exc)) from exc
    legacy_store = MemoryStore(root)
    if session_id is not None:
        legacy_store.bind(session_id=session_id)
    return MemoryGateway(
        legacy_store,
        remote_client,
        project_id,
        session_id=session_id,
    )


__all__ = [
    "MemoryGateway",
    "MemoryGatewayConfigurationError",
    "MemoryGatewayError",
    "SavedMemoryReference",
    "open_memory_store",
]
