import os
from dataclasses import dataclass, field, replace
from threading import Lock


@dataclass
class RuntimeConfig:
    default_model: str = "claude-sonnet-4-5"
    default_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_retries: int = 1
    match_threshold: float = 0.75
    cache_dir: str = ".voss-cache"
    timeout_seconds: float = 60.0


_config = RuntimeConfig()
_lock = Lock()


def get_config() -> RuntimeConfig:
    return _config


def configure(**kwargs) -> RuntimeConfig:
    global _config
    with _lock:
        _config = replace(_config, **kwargs)
    return _config


def reset_config() -> RuntimeConfig:
    global _config
    with _lock:
        _config = RuntimeConfig()
    return _config
