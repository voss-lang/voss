"""Public API stability test.

Pins the exact public surface of ``voss_runtime`` and ``voss.harness``.
Any change to ``__all__`` MUST update the expected sets below in the same
PR — that's the human signal that the public-API contract in
``docs/sdk.md`` is being touched.

This test does NOT prevent change. It surfaces change.
"""

from __future__ import annotations


EXPECTED_RUNTIME_PUBLIC_API: frozenset[str] = frozenset(
    {
        "AgentHandle",
        "BudgetExceededError",
        "BudgetScope",
        "ConfidenceTooLowError",
        "ContextScope",
        "EpisodicMemory",
        "ModelProvider",
        "ParseError",
        "ProbableValue",
        "ProviderError",
        "ProviderResponse",
        "RuntimeConfig",
        "SemanticMatcher",
        "SemanticMemory",
        "StubProvider",
        "ToolDescriptor",
        "VossAgent",
        "VossRuntimeError",
        "WorkingMemory",
        "configure",
        "current_budget",
        "gather",
        "get_config",
        "reset_config",
        "run_with_budget",
        "tool",
    }
)


EXPECTED_HARNESS_PUBLIC_API: frozenset[str] = frozenset(
    {
        "Plan",
        "PermissionGate",
        "RunSemantics",
        "ToolCall",
        "ToolEntry",
        "TurnResult",
        "main",
        "run_turn",
    }
)


def test_runtime_public_api_matches_contract():
    import voss_runtime

    actual = frozenset(voss_runtime.__all__)
    added = actual - EXPECTED_RUNTIME_PUBLIC_API
    removed = EXPECTED_RUNTIME_PUBLIC_API - actual

    assert not added and not removed, (
        "voss_runtime.__all__ drift detected.\n"
        f"  Added (new public symbols): {sorted(added)}\n"
        f"  Removed (broken public surface): {sorted(removed)}\n"
        "If this change is intentional, update EXPECTED_RUNTIME_PUBLIC_API "
        "in this test AND update docs/sdk.md."
    )


def test_runtime_public_api_symbols_importable():
    import voss_runtime

    for name in EXPECTED_RUNTIME_PUBLIC_API:
        assert hasattr(voss_runtime, name), (
            f"voss_runtime claims {name} in __all__ but the symbol is missing."
        )


def test_harness_public_api_matches_contract():
    import voss.harness as harness

    actual = frozenset(harness.__all__)
    added = actual - EXPECTED_HARNESS_PUBLIC_API
    removed = EXPECTED_HARNESS_PUBLIC_API - actual

    assert not added and not removed, (
        "voss.harness.__all__ drift detected.\n"
        f"  Added (new public symbols): {sorted(added)}\n"
        f"  Removed (broken public surface): {sorted(removed)}\n"
        "If this change is intentional, update EXPECTED_HARNESS_PUBLIC_API "
        "in this test AND update docs/sdk.md."
    )


def test_harness_public_api_symbols_importable():
    import voss.harness as harness

    for name in EXPECTED_HARNESS_PUBLIC_API:
        assert hasattr(harness, name), (
            f"voss.harness claims {name} in __all__ but the symbol is missing."
        )
