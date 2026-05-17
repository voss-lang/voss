"""T4 D-04 cache-token extraction helpers.

Use a universal probe instead of provider/model branching so Anthropic, OpenAI,
stub, and future provider usage shapes all degrade to the same default-zero
contract.
"""
from __future__ import annotations


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def extract_cache_tokens(usage_obj) -> tuple[int, int]:
    if usage_obj is None:
        return (0, 0)

    creation = _as_int(getattr(usage_obj, "cache_creation_input_tokens", 0))
    read = _as_int(getattr(usage_obj, "cache_read_input_tokens", 0))

    if read == 0:
        details = getattr(usage_obj, "prompt_tokens_details", None)
        if isinstance(details, dict):
            cached_tokens = details.get("cached_tokens", 0)
        else:
            cached_tokens = getattr(details, "cached_tokens", 0)
        read = _as_int(cached_tokens)

    return (creation, read)
