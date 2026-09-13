from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.memory_gateway import (
    MemoryGateway,
    MemoryGatewayConfigurationError,
    SavedMemoryReference,
    open_memory_store,
)
from voss.harness.memory_store import Hit, MemoryStore


class FakeLegacyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cwd = root
        self._pins_path = root / ".pins.json"
        self.calls: list[tuple[str, str | None]] = []
        self.telemetry: list[Hit] = []

    def recall(self, query: str, *, top_k: int, source: str | None = None) -> list[Hit]:
        self.calls.append((query, source))
        if source.startswith("turn"):
            return [
                Hit("turn", "turn:s1:000", 4.0, "turn body"),
                Hit("note", "note:stale", 8.0, "stale retained note"),
            ]
        if source.startswith("ledger"):
            return [Hit("ledger", "ledger:r1:000", 3.0, "ledger body")]
        return []

    def _load_memory_config(self) -> dict[str, int]:
        return {}

    def _record_telemetry(self, hits: list[Hit]) -> None:
        self.telemetry.extend(hits)

    def bind(self, *, session_id: str):
        self.bound_session_id = session_id
        return self

    def summary(self, *, source: str | None = None) -> str:
        return f"legacy summary {source}"


class FakeRemoteClient:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, list[str] | None, int]] = []
        self.created: list[dict] = []
        self.deleted: list[dict] = []
        self.records = [
            {
                "id": "m1",
                "project_id": "demo",
                "kind": "note",
                "body": "remote retained body",
                "revision": 1,
                "status": "active",
                "pinned": False,
                "provenance": {"session_id": "s2", "origin": "test"},
                "score": 0.9,
                "updated_at": "2026-09-12T10:00:00+00:00",
            }
        ]

    def search(self, project_id: str, query: str, *, kinds=None, top_k: int = 5):
        self.search_calls.append((query, kinds, top_k))
        return list(self.records)

    def create_memory(self, project_id: str, kind: str, body: str, **kwargs):
        record = {
            "id": "new-1",
            "project_id": project_id,
            "kind": kind,
            "body": body,
            "revision": 1,
            "provenance": kwargs.get("provenance") or {},
        }
        self.created.append(record | {"kwargs": kwargs})
        return record

    def list_memories(self, project_id: str, *, kind=None, pinned=None, limit=100, cursor=None):
        records = list(self.records)
        if kind:
            records = [record for record in records if record["kind"] == kind]
        if pinned is True:
            records = [record for record in records if record.get("pinned")]
        return {"data": records, "next_cursor": None}

    def get_memory(self, project_id: str, memory_id: str):
        return next(record for record in self.records if record["id"] == memory_id)

    def delete_memory(self, project_id: str, memory_id: str, **kwargs):
        self.deleted.append({"project_id": project_id, "id": memory_id, **kwargs})
        return {"id": memory_id, "revision": kwargs["expected_revision"], "status": "deleted"}


def test_recall_fuses_remote_retained_with_history_and_filters_old_retained() -> None:
    legacy = FakeLegacyStore(Path("/synthetic/project"))
    remote = FakeRemoteClient()
    gateway = MemoryGateway(legacy, remote, "demo")

    hits = gateway.recall("query", top_k=3)

    locators = {hit.locator for hit in hits}
    assert "turn:s1:000" in locators
    assert "ledger:r1:000" in locators
    assert "memory:demo:m1" in locators
    assert "note:stale" not in locators
    remote_hit = next(hit for hit in hits if hit.locator == "memory:demo:m1")
    assert remote_hit.source == "notes"
    assert remote_hit.session_id == "s2"
    assert remote_hit.ts == "2026-09-12T10:00:00+00:00"
    assert remote.search_calls == [("query", None, 9)]


def test_source_filter_keeps_history_python_and_retained_laravel() -> None:
    legacy = FakeLegacyStore(Path("/synthetic/project"))
    remote = FakeRemoteClient()
    gateway = MemoryGateway(legacy, remote, "demo")

    history = gateway.recall("query", source="turns")
    retained = gateway.recall("query", source="notes")

    assert [hit.locator for hit in history] == ["turn:s1:000"]
    assert [hit.locator for hit in retained] == ["memory:demo:m1"]
    assert remote.search_calls[-1] == ("query", ["note"], 15)


