from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory

from voss.harness import session as ss


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


class TestSessionRoundtrip:
    def test_save_then_list(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        history.add("rename foo to bar", role="user")
        history.add("done. 3 files changed.", role="assistant")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4-5")
        rec.total_cost_usd = 0.012
        path = ss.save(rec, history)
        assert path.exists()
        sessions = ss.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == rec.id
        assert sessions[0].first_task().startswith("rename foo")

    def test_load_by_id_prefix(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        history.add("hi", role="user")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        loaded_rec, loaded_hist = ss.load(rec.id[:6])
        assert loaded_rec.id == rec.id
        assert loaded_hist.last(10)[0]["content"] == "hi"

    def test_load_by_name(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m", name="rename-task")
        ss.save(rec, history)
        loaded, _ = ss.load("rename-task")
        assert loaded.name == "rename-task"

    def test_load_missing_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            ss.load("nonexistent")

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=10)
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        assert ss.delete(rec.id) is True
        assert ss.delete(rec.id) is False

    def test_first_task_truncated(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=10)
        history.add("x" * 200, role="user")
        rec = ss.SessionRecord.new(cwd=tmp_path, model="m")
        ss.save(rec, history)
        loaded, _ = ss.load(rec.id)
        assert len(loaded.first_task()) <= 60
