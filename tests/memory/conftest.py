"""V23 retrieval-aware ranking: bridge tests/harness fixtures into tests/memory/.

Exposes ``tmp_voss_repo`` + ``chroma_disabled_env`` (defined only in
``tests/harness/conftest.py``) to test modules under ``tests/memory/`` without
redefining them — single source of truth stays in tests/harness/conftest.py.
"""

pytest_plugins = ["tests.harness.conftest"]
