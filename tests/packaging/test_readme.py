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
