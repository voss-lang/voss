import asyncio
from pathlib import Path

import pytest

from voss.harness.tools import make_toolset


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
