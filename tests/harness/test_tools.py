import asyncio
from pathlib import Path

import pytest

from voss.harness.tools import ToolEntry, make_toolset


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("print('hello')\n")
    (tmp_path / "README.md").write_text("# proj\n")
    return tmp_path


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


class TestFsRead:
    def test_reads_text_file(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_read"].invoke(path="src/a.py"))
        assert "hello" in out

    def test_missing_file_returns_error(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_read"].invoke(path="missing.txt"))
        assert "not found" in out

    def test_directory_returns_error(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_read"].invoke(path="src"))
        assert "directory" in out

    def test_path_escape_rejected(self, project: Path) -> None:
        tools = make_toolset(project)
        with pytest.raises(Exception):
            _run(tools["fs_read"].invoke(path="../../../etc/passwd"))


class TestFsGlob:
    def test_lists_matching_files(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_glob"].invoke(pattern="**/*.py"))
        assert "src/a.py" in out

    def test_no_match(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_glob"].invoke(pattern="*.nonexistent"))
        assert "no matches" in out


class TestShellRun:
    def test_allowlisted_command_runs(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["shell_run"].invoke(cmd="ls"))
        assert "src" in out
        assert "README.md" in out

    def test_denied_command_blocked(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["shell_run"].invoke(cmd="rm -rf ."))
        assert "denied" in out

    def test_unknown_binary_blocked(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["shell_run"].invoke(cmd="evilbinary --pwn"))
        assert "denied" in out


class TestToolEntryClassification:
    def test_registry_values_are_tool_entries(self, tmp_path: Path) -> None:
        tools = make_toolset(tmp_path)
        for name, entry in tools.items():
            assert isinstance(entry, ToolEntry), name
            assert entry.descriptor.name == name
            assert isinstance(entry.is_mutating, bool)

    def test_read_only_tools_are_non_mutating(self, tmp_path: Path) -> None:
        tools = make_toolset(tmp_path)
        for name in ("fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"):
            assert tools[name].is_mutating is False, name

    def test_mutating_tools_flagged(self, tmp_path: Path) -> None:
        tools = make_toolset(tmp_path)
        for name in ("fs_write", "fs_edit", "shell_run"):
            assert tools[name].is_mutating is True, name

    def test_descriptor_invoke_still_works(self, project: Path) -> None:
        tools = make_toolset(project)
        out = _run(tools["fs_read"].descriptor.invoke(path="src/a.py"))
        assert "hello" in out

    def test_mutating_count(self, tmp_path: Path) -> None:
        tools = make_toolset(tmp_path)
        # T2-05 added fs_read_many (is_mutating=False); T3-05 added web_fetch
        # (is_mutating=False, is_network=True). 5 mutating, 8 non-mutating.
        assert sum(1 for e in tools.values() if e.is_mutating) == 5
        assert sum(1 for e in tools.values() if not e.is_mutating) == 8
