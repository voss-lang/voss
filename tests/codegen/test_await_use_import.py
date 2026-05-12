from __future__ import annotations

from voss.analyzer import analyze
from voss.codegen import generate_python
from voss.parser import parse


def _compile(source: str) -> str:
    program = parse(source)
    analysis = analyze(program, emit_indexes=False)
    result = generate_python(program, analysis=analysis)
    return result.source


def test_use_imported_name_is_awaited_in_async_context():
    source = _compile("use foo::bar\nfn caller() { bar() }\n")
    assert "await bar()" in source


def test_use_imported_alias_is_awaited():
    source = _compile("use foo::bar as baz\nfn caller() { baz() }\n")
    assert "await baz()" in source


def test_use_imported_member_call_not_awaited():
    source = _compile("use voss::harness as h\nfn caller() { h.run_turn() }\n")
    assert "await h.run_turn()" not in source


def test_local_fn_still_awaited():
    source = _compile("fn other() { }\nfn caller() { other() }\n")
    assert "await other()" in source
