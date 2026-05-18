"""
M10-06 performance sampling (10K / 100K).

These tests are intentionally lightweight. Real large-fixture generation
and timing is a manual checkpoint as described in M10-06 Task 2.
"""

import pytest


@pytest.mark.slow
def test_10k_scan_budget_placeholder():
    """Placeholder – real 10K fixture timing is recorded in the SUMMARY."""
    # In a real run the executor would generate a 10K LoC tree and assert <= 5s
    # or record the measured time + whether partial warning appeared.
    pytest.skip("Manual performance checkpoint – see M10-06 SUMMARY")


@pytest.mark.slow
def test_100k_scan_budget_placeholder():
    """Placeholder for 100K-LoC scan."""
    pytest.skip("Manual performance checkpoint – see M10-06 SUMMARY")
