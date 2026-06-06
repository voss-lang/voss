"""V2-01: principles config substrate (loader, frozen config, merge, defaults)."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from voss.harness.principles import (
    DEFAULT_PRINCIPLES,
    PrinciplesConfig,
    VossPrinciplesConfigError,
    load_principles,
    resolve_principles,
    resolve_with_sources,
)


def _write(cwd: Path, text: str) -> None:
    (cwd / ".voss").mkdir(parents=True, exist_ok=True)
    (cwd / ".voss" / "principles.yml").write_text(text, encoding="utf-8")


# ---- Task 1: config + defaults + loader -----------------------------------


def test_config_is_frozen() -> None:
    cfg = PrinciplesConfig((("a", "b"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.principles = (("x", "y"),)  # type: ignore[misc]


def test_default_principles_exact_six() -> None:
    d = dict(DEFAULT_PRINCIPLES)
    assert list(d.keys()) == ["diff", "evidence", "tests", "scope", "review", "reversibility"]
    assert d["diff"] == "Make the smallest diff that solves the task."
    assert d["evidence"] == "No factual claim without evidence."
    assert d["tests"] == "Tests prove behavior, not coverage theater."
    assert d["scope"] == "Do not edit outside assigned scope."
    assert d["review"] == "Review intent and correctness before style."
    assert d["reversibility"] == "Prefer reversible changes unless the user approves risk."


def test_valid_file_loads(tmp_path: Path) -> None:
    _write(tmp_path, 'foo: "bar"\n')
    layer = load_principles(tmp_path)
    assert ("foo", "bar") in layer.items


def test_missing_file_no_raise(tmp_path: Path) -> None:
    layer = load_principles(tmp_path)  # no .voss/principles.yml
    assert layer.items == ()
    assert layer.disable == ()


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    _write(tmp_path, "foo: : :\n")
    with pytest.raises(VossPrinciplesConfigError):
        load_principles(tmp_path)


def test_top_level_list_raises(tmp_path: Path) -> None:
    _write(tmp_path, "- a\n- b\n")
    with pytest.raises(VossPrinciplesConfigError):
        load_principles(tmp_path)


def test_non_string_value_raises(tmp_path: Path) -> None:
    _write(tmp_path, "tests: 5\n")
    with pytest.raises(VossPrinciplesConfigError):
        load_principles(tmp_path)


def test_bad_disable_raises(tmp_path: Path) -> None:
    _write(tmp_path, "disable: 5\n")
    with pytest.raises(VossPrinciplesConfigError):
        load_principles(tmp_path)


# ---- Task 2: merge (additive override + disable) + sources -----------------


def _sources(cwd: Path) -> dict[str, str]:
    return {k: src for k, _, src in resolve_with_sources(cwd)}


def test_no_file_six_defaults(tmp_path: Path) -> None:
    cfg = resolve_principles(tmp_path)
    assert cfg.keys() == ["diff", "evidence", "tests", "scope", "review", "reversibility"]
    assert all(src == "default" for src in _sources(tmp_path).values())


def test_add_key(tmp_path: Path) -> None:
    _write(tmp_path, 'bias: "Prefer boring tech."\n')
    cfg = resolve_principles(tmp_path)
    assert cfg.keys() == [
        "diff", "evidence", "tests", "scope", "review", "reversibility", "bias",
    ]
    src = _sources(tmp_path)
    assert src["bias"] == "project"
    assert src["diff"] == "default"


def test_override_keeps_position(tmp_path: Path) -> None:
    _write(tmp_path, 'tests: "Custom tests rule."\n')
    cfg = resolve_principles(tmp_path)
    m = cfg.as_mapping()
    assert m["tests"] == "Custom tests rule."
    # position stable: tests stays 3rd
    assert cfg.keys().index("tests") == 2
    assert _sources(tmp_path)["tests"] == "project"
    assert _sources(tmp_path)["scope"] == "default"


def test_disable_list_removes(tmp_path: Path) -> None:
    _write(tmp_path, "disable: [scope]\n")
    cfg = resolve_principles(tmp_path)
    assert "scope" not in cfg.keys()
    assert len(cfg) == 5


def test_null_value_disables(tmp_path: Path) -> None:
    _write(tmp_path, "review: null\n")
    cfg = resolve_principles(tmp_path)
    assert "review" not in cfg.keys()
    assert len(cfg) == 5


def test_disable_wins_over_redefine(tmp_path: Path) -> None:
    # D-04 locked conflict rule: explicit disable beats a redefinition.
    _write(tmp_path, 'disable: [tests]\ntests: "ignored override"\n')
    cfg = resolve_principles(tmp_path)
    assert "tests" not in cfg.keys()
