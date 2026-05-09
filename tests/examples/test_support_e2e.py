"""End-to-end validation for ``support.voss`` (PRD §7.2, EX-02).

Default tests are hermetic: they patch ``SemanticMatcher`` so cases are
encoded with synthetic 3-D vectors and use the runtime ``StubProvider``
for the ``ctx.ask`` fallback. No live providers, no model downloads.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.examples.helpers import (
    SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    assert_no_repo_cache_artifacts,
    assert_python_parses,
    copy_example,
    deterministic_subprocess_env,
    install_support_fake_encoder_in_process,
    register_stub,
    run_cmd,
    run_voss,
)


@pytest.fixture(autouse=True)
def _patch_semantic_matcher_in_process():
    """Patch SemanticMatcher and IndexBuilder for in-process usage."""
    install_support_fake_encoder_in_process()
    yield


def _import_generated_module(path: Path, *, name: str = "voss_generated_support"):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _inject_support_helpers(module) -> None:
    """Provide escalate/refundFlow/authSupport helpers to a generated module."""
    module.escalate = lambda msg: f"[escalated] {msg}"
    module.refundFlow = lambda msg: f"[refund flow] {msg}"
    module.authSupport = lambda msg: f"[auth support] {msg}"


def test_support_check_has_no_errors_and_no_cache(tmp_path: Path):
    copy_example(tmp_path, "support")

    env = deterministic_subprocess_env(
        tmp_path,
        default_response="stub-response",
        extra_sitecustomize=SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    )
    result = run_voss(["check", "support.voss"], cwd=tmp_path, env=env)

    assert result.returncode == 0, result.stderr
    assert "error" not in result.stderr.lower()
    assert not (tmp_path / "support.py").exists()
    assert not (tmp_path / ".voss-cache").exists()
    assert_no_repo_cache_artifacts()


def test_support_compile_emits_temp_semantic_index(tmp_path: Path):
    copy_example(tmp_path, "support")

    out_path = tmp_path / "out" / "support.py"
    env = deterministic_subprocess_env(
        tmp_path,
        default_response="stub-response",
        extra_sitecustomize=SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    )
    result = run_voss(
        ["compile", "support.voss", "-o", str(out_path)],
        cwd=tmp_path,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    assert_python_parses(out_path)

    idx_path = tmp_path / ".voss-cache" / "support.idx"
    assert idx_path.exists(), "voss compile must emit support.idx under tmp .voss-cache"
    # Must not leak into repo root.
    assert_no_repo_cache_artifacts()

    manifest = json.loads(idx_path.read_text())
    assert manifest["program"] == "support"
    matches = manifest["matches"]
    assert isinstance(matches, list) and len(matches) == 1
    cases = matches[0]["cases"]
    assert len(cases) == 3
    labels = [c["label"] for c in cases]
    assert labels == ["case_0", "case_1", "case_2"]


@pytest.mark.parametrize(
    "user_message,expected_prefix",
    [
        ("I'm so angry, fix it", "[escalated] "),
        ("Can I get a refund?", "[refund flow] "),
        ("I can't log in", "[auth support] "),
    ],
)
def test_support_generated_routes_match_raw_python(
    tmp_path: Path, user_message: str, expected_prefix: str
):
    # Compile via in-process API so we can import the generated module.
    from voss import analyze, generate_python, parse

    copy_example(tmp_path, "support")
    src_path = tmp_path / "support.voss"
    program = parse(src_path.read_text(), file=str(src_path))
    analysis = analyze(
        program,
        source_path=str(src_path),
        project_root=tmp_path,
        cache_dir=Path(".voss-cache"),
        emit_indexes=True,
    )
    assert not analysis.errors
    result = generate_python(
        program,
        source_path=str(src_path),
        analysis=analysis,
        project_root=tmp_path,
        cache_dir=Path(".voss-cache"),
    )
    out_path = tmp_path / "out" / "support.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.source)
    assert_python_parses(out_path)

    module = _import_generated_module(out_path)
    _inject_support_helpers(module)

    from examples.raw_python.support import handle_message as raw_handle_message

    generated_value = asyncio.run(module.handleMessage(user_message))
    raw_value = asyncio.run(raw_handle_message(user_message))

    assert generated_value == expected_prefix + user_message
    assert raw_value == expected_prefix + user_message
    assert generated_value == raw_value


def test_support_generic_falls_through_to_stub(tmp_path: Path):
    """Wildcard branch in match goes through ContextScope + stub."""
    from voss import analyze, generate_python, parse

    copy_example(tmp_path, "support")
    src_path = tmp_path / "support.voss"
    program = parse(src_path.read_text(), file=str(src_path))
    analysis = analyze(
        program,
        source_path=str(src_path),
        project_root=tmp_path,
        cache_dir=Path(".voss-cache"),
        emit_indexes=True,
    )
    result = generate_python(
        program,
        source_path=str(src_path),
        analysis=analysis,
        project_root=tmp_path,
        cache_dir=Path(".voss-cache"),
    )
    out_path = tmp_path / "out" / "support.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.source)

    module = _import_generated_module(out_path, name="voss_generated_support_generic")
    _inject_support_helpers(module)

    from examples.raw_python.support import handle_message as raw_handle_message

    generic_msg = "What pricing tiers do you have?"
    expected_stub = "tier-info-from-stub"
    with register_stub(expected_stub):
        generated_value = asyncio.run(module.handleMessage(generic_msg))
        raw_value = asyncio.run(raw_handle_message(generic_msg))

    assert generated_value == expected_stub
    assert raw_value == expected_stub


def test_support_voss_run_matches_compile_python(tmp_path: Path):
    copy_example(tmp_path, "support")

    env = deterministic_subprocess_env(
        tmp_path,
        default_response="stub-response",
        extra_sitecustomize=SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    )

    out_path = tmp_path / "out" / "support.py"
    compile_result = run_voss(
        ["compile", "support.voss", "-o", str(out_path)],
        cwd=tmp_path,
        env=env,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    py_run = run_cmd(
        [sys.executable, str(out_path)],
        cwd=tmp_path,
        env=env,
    )
    assert py_run.returncode == 0, py_run.stderr
    assert "Traceback" not in py_run.stderr

    voss_run = run_voss(["run", "support.voss"], cwd=tmp_path, env=env)
    assert voss_run.returncode == 0, voss_run.stderr
    assert "Traceback" not in voss_run.stderr

    assert voss_run.stdout == py_run.stdout
    assert_no_repo_cache_artifacts()
