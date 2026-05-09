"""CLI matrix test (EX-01..03): every example through check, compile, run."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.examples.helpers import (
    SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    assert_no_repo_cache_artifacts,
    assert_python_parses,
    copy_example,
    deterministic_subprocess_env,
    run_cmd,
    run_voss,
)


# Sitecustomize for research subprocess (provides webSearch in builtins).
RESEARCH_SUBPROCESS_SITECUSTOMIZE = """
import builtins as _builtins
from voss_runtime import tool as _voss_tool


@_voss_tool
def webSearch(query: str, max_results: int = 5) -> list:
    return [f"result-{i} for {query}" for i in range(max_results)]


_builtins.webSearch = webSearch
"""


# Per-example matrix configuration: stub default response and the extra
# sitecustomize text required for that example's subprocess runs.
EXAMPLE_MATRIX = [
    pytest.param(
        "classify",
        "cancel_subscription",
        "",
        "cancel_subscription",
        id="classify",
    ),
    pytest.param(
        "support",
        "stub-response",
        SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
        None,  # support generated has no main entry; stdout is empty.
        id="support",
    ),
    pytest.param(
        "research",
        "STUB SUMMARY",
        RESEARCH_SUBPROCESS_SITECUSTOMIZE,
        "STUB SUMMARY",
        id="research",
    ),
]


@pytest.mark.parametrize(
    "example,stub_response,extra_sitecustomize,expected_stdout_contains",
    EXAMPLE_MATRIX,
)
def test_cli_matrix(
    tmp_path: Path,
    example: str,
    stub_response: str,
    extra_sitecustomize: str,
    expected_stdout_contains: str | None,
):
    copy_example(tmp_path, example)
    source_name = f"{example}.voss"
    out_path = tmp_path / "out" / f"{example}.py"

    env = deterministic_subprocess_env(
        tmp_path,
        default_response=stub_response,
        extra_sitecustomize=extra_sitecustomize,
    )

    # 1) voss check
    check_result = run_voss(["check", source_name], cwd=tmp_path, env=env)
    assert check_result.returncode == 0, check_result.stderr
    assert "Traceback" not in check_result.stderr
    # check must not emit a generated python file.
    assert not (tmp_path / f"{example}.py").exists()

    # 2) voss compile
    compile_result = run_voss(
        ["compile", source_name, "-o", str(out_path)],
        cwd=tmp_path,
        env=env,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    assert out_path.exists()
    assert_python_parses(out_path)

    # Generated python must not import the compiler.
    generated_source = out_path.read_text()
    assert "from voss " not in generated_source
    assert "from voss." not in generated_source
    assert "import voss\n" not in generated_source
    assert "voss.analyzer" not in generated_source
    assert "voss.codegen" not in generated_source

    # 3) python3 generated.py
    py_result = run_cmd(
        [sys.executable, str(out_path)],
        cwd=tmp_path,
        env=env,
        timeout=120.0,
    )
    assert py_result.returncode == 0, py_result.stderr
    assert "Traceback" not in py_result.stderr

    # 4) voss run
    run_result = run_voss(
        ["run", source_name],
        cwd=tmp_path,
        env=env,
        timeout=120.0,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr

    # 5) stdout parity between voss compile + python3 and voss run.
    assert run_result.stdout == py_result.stdout
    if expected_stdout_contains is not None:
        assert expected_stdout_contains in run_result.stdout

    # 6) no repo-local cache or generated artifacts.
    assert_no_repo_cache_artifacts()
    repo_root = Path(__file__).resolve().parents[2]
    leaks = [
        p
        for p in (
            repo_root / f"{example}.py",
            repo_root / "out",
        )
        if p.exists()
    ]
    assert not leaks, f"unexpected repo-root artifacts: {leaks}"
