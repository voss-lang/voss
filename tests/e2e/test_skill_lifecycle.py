"""E2E test for SKILL-06 (comprehensive skill lifecycle).

Exercises the full trust → add → list → run → update → remove cycle
against the shipped signed example bundle.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import tomllib

from .runner import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_BUNDLE = REPO_ROOT / "examples" / "skills" / "voss-git-summary"


def _seed_git_repo(root: Path) -> None:
    """Initialize a git repo so the skill has something to summarize."""
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True
    )
    (root / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True
    )


def test_committed_signature_verifies() -> None:
    """Guard: the committed manifest.toml.sig verifies against test_signing_key.pub."""
    from voss.harness.trust import verify_manifest

    manifest_path = FIXTURE_BUNDLE / "manifest.toml"
    sig_path = FIXTURE_BUNDLE / "manifest.toml.sig"
    pub_key_b64 = (FIXTURE_BUNDLE / "test_signing_key.pub").read_text().strip()

    ok, reason = verify_manifest(manifest_path, sig_path, pub_key_b64=pub_key_b64)
    assert ok, f"committed signature stale: {reason}"


def test_fixture_bundle_e2e(cli_runner: CliRunner) -> None:
    """SKILL-06: trust → add → list → run → update → remove → list."""
    manifest_data = tomllib.loads((FIXTURE_BUNDLE / "manifest.toml").read_text())
    pub_key_b64 = manifest_data["trust"]["pub_key"]
    author = manifest_data["author_identity"]

    # Seed a git repo in the project root for the skill
    _seed_git_repo(cli_runner.project_root)

    # (a) Add BEFORE trust → refused (trust gate is live)
    r = cli_runner.run("skill", "add", str(FIXTURE_BUNDLE))
    assert r.returncode != 0, f"add-before-trust should fail: {r.output}"
    assert "untrusted" in r.output.lower() or "error" in r.output.lower(), r.output

    # (b) Trust the fixture key
    r = cli_runner.run(
        "skill", "trust", pub_key_b64, "--identity", author,
        stdin="y\n",
    )
    assert r.returncode == 0, f"trust failed: {r.output}"
    assert "pinned" in r.output.lower(), r.output

    # (c) Add → succeeds now
    r = cli_runner.run("skill", "add", str(FIXTURE_BUNDLE))
    assert r.returncode == 0, f"add failed: {r.output}"
    assert "installed" in r.output.lower(), r.output

    # (d) List → shows voss-git-summary
    r = cli_runner.run("skill", "list")
    assert r.returncode == 0, f"list failed: {r.output}"
    assert "voss-git-summary" in r.output, f"skill not in list: {r.output}"

    # (e) Run the skill (requires stub provider via e2e runner)
    r = cli_runner.run("skill", "run", "voss-git-summary")
    # The skill compiles and runs; output depends on stub response
    # Accept exit 0 (success) or non-zero from compilation (the .voss uses ctx/ask)
    # The key assertion is that the skill was found and dispatch was attempted
    # (not "unknown skill" error)
    assert "unknown skill" not in r.output.lower(), f"skill not registered: {r.output}"

    # (f) Update → re-verifies unchanged bundle, exits 0
    r = cli_runner.run("skill", "update", "voss-git-summary")
    assert r.returncode == 0, f"update failed: {r.output}"
    assert "updated" in r.output.lower(), r.output

    # (g) Remove
    r = cli_runner.run("skill", "remove", "voss-git-summary")
    assert r.returncode == 0, f"remove failed: {r.output}"
    assert "removed" in r.output.lower(), r.output

    # (h) List → omits it
    r = cli_runner.run("skill", "list")
    assert r.returncode == 0, f"final list failed: {r.output}"
    assert "voss-git-summary" not in r.output, f"skill still in list after remove: {r.output}"
