"""Skill smoke tests — 7 red stubs (T7-01 seam).

Each stub fails with `pytest.fail("not yet")` until its owning downstream
plan turns it green. Test names are FINAL contracts — do not rename.

Ownership:
  T7-02 → test_rename_symbol (SKL-01), test_voss_lint (SKL-06), test_registry_count
  T7-03 → test_summarize_diff (SKL-03), test_audit_cognition (SKL-05)
  T7-04 → test_add_test (SKL-02), test_port_py_to_voss (SKL-04)

Functions take no fixture params at this stage; downstream plans add
`git_repo`/`tmp_path` params when they implement the body. Do NOT import
skill handlers here — they do not exist yet, and importing them would make
collection error instead of cleanly fail.
"""
import pytest


def test_rename_symbol():  # SKL-01 — owned by T7-02
    pytest.fail("not yet")


def test_add_test():  # SKL-02 — owned by T7-04
    pytest.fail("not yet")


def test_summarize_diff():  # SKL-03 — owned by T7-03
    pytest.fail("not yet")


def test_port_py_to_voss():  # SKL-04 — owned by T7-04
    pytest.fail("not yet")


def test_audit_cognition():  # SKL-05 — owned by T7-03
    pytest.fail("not yet")


def test_voss_lint():  # SKL-06 — owned by T7-02
    pytest.fail("not yet")


def test_registry_count():  # all SKL registered — owned by T7-02
    pytest.fail("not yet")
