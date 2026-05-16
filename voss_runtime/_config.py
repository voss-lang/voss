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
    max_output_tokens: int = 4096
    # T1-04: agent iteration-loop cap. Default 8 per SPEC ITER-01; overridable
    # via [agent] max_iterations in ~/.config/voss/config.toml. T1-05 reads
    # this field at loop entry; cli boot wires the TOML override via configure.
    max_iterations: int = 8
    # T2-02: parallel read-batch semaphore cap (PAR-05). Default 8, range 1-32;
    # overridable via [agent] max_parallel_reads in ~/.config/voss/config.toml.
    # T2-03 scheduler reads this field at batch dispatch; cli boot wires the
    # TOML override via configure alongside max_iterations.
    max_parallel_reads: int = 8


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
