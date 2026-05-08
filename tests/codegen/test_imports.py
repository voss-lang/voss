from __future__ import annotations

import pytest

from voss.ast_nodes import UseStmt
from voss.codegen import ImportCollector, generate_python

from tests.codegen.conftest import (
    assert_no_compiler_imports,
    assert_python_parses,
    program,
    span,
)


def test_import_collector_sorts_runtime_names():
    collector = ImportCollector()
    collector.add_runtime("ProbableValue")
    collector.add_runtime("ContextScope")
    lines, _meta = collector.render()
    assert "from voss_runtime import ContextScope, ProbableValue" in lines


def test_import_collector_keeps_asyncio_separate():
    collector = ImportCollector()
    collector.add_stdlib("asyncio")
    collector.add_runtime("ContextScope")
    lines, _meta = collector.render()
    assert "import asyncio" in lines
    assert "from voss_runtime import ContextScope" in lines
    # Stdlib import must come before runtime import.
    assert lines.index("import asyncio") < lines.index("from voss_runtime import ContextScope")


def test_import_collector_lowers_use_two_part_path():
    collector = ImportCollector()
    collector.add_use(("foo", "bar"))
    lines, _meta = collector.render()
    assert "from foo import bar" in lines


def test_import_collector_lowers_use_three_part_path():
    collector = ImportCollector()
    collector.add_use(("foo", "bar", "baz"))
    lines, _meta = collector.render()
    assert "from foo.bar import baz" in lines


def test_import_collector_supports_alias():
    collector = ImportCollector()
    collector.add_use(("foo", "bar"), alias="baz")
    lines, _meta = collector.render()
    assert "from foo import bar as baz" in lines


def test_generated_source_has_no_compiler_imports():
    use = UseStmt(span=span(), path=("foo", "bar"))
    result = generate_python(program(use))
    assert_no_compiler_imports(result.source)
    assert_python_parses(result.source)
    assert "from foo import bar" in result.source