def test_remote_writes_return_truthful_reference_and_forward_provenance() -> None:
    legacy = FakeLegacyStore(Path("/synthetic/project"))
    remote = FakeRemoteClient()
    gateway = MemoryGateway(legacy, remote, "demo", session_id="bound")

    note = gateway.write_note("a note")
    convention = gateway.write_convention(
        SimpleNamespace(
            statement="use the service",
            evidence_turn_idx=4,
            confidence=0.8,
            evidence_quote="service evidence",
        )
    )

    assert isinstance(note, SavedMemoryReference)
    assert note.id == "new-1"
    assert note.name == "memory:demo:new-1"
    assert note.display == "memory:demo:new-1"
    assert str(note) == "memory:demo:new-1"
    assert remote.created[0]["kwargs"]["provenance"] == {"session_id": "bound"}
    assert remote.created[1]["kwargs"]["provenance"] == {
        "session_id": "bound",
        "evidence_turn_idx": 4,
        "confidence": 0.8,
        "evidence_quote": "service evidence",
    }
    assert convention.kind == "convention"


def test_laravel_pins_ignore_stale_legacy_retained_pins(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    (root / ".pins.json").write_text(
        json.dumps(
            {
                "pins": [
                    {"locator": "note:old", "pinned_at": "2026-09-12T12:00:00+00:00"},
                ]
            }
        )
    )
    legacy = FakeLegacyStore(root)
    remote = FakeRemoteClient()
    remote.records[0]["pinned"] = True
    remote.records[0]["updated_at"] = "2026-09-12T13:00:00+00:00"

    rendered = MemoryGateway(legacy, remote, "demo").render_pinned_memory_text(
        model="synthetic"
    )

    assert "remote retained body" in rendered
    assert "old" not in rendered


def test_telemetry_delegates_history_only() -> None:
    legacy = FakeLegacyStore(Path("/synthetic/project"))
    gateway = MemoryGateway(legacy, FakeRemoteClient(), "demo")
    history = Hit("turn", "turn:s1:000", 1.0, "history")
    retained = Hit("notes", "memory:demo:m1", 1.0, "retained")

    gateway._record_telemetry([history, retained])

    assert legacy.telemetry == [history]


def test_summary_contains_only_history_files_and_active_remote_records(tmp_path: Path) -> None:
    root = tmp_path / "synthetic-project-summary"
    legacy = FakeLegacyStore(root)
    root.joinpath("turns").mkdir(parents=True)
    root.joinpath("turns", "s1.jsonl").write_text("turn")
    remote = FakeRemoteClient()
    remote.records.append({"id": "deleted", "kind": "note", "body": "stale", "status": "deleted"})

    summary = MemoryGateway(legacy, remote, "demo").summary()

    assert "Backend: laravel (project demo)" in summary
    assert "notes: 1 files" in summary
    assert "stale" not in summary


def test_forget_supports_exact_remote_locator_without_touching_legacy() -> None:
    legacy = FakeLegacyStore(Path("/synthetic/project"))
    remote = FakeRemoteClient()
    gateway = MemoryGateway(legacy, remote, "demo")

    assert gateway.forget("memory:demo:m1") == 1
    assert remote.deleted[0]["id"] == "m1"
    with pytest.raises(NotImplementedError):
        gateway.forget("note:old", confirm=True)


def test_factory_preserves_legacy_default_without_constructing_remote(monkeypatch, tmp_path: Path) -> None:
    from voss.harness import memory_gateway as module

    def fail_remote(cls):
        raise AssertionError("remote client must not be constructed in legacy mode")

    monkeypatch.setattr(module.MemoryApiClient, "from_env", classmethod(fail_remote))

    store = open_memory_store(tmp_path)

    assert isinstance(store, MemoryStore)
    assert not isinstance(store, MemoryGateway)


def test_factory_requires_explicit_project_and_builds_laravel_gateway(monkeypatch, tmp_path: Path) -> None:
    from voss.harness import memory_gateway as module

    config = tmp_path / ".voss"
    config.mkdir()
    (config / "config.yml").write_text(
        "memory:\n  retained_backend: laravel\n  service_project: demo\n"
    )
    remote = FakeRemoteClient()
    monkeypatch.setattr(module.MemoryApiClient, "from_env", classmethod(lambda cls: remote))

    store = open_memory_store(tmp_path, session_id="s1")

    assert isinstance(store, MemoryGateway)
    assert store.project_id == "demo"
    assert store._session_id == "s1"


def test_factory_rejects_laravel_without_service_project(tmp_path: Path) -> None:
    config = tmp_path / ".voss"
    config.mkdir()
    (config / "config.yml").write_text("memory:\n  retained_backend: laravel\n")

    with pytest.raises(MemoryGatewayConfigurationError):
        open_memory_store(tmp_path)


def test_factory_rejects_malformed_config_instead_of_defaulting_to_legacy(tmp_path: Path) -> None:
    config = tmp_path / ".voss"
    config.mkdir()
    (config / "config.yml").write_text("memory: [")

    with pytest.raises(MemoryGatewayConfigurationError):
        open_memory_store(tmp_path)
