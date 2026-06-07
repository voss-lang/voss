"""RED scaffold: `voss team run` acceptance surface (VEM-CLI / VEM-PERSIST / VEM-SIGNOFF).

Wave 0 (V7-01). These tests encode the V7 acceptance contract BEFORE the
implementation in V7-02. They are RED now — the `team run` subcommand does not
exist on the team group yet, so CliRunner invocations exit non-zero and the
sidecar assertions fail. GREEN follows V7-02.

The bodies drive the REAL planned surface (no fictional API, no xfail):
  voss team run "<goal>" --cwd <dir>  composing V3 team config + V4 session tree
  + V5 board + V6 Reviewer-A/B slots + the O5 em_loop, pre-spawning >=1 card,
  persisting RunFinal (10 fields) to <cwd>/.voss/sessions/<root_id>/run-final.json
  with a superset "sign_off" key, then prompting approve/reject via click.prompt.

RunFinal is the 10-field frozen record at voss/harness/em/tickets.py:112 —
do NOT assert on evidence_refs/diff_summary/residual (those live on Ticket).
"""

from __future__ import annotations

import json

import click
import pytest
from click.testing import CliRunner

from voss.harness import cli

# The 10 RunFinal fields (voss/harness/em/tickets.py:112), frozen+slots.
_RUN_FINAL_FIELDS = {
    "root_id", "idea", "total_cards", "done_count", "blocked_count",
    "killed_count", "rescope_count", "em_iterations", "ts", "kind",
}

# A minimal team source compile_team accepts (mirrors test_team_check_cli _VALID).
_VALID_TEAM = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { budget: 50 tokens, scope: "src/api/**", tools: ["fs"] }
  }
}
'''


@pytest.fixture()
def root() -> click.Group:
    g = click.Group("voss")
    cli.register(g)
    return g


@pytest.fixture(autouse=True)
def _model_tiers(monkeypatch):
    """Default-roster construction resolves tiers via voss.harness.config.get_model_tiers
    (V7-RESEARCH Pitfall 7). Pin a mapping covering every DEFAULT_ROSTER tier so
    _default_team_config() in V7-02 cannot raise VossTeamConfigError. Monkeypatch
    target — keep consistent in V7-02:  voss.harness.config.get_model_tiers
    """
    monkeypatch.setattr(
        "voss.harness.config.get_model_tiers",
        lambda: {"strong": "stub-strong", "cheap": "stub-cheap", "fast": "stub-fast"},
    )


def _write_team(tmp_path, src: str = _VALID_TEAM):
    d = tmp_path / ".voss"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "team.voss"
    f.write_text(src, encoding="utf-8")
    return f


def _sidecar(tmp_path):
    """The single run-final.json under .voss/sessions/<root_id>/ (glob, not hardcode)."""
    matches = sorted(tmp_path.glob(".voss/sessions/*/run-final.json"))
    assert len(matches) == 1, f"expected one run-final.json, found {matches}"
    return matches[0]


def _node_json_set(tmp_path) -> set:
    """Session-node JSON files (excluding the review/run-final sidecars)."""
    return {
        p
        for p in tmp_path.glob(".voss/sessions/*/*.json")
        if not p.name.endswith(".review.json") and p.name != "run-final.json"
    }


class TestTeamRunCLI:
    def test_stub_run_exits_zero(self, root, tmp_path):
        res = CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        assert res.exit_code == 0, res.output

    def test_produces_card_and_run_final(self, root, tmp_path):
        CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        sidecar = _sidecar(tmp_path)
        data = json.loads(sidecar.read_text())
        # >=1 pre-spawned med card drove the loop to a terminal RunFinal.
        assert data["total_cards"] >= 1

    def test_run_final_persisted(self, root, tmp_path):
        CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        # <cwd>/.voss/sessions/<root_id>/run-final.json exists under the root.
        assert _sidecar(tmp_path).is_file()

    def test_default_roster_fallback(self, root, tmp_path):
        # No .voss/team.voss -> DEFAULT_ROSTER (7+ roles); run completes.
        res = CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        assert res.exit_code == 0, res.output

    def test_team_file_override(self, root, tmp_path):
        _write_team(tmp_path)
        res = CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        assert res.exit_code == 0, res.output


class TestRunFinalPersist:
    def test_fields_serialized(self, root, tmp_path):
        CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        data = json.loads(_sidecar(tmp_path).read_text())
        # Exactly the 10 RunFinal field keys present (sign_off is a superset key).
        assert _RUN_FINAL_FIELDS <= set(data.keys())
        assert _RUN_FINAL_FIELDS == {k for k in data.keys() if k != "sign_off"}

    def test_rereadable(self, root, tmp_path):
        CliRunner().invoke(
            root, ["team", "run", "ship the thing", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        data = json.loads(_sidecar(tmp_path).read_text())  # no re-run needed
        assert data["idea"] == "ship the thing"


class TestSignOff:
    def test_prompt_appears(self, root, tmp_path):
        res = CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        out = res.output.lower()
        assert "approve" in out and "reject" in out  # prompt text
        assert "build API" in res.output or "total_cards" in res.output.lower()

    def test_approve_recorded(self, root, tmp_path):
        CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="approve\n",
        )
        data = json.loads(_sidecar(tmp_path).read_text())
        assert data["sign_off"]["decision"] == "approve"

    def test_reject_recorded_no_revert(self, root, tmp_path):
        # Capture node-JSON set immediately after the run via a first reject,
        # then assert reject is record-only (no node files added/removed).
        CliRunner().invoke(
            root, ["team", "run", "build API", "--cwd", str(tmp_path)],
            input="reject\n",
        )
        before = _node_json_set(tmp_path)
        data = json.loads(_sidecar(tmp_path).read_text())
        after = _node_json_set(tmp_path)
        assert data["sign_off"]["decision"] == "reject"
        assert before == after  # reject records, never reverts the lineage
