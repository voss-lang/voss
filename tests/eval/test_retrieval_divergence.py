"""J3-01 D-20: query(top_k=5) vs query(top_k=15)[:5] divergence on dev queries."""
from __future__ import annotations

import pytest

from voss.eval.retrieval import POOL_SIZE, divergence, main
from voss.harness.memory_store import Hit


def _hits(*locators: str) -> list[Hit]:
    return [Hit(source="code", locator=loc, score=1.0, excerpt="") for loc in locators]


class FakeIndex:
    def __init__(self, rankings: dict[tuple[str, int], list[Hit]]) -> None:
        self.rankings = rankings

    def query(self, text: str, top_k: int = 5) -> list[Hit]:
        return self.rankings[(text, top_k)]


def test_divergence_lists_only_queries_whose_top_five_differs() -> None:
    same = _hits("a", "b", "c", "d", "e")
    index = FakeIndex({
        ("same", 5): same,
        ("same", POOL_SIZE): same + _hits("f", "g"),
        ("moved", 5): _hits("a", "b", "c", "d", "e"),
        ("moved", POOL_SIZE): _hits("a", "c", "b", "d", "e", "f"),
    })
    queries = {"q2": {"text": "moved"}, "q1": {"text": "same"}}

    assert divergence(index, queries) == ["q2"]


def test_divergence_command_has_no_split_option(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["divergence", "--help"])

    assert exit_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "--root" in help_text
    assert "--split" not in help_text
    assert "--locked-final" not in help_text
