"""M5 D-18: README install section contains the required content.

Content-assert tests pin the v0.1 distribution narrative in the README so the
install instructions cannot silently drift to a stale or incorrect path
(e.g. re-introducing `cargo install voss` or losing the `voss doctor` first-run
guidance).
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text()


def test_pip_install_voss_present():
    assert "pip install voss" in _readme()


def test_voss_doctor_first_run_mentioned():
    assert "voss doctor" in _readme()


def test_samples_link_present():
    text = _readme()
    assert "samples/" in text or "samples](" in text


def test_v01_framing_line_present():
    text = _readme()
    assert "Python harness" in text or "python harness" in text


def test_no_rust_install_path():
    text = _readme()
    assert "cargo install" not in text
    assert "brew install voss" not in text


def test_npm_install_voss_cli_present():
    """M6 NPM-05: the v0.1 README documents the npm install path.

    Scope note: M6-01 D-1 substituted `@voss/cli` -> `@vosslang/cli`
    because the `voss` npm org was already taken on publish day. The
    README references the actual published package name.
    """
    text = _readme()
    assert (
        "npm i -g @vosslang/cli" in text
        or "npm install -g @vosslang/cli" in text
    ), "README is missing the canonical `npm i -g @vosslang/cli` command"


def test_npm_install_is_primary_over_pip():
    """The npm install command must appear BEFORE `pip install voss` so
    readers see the recommended path first (NPM-05)."""
    text = _readme()
    npm_idx = text.find("npm i -g @vosslang/cli")
    if npm_idx == -1:
        npm_idx = text.find("npm install -g @vosslang/cli")
    pip_idx = text.find("pip install voss")
    assert npm_idx != -1, (
        "README is missing the npm install command literal "
        "(expected `npm i -g @vosslang/cli` or `npm install -g @vosslang/cli`)"
    )
    assert pip_idx != -1, "README is missing the pip install command literal"
    assert npm_idx < pip_idx, (
        f"npm install must appear before pip install in README "
        f"(npm at offset {npm_idx}, pip at offset {pip_idx})"
    )
