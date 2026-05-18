from __future__ import annotations

import io
import json
import subprocess
import types
from pathlib import Path
from unittest.mock import patch

from voss.harness.cli import _build_slash_registry
from voss.harness.tools import make_toolset
from voss.harness.voss_lint_schema import parse_lint_json


M11_TOOLS = (
    "voss_probable_inspect",
    "voss_budget_trace",
    "voss_py_diff",
)

PROTECTED_RUNTIME_FILES = (
    "voss/harness/recorder.py",
    "voss_runtime/probable.py",
    "voss_runtime/budget.py",
    "voss_runtime/agent.py",
)


def test_all_m11_tools_are_read_only(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)

    for name in M11_TOOLS:
        assert name in tools
        assert tools[name].is_mutating is False


def test_m11_slash_commands_registered() -> None:
    registry = _build_slash_registry()

    for name in ("/probable", "/btrace", "/vdiff"):
        assert registry.lookup(name) is not None, f"{name} is not registered"


def test_budget_slash_remains_registered_with_usd_budget_behavior() -> None:
    command = _build_slash_registry().lookup("/budget")

    assert command is not None
    assert "USD" in command.help
    assert "budget" in command.help.lower()


def test_lint_schema_consumer_parses_live_skill_output(tmp_path: Path) -> None:
    from voss.harness.skills.voss_lint_as_skill import run

    source = tmp_path / "bad.voss"
    source.write_text(
        'fn classify(text: string) -> string {\n'
        '    let intent: probable<string> = ask("Classify: " + text)\n'
        "    return intent\n"
        "}\n",
        encoding="utf-8",
    )

    buf = io.StringIO()
    with patch("click.echo", side_effect=lambda s, **kw: buf.write(str(s) + "\n")):
        run(
            cwd=tmp_path,
            provider=None,
            history=None,
            record=types.SimpleNamespace(model="fake", id="m11"),
            renderer=None,
            tools=None,
            gate=None,
            args=[str(source)],
        )

    findings = parse_lint_json(buf.getvalue())

    assert findings
    assert any(finding.rule == "ANLY001" for finding in findings)
    assert json.loads(buf.getvalue())["version"] == 1


def test_protected_runtime_recorder_files_not_modified_in_git_diff() -> None:
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *PROTECTED_RUNTIME_FILES],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert result.stdout == ""
