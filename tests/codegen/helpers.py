from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from voss.diagnostics import AnalysisResult, EmittedIndex


def write_generated_module(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / f"{name}.py"
    path.write_text(source)
    return path


def load_module_from_path(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_module_with_globals(
    path: Path, module_name: str, globals_: dict[str, object]
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update(globals_)
    sys.modules.pop(module_name, None)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def assert_allowed_imports(
    source: str, declared_user_roots: set[str] = frozenset()
) -> None:
    allowed_roots = {"asyncio", "pydantic", "voss_runtime", *declared_user_roots}
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert root in allowed_roots, f"unexpected import root: {root}"
                assert root != "voss", "generated source must not import compiler modules"
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "generated source must not use relative imports"
            assert node.module is not None
            root = node.module.split(".", 1)[0]
            assert root in allowed_roots, f"unexpected import root: {root}"
            assert root != "voss", "generated source must not import compiler modules"


def fake_analysis(index_path: Path | None = None) -> AnalysisResult:
    if index_path is None:
        return AnalysisResult(diagnostics=(), indexes=())
    return AnalysisResult(
        diagnostics=(),
        indexes=(
            EmittedIndex(
                match_id="match_7_5",
                path=index_path,
                case_count=3,
                threshold=0.55,
                model="fake-embedding-model",
            ),
        ),
    )
