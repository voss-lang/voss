"""Shared routing and tool-free conversation for the CLI and server."""
from __future__ import annotations

from pathlib import Path

from voss_runtime import EpisodicMemory
from voss_runtime.providers.base import ModelProvider, ProviderResponse

from .agent import HISTORY_WINDOW, _compose_prior_context_block


SYSTEM = """You are the ambient assistant inside the Voss shell.
Answer directly and concisely. You may use the provided harness state and
project summary, but you do not have tool access in this phase. If the user
asks for code changes, tests, shell execution, multi-agent work, or any durable
repo operation, say that the request should be handled as a Voss run instead of
pretending to do it. Do not identify yourself as Voss; Voss is the harness that
can promote this conversation into a structured run."""

_WORK_INTENT_PREFIXES = (
    "add ",
    "build ",
    "change ",
    "check ",
    "create ",
    "debug ",
    "fix ",
    "implement ",
    "inspect ",
    "investigate ",
    "make ",
    "modify ",
    "patch ",
    "refactor ",
    "read ",
    "remove ",
    "repair ",
    "run ",
    "search ",
    "test ",
    "update ",
    "use ",
    "write ",
)
_WORK_INTENT_TERMS = (
    " add test",
    " add tests",
    " change ",
    " edit ",
    " fix ",
    " implement ",
    " refactor ",
    " run tests",
    " update ",
    " write ",
    " open pr",
    " pull request",
    " github",
    " mcp ",
    " skill ",
    " skills ",
    " inspect ",
    " check ",
    " read ",
    " search ",
    " git ",
    " fetch ",
    " review ",
)
_STATUS_QUESTION_TERMS = (
    "what model",
    "which model",
    "model are you",
    "model is active",
    "what auth",
    "which auth",
    "auth path",
    "credential source",
    "who are you",
    "what are you",
    "status",
)


def route(line: str) -> str:
    """Route a conversation turn before entering the structured Voss Plan loop."""
    normalized = " ".join(line.lower().strip().split())
    if not normalized:
        return "ambient"
    if normalized in {"go ahead", "do it", "continue", "proceed"} or normalized.startswith(_WORK_INTENT_PREFIXES):
        return "voss_run"
    padded = f" {normalized} "
    if any(term in padded for term in _WORK_INTENT_TERMS):
        return "voss_run"
    if any(term in normalized for term in _STATUS_QUESTION_TERMS):
        return "local"
    return "ambient"


def status_answer(*, provider: str, model: str, mode: str) -> str:
    parts = [f"Provider: {provider or 'unknown'}", f"Model: {model}", "Phase: ambient"]
    if mode:
        parts.append(f"Permission mode: {mode}")
    return "\n".join(parts)


async def complete(
    line: str, *, provider: ModelProvider, model: str, cwd: Path,
    history: EpisodicMemory, status: str, project_index_text: str = "",
    prior_context: dict | list | None = None,
) -> ProviderResponse:
    system = f"{SYSTEM}\n\nHarness state:\n{status}\nWorking directory: {cwd}"
    if project_index_text:
        system += f"\n\nProject summary:\n{project_index_text}"
    if history.summary:
        system += f"\n\nConversation summary:\n{history.summary}"
    prior = _compose_prior_context_block(prior_context)
    if prior:
        system += f"\n\n{prior}"
    messages = [{"role": "system", "content": system}]
    messages.extend(m for m in history.last(HISTORY_WINDOW) if m["role"] in ("user", "assistant"))
    messages.append({"role": "user", "content": line})
    history.add(line, role="user")
    response = await provider.complete(
        messages=messages, model=model, temperature=0.2, max_tokens=1200,
    )
    history.add(response.text, role="assistant")
    return response
