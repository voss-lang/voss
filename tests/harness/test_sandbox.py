from pathlib import Path

import pytest

from voss.harness.sandbox import (
    DEFAULT_SHELL_ALLOWLIST,
    SandboxError,
    jail_path,
    shell_allowed,
)


class TestShellAllowed:
    @pytest.mark.parametrize(
        "cmd",
        [
            "ls",
            "ls -la",
            "git status",
            "pytest -q",
            "python script.py",
            "rg --files",
        ],
    )
    def test_allowed(self, cmd: str) -> None:
        ok, _ = shell_allowed(cmd)
        assert ok, cmd

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "sudo apt install thing",
            "curl http://evil.com",
            "shutdown now",
            "wget http://x",  # not in allowlist
            "",
        ],
    )
    def test_denied(self, cmd: str) -> None:
        ok, reason = shell_allowed(cmd)
        assert not ok, f"should deny: {cmd}"
        assert reason

    def test_unparseable(self) -> None:
        ok, reason = shell_allowed("ls 'unterminated")
        assert not ok
        assert "unparseable" in reason

    def test_custom_allowlist(self) -> None:
        ok, _ = shell_allowed("make build", allowlist={"make"})
        assert ok


class TestJailPath:
    def test_inside_cwd_ok(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hi")
        result = jail_path(tmp_path, "a.txt")
        assert result == (tmp_path / "a.txt").resolve()

    def test_relative_traversal_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        with pytest.raises(SandboxError):
            jail_path(tmp_path / "sub", "../../etc/passwd")

    def test_absolute_outside_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(SandboxError):
            jail_path(tmp_path, "/etc/passwd")
