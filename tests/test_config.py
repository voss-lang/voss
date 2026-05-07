import threading

import pytest

from voss_runtime import RuntimeConfig, configure, get_config, reset_config


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    yield
    reset_config()


def test_defaults():
    cfg = get_config()
    assert cfg.default_model == "claude-sonnet-4-5"
    assert cfg.default_embedding_model == "text-embedding-3-small"
    assert cfg.local_embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert cfg.max_retries == 1
    assert cfg.match_threshold == 0.75
    assert cfg.cache_dir == ".voss-cache"
    assert cfg.timeout_seconds == 60.0


def test_single_key_override():
    configure(max_retries=5)
    cfg = get_config()
    assert cfg.max_retries == 5
    # Other defaults preserved.
    assert cfg.default_model == "claude-sonnet-4-5"
    assert cfg.match_threshold == 0.75


def test_multi_key_override():
    configure(max_retries=3, match_threshold=0.9, cache_dir="/tmp/voss")
    cfg = get_config()
    assert cfg.max_retries == 3
    assert cfg.match_threshold == 0.9
    assert cfg.cache_dir == "/tmp/voss"
    # Untouched defaults remain.
    assert cfg.default_model == "claude-sonnet-4-5"


def test_reset_config_restores_defaults():
    configure(max_retries=99, cache_dir="/elsewhere", timeout_seconds=1.0)
    reset_config()
    cfg = get_config()
    assert cfg == RuntimeConfig()


def test_threadsafe_replace():
    n = 32
    values = list(range(1, n + 1))
    errors: list[BaseException] = []

    def worker(v: int):
        try:
            configure(max_retries=v)
        except BaseException as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(v,)) for v in values]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    final = get_config().max_retries
    assert final in values
