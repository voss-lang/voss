from .base import ModelProvider, ProviderResponse
from .litellm_provider import LiteLLMProvider
from .stub import StubProvider

_registry: dict[str, ModelProvider] = {}


def register(name: str, provider: ModelProvider) -> None:
    _registry[name] = provider


def get(name: str | None = None) -> ModelProvider:
    from voss_runtime._config import get_config

    key = name or get_config().default_model
    if key in _registry:
        return _registry[key]
    return _registry.get("__default__", LiteLLMProvider())


register("__default__", LiteLLMProvider())
register("__stub__", StubProvider())

__all__ = [
    "LiteLLMProvider",
    "ModelProvider",
    "ProviderResponse",
    "StubProvider",
    "get",
    "register",
]
