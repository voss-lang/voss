"""V10 RED scaffold — principles{} block compile + YAML merge (VLANG-01a).

Targets the planned surface: TeamConfig.principles (a PrinciplesConfig) and the
`compile_team(decl, cwd=...)` keyword. These do not exist yet — RED expected.
No expected-fail/skip masks (gsd-scaffold-fictional-api).
"""
from __future__ import annotations

from pathlib import Path

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import compile_team


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def _write_principles_yaml(cwd: Path, text: str) -> None:
    (cwd / ".voss").mkdir(parents=True, exist_ok=True)
    (cwd / ".voss" / "principles.yml").write_text(text, encoding="utf-8")


_TEAM_WITH_PRINCIPLES = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  principles {
    diff: "Block-level diff principle."
    evidence: "Block-level evidence principle."
  }
  roster e {
    backend { scope: "src/**" }
  }
}
"""


def test_principles_block_compiles_to_principles_config() -> None:
    from voss.harness.principles import PrinciplesConfig

    config, _registry = compile_team(_only_team(_prog(_TEAM_WITH_PRINCIPLES)))
    assert isinstance(config.principles, PrinciplesConfig)
    keys = dict(config.principles.principles)
    assert keys["diff"] == "Block-level diff principle."
    assert keys["evidence"] == "Block-level evidence principle."


def test_principles_block_and_yaml_merge(tmp_path: Path) -> None:
    # File layer sets `diff`; the block overrides `diff` and adds `evidence`.
    # LOCKED order: merge(merge(DEFAULTS, file_layer), block_layer) — block wins.
    _write_principles_yaml(
        tmp_path,
        'diff: "File-level diff principle."\n',
    )
    config, _registry = compile_team(
        _only_team(_prog(_TEAM_WITH_PRINCIPLES)), cwd=tmp_path
    )
    merged = dict(config.principles.principles)
    assert merged["diff"] == "Block-level diff principle."  # block overrides file
    assert merged["evidence"] == "Block-level evidence principle."
