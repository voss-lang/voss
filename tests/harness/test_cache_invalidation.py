"""CACHE-06: D-08 drift triggers force a byte-different rendered prefix."""

import json

import pytest

from voss.harness.agent import _compose_loop_system, _compose_system_blocks


def _render(
    *,
    voss_md: str,
    cognition: str,
    prior_ctx: str,
    max_iters: int,
) -> list[dict]:
    return _compose_system_blocks(
        voss_md_block=f"# VOSS.md\n{voss_md}" if voss_md else "",
        cognition_text=cognition,
        prior_context_text=prior_ctx,
        loop_system=_compose_loop_system(max_iters),
    )


BASE = {
    "voss_md": "stable VOSS instructions",
    "cognition": "stable cognition",
    "prior_ctx": "stable prior context",
    "max_iters": 8,
}


@pytest.mark.parametrize(
    "drift_key,changed_value",
    (
        ("voss_md", "updated VOSS instructions"),
        ("cognition", "updated cognition"),
        ("prior_ctx", "updated prior context"),
        ("max_iters", 9),
    ),
    ids=("voss_md", "cognition", "prior_ctx", "max_iters"),
)
def test_drift_changes_rendered_prefix(drift_key: str, changed_value) -> None:
    before = dict(BASE)
    after = {**BASE, drift_key: changed_value}

    before_bytes = json.dumps(_render(**before), sort_keys=True).encode()
    after_bytes = json.dumps(_render(**after), sort_keys=True).encode()

    assert before_bytes != after_bytes, f"{drift_key} drift did not alter prefix"
