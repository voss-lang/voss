"""Reviewer-B: independent tiered judgment reviewer (O4-02, ORVW-04..07).

B sees ONLY: original idea, acceptance criteria, artifact, repository context,
and Reviewer-A's verification summary. Zero EM narrative. The isolation
guarantee is structural: `messages[]` contains exactly 2 entries (system + user)
and the user message is built from card attributes only. No method on ReviewerB
accepts EM context.

B produces a ReviewerVerdict via a single `provider.complete()` call.
ParseError / None → fail-safe verdict="block" (a parse failure at the gate
is safer than a silent skip — contrast with judge.py which returns None).

ReviewerVerdict is a frozen dataclass (O3-01), not a pydantic BaseModel. This
module defines a pydantic mirror `_ReviewerBOutput` for use as `response_format`
in `provider.complete()`, then translates the parsed output back to the frozen
dataclass with source="B" and tier hardcoded (do not trust the LLM's values).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from voss.template_render import render_package_template
from voss.harness.prompt_override import default_runtime_vars, load_prompt
from voss_runtime.exceptions import ParseError
from voss_runtime.providers.base import ModelProvider, ProviderResponse

from .verdict import ReviewerVerdict


# Pydantic mirror — ReviewerVerdict is a frozen dataclass; provider.complete()
# needs a pydantic BaseModel as response_format.
class _ReviewerBOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conf: float
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: list[str] = []
    domain_inferred: str = "unknown"  # VREV-06: clamped in _to_verdict


REVIEWER_B_SYSTEM = render_package_template(
    "voss",
    "templates/prompts/reviewer_b_system.txt.jinja",
    {},
)


class ReviewerB:
    """Independent tiered judgment reviewer implementing the Reviewer Protocol.

    Constructor accepts provider + two model strings (fast/strong) so the
    tier is injectable for testing. Tier selection happens at call time via
    the `tier` keyword argument to `review()`.
    """

    def __init__(
        self,
        *,
        provider: ModelProvider,
        fast_model: str,
        strong_model: str,
    ) -> None:
        self._provider = provider
        self._fast_model = fast_model
        self._strong_model = strong_model

    def review(
        self,
        card: object,
        *,
        tier: Literal["fast", "strong"] = "fast",
    ) -> ReviewerVerdict:
        """Produce a ReviewerVerdict via a single provider.complete() call.

        Sync (matches the Reviewer Protocol). Internally bridges the async
        provider call using a thread-pool executor when an event loop is
        already running (e.g. inside pytest-asyncio tests).
        """
        model = self._fast_model if tier == "fast" else self._strong_model

        # Build user message from card attributes ONLY — isolation guarantee.
        original_idea = getattr(card, "original_idea", "") or ""
        acceptance = getattr(card, "acceptance_criteria", "") or getattr(card, "acceptance", "") or ""
        artifact_text = getattr(card, "artifact_text", "") or str(getattr(card, "artifact", "") or "")
        file_diff = getattr(card, "file_diff", "") or ""
        a_verification = getattr(card, "a_verification_summary", "") or ""

        user_msg = (
            f"## Original Idea\n{original_idea}\n\n"
            f"## Acceptance Criteria\n{acceptance}\n\n"
            f"## Artifact\n{artifact_text}\n\n"
            f"## File Diff\n{file_diff}\n\n"
            f"## Reviewer-A Verification Summary\n{a_verification}\n"
        )

        # Prompt resolved at load time so a project copy under .voss/prompts/
        # is honored; absent copy is byte-identical to REVIEWER_B_SYSTEM (R5).
        prompt_root = Path.cwd()
        system = load_prompt(
            "reviewer_b_system",
            resource="templates/prompts/reviewer_b_system.txt.jinja",
            cwd=prompt_root,
            runtime_vars=default_runtime_vars("reviewer-b", prompt_root),
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        resp = self._call_provider_sync(messages, model)
        return self._to_verdict(resp, tier)

    def _call_provider_sync(
        self,
        messages: list[dict],
        model: str,
    ) -> ProviderResponse:
        """Bridge async provider.complete() into the sync review() method."""
        coro = self._provider.complete(
            messages=messages,
            model=model,
            response_format=_ReviewerBOutput,
            temperature=0.0,
        )
        try:
            asyncio.get_running_loop()
            # Already in async context (e.g. pytest-asyncio) — run in thread.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            # No running loop — straightforward.
            return asyncio.run(coro)

    # VREV-06 (T-V6-02-01): the LLM-controlled domain string is clamped to this
    # closed set before it becomes a verdict value; anything else -> "unknown".
    _ALLOWED_DOMAINS: frozenset[str] = frozenset({"code", "ai", "docs", "unknown"})

    @staticmethod
    def _to_verdict(
        resp: ProviderResponse,
        tier: Literal["fast", "strong"],
    ) -> ReviewerVerdict:
        """Translate provider response to ReviewerVerdict.

        Hardcodes source="B" and the actual tier — LLM output does NOT
        control these fields.
        """
        parsed = resp.parsed
        if parsed is None:
            return ReviewerVerdict(
                conf=0.0,
                source="B",
                tier=tier,
                verdict="block",
                notes="structured output was None",
                evidence_refs=(),
            )
        domain = (
            parsed.domain_inferred
            if parsed.domain_inferred in ReviewerB._ALLOWED_DOMAINS
            else "unknown"
        )
        return ReviewerVerdict(
            conf=float(parsed.conf),
            source="B",
            tier=tier,
            verdict=parsed.verdict,
            notes=parsed.notes,
            evidence_refs=tuple(parsed.evidence_refs),
            domain_inferred=domain,  # type: ignore[arg-type]
        )
