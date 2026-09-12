from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid

import pytest
from click.testing import CliRunner

from voss.harness.cli import shell_init_cmd


@pytest.mark.parametrize("shell", ["zsh", "bash", "fish"])
def test_shell_init_command_prints_gated_snippet(shell):
    result = CliRunner().invoke(shell_init_cmd, ["--shell", shell])
    assert result.exit_code == 0
    assert "VOSS_EMBEDDED" in result.output
    assert "voss-cmd=" in result.output


@pytest.mark.parametrize("shell", ["zsh", "bash", "fish"])
@pytest.mark.parametrize("command, expected_exit", [
    ("pnpm test", 1),
    ("printf hello | pnpm test", 1),
    ("sleep 0.1 &", 0),
    ("bash --noprofile --norc -c 'pnpm test'", 1),
])
def test_interactive_shell_captures_failed_test_with_real_hooks(shell, tmp_path, command, expected_exit):
    binary = shutil.which(shell)
    if binary is None:
        pytest.skip(f"{shell} unavailable")
    snippet = tmp_path / "init"
    snippet.write_text(CliRunner().invoke(shell_init_cmd, ["--shell", shell]).output)
    runner = tmp_path / "pnpm"
    runner.write_text("#!/bin/sh\nprintf 'FAIL sample.spec.ts\\n'\nexit 1\n")
    runner.chmod(0o700)
    flags = {"zsh": ["-f", "-i"], "bash": ["--noprofile", "--norc", "-i"], "fish": ["--no-config", "-i"]}
    prefix = "PROMPT_COMMAND=true\n" if shell == "bash" else ""
    script = prefix + f"source {snippet}\nsource {snippet}\n{command}\nexit\n"
    proc = subprocess.run(
        [binary, *flags[shell]], input=script, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=tmp_path,
        env={"HOME": str(tmp_path), "PATH": f"{tmp_path}:{os.defpath}", "TERM": "xterm-256color", "VOSS_EMBEDDED": "1"},
        timeout=10,
    )
    wire = proc.stdout + proc.stderr
    matches = list(re.finditer(r"\x1b\]1337;voss-cmd=(.*?)\x07", wire))
    target = next(m for m in matches if json.loads(m[1])["argv_text"] == command)
    meta = json.loads(target[1])
    assert uuid.UUID(meta["cmd_id"]).version == 4
    assert meta["cwd"] == str(tmp_path)
    output, end = wire[target.end():].split("\x1b]133;D;", 1)
    if expected_exit:
        assert "FAIL sample.spec.ts" in output
    assert end.startswith(f"{expected_exit}\x07")
    if command.startswith("bash "):
        assert not any(json.loads(m[1])["argv_text"] == "pnpm test" for m in matches)
