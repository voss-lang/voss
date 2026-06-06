"""VREV-10 RED scaffold: `voss review [run_id]` CLI.

RED until V6 adds review_cmd to voss.harness.cli. review_cmd is imported at
test-function level so an absent symbol fails the individual tests (RED) without
aborting collection of the rest of the board suite.
"""

from __future__ import annotations

import json

from click.testing import CliRunner


def _review_cmd():
    from voss.harness.cli import review_cmd  # lazy: RED via ImportError until V6

    return review_cmd


class TestReviewCli:
    def test_unknown_run_id_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(_review_cmd(), ["nonexistent-run-id"])
        assert result.exit_code != 0
        assert "unknown run_id" in (result.output + (result.stderr or ""))

    def test_no_sessions_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(_review_cmd(), [])
        assert result.exit_code != 0

    def test_existing_run_exits_zero(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
            from pathlib import Path

            root_id = "testrootid"
            sidecar_dir = Path(fs) / ".voss" / "sessions" / root_id
            sidecar_dir.mkdir(parents=True)
            (sidecar_dir / "nodeabc.review.json").write_text(
                json.dumps(
                    {
                        "a_verification": {
                            "result": "pass", "notes": "ok",
                            "test_path_or_rubric": None,
                        },
                        "b_verdict": {
                            "conf": 0.95, "verdict": "pass", "notes": "good",
                            "evidence_refs": [], "domain_inferred": "code",
                            "source": "B", "tier": "strong",
                        },
                        "final_outcome": "Done",
                    }
                )
            )
            result = runner.invoke(_review_cmd(), [root_id])
        assert result.exit_code == 0
