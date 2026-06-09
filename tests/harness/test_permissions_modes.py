"""Mode-tier permission matrix tests (D-05, D-06).

Covers `mode_allows` predicate and `PermissionGate.check` structural denial.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.permissions import PermissionGate, PermissionStore, mode_allows


class TestModeAllows:
    def test_plan_allows_reads(self) -> None:
        assert mode_allows("plan", "fs_read", False) == (True, "ok")
        assert mode_allows("plan", "fs_glob", False) == (True, "ok")
        assert mode_allows("plan", "git_status", False) == (True, "ok")

    def test_plan_denies_writes(self) -> None:
        assert mode_allows("plan", "fs_write", True) == (False, "denied by mode plan")
        assert mode_allows("plan", "fs_edit", True) == (False, "denied by mode plan")

    def test_plan_denies_shell(self) -> None:
        assert mode_allows("plan", "shell_run", True) == (False, "denied by mode plan")

    def test_edit_allows_reads(self) -> None:
        assert mode_allows("edit", "fs_read", False) == (True, "ok")

    def test_edit_allows_writes(self) -> None:
        assert mode_allows("edit", "fs_write", True) == (True, "ok")
        assert mode_allows("edit", "fs_edit", True) == (True, "ok")

    def test_edit_denies_shell(self) -> None:
        assert mode_allows("edit", "shell_run", True) == (False, "denied by mode edit")

    def test_auto_allows_everything(self) -> None:
        assert mode_allows("auto", "shell_run", True) == (True, "ok")
        assert mode_allows("auto", "fs_write", True) == (True, "ok")
        assert mode_allows("auto", "fs_read", False) == (True, "ok")


def _fail_prompt(*_args, **_kwargs) -> str:
    pytest.fail("prompt called — structural denial should bypass prompting")


class TestGateStructuralDenial:
    def test_plan_mode_denies_write_without_prompting(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="plan", store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("fs_write", {"path": "x", "content": "y"}, is_mutating=True)
        assert allowed is False
        assert why == "denied by mode plan"

    def test_plan_mode_denies_shell_without_prompting(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="plan", store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("shell_run", {"cmd": "ls"}, is_mutating=True)
        assert allowed is False
        assert why == "denied by mode plan"

    def test_edit_mode_denies_shell_without_prompting(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="edit", auto_yes=True, store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("shell_run", {"cmd": "ls"}, is_mutating=True)
        assert allowed is False
        assert why == "denied by mode edit"

    def test_plan_mode_allows_reads(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="plan", auto_yes=True, store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("fs_read", {"path": "x"}, is_mutating=False)
        assert allowed is True

    def test_edit_mode_allows_writes_via_auto_yes(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="edit", auto_yes=True, store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("fs_write", {"path": "x", "content": "y"}, is_mutating=True)
        assert allowed is True

    def test_edit_mode_prompts_for_mutating_capability_metadata(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        calls: list[str] = []

        def prompt_fn(name, args):
            calls.append(name)
            return "a"

        gate = PermissionGate(
            mode="edit",
            auto_yes=False,
            store=PermissionStore(cwd=tmp_path),
            prompt_fn=prompt_fn,
        )
        allowed, why = gate.check("memory_remember", {"text": "note"}, is_mutating=True)
        assert allowed is True
        assert why == "allowed once"
        assert calls == ["memory_remember"]

    def test_edit_mode_prompts_for_mutating_review_capability(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        calls: list[str] = []

        def prompt_fn(name, args):
            calls.append(name)
            return "a"

        gate = PermissionGate(
            mode="edit",
            auto_yes=False,
            store=PermissionStore(cwd=tmp_path),
            prompt_fn=prompt_fn,
        )
        allowed, why = gate.check("subagent_run", {"agent": "reviewer"}, is_mutating=True)
        assert allowed is True
        assert why == "allowed once"
        assert calls == ["subagent_run"]

    def test_edit_mode_auto_allows_non_mutating_capability(
        self, tmp_path: Path
    ) -> None:
        gate = PermissionGate(mode="edit", auto_yes=False, store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("memory_recall", {"query": "x"}, is_mutating=False)
        assert allowed is True
        assert why == "auto"

    def test_auto_mode_allows_shell(self, tmp_path: Path) -> None:
        gate = PermissionGate(mode="auto", store=PermissionStore(cwd=tmp_path))
        gate.prompt_fn = _fail_prompt
        allowed, why = gate.check("shell_run", {"cmd": "ls"}, is_mutating=True)
        assert allowed is True
