"""Skill smoke tests — one per SKL + a registry-count guard.

Each stub fails with `pytest.fail("not yet")` until its owning downstream
plan turns it green. Test names are FINAL contracts — do not rename.

Ownership:
  T7-02 → test_rename_symbol (SKL-01), test_voss_lint (SKL-06)  [GREEN]
  T7-03 → test_summarize_diff (SKL-03), test_audit_cognition (SKL-05)
  T7-04 → test_add_test (SKL-02), test_port_py_to_voss (SKL-04)

`test_registry_count` is the last-to-green guard: it asserts the FINAL
registry count of 7 and is owned by T7-04. It legitimately stays RED through
T7-02 and T7-03 and MUST NOT be weakened (T7-01-PLAN registry-count
contract). T7-02 proves its own two registrations via direct
`default_skill_registry().get(...)` checks inside the two tests it owns.
"""
import io
import json
import shutil
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from voss.harness.skill_registry import default_skill_registry

from tests.skills.conftest import PermissionGate, PlainRenderer, make_toolset

FIXTURES = Path(__file__).parent / "fixtures"


def test_rename_symbol(tmp_path: Path) -> None:  # SKL-01 — owned by T7-02
    from voss.harness.skills.rename_symbol import run

    for f in (FIXTURES / "rename-symbol").glob("*.py"):
        shutil.copy(f, tmp_path / f.name)

    before = {p.name: p.read_text() for p in tmp_path.glob("*.py")}

    # (a) plan mode — clean refusal, ZERO bytes mutated, no escalation.
    run(
        cwd=tmp_path,
        provider=None,
        history=None,
        record=None,
        renderer=PlainRenderer(),
        tools=make_toolset(tmp_path),
        gate=PermissionGate(mode="plan"),
        args=["foo", "bar"],
    )
    after_plan = {p.name: p.read_text() for p in tmp_path.glob("*.py")}
    assert after_plan == before, "plan mode mutated files — gate bypass"

    # (b) edit/auto — rename foo -> bar across every *.py via gated fs_edit.
    run(
        cwd=tmp_path,
        provider=None,
        history=None,
        record=None,
        renderer=PlainRenderer(),
        tools=make_toolset(tmp_path),
        gate=PermissionGate(auto_yes=True),
        args=["foo", "bar"],
    )
    joined = "\n".join(p.read_text() for p in sorted(tmp_path.glob("*.py")))
    assert "foo" not in joined and "bar" in joined, joined

    entry = default_skill_registry().get("rename-symbol")
    assert entry is not None and entry.mutating is True


def test_voss_lint(tmp_path: Path) -> None:  # SKL-06 — owned by T7-02
    from voss.harness.skills.voss_lint_as_skill import run

    shutil.copy(FIXTURES / "voss-lint" / "bad.voss", tmp_path / "bad.voss")

    buf = io.StringIO()
    with patch("click.echo", side_effect=lambda s, **kw: buf.write(str(s) + "\n")):
        run(
            cwd=tmp_path,
            provider=None,
            history=None,
            record=types.SimpleNamespace(model="fake", id="t"),
            renderer=PlainRenderer(),
            tools=make_toolset(tmp_path),
            gate=PermissionGate(auto_yes=True),
            args=[str(tmp_path)],
        )

    schema = json.loads(buf.getvalue())
    assert schema["version"] == 1
    assert isinstance(schema["findings"], list)
    assert schema["findings"], "expected the seeded bad.voss violation"

    expected_keys = {"file", "line", "col", "rule", "severity", "msg", "hint"}
    for finding in schema["findings"]:
        assert set(finding) == expected_keys, finding

    seeded = [f for f in schema["findings"] if f["rule"] == "ANLY001"]
    assert seeded, schema["findings"]
    assert seeded[0]["severity"] == "warning"
    assert "unguarded" in seeded[0]["msg"]

    entry = default_skill_registry().get("voss-lint-as-skill")
    assert entry is not None and entry.mutating is False


def test_add_test():  # SKL-02 — owned by T7-04
    pytest.fail("not yet")


def test_summarize_diff():  # SKL-03 — owned by T7-03
    pytest.fail("not yet")


def test_port_py_to_voss():  # SKL-04 — owned by T7-04
    pytest.fail("not yet")


def test_audit_cognition():  # SKL-05 — owned by T7-03
    pytest.fail("not yet")


def test_registry_count():  # last-to-green guard — owned by T7-04
    pytest.fail("not yet")
