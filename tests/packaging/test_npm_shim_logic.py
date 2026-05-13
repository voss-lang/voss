"""M6-02 NPM-03: structural + branch tests for the Node bin shim.

These tests pin the static guarantees of `npm/bin/voss.js` so that
accidental edits in later plans break loudly. They are intentionally
fast (file reads + one short subprocess invocation) and are NOT marked
`@pytest.mark.slow`. The full behavioural smoke (real PBS extract +
spawn) is M6-05's job.

If the host has no `node` on PATH, every test in this module skips
rather than fails — Voss is still primarily a Python project; npm is a
distribution channel.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from tests.packaging.test_entrypoint import _repo_root


SHIM_PATH = _repo_root() / "npm" / "bin" / "voss.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not on PATH; npm shim tests require Node.js",
)


def _shim_text() -> str:
    return SHIM_PATH.read_text(encoding="utf-8")


def test_shim_reports_unsupported_platform_or_missing_package():
    """On a fresh checkout no platform subpackage is in node_modules.

    The shim must exit 1 and explain to the user either (a) the platform
    is unsupported or (b) the platform subpackage is not installed.
    Which message wins depends on the host arch/os — both are correct
    failure modes for NPM-03's "clear error before fall-through" guarantee.
    """
    result = subprocess.run(
        ["node", str(SHIM_PATH), "--help"],
        capture_output=True,
        text=True,
        cwd=str(_repo_root()),
        timeout=10,
    )
    assert result.returncode == 1, (
        f"shim exited {result.returncode}; expected 1 on no-subpackage host.\n"
        f"stderr: {result.stderr!r}\nstdout: {result.stdout!r}"
    )
    stderr = result.stderr
    assert ("not installed" in stderr) or ("unsupported platform" in stderr), (
        f"shim stderr did not match either expected branch.\nstderr: {stderr!r}"
    )


def test_shim_has_shebang_and_strict_mode():
    text = _shim_text()
    lines = text.splitlines()
    assert lines[0].startswith("#!/usr/bin/env node"), (
        f"first line is not the node shebang: {lines[0]!r}"
    )
    assert any("'use strict'" in ln for ln in lines[:5]), (
        f"'use strict' not found in first 5 lines: {lines[:5]!r}"
    )


def test_shim_branches_on_windows_platform():
    """Both 'python.exe' (Windows) and 'bin/python3' (Unix) literals must
    appear so neither OS branch is silently dropped by a future edit."""
    text = _shim_text()
    assert "python.exe" in text, "Windows python path literal missing"
    assert "bin/python3" in text, "Unix python path literal missing"


def test_shim_invokes_voss_cli_module_form():
    """The spawn args must be the `-m voss.cli` module form so the shim
    works even if pip's console-script symlink was not created in the
    vendored env (PEP 517 corner case noted in CONTEXT.md)."""
    text = _shim_text()
    pattern = re.compile(r"'-m'.{0,40}'voss\.cli'", re.DOTALL)
    assert pattern.search(text), (
        "spawn args do not contain '-m', 'voss.cli' (module-form invocation)"
    )


def test_shim_maps_sigint_to_130():
    """Unix convention: child killed by signal N → exit code 128+N.
    SIGINT (2) → 130. The shim must contain that mapping (either as the
    literal 130 in a SIGINT-keyed table or as `128 + 2` arithmetic)."""
    text = _shim_text()
    has_literal = "SIGINT" in text and "130" in text
    has_arithmetic = "SIGINT" in text and "128 + 2" in text
    assert has_literal or has_arithmetic, (
        "SIGINT→130 mapping not found in shim"
    )
