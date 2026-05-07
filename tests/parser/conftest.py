import pytest
from voss import parse as _parse

@pytest.fixture
def parse_source():
    def _impl(src: str, file: str = "<test>"):
        if not src.endswith("\n"):
            src = src + "\n"
        return _parse(src, file)
    return _impl
