"""CACHE-06: prompt cache invalidation drift stubs for T4-03."""

import pytest


@pytest.mark.parametrize(
    "drift_key",
    ("voss_md", "cognition", "prior_ctx", "max_iters"),
    ids=("voss_md", "cognition", "prior_ctx", "max_iters"),
)
def test_drift_changes_rendered_prefix(drift_key: str) -> None:
    pytest.fail("T4-03 lands cache invalidation")
