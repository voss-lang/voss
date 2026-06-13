import os

from .base import ModelProvider, ProviderResponse
from .fallback import FallbackProvider, is_retryable_error
from .stub import StubProvider

_registry: dict[str, ModelProvider] = {}


def _default_provider() -> ModelProvider:
    provider = _registry.get("__default__")
    if provider is not None:
        return provider
    from .litellm_provider import LiteLLMProvider

    provider = LiteLLMProvider()
    _registry["__default__"] = provider
    return provider


def __getattr__(name: str):
    if name == "LiteLLMProvider":
        from .litellm_provider import LiteLLMProvider

        return LiteLLMProvider
    raise AttributeError(name)


def register(name: str, provider: ModelProvider) -> None:
    _registry[name] = provider


def has(name: str) -> bool:
    return name in _registry


def get(name: str | None = None) -> ModelProvider:
    # D-01: hermetic env → force stub unless caller asked for a registered name explicitly.
    if os.environ.get("VOSS_HERMETIC") == "1":
        if name is not None and name in _registry:
            return _registry[name]
        return _registry["__stub__"]
    from voss_runtime._config import get_config

    key = name or get_config().default_model
    if key in _registry:
        return _registry[key]
    return _default_provider()


register("__stub__", StubProvider())

__all__ = [
    "FallbackProvider",
    "LiteLLMProvider",
    "ModelProvider",
    "ProviderResponse",
    "StubProvider",
    "get",
    "has",
    "is_retryable_error",
    "register",
]
