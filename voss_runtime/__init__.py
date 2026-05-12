"""Voss runtime library — public API surface.

This package is what compiled ``.voss`` programs import at runtime. It is
also the **embedding API** for Python applications that want to use Voss
primitives (``ProbableValue``, ``ContextScope``, ``BudgetScope``,
``SemanticMatcher``, ``VossAgent``, memory classes, ``StubProvider``) without
going through the harness CLI.

**Public API contract:** Only names listed in ``__all__`` are part of the
stable public API. Anything reached via a submodule path
(``voss_runtime.providers.litellm_provider`` etc.) is private and may change
in any release. See ``docs/sdk.md`` for the full versioning contract.

Pre-1.0 (current track): breaking changes to ``__all__`` are allowed in
minor releases. Patch releases will not break the public surface.
"""

from voss_runtime._config import (
    RuntimeConfig,
    configure,
    get_config,
    reset_config,
)
from voss_runtime.budget import (
    BudgetScope,
    current_budget,
    run_with_budget,
)
from voss_runtime.exceptions import (
    BudgetExceededError,
    ConfidenceTooLowError,
    ParseError,
    ProviderError,
    VossRuntimeError,
)
from voss_runtime.agent import AgentHandle, VossAgent, gather
from voss_runtime.context import ContextScope
from voss_runtime.memory import EpisodicMemory, SemanticMemory, WorkingMemory
from voss_runtime.probable import ProbableValue
from voss_runtime.providers import (
    ModelProvider,
    ProviderResponse,
    StubProvider,
)
from voss_runtime.semantic import SemanticMatcher
from voss_runtime.tools import ToolDescriptor, tool

__version__ = "0.1.0"
__all__: list[str] = [
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
]
