"""VBUS-07 coordination doc + verb --help parse.

GREEN as of V17-07 (doc) + V17-03 (claims verbs). The bus-verb portion
stays xfail-gated until V17-06 ships post-V15.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.claims import claims_group

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "agent-coordination.md"

CLAIMS_VERBS = ("stake", "check", "release", "extend", "list")
BUS_VERBS = ("send", "inbox", "wait")


def test_coordination_doc_exists() -> None:
    assert DOC.exists(), "docs/agent-coordination.md missing (VBUS-07)"
    body = DOC.read_text()
    # Doc must cover the verbs, exit codes, and identity env var.
    assert "VOSS_AGENT_ID" in body
    for verb in CLAIMS_VERBS:
        assert verb in body, f"doc does not mention claims verb {verb!r}"


def test_claims_verbs_help_exit_0() -> None:
    runner = CliRunner()
    assert runner.invoke(claims_group, ["--help"]).exit_code == 0
    for verb in CLAIMS_VERBS:
        result = runner.invoke(claims_group, [verb, "--help"])
        assert result.exit_code == 0, f"claims {verb} --help: {result.output}"


@pytest.mark.xfail(
    reason="bus verbs are V15-gated — ship in V17-06", strict=False
)
def test_bus_verbs_help_exit_0() -> None:
    try:
        from voss.harness.bus_client import bus_group
    except ImportError:
        pytest.fail("voss.harness.bus_client not importable yet (V17-06, V15-gated)")
    runner = CliRunner()
    assert runner.invoke(bus_group, ["--help"]).exit_code == 0
    for verb in BUS_VERBS:
        result = runner.invoke(bus_group, [verb, "--help"])
        assert result.exit_code == 0, f"bus {verb} --help: {result.output}"
