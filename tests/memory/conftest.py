"""V23 retrieval-aware ranking: bridge tests/harness fixtures into tests/memory/.

Exposes ``tmp_voss_repo`` + ``chroma_disabled_env`` (defined only in
``tests/harness/conftest.py``) to test modules under ``tests/memory/`` without
redefining them — single source of truth stays in tests/harness/conftest.py.
"""

# pytest 8.1+ forbids `pytest_plugins` in a non-top-level conftest; re-export
# the fixtures directly instead (single source of truth stays in tests/harness).
from tests.harness.conftest import (  # noqa: F401,E402  (re-exported fixtures)
    chroma_disabled_env,
    tmp_voss_repo,
)
