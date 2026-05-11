import json
import stat
from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory

from voss.harness import session as ss


class TestSessionRoundtrip:
    def test_save_then_list(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        history.add("rename foo to bar", role="user")
        history.add("done. 3 files changed.", role="assistant")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4-5")
        rec.total_cost_usd = 0.012
        path = ss.save(rec, history)
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        sessions = ss.list_sessions(cwd=tmp_path)
        assert len(sessions) == 1
        assert sessions[0].id == rec.id
        assert sessions[0].first_task().startswith("rename foo")

    def test_load_by_id_prefix(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        history.add("hi", role="user")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        loaded_rec, loaded_hist = ss.load(rec.id[:6], cwd=tmp_path)
        assert loaded_rec.id == rec.id
        assert loaded_hist.last(10)[0]["content"] == "hi"

    def test_load_by_name(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m", name="rename-task")
        ss.save(rec, history)
        loaded, _ = ss.load("rename-task", cwd=tmp_path)
        assert loaded.name == "rename-task"

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ss.load("nonexistent", cwd=tmp_path)

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=10)
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        assert ss.delete(rec.id, cwd=tmp_path) is True
        assert ss.delete(rec.id, cwd=tmp_path) is False

    def test_first_task_truncated(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=10)
        history.add("x" * 200, role="user")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        loaded, _ = ss.load(rec.id, cwd=tmp_path)
        assert len(loaded.first_task()) <= 60


class TestPerCwdStorage:
    def test_save_writes_per_cwd_path(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=10)
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        path = ss.save(rec, history)
        expected = (tmp_path / ".voss" / "sessions" / f"{rec.id}.json").resolve()
        assert path == expected
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        # Ensure JSON parses cleanly.
        json.loads(path.read_text())

    def test_legacy_path_never_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        legacy_root = tmp_path / "legacy_state"
        monkeypatch.setenv("XDG_STATE_HOME", str(legacy_root))
        cwd_dir = tmp_path / "proj"
        cwd_dir.mkdir()
        rec = ss.SessionRecord.new(cwd=cwd_dir, model="m")
        history = EpisodicMemory(capacity=10)
        ss.save(rec, history)
        legacy_dir = legacy_root / "voss" / "sessions"
        # The legacy directory should not have any session files.
        if legacy_dir.exists():
            assert list(legacy_dir.glob("*.json")) == []

    def test_load_falls_back_to_legacy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        legacy_root = tmp_path / "legacy"
        monkeypatch.setenv("XDG_STATE_HOME", str(legacy_root))
        legacy_dir = legacy_root / "voss" / "sessions"
        legacy_dir.mkdir(parents=True)
        sid = "abcdef123456"
        data = {
            "id": sid,
            "name": "old-session",
            "cwd": str(tmp_path),
            "model": "m",
            "started_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "total_cost_usd": 0.0,
            "turns": [{"role": "user", "content": "old hi"}],
        }
        (legacy_dir / f"{sid}.json").write_text(json.dumps(data))
        empty_cwd = tmp_path / "fresh"
        empty_cwd.mkdir()
        loaded, hist = ss.load(sid, cwd=empty_cwd)
        assert loaded.id == sid
        assert getattr(loaded, "_legacy", False) is True
        assert hist.last(10)[0]["content"] == "old hi"

    def test_load_legacy_without_runs_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        legacy_root = tmp_path / "legacy"
        monkeypatch.setenv("XDG_STATE_HOME", str(legacy_root))
        legacy_dir = legacy_root / "voss" / "sessions"
        legacy_dir.mkdir(parents=True)
        sid = "deadbeefcafe"
        data = {
            "id": sid,
            "name": "legacy",
            "cwd": str(tmp_path),
            "model": "m",
            "started_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "total_cost_usd": 0.0,
            "turns": [],
            # NOTE: no "runs" key
        }
        (legacy_dir / f"{sid}.json").write_text(json.dumps(data))
        loaded, _ = ss.load(sid, cwd=tmp_path / "x")
        assert loaded.runs == []

    def test_list_sessions_cwd_scoped(self, tmp_path: Path) -> None:
        cwd_a = tmp_path / "A"
        cwd_b = tmp_path / "B"
        cwd_a.mkdir()
        cwd_b.mkdir()
        history = EpisodicMemory(capacity=10)
        rec_a1 = ss.SessionRecord.new(cwd=cwd_a, model="m")
        ss.save(rec_a1, history)
        rec_a2 = ss.SessionRecord.new(cwd=cwd_a, model="m")
        ss.save(rec_a2, history)
        rec_b1 = ss.SessionRecord.new(cwd=cwd_b, model="m")
        ss.save(rec_b1, history)
        sessions = ss.list_sessions(cwd=cwd_a)
        ids = {r.id for r in sessions}
        assert ids == {rec_a1.id, rec_a2.id}

    def test_list_sessions_include_legacy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        legacy_root = tmp_path / "legacy"
        monkeypatch.setenv("XDG_STATE_HOME", str(legacy_root))
        cwd_dir = tmp_path / "proj"
        cwd_dir.mkdir()
        rec = ss.SessionRecord.new(cwd=cwd_dir, model="m")
        ss.save(rec, EpisodicMemory(capacity=5))

        legacy_dir = legacy_root / "voss" / "sessions"
        legacy_dir.mkdir(parents=True)
        legacy_id = "legacy00abcd"
        legacy_data = {
            "id": legacy_id,
            "name": "old",
            "cwd": str(cwd_dir),
            "model": "m",
            "started_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "total_cost_usd": 0.0,
            "turns": [],
        }
        (legacy_dir / f"{legacy_id}.json").write_text(json.dumps(legacy_data))

        sessions = ss.list_sessions(cwd=cwd_dir, include_legacy=True)
        assert len(sessions) == 2
        legacy_hits = [r for r in sessions if getattr(r, "_legacy", False)]
        assert len(legacy_hits) == 1
        assert legacy_hits[0].id == legacy_id
