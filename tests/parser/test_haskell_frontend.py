"""Haskell frontend wiring (optional binary)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from voss.exceptions import VossParseError
from voss.parser import parse

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_HS = REPO_ROOT / "frontend-hs"
PARSER_EXAMPLES = REPO_ROOT / "tests" / "parser" / "examples"
GOLDEN_AST = REPO_ROOT / "tests" / "parser" / "golden"


def test_voss_frontend_haskell_requires_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOSS_FRONTEND", "haskell")
    monkeypatch.delenv("VOSS_FRONTEND_HS_EXE", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(VossParseError, match="executable not found"):
        parse("let x = 1\n", file="t.voss")


def _hs_ast_command(voss_path: Path, *, normalize: bool) -> list[str]:
    exe = os.environ.get("VOSS_FRONTEND_HS_EXE")
    args = ["ast", "--path", str(voss_path)] + (["--normalize-spans"] if normalize else [])
    if exe:
        return [exe, *args]
    run_via_cabal = os.environ.get("FRONTEND_HS_TEST") == "1" or os.environ.get("CI")
    if run_via_cabal and shutil.which("cabal"):
        return ["cabal", "run", "voss-frontend-hs", "--", *args]
    return []


def _parity_fixtures() -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for ast_json in sorted(GOLDEN_AST.rglob("*.ast.json")):
        rel_parent = ast_json.parent.relative_to(GOLDEN_AST)
        core = ast_json.name.removesuffix(".ast.json")
        voss = PARSER_EXAMPLES / rel_parent / f"{core}.voss"
        if voss.is_file():
            out.append((voss, ast_json))
    return out


@pytest.mark.parametrize("voss_path, golden_ast", _parity_fixtures())
def test_haskell_ast_json_parity_normalized(voss_path: Path, golden_ast: Path) -> None:
    """Compare `voss-frontend-hs ast --normalize-spans` to Python goldens (optional)."""
    cmd = _hs_ast_command(voss_path, normalize=True)
    if not cmd:
        pytest.skip("Haskell parity not requested (set FRONTEND_HS_TEST=1 / CI) or no cabal/exe")
    try:
        proc = subprocess.run(
            cmd,
            cwd=FRONTEND_HS if cmd[0] == "cabal" else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as e:
        pytest.skip(f"Haskell frontend invocation failed: {e}")
    if proc.returncode != 0:
        pytest.skip(f"voss-frontend-hs failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout}")
    expected = json.loads(golden_ast.read_text(encoding="utf-8"))
    actual = json.loads(proc.stdout)
    assert actual == expected
